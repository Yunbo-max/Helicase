"""Recompute this release's public arithmetic; no network, models, or private data."""
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent


def close(a, b):
    assert math.isfinite(float(a)) and abs(float(a)-float(b)) < 1e-12, (a, b)


def verify():
    rows = list(csv.DictReader((ROOT/'per_execution.csv').open()))
    summary = json.loads((ROOT/'summary.json').read_text())
    queries = [f'Q{i}' for i in range(61, 81)]
    expected = {(q, m, r) for q in queries for m in ('full', 'uniform') for r in (1, 2)}
    assert len(rows) == 80
    assert {(r['query_id'], r['method'], int(r['repeat'])) for r in rows} == expected
    for row in rows:
        assert row['phase'] == 'formal'
        p, r, m = (int(row[k]) for k in ('n_pred_units', 'n_reference_units', 'matched_units'))
        assert 0 <= m <= min(p, r) and r > 0
        close(row['answer_precision'], m/p if p else 0)
        close(row['answer_recall'], m/r)
        close(row['answer_f1'], 2*m/(p+r))
    query_means = {}
    for method in ('full', 'uniform'):
        selected = [r for r in rows if r['method'] == method]
        assert summary['methods'][method]['status_counts'] == dict(collections.Counter(r['status'] for r in selected))
        for metric in ('answer_precision', 'answer_recall', 'answer_f1'):
            close(summary['methods'][method][metric], math.fsum(float(r[metric]) for r in selected)/40)
        repeats = [math.fsum(float(r['answer_f1']) for r in selected if int(r['repeat']) == repeat)/20
                   for repeat in (1, 2)]
        for got, want in zip(summary['methods'][method]['repeat_f1_means'], repeats):
            close(got, want)
        close(summary['methods'][method]['repeat_f1_sample_sd'], abs(repeats[0]-repeats[1])/math.sqrt(2))
        query_means[method] = [math.fsum(float(r['answer_f1']) for r in selected if r['query_id'] == q)/2 for q in queries]
        for field in ('agent_calls', 'actual_input_tokens', 'actual_output_tokens', 'search_requests', 'page_requests'):
            total = math.fsum(float(r[field]) for r in selected)
            close(summary['resources'][method][field+'_total'], total)
            close(summary['resources'][method][field+'_mean_per_execution'], total/40)
    differences = [a-b for a, b in zip(query_means['full'], query_means['uniform'])]
    close(summary['f1_difference'], math.fsum(differences)/20)
    rng = random.Random(summary['seed'])
    boot = sorted(math.fsum(differences[math.floor(rng.random()*20)] for _ in range(20))/20
                  for _ in range(summary['n_boot']))
    for p, got in zip((.025, .975), summary['paired_95ci']):
        pos = (len(boot)-1)*p
        lower = math.floor(pos)
        close(got, boot[lower]*(1-(pos-lower))+boot[lower+1]*(pos-lower))
    per_query = list(csv.DictReader((ROOT/'per_query.csv').open()))
    assert len(per_query) == 20 and [r['query_id'] for r in per_query] == queries
    for i, row in enumerate(per_query):
        close(row['full_f1'], query_means['full'][i])
        close(row['uniform_f1'], query_means['uniform'][i])
        close(row['difference'], differences[i])
        for method in ('full', 'uniform'):
            pair = [r for r in rows if r['query_id'] == row['query_id'] and r['method'] == method]
            for field in ('answer_precision', 'answer_recall', 'actual_input_tokens', 'actual_output_tokens',
                          'agent_calls', 'search_requests', 'page_requests'):
                close(row[method+'_'+field], math.fsum(float(r[field]) for r in pair)/2)
    manifest = json.loads((ROOT/'manifest.json').read_text())
    for name, wanted in manifest['public_file_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == wanted, name
    return {'executions': 80, 'queries': 20, 'status_counts': dict(collections.Counter(r['status'] for r in rows)),
            'f1_difference': summary['f1_difference'], 'paired_95ci': summary['paired_95ci'],
            'public_arithmetic_and_hashes_verified': True,
            'scope': 'CSV arithmetic and release hashes only; original semantic pairs and call ledgers require private artifacts.'}


if __name__ == '__main__':
    print(json.dumps(verify(), ensure_ascii=False))
