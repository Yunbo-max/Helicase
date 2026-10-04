"""Isolated two-arm Q4 jobs; invocation/tool caps, measured-only token usage."""
from __future__ import annotations

import argparse
import fcntl
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from .common import digest, file_hash, redact, utcnow, write_json
from .planning_control import make_schedule
from .runner import source_fingerprint, stop_child

PILOT_CAPS = {'model_calls': 96, 'search_requests': 36, 'page_requests': 60,
              'final_calls': 1, 'max_iterations': 3, 'fixed_n': 2}


def load_questions(path):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    result = [{'query_id': f"Q{int(str(r.get('id', r.get('query_id'))).removeprefix('Q'))}",
               'question': r['question'], 'quadrant': 'Q4'}
              for r in rows if r.get('quadrant') == 'Q4']
    make_schedule(result, seed=20261004)  # exact fixed-20 coverage validation
    return result


def derive_formal_caps(rows):
    expected = {(q, m) for q in ('Q61', 'Q73') for m in ('full', 'uniform')}
    keys = [(r.get('query_id'), r.get('method')) for r in rows if r.get('phase') == 'pilot']
    if len(rows) != 4 or len(keys) != 4 or set(keys) != expected:
        raise ValueError('All four technical pilots are required')
    def cap(values, minimum):
        if any(type(v) is not int or v < 0 for v in values):
            raise ValueError('Nonnegative measured resource counts required')
        return max(minimum, 5*math.ceil(1.25*max(values)/5))
    return {'model_calls': cap([r['calls']['calls_used'] for r in rows], 20),
            'search_requests': cap([r['retrieval']['requests']['search'] for r in rows], 5),
            'page_requests': cap([r['retrieval']['requests']['page'] for r in rows], 5),
            'final_calls': 1, 'max_iterations': 3, 'fixed_n': 2}


def pending_jobs(out, jobs):
    return [j for j in jobs if not (Path(out)/j['run_key']/'status.json').exists()]


def _implementation_hashes():
    root = Path(__file__).parent
    paths = set(root.glob('planning_*.py')) | {root/name for name in ('common.py', 'codex_client.py', 'runner.py')}
    return {p.name: file_hash(p) for p in sorted(paths)}


def systemic_failure(result, status):
    return (status in ('failed', 'timeout', 'no_answer')
            or bool(result.get('control_issues'))
            or bool(result.get('calls', {}).get('calls_failed'))
            or bool(result.get('retrieval', {}).get('violation')))


def validate_job_identity(out, freeze, job):
    questions = json.loads((Path(out)/'questions.json').read_text())
    if digest(questions) != freeze['questions_sha256'] or job.get('phase') not in ('pilot', 'formal'):
        raise ValueError('Frozen questions or execution phase mismatch')
    schedule = make_schedule(questions, seed=freeze['seed'], pilot=job['phase'] == 'pilot')
    expected = next((r for r in schedule if r['run_key'] == job.get('run_key')), None)
    if expected is None or any(job.get(k) != v for k, v in expected.items()):
        raise ValueError('Worker identity/question/seed differs from frozen schedule')


def prepare(out, dataset, runtime_root, backend_root, *, seed=20261004):
    out = Path(out).resolve()
    if (out/'freeze.json').exists():
        raise ValueError('Existing frozen experiment: do not overwrite; use a new directory')
    questions = load_questions(dataset)
    out.mkdir(parents=True, exist_ok=True)
    snapshots = out/'runtime_sources'
    for name, root in (('helicase', Path(runtime_root)/'helicase'),
                       ('helix_core', Path(backend_root)/'helix_core')):
        if not (root/'__init__.py').is_file():
            raise ValueError(f'Missing native source package: {name}')
        shutil.copytree(root, snapshots/name,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store', '.env*', '.git'))
    native_hashes = source_fingerprint([snapshots/'helicase', snapshots/'helix_core'])
    freeze = {'created_at': utcnow(), 'reference_file_sha256': file_hash(dataset),
              'questions_sha256': digest(questions), 'seed': seed,
              'native_files': native_hashes, 'implementation_files': _implementation_hashes(),
              'model': 'gpt-5.5', 'reasoning_effort': 'medium',
              'token_policy': 'measured_only', 'matched_token_budget': False,
              'cap_unit': 'CLI invocations and actual retrieval HTTP attempts',
              'pilot_caps': PILOT_CAPS,
              'formal_cap_rule': 'ceil_to_5(1.25 * maximum observed across four pilots); '
                                 'minimum 20 model calls, 5 searches, 5 page attempts',
              'fixed_n': 2, 'max_iterations': 3, 'search_max_results': 5,
              'reader_max_workers': 4, 'prefilter_max_workers': 2,
              'playwright_page_fallback': False, 'page_ocr': False,
              'stop_rule': 'iteration cap OR any resource allowance reached OR no valid '
                           'candidate; errors are recorded distinctly',
              'protocol_label': 'controlled planning comparison, not full-default component ablation'}
    write_json(out/'questions.json', questions)
    write_json(out/'pilot_schedule.json', make_schedule(questions, seed=seed, pilot=True))
    write_json(out/'formal_schedule.json', make_schedule(questions, seed=seed))
    write_json(out/'freeze.json', freeze)
    return freeze


def freeze_formal(out):
    out = Path(out)
    rows = []
    for job in json.loads((out/'pilot_schedule.json').read_text()):
        directory = out/job['run_key']
        row = json.loads((directory/'native_output.json').read_text())
        # Predeclare functional gates; no scoring/ranking is read here.
        if (not row.get('report', '').strip() or not row.get('ref2url')
                or not row.get('knowledge_graph', {}).get('edges')
                or row['calls']['calls_failed'] or row.get('control_issues')
                or row.get('native_failure_flags')
                or row['retrieval']['violation']):
            raise ValueError(f'Pilot requires functional review before formal freeze: {job["run_key"]}')
        rows.append(dict(row, phase='pilot', query_id=job['query_id'], method=job['method']))
    config = {'created_at': utcnow(), 'caps': derive_formal_caps(rows),
              'pilot_outputs': {j['run_key']: file_hash(out/j['run_key']/'native_output.json')
                                for j in json.loads((out/'pilot_schedule.json').read_text())},
              'freeze_sha256': file_hash(out/'freeze.json'),
              'no_evaluation_scores_used': True}
    path = out/'formal_config.json'
    if path.exists():
        raise ValueError('Formal caps already frozen')
    write_json(path, config)
    return config


def batch(out, phase, *, max_jobs=80, wall_seconds=7200):
    out = Path(out).resolve()
    with (out/'batch.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _batch(out, phase, max_jobs=max_jobs, wall_seconds=wall_seconds)


def _batch(out, phase, *, max_jobs, wall_seconds):
    if phase not in ('pilot', 'formal') or max_jobs < 1 or wall_seconds < 1:
        raise ValueError('Valid phase and positive job/time caps required')
    out = Path(out).resolve()
    freeze = json.loads((out/'freeze.json').read_text())
    if freeze['implementation_files'] != _implementation_hashes():
        raise ValueError('Implementation changed after freeze; make a new version')
    if source_fingerprint([out/'runtime_sources/helicase', out/'runtime_sources/helix_core']) != freeze['native_files']:
        raise ValueError('Native sources changed after freeze')
    caps = freeze['pilot_caps'] if phase == 'pilot' else json.loads((out/'formal_config.json').read_text())['caps']
    schedule = json.loads((out/f'{phase}_schedule.json').read_text())
    launched = 0
    for job in pending_jobs(out, schedule):
        if launched >= max_jobs:
            break
        directory = out/job['run_key']
        directory.mkdir(parents=True, exist_ok=False)
        payload = dict(job, caps=caps, output_dir=str(directory), experiment_dir=str(out))
        write_json(directory/'job.json', payload)
        write_json(directory/'status.json', {'status': 'running', 'started_at': utcnow()})
        launched += 1
        print(json.dumps({'event': 'started', 'run_key': job['run_key'], 'time': utcnow()}), flush=True)
        env = dict(os.environ, PYTHONHASHSEED=str(job['seed']), ENABLE_PAGE_OCR='false',
                   NEO4J_ENABLED='false', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                   READER_MAX_WORKERS='4', PREFILTER_MAX_WORKERS='2', SEARCH_MAX_RESULTS='5',
                   SEARCH_ENGINE='serper', MPLCONFIGDIR=str(out/'matplotlib_cache'))
        argv = [sys.executable, '-m', 'reviewer_analysis.revision_v2.planning_run',
                'worker', '--job', str(directory/'job.json')]
        started = time.monotonic()
        process = None
        status = 'failed'
        result = {}
        try:
            process = subprocess.Popen(argv, env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, start_new_session=True)
            try:
                output, _ = process.communicate(timeout=wall_seconds)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                output, _ = process.communicate()
                status = 'timeout'
            (directory/'worker.log').write_text(redact(output or ''), encoding='utf8')
            if process.returncode == 0 and (directory/'native_output.json').exists():
                result = json.loads((directory/'native_output.json').read_text())
                status = 'partial' if (result['native_failure_flags'] or result['control_issues']
                    or result['calls']['calls_failed']) else 'complete'
                if not result['report'].strip():
                    status = 'no_answer'
            write_json(directory/'status.json', {'status': status, 'ended_at': utcnow(),
                'returncode': process.returncode, 'elapsed_seconds': time.monotonic()-started})
        except BaseException:
            if process is not None:
                output, _ = stop_child(process)
                (directory/'worker.log').write_text(redact(output or ''), encoding='utf8')
            write_json(directory/'status.json', {'status': 'interrupted', 'ended_at': utcnow()})
            raise
        print(json.dumps({'event': 'finished', 'run_key': job['run_key'], 'status': status}), flush=True)
        states = {j['run_key']: json.loads((out/j['run_key']/'status.json').read_text())['status']
                  for j in schedule if (out/j['run_key']/'status.json').exists()}
        write_json(out/f'{phase}_progress.json', {'updated_at': utcnow(), 'states': states,
            'finished': sum(s != 'running' for s in states.values()), 'total': len(schedule)})
        if systemic_failure(result, status) or (phase == 'pilot' and status == 'partial'):
            # Preserve failed job; stop systemic failures before wasting all runs.
            break
    return {'launched': launched, 'unstarted': len(pending_jobs(out, schedule))}


def worker(job_path):
    job = json.loads(Path(job_path).read_text())
    out = Path(job['output_dir'])
    root = Path(job['experiment_dir'])/'runtime_sources'
    freeze = json.loads((Path(job['experiment_dir'])/'freeze.json').read_text())
    validate_job_identity(job['experiment_dir'], freeze, job)
    if freeze['implementation_files'] != _implementation_hashes():
        raise ValueError('Worker implementation differs from frozen code')
    if source_fingerprint([root/'helicase', root/'helix_core']) != freeze['native_files']:
        raise ValueError('Worker native code differs from frozen source')
    expected_caps = freeze['pilot_caps'] if job['phase'] == 'pilot' else json.loads(
        (Path(job['experiment_dir'])/'formal_config.json').read_text())['caps']
    if job['caps'] != expected_caps:
        raise ValueError('Worker budget differs from frozen phase configuration')
    if os.environ.get('PYTHONHASHSEED') != str(job['seed']):
        raise ValueError('Launch workers through batch with the frozen PYTHONHASHSEED')
    os.environ.update(ENABLE_PAGE_OCR='false', NEO4J_ENABLED='false',
                      HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                      READER_MAX_WORKERS='4', PREFILTER_MAX_WORKERS='2',
                      SEARCH_MAX_RESULTS='5', SEARCH_ENGINE='serper')
    # Append dependencies after stdlib; old site-packages/typing.py must not shadow typing.
    dependencies = os.environ.get('HELICASE_DEPENDENCY_PATHS', '').split(os.pathsep)
    sys.path.extend(p for p in dependencies if p and p not in sys.path)
    sys.path.insert(0, str(root))
    from .planning_codex import CallLedger, CodexAdapter
    from .planning_native import configure_native, run_native
    from .planning_retrieval import RetrievalMeter, install_retrieval_meter
    from dotenv import load_dotenv
    env_file = os.environ.get('HELICASE_ENV_FILE')
    if env_file:
        load_dotenv(env_file, override=False)
    if not os.environ.get('SERPER_API_KEY'):
        raise ValueError('SERPER_API_KEY must be supplied through the approved worker environment')
    from helix_core.agent.core.tools import WebSearchTool
    WebSearchTool.configure_engine('serper', api_key=os.environ['SERPER_API_KEY'])
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    import random
    import numpy as np
    random.seed(job['seed']); np.random.seed(job['seed'])
    caps = job['caps']
    calls = CallLedger(caps['model_calls'], final_calls=caps['final_calls'], journal=out/'calls.json')
    retrieval = RetrievalMeter(caps['search_requests'], caps['page_requests'], journal=out/'retrieval.jsonl')
    adapter = CodexAdapter(out/'model_traces', calls)
    native = configure_native(adapter, method=job['method'], seed=job['seed'], trace_dir=out,
                               fixed_n=caps['fixed_n'], max_iterations=caps['max_iterations'])
    # Fail before any experimental model call if genuine similarity is unavailable.
    native.uq.embedder.embed('supplier relationship')
    if native.uq.embedder._model == 'fallback':
        raise RuntimeError('Actual sentence embeddings required; hash fallback is not a semantic UQ control')
    write_json(out/'resolved_config.json', {'native': asdict(native.config),
        'adapter': adapter.public_config, 'caps': caps, 'matched_token_budget': False})
    with install_retrieval_meter(retrieval):
        run_native(native, job['question'], calls=calls, retrieval=retrieval, output_dir=out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'pilot', 'freeze-formal', 'formal', 'worker'))
    parser.add_argument('--out'); parser.add_argument('--dataset')
    parser.add_argument('--runtime-root'); parser.add_argument('--backend-root')
    parser.add_argument('--job'); parser.add_argument('--max-jobs', type=int, default=80)
    args = parser.parse_args()
    if args.command == 'worker':
        worker(args.job); return
    if args.command == 'prepare':
        value = prepare(args.out, args.dataset, args.runtime_root, args.backend_root)
    elif args.command == 'freeze-formal':
        value = freeze_formal(args.out)
    else:
        value = batch(args.out, args.command, max_jobs=args.max_jobs)
    print(json.dumps(value, ensure_ascii=False))


if __name__ == '__main__':
    main()
