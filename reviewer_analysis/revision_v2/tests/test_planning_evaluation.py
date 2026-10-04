import importlib
import json
from pathlib import Path

import pytest

from reviewer_analysis.revision_v2.common import digest, write_json


@pytest.fixture
def api():
    return importlib.import_module('reviewer_analysis.revision_v2.planning_evaluation')


def sources(tmp_path):
    experiment, reference = tmp_path/'experiment', tmp_path/'reference'
    experiment.mkdir(); reference.mkdir()
    jobs, cards, templates = [], {}, []
    for i in range(61, 81):
        qid, question = f'Q{i}', f'Who qualifies for {i}?'
        targets = [{'id': 'r1', 'label': 'A'}]
        cards[qid] = {'question': question, 'targets': targets, 'notes': 'Fixed units.',
                      'original_reference_sha256': digest('A qualifies.')}
        templates.append({'key': [qid], 'payload': {'question': question,
            'reference_targets': targets, 'original_reference': 'A qualifies.',
            'counting_notes': 'Fixed units.', 'predicted_units': [{'id': 'OLD_PREDICTION_DO_NOT_REUSE'}]},
            'source_map': {'OLD_METHOD': {}}})
        for method in ('full', 'uniform'):
            for repeat in (1, 2):
                key = f'formal/{repeat:02d}/{qid}/{method}'
                job = {'phase': 'formal', 'query_id': qid, 'question': question,
                       'method': method, 'repeat': repeat, 'run_key': key}
                jobs.append(job)
                path = experiment/key; path.mkdir(parents=True)
                write_json(path/'status.json', {'status': 'complete'})
                write_json(path/'native_output.json', {'query': question, 'report': 'A qualifies.',
                    'knowledge_graph': {'nodes': {'n1': {}}, 'edges': {'e1': {}}},
                    'calls': {'calls_used': 5, 'calls_failed': 0, 'input_tokens': 100,
                              'output_tokens': 20, 'unknown_usage_attempts': 0, 'inflight': 0},
                    'retrieval': {'requests': {'search': 2, 'page': 3}},
                    'native_failure_flags': [], 'control_issues': [], 'termination': 'iteration_limit'})
    write_json(experiment/'formal_schedule.json', jobs)
    write_json(reference/'reference_cards.json', cards)
    write_json(reference/'match_tasks.json', templates)
    write_json(reference/'freeze_manifest.json', {'protocol': 'blind_direct_answers_v4',
        'cards_sha256': digest(cards), 'reference_only_epistemic_questions': ['Q63'],
        'reference_independent_provenance_verified': False})
    return experiment, reference


class Judge:
    public_config = {'requested_model': 'gpt-5.5', 'reasoning_effort': 'medium'}

    def __init__(self, invalid=False):
        self.calls = 0
        self.invalid = invalid
        self.payloads = []

    def chat(self, prompt, payload):
        self.calls += 1
        self.payloads.append(payload)
        if self.invalid:
            result = {}
        elif 'reports' in payload:
            result = {'reports': [{'source_id': r['source_id'], 'answers': [{'label': 'A',
                'claim': 'A qualifies.', 'status': 'actual', 'quotes': ['A qualifies.']}],
                'excluded': []} for r in payload['reports']]}
        elif 'groups' in payload:
            result = {'groups': [{'source_id': g['source_id'], 'units': [{'label': u['label'],
                'claim': u['claim'], 'status': u['status'], 'input_ids': [u['id']]}
                for u in g['units']]} for g in payload['groups']]}
        else:
            result = {'candidates': [{'predicted_id': u['id'], 'reference_id': 'r1',
                                     'reason': 'Same explicit answer.'} for u in payload['predicted_units']],
                      'unmatched': []}
        return json.dumps(result), {'input_tokens': 10, 'output_tokens': 5}, None


def test_new_reports_only_blind_pipeline_keeps_failed_run_and_separate_usage(api, tmp_path):
    experiment, reference = sources(tmp_path)
    failed = experiment/'formal/01/Q61/full'
    (failed/'native_output.json').unlink()
    write_json(failed/'status.json', {'status': 'timeout'})
    out = tmp_path/'evaluation'
    api.prepare(experiment, out, reference_source=reference)
    assert 'OLD_PREDICTION' not in (out/'references.json').read_text()
    judge = Judge()
    api.run_evaluation(out, execute=True, client=judge, workers=1, n_boot=100)
    assert judge.calls == 119
    api.run_evaluation(out, execute=True, client=judge, workers=1, n_boot=100)
    assert judge.calls == 119
    result = json.loads((out/'summary.json').read_text())
    assert result['n_executions'] == 80
    assert result['methods']['full']['answer_f1'] == pytest.approx(39/40)
    assert result['methods']['uniform']['answer_f1'] == 1
    assert result['evaluation_usage']['calls'] == 119
    assert result['resources']['full']['actual_input_tokens_total'] is None
    assert result['resources']['full']['known_input_tokens_total'] == 3900
    rows = json.loads((out/'per_execution.json').read_text())
    row = next(r for r in rows if r['query_id']=='Q61' and r['method']=='full' and r['repeat']==1)
    assert row['status'] == 'no_answer' and row['worker_status'] == 'timeout'
    assert row['answer_f1'] == 0 and row['agent_calls'] is None
    assert 'legacy_composite' not in row
    assert result['protocol_caveats']['reference_only_epistemic_questions'] == ['Q63']
    for payload in judge.payloads:
        if 'reports' in payload or 'groups' in payload:
            assert 'reference_targets' not in payload
            assert not any(k in json.dumps(payload) for k in ('"method"', '"run_id"'))
        if 'groups' in payload:
            assert len(payload['groups']) == 4
    assert (out/'per_query.csv').exists() and (out/'per_execution.csv').exists()


def test_dry_run_never_calls_judge_and_frozen_input_drift_is_rejected(api, tmp_path):
    experiment, reference = sources(tmp_path)
    out = tmp_path/'evaluation'
    api.prepare(experiment, out, reference_source=reference)
    judge = Judge()
    assert api.run_evaluation(out, execute=False, client=judge)['execute'] is False
    assert judge.calls == 0
    path = experiment/'formal/01/Q61/full/native_output.json'
    value = json.loads(path.read_text()); value['report'] = 'Changed.'; write_json(path, value)
    with pytest.raises(ValueError, match='changed'):
        api.run_evaluation(out, execute=True, client=judge)
    assert judge.calls == 0


def test_validation_failure_is_retained_and_never_silently_scored_or_retried(api, tmp_path):
    experiment, reference = sources(tmp_path)
    out = tmp_path/'evaluation'
    api.prepare(experiment, out, reference_source=reference)
    judge = Judge(invalid=True)
    api.run_model_stage(out, 'extract', execute=True, client=judge, workers=1)
    api.run_model_stage(out, 'extract', execute=True, client=judge, workers=1)
    assert judge.calls == 80
    with pytest.raises(ValueError, match='successful'):
        api.run_model_stage(out, 'normalize', execute=True, client=judge)
    assert len(list((out/'extract/items').glob('*.json'))) == 80
    item = json.loads(next((out/'extract/items').glob('*.json')).read_text())
    assert item['raw_response'] == '{}' and item['error_kind'] == 'content_validation'


@pytest.mark.parametrize('mutation', ['pilot', 'duplicate', 'running'])
def test_exact_formal_population_and_terminal_status_are_required(api, tmp_path, mutation):
    experiment, reference = sources(tmp_path)
    path = experiment/'formal_schedule.json'
    jobs = json.loads(path.read_text())
    if mutation == 'pilot': jobs[0]['phase'] = 'pilot'
    elif mutation == 'duplicate': jobs[-1] = jobs[0]
    else: write_json(experiment/jobs[0]['run_key']/'status.json', {'status': 'running'})
    write_json(path, jobs)
    with pytest.raises(ValueError):
        api.prepare(experiment, tmp_path/'evaluation', reference_source=reference)


def test_partial_usage_is_not_reported_as_measured_total(api):
    got = api.resource_fields({'calls': {'calls_used': 3, 'input_tokens': 7, 'output_tokens': 2,
        'unknown_usage_attempts': 1, 'inflight': 0}, 'retrieval': {'requests': {'search': 2, 'page': 4}}})
    assert got['agent_calls'] == 3
    assert got['actual_input_tokens'] is None and got['known_input_tokens'] == 7
    assert got['unknown_usage_attempts'] == 1 and got['search_requests'] == 2
