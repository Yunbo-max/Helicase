"""Query-level paired statistics for exactly 80 runs from one frozen evaluator.

Scores must be per execution (one judge/protocol), not averages across judges.
Resource summaries are joined separately from the actual dispatch ledgers.
"""
from collections import Counter
import math
import random
import statistics


def _quantile(values, probability):
    ordered = sorted(values)
    position = (len(ordered)-1)*probability
    lower = int(position)
    upper = min(lower+1, len(ordered)-1)
    return ordered[lower]+(position-lower)*(ordered[upper]-ordered[lower])


def analyse_repeats(rows, *, n_boot=10000, seed=20261004):
    if type(n_boot) is not int or n_boot < 100:
        raise ValueError('At least 100 bootstrap samples required')
    methods = ('full', 'uniform')
    queries = [f'Q{i}' for i in range(61, 81)]
    expected = {(q, m, r) for q in queries for m in methods for r in (1, 2)}
    indexed = {}
    metrics = ('answer_precision', 'answer_recall', 'answer_f1')
    statuses = {'complete', 'partial', 'failed', 'no_answer', 'budget_exhausted'}
    for row in rows:
        key = (row.get('query_id'), row.get('method'), row.get('repeat'))
        if (row.get('phase') != 'formal' or key not in expected or key in indexed
                or type(row.get('repeat')) is not int or row.get('status') not in statuses):
            raise ValueError('Require unique, formally evaluated Q4 executions')
        for metric in metrics:
            value = row.get(metric)
            if (type(value) not in (float, int) or not math.isfinite(value)
                    or not 0 <= value <= 1):
                raise ValueError('Scores must be finite fractions in [0,1]')
        precision, recall, f1 = (row[k] for k in metrics)
        correct = 2*precision*recall/(precision+recall) if precision+recall else 0
        if abs(f1-correct) > 1e-8:
            raise ValueError('Per-execution F1 is inconsistent with precision/recall')
        if row['status'] == 'no_answer' and any(row[k] != 0 for k in metrics):
            raise ValueError('No-answer executions must retain explicit zero scores')
        indexed[key] = row
    if set(indexed) != expected:
        raise ValueError('All 80 formal executions, including failures, are required')
    method_results = {}
    query_f1 = {}
    for method in methods:
        selected = [indexed[q, method, r] for q in queries for r in (1, 2)]
        means = [statistics.mean(indexed[q, method, r]['answer_f1'] for q in queries)
                 for r in (1, 2)]
        method_results[method] = {
            **{k: statistics.mean(row[k] for row in selected) for k in metrics},
            'repeat_f1_means': means,
            'repeat_f1_sample_sd': statistics.stdev(means),
            'status_counts': dict(Counter(row['status'] for row in selected)),
        }
        query_f1[method] = [statistics.mean(indexed[q, method, r]['answer_f1']
                                           for r in (1, 2)) for q in queries]
    differences = [a-b for a, b in zip(query_f1['full'], query_f1['uniform'])]
    rng = random.Random(seed)
    boot = [statistics.mean(rng.choices(differences, k=20)) for _ in range(n_boot)]
    return {'n_queries': 20, 'n_executions': 80, 'methods': method_results,
            'f1_difference': statistics.mean(differences),
            'paired_95ci': [_quantile(boot, .025), _quantile(boot, .975)],
            'per_query': [{'query_id': q, 'full_f1': query_f1['full'][i],
                           'uniform_f1': query_f1['uniform'][i],
                           'difference': differences[i]} for i, q in enumerate(queries)],
            'n_boot': n_boot, 'seed': seed,
            'limitations': 'Two repeat means yield an unstable sample SD; '
                           'query bootstrap uses 20 units, not 40 independent questions.'}
