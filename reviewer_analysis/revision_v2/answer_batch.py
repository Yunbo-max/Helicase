"""Bounded, resumable closed-book evaluation calls; no search-agent execution."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import fcntl
import json
from pathlib import Path
from .common import digest, redact, utcnow, write_json
from .judging import make_client, parse_object


def run_stage(tasks, out, prompt, transform, *, client=None, workers=4):
    if not 1 <= workers <= 4: raise ValueError('Use one to four workers')
    out = Path(out); (out/'items').mkdir(parents=True, exist_ok=True)
    client = client or make_client(out/'calls')
    manifest = {'tasks_sha256': digest(tasks), 'prompt_sha256': digest(prompt), 'client': client.public_config}
    with (out/'run.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = out/'manifest.json'
        if path.exists() and json.loads(path.read_text()) != manifest: raise ValueError('Frozen manifest changed')
        write_json(path, manifest); write_json(out/'tasks.json', tasks); (out/'prompt.txt').write_text(prompt)
        ids = [digest(t)[:24] for t in tasks]
        if len(ids) != len(set(ids)): raise ValueError('Duplicate task')
        rows = []; pending = []
        for t, ident in zip(tasks, ids):
            p = out/'items'/(ident+'.json')
            if not p.exists(): pending.append((t, p)); continue
            row = json.loads(p.read_text())
            if row['task'] != t: raise ValueError('Cached input mismatch')
            if 'result' in row and transform(parse_object(row['raw_response']), t) != row['result']:
                raise ValueError('Cached result failed revalidation')
            rows.append(row)
        def snapshot():
            result = {'total': len(tasks), 'saved': len(rows), 'successful': sum('result' in r for r in rows),
                      'failed': sum('error' in r for r in rows), 'pending': len(tasks)-len(rows), 'updated_at': utcnow()}
            write_json(out/'progress.json', result); return result
        snapshot()
        def work(item):
            t, p = item; row = {'task': t, 'created_at': utcnow(), 'api_calls': 1}
            kind = 'model_call'
            try:
                raw, usage, model = client.chat(prompt, t['payload'])
                row.update(raw_response=raw, usage=usage, returned_model=model)
                kind = 'content_validation'; row['result'] = transform(parse_object(raw), t)
            except Exception as exc: row.update(error=redact(str(exc)), error_kind=kind)
            write_json(p, row); return row
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for fut in as_completed([pool.submit(work, item) for item in pending]):
                rows.append(fut.result()); print(json.dumps(snapshot()), flush=True)
        return snapshot()


def extraction_transform(obj, task):
    from .answer_units import resolve_exact_offsets, validate_units
    p = task['payload']; fixed, corrections = resolve_exact_offsets(obj, p['text'], p['start'])
    return {'source_key': task['source_key'], 'units': validate_units(fixed, p['text'], p['start'], p['question']),
            'offset_corrections': corrections}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tasks', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--workers', type=int, default=4); ap.add_argument('--execute', action='store_true')
    args = ap.parse_args()
    from .answer_units import validate_tasks, EXTRACT_PROMPT
    tasks = json.loads(Path(args.tasks).read_text()); validate_tasks(tasks)
    if not args.execute: print(json.dumps({'tasks': len(tasks), 'execute': False})); return
    print(json.dumps(run_stage(tasks, args.out, EXTRACT_PROMPT, extraction_transform, workers=args.workers)))


if __name__ == '__main__': main()
