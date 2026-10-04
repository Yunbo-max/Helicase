"""Frozen reference-blind answer evaluation of 80 NEW formal planning runs.

Only fixed reference fields are reused from the historical evaluation. All new
predictions are extracted from whole reports, normalized anonymously, and matched
afresh. Agent resources and evaluator CLI usage are reported separately.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import statistics

from . import answer_blind as protocol
from .answer_batch import run_stage
from .codex_client import CodexClient
from .common import digest, file_hash, utcnow, write_json
from .judging import parse_object
from .planning_statistics import analyse_repeats


DEFAULT_REFERENCE_SOURCE = Path('/Users/yunbo/Documents/GitHub/Data_provider/Helicase/'
    'reviewer_analysis/revision_v2/private/complementary_eval_v1/answer_blind_scpqa_v1')
QUERIES = tuple(f'Q{i}' for i in range(61, 81))
METHODS = ('full', 'uniform')
STAGES = {'extract': (protocol.EXTRACT_PROMPT, protocol.extract_transform),
          'normalize': (protocol.NORMALIZE_PROMPT, protocol.normalize_transform),
          'match': (protocol.MATCH_PROMPT, protocol.match_transform)}
REFERENCE_FIELDS = ('question', 'original_reference', 'reference_targets', 'counting_notes')


def _read(path):
    return json.loads(Path(path).read_text())


def _helpers():
    names = ('planning_evaluation.py', 'planning_statistics.py', 'answer_blind.py',
             'answer_batch.py', 'answer_units.py', 'codex_client.py', 'common.py', 'judging.py')
    return {name: file_hash(Path(__file__).with_name(name)) for name in names}


def _count(value):
    return value if type(value) is int and value >= 0 else None


def resource_fields(record):
    """Unknown token totals stay null; measured subtotals remain available."""
    calls, retrieval = record.get('calls') or {}, record.get('retrieval') or {}
    requests = retrieval.get('requests') or {}
    unknown = _count(calls.get('unknown_usage_attempts', calls.get('unknown_usage_calls')))
    inflight = _count(calls.get('inflight'))
    known = calls.get('known_usage') or {}
    input_tokens = _count(calls.get('input_tokens', known.get('input_tokens')))
    output_tokens = _count(calls.get('output_tokens', known.get('output_tokens')))
    complete = unknown == 0 and inflight == 0
    return {'agent_calls': _count(calls.get('calls_used', calls.get('calls_reserved'))),
            'agent_failed_calls': _count(calls.get('calls_failed')),
            'actual_input_tokens': input_tokens if complete else None,
            'actual_output_tokens': output_tokens if complete else None,
            'known_input_tokens': input_tokens, 'known_output_tokens': output_tokens,
            'unknown_usage_attempts': unknown, 'agent_inflight_calls': inflight,
            'search_requests': _count(requests.get('search')),
            'page_requests': _count(requests.get('page'))}


def _retrieval_from_journal(path):
    """Recover actual reservations from an interrupted worker's durable journal."""
    counts = {'search': 0, 'page': 0}
    seen = set()
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get('event') == 'request_reserved':
            if row['ticket'] in seen or row['kind'] not in counts:
                raise ValueError('Invalid retrieval journal')
            seen.add(row['ticket']); counts[row['kind']] += 1
    return {'requests': counts}


def _load_records(experiment):
    expected = {(q, m, r) for q in QUERIES for m in METHODS for r in (1, 2)}
    jobs = _read(experiment/'formal_schedule.json')
    seen, records = set(), []
    inputs = {str(experiment/'formal_schedule.json'): file_hash(experiment/'formal_schedule.json')}
    terminal = {'complete', 'partial', 'failed', 'timeout', 'interrupted', 'no_answer', 'budget_exhausted'}
    for job in jobs:
        key = (job.get('query_id'), job.get('method'), job.get('repeat'))
        if (job.get('phase') != 'formal' or type(job.get('repeat')) is not int
                or key not in expected or key in seen):
            raise ValueError('Require exactly 80 unique formal executions; no pilots')
        seen.add(key)
        expected_key = f"formal/{job['repeat']:02d}/{job['query_id']}/{job['method']}"
        if job['run_key'] != expected_key:
            raise ValueError('Unexpected execution directory identity')
        directory = experiment/expected_key
        for name in ('native_output.json', 'status.json', 'calls.json', 'retrieval.jsonl'):
            path = directory/name
            inputs[str(path)] = file_hash(path) if path.exists() else None
        if not (directory/'status.json').is_file():
            raise ValueError('All 80 executions must have terminal status records')
        status = _read(directory/'status.json')['status']
        if status not in terminal:
            raise ValueError(f'Execution is not terminal: {expected_key}')
        native = _read(directory/'native_output.json') if (directory/'native_output.json').exists() else {}
        report = native.get('report', '')
        if not isinstance(report, str):
            raise ValueError('Report must be a string')
        if not report.strip() and status == 'complete':
            raise ValueError('Complete execution cannot have a missing report')
        if native.get('query', job['question']) != job['question']:
            raise ValueError('Report question differs from schedule')
        if not native.get('calls') and (directory/'calls.json').exists():
            native['calls'] = _read(directory/'calls.json')
        if not native.get('retrieval') and (directory/'retrieval.jsonl').exists():
            native['retrieval'] = _retrieval_from_journal(directory/'retrieval.jsonl')
        graph = native.get('knowledge_graph') or {}
        records.append(dict(job, run_id=expected_key, report=report,
            no_answer=not bool(report.strip()), worker_status=status,
            native_counts=[len(graph.get('nodes') or {}), len(graph.get('edges') or {})],
            native_failure_flags=native.get('native_failure_flags') or [],
            control_issue_count=len(native.get('control_issues') or []),
            termination=native.get('termination'), resources=resource_fields(native)))
    if seen != expected:
        raise ValueError('All 80 formal executions, including failed jobs, are required')
    return sorted(records, key=lambda r: (r['query_id'], r['method'], r['repeat'])), inputs


def _load_references(source):
    cards, templates, manifest = (_read(source/name) for name in
        ('reference_cards.json', 'match_tasks.json', 'freeze_manifest.json'))
    if manifest.get('protocol') != protocol.VERSION or set(cards) != set(QUERIES):
        raise ValueError('Require frozen blind_direct_answers_v4 Q61–Q80 references')
    if manifest.get('cards_sha256') != digest(cards):
        raise ValueError('Reference cards differ from their frozen manifest')
    references = {}
    for task in templates:
        qid = task['key'][0]
        if qid not in cards or qid in references:
            raise ValueError('Invalid reference task identities')
        # Do not retain historical predictions, source identities or match decisions.
        reference = {k: task['payload'][k] for k in REFERENCE_FIELDS}
        card = cards[qid]
        if (reference['reference_targets'] != card['targets']
                or reference['question'] != card['question']
                or reference['counting_notes'] != card['notes']
                or digest(reference['original_reference']) != card['original_reference_sha256']):
            raise ValueError('Reference template disagrees with frozen card')
        references[qid] = reference
    if set(references) != set(QUERIES):
        raise ValueError('All 20 fixed reference templates are required')
    return references, cards, manifest


def prepare(experiment, out, *, reference_source=DEFAULT_REFERENCE_SOURCE):
    experiment, out, source = Path(experiment).resolve(), Path(out).resolve(), Path(reference_source).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Evaluation directory must be new; never overwrite a freeze')
    records, inputs = _load_records(experiment)
    references, cards, source_manifest = _load_references(source)
    if any(r['question'] != references[r['query_id']]['question'] for r in records):
        raise ValueError('New questions differ from the fixed reference questions')
    out.mkdir(parents=True, exist_ok=True)
    write_json(out/'records.json', records)
    write_json(out/'references.json', references)
    write_json(out/'reference_cards.json', cards)
    prompts = {}
    for stage, (prompt, _) in STAGES.items():
        path = out/(stage+'_prompt.txt'); path.write_text(prompt)
        prompts[path.name] = file_hash(path)
    caveats = {
        'reference_only_epistemic_questions': source_manifest.get('reference_only_epistemic_questions', []),
        'reference_independent_provenance_verified': source_manifest.get('reference_independent_provenance_verified', False),
        'scope': 'Approximate reference agreement using frozen blind_direct_answers_v4, not world factuality. '
                 'The unchanged extraction protocol excludes epistemic admissions while some fixed references '
                 'are epistemic answers; this asymmetry is retained, including those questions. '
                 'Reference-absent answers are unmatched, not proven false. No historical predictions or scores are reused.',
        'reported_metric': 'Answer precision/recall/F1 only; legacy structural composites are audit output only.'}
    freeze = {'created_at': utcnow(), 'protocol': protocol.VERSION, 'model': 'gpt-5.5',
        'reasoning_effort': 'medium', 'experiment': str(experiment),
        'input_files': inputs, 'reference_source': str(source),
        'reference_source_hashes': {name: file_hash(source/name) for name in
            ('reference_cards.json', 'match_tasks.json', 'freeze_manifest.json')},
        'helper_hashes': _helpers(), 'protocol_caveats': caveats,
        'frozen_files': dict(prompts, **{name: file_hash(out/name) for name in
            ('records.json', 'references.json', 'reference_cards.json')})}
    write_json(out/'evaluation_freeze.json', freeze)
    return {'executions': 80, 'questions': 20, 'no_answer': sum(r['no_answer'] for r in records),
            'execute': False, 'freeze_sha256': file_hash(out/'evaluation_freeze.json')}


def _verify(out):
    freeze = _read(out/'evaluation_freeze.json')
    if freeze['helper_hashes'] != _helpers():
        raise ValueError('Evaluation helper code changed after freeze')
    for name, wanted in freeze['frozen_files'].items():
        if file_hash(out/name) != wanted:
            raise ValueError('Frozen evaluation input changed')
    for name, wanted in freeze['input_files'].items():
        path = Path(name)
        if (file_hash(path) if path.exists() else None) != wanted:
            raise ValueError('Original experiment input changed after evaluation freeze')
    source = Path(freeze['reference_source'])
    for name, wanted in freeze['reference_source_hashes'].items():
        if file_hash(source/name) != wanted:
            raise ValueError('Original reference source changed after evaluation freeze')
    return freeze


def _successful_results(out, stage, tasks):
    results = []
    transform = STAGES[stage][1]
    for task in tasks:
        path = out/stage/'items'/(digest(task)[:24]+'.json')
        if not path.exists():
            raise ValueError(f'{stage} requires successful results for every task')
        row = _read(path)
        if row.get('task') != task or 'result' not in row:
            raise ValueError(f'{stage} requires successful results; failures remain retained')
        result = transform(parse_object(row['raw_response']), task)
        if result != row['result']:
            raise ValueError(f'{stage} cached result failed revalidation')
        results.append(result)
    return results


def build_tasks(out, stage):
    out = Path(out)
    records = _read(out/'records.json')
    extraction = [protocol.extraction_task([r]) for r in records if not r['no_answer']]
    if stage == 'extract':
        return extraction
    groups = [group for row in _successful_results(out, 'extract', extraction) for group in row['groups']]
    for record in records:
        if record['no_answer']:
            task = protocol.extraction_task([record])
            sid = next(iter(task['source_map']))
            groups.append(dict(task['source_map'][sid], source_id=sid, units=[], excluded=[],
                               report_sha256=digest(record['report']), no_answer=True))
    normalization = []
    for qid in QUERIES:
        selected = sorted((g for g in groups if g['query_id'] == qid), key=lambda g: g['source_id'])
        if len(selected) != 4 or len({g['source_id'] for g in selected}) != 4:
            raise ValueError('Exactly four anonymous sources per question required')
        public = [{'source_id': g['source_id'], 'units': [{k: u[k] for k in
                   ('id', 'label', 'claim', 'status', 'quotes')} for u in g['units']]} for g in selected]
        question = next(r['question'] for r in records if r['query_id'] == qid)
        normalization.append({'key': [qid], 'payload': {'question': question, 'groups': public},
                              'groups': selected, 'version': protocol.VERSION})
    if stage == 'normalize':
        return normalization
    if stage != 'match':
        raise ValueError('Unknown evaluation stage')
    normalized = _successful_results(out, 'normalize', normalization)
    references = _read(out/'references.json')
    record_map = {(r['method'], r['query_id'], r['run_id']): r for r in records}
    tasks = []
    for task, row in zip(normalization, normalized):
        qid = task['key'][0]
        public, mapping = [], {}
        for group in row['groups']:
            record = record_map[group['method'], group['query_id'], group['run_id']]
            public.extend({k: u[k] for k in ('id', 'label', 'claim', 'status', 'quotes')} for u in group['units'])
            mapping[group['source_id']] = {'method': group['method'], 'run_id': group['run_id'],
                'ids': [u['id'] for u in group['units']], 'native_counts': record['native_counts']}
        tasks.append({'key': [qid], 'payload': dict(references[qid], predicted_units=public),
                      'source_map': mapping, 'version': protocol.VERSION})
    return tasks


def run_model_stage(out, stage, *, execute=False, client=None, workers=4):
    out = Path(out); _verify(out)
    tasks = build_tasks(out, stage)
    if not execute:
        return {'stage': stage, 'tasks': len(tasks), 'execute': False}
    client = client if client is not None else CodexClient(out/stage/'calls', model='gpt-5.5')
    if client.public_config.get('requested_model') != 'gpt-5.5':
        raise ValueError('Frozen evaluation requires gpt-5.5')
    prompt, transform = STAGES[stage]
    return run_stage(tasks, out/stage, prompt, transform, client=client, workers=workers)


def _sum_complete(rows, field):
    values = [r.get(field) for r in rows]
    return sum(values) if all(v is not None for v in values) else None


def _resource_summary(rows):
    result = {'executions': len(rows)}
    for field in ('agent_calls', 'actual_input_tokens', 'actual_output_tokens', 'search_requests', 'page_requests'):
        total = _sum_complete(rows, field)
        result[field+'_total'] = total
        result[field+'_mean_per_execution'] = total/len(rows) if total is not None else None
        result[field+'_known_executions'] = sum(r.get(field) is not None for r in rows)
    for field in ('known_input_tokens', 'known_output_tokens'):
        result[field+'_total'] = sum(r[field] for r in rows if r.get(field) is not None)
        result[field+'_known_executions'] = sum(r.get(field) is not None for r in rows)
    result['known_unknown_usage_attempts'] = sum(r['unknown_usage_attempts'] for r in rows
                                                if r.get('unknown_usage_attempts') is not None)
    result['unknown_usage_metadata_executions'] = sum(r.get('unknown_usage_attempts') is None for r in rows)
    return result


def evaluation_usage(out):
    rows = [_read(path) for stage in STAGES for path in sorted((out/stage/'items').glob('*.json'))]
    known_input, known_output, unknown = 0, 0, 0
    for row in rows:
        usage = row.get('usage') or {}
        i, o = _count(usage.get('input_tokens')), _count(usage.get('output_tokens'))
        if i is None or o is None:
            unknown += 1
        else:
            known_input += i; known_output += o
    return {'calls': sum(row.get('api_calls', 0) for row in rows),
            'known_input_tokens': known_input, 'known_output_tokens': known_output,
            'actual_input_tokens': known_input if not unknown else None,
            'actual_output_tokens': known_output if not unknown else None,
            'unknown_usage_calls': unknown, 'failed_tasks': sum('error' in r for r in rows),
            'separate_from_agent_usage': True,
            'cap_unit': 'Evaluator CLI invocation attempts, not independently measured HTTP requests'}


def _csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def collect(out, *, n_boot=10000, seed=20261004):
    out = Path(out); freeze = _verify(out)
    tasks = build_tasks(out, 'match')
    matched = _successful_results(out, 'match', tasks)
    scores = {}
    for result in matched:
        for score in result['scores']:
            key = (score['method'], score['query_id'], score['run_id'])
            if key in scores:
                raise ValueError('Duplicate evaluated execution')
            scores[key] = score
    rows = []
    for record in _read(out/'records.json'):
        score = scores[record['method'], record['query_id'], record['run_id']]
        if record['no_answer']:
            status = 'no_answer'
        elif record['worker_status'] in ('timeout', 'interrupted', 'failed'):
            status = 'failed'
        else:
            status = record['worker_status']
        rows.append({k: record[k] for k in ('phase', 'query_id', 'method', 'repeat', 'run_id')} |
            {k: score[k] for k in ('answer_precision', 'answer_recall', 'answer_f1',
                                   'n_pred_units', 'n_reference_units', 'matched_units')} |
            record['resources'] | {'status': status, 'worker_status': record['worker_status'],
                'native_failure_count': len(record['native_failure_flags']),
                'native_failure_flags': json.dumps(record['native_failure_flags']),
                'control_issue_count': record['control_issue_count'], 'termination': record['termination'],
                'matched_token_budget': False})
    summary = analyse_repeats(rows, n_boot=n_boot, seed=seed)
    summary['resources'] = {method: _resource_summary([r for r in rows if r['method'] == method])
                            for method in METHODS}
    summary['evaluation_usage'] = evaluation_usage(out)
    summary['protocol_caveats'] = freeze['protocol_caveats']
    summary['evaluation_freeze_sha256'] = file_hash(out/'evaluation_freeze.json')
    for query in summary['per_query']:
        for method in METHODS:
            pair = [r for r in rows if r['query_id'] == query['query_id'] and r['method'] == method]
            for field in ('answer_precision', 'answer_recall', 'actual_input_tokens', 'actual_output_tokens',
                          'agent_calls', 'search_requests', 'page_requests'):
                total = _sum_complete(pair, field)
                query[method+'_'+field] = total/2 if total is not None else None
            query[method+'_no_answer_count'] = sum(r['status'] == 'no_answer' for r in pair)
    write_json(out/'per_execution.json', rows)
    write_json(out/'summary.json', summary)
    _csv(out/'per_execution.csv', rows); _csv(out/'per_query.csv', summary['per_query'])
    table = ['| Method (40 executions) | Precision | Recall | F1 | Input tokens/run | Output tokens/run | Model calls/run | Searches/run | Pages/run |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for method in METHODS:
        metrics, resources = summary['methods'][method], summary['resources'][method]
        values = [f'{metrics[k]:.4f}' for k in ('answer_precision', 'answer_recall', 'answer_f1')]
        for field in ('actual_input_tokens', 'actual_output_tokens', 'agent_calls', 'search_requests', 'page_requests'):
            value = resources[field+'_mean_per_execution']
            values.append(f'{value:.2f}' if value is not None else
                          f'unknown ({resources[field+"_known_executions"]}/40 measured)')
        table.append('| '+method+' | '+' | '.join(values)+' |')
    table.extend(['', f'Full − uniform F1: {summary["f1_difference"]:.4f}; paired 95% query-bootstrap CI '
                  f'[{summary["paired_95ci"][0]:.4f}, {summary["paired_95ci"][1]:.4f}].', '',
                  'Unknown usage is not zero. Known token subtotals and evaluation-only usage are in summary.json. '
                  'Tokens are measured only, not matched. Two repeats are averaged within each of 20 questions.', '',
                  freeze['protocol_caveats']['scope']])
    (out/'summary_table.md').write_text('\n'.join(table)+'\n')
    return summary


def run_evaluation(out, *, execute=False, client=None, workers=4, n_boot=10000):
    out = Path(out); _verify(out)
    if not execute:
        return {'execute': False, 'extract_tasks': len(build_tasks(out, 'extract')),
                'normalize_tasks': 20, 'match_tasks': 20, 'executions': 80}
    for stage in STAGES:
        progress = run_model_stage(out, stage, execute=True, client=client, workers=workers)
        if progress['failed'] or progress['pending']:
            raise ValueError(f'{stage} requires successful validated results before continuing')
    return collect(out, n_boot=n_boot)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'extract', 'normalize', 'match', 'collect', 'execute'))
    parser.add_argument('--out', required=True)
    parser.add_argument('--experiment')
    parser.add_argument('--reference-source', default=str(DEFAULT_REFERENCE_SOURCE))
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--n-boot', type=int, default=10000)
    args = parser.parse_args()
    if args.command == 'prepare':
        if not args.experiment:
            parser.error('prepare requires --experiment')
        result = prepare(args.experiment, args.out, reference_source=args.reference_source)
    elif args.command == 'collect':
        result = collect(args.out, n_boot=args.n_boot)
    elif args.command == 'execute':
        result = run_evaluation(args.out, execute=args.execute, workers=args.workers, n_boot=args.n_boot)
    else:
        result = run_model_stage(args.out, args.command, execute=args.execute, workers=args.workers)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
