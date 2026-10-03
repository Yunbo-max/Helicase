"""Pure planning controls for the proposed two-arm experiment.

These are independently testable components, not yet connected to the native
agent. Integrations must construct both arms' candidates from the neutral view.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import random


def _key(text):
    return ' '.join(text.casefold().split())


@dataclass(frozen=True)
class Candidate:
    target: str
    description: str

    def __post_init__(self):
        if not all(isinstance(v, str) and v.strip()
                   for v in (self.target, self.description)):
            raise ValueError('Candidate target and description must be nonempty')

    @property
    def goal_key(self):
        return (_key(self.target), _key(self.description))


def select_target(candidates, method, rng, score, completed=()):
    """Uniform samples distinct targets, then distinct goals within that target.

    `score` is called ONLY in full mode; the integration supplies the existing
    estimated uncertainty reduction / action cost. Completed keys denote exact
    goals, not entire concepts, so a new investigation angle remains eligible.
    """
    if method not in ('full', 'uniform'):
        raise ValueError('Only full and uniform are allowed')
    done = set(completed)
    unique = {}
    for candidate in sorted(candidates, key=lambda c: (c.target, c.description)):
        if candidate.goal_key not in done:
            unique.setdefault(candidate.goal_key, candidate)
    ordered = [unique[k] for k in sorted(unique)]
    if not ordered:
        return None
    if method == 'uniform':
        groups = {}
        for candidate in ordered:
            groups.setdefault(_key(candidate.target), []).append(candidate)
        target = rng.choice(sorted(groups))
        return rng.choice(groups[target])
    values = [float(score(c)) for c in ordered]
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Full planner scores must be finite')
    best = max(values)
    return rng.choice([c for c, v in zip(ordered, values) if v == best])


_DERIVED_FIELDS = {
    'uncertainty', 'memory_uncertainty', 'uncertainty_history', 'confidence',
    'priority', 'rank', 'score', 'u', 'u_memory', 'uq', 'best_angle', 'worst_angle',
    'novelty', 'redundancy', 'estimated_reduction', 'high_uncertainty_facts',
    'metadata', 'summary',
}


def _facts(value):
    """Remove typed control metadata, never delete words from factual text.

    This covers the current schema, not arbitrary new metadata conventions;
    adding a producer field requires an integration leakage test.
    """
    if isinstance(value, dict):
        return {k: _facts(v) for k, v in sorted(value.items())
                if k.casefold() not in _DERIVED_FIELDS
                and not k.casefold().startswith(('uq_', 'uncertainty_'))}
    if isinstance(value, list):
        return [_facts(v) for v in value]
    return value


def neutral_planning_view(graph, history):
    """Project raw KG facts and completion history without UQ-derived summaries."""
    node_fields = ('id', 'name', 'node_type', 'properties', 'sources',
                   'parent_id', 'decomposed')
    edge_fields = ('id', 'source_id', 'target_id', 'relation_type', 'properties',
                   'evidence_refs')
    return {
        'nodes': [{k: _facts(n[k]) for k in node_fields if k in n}
                  for _, n in sorted(graph.get('nodes', {}).items())],
        'edges': [{k: _facts(e[k]) for k in edge_fields if k in e}
                  for _, e in sorted(graph.get('edges', {}).items())],
        'history': [{k: a[k] for k in ('description', 'target_concept', 'status')
                     if k in a} for a in history],
    }


def make_schedule(rows, *, seed, pilot=False):
    """4 separate pilots or 80 paired formal jobs, never include reference text."""
    if type(seed) is not int or type(pilot) is not bool:
        raise ValueError('An integer seed and boolean pilot flag are required')
    expected = {f'Q{i}' for i in range(61, 81)}
    queries = {}
    for row in rows:
        qid = row.get('query_id', row.get('id'))
        if isinstance(qid, int):
            qid = f'Q{qid}'
        question = row.get('question', row.get('query'))
        if (qid not in expected or qid in queries or row.get('quadrant') != 'Q4'
                or not isinstance(question, str) or not question.strip()):
            raise ValueError('Require exactly one nonempty Q4 question for Q61–Q80')
        queries[qid] = question
    if set(queries) != expected:
        raise ValueError('Require all 20 Q4 questions Q61–Q80')
    phase = 'pilot' if pilot else 'formal'
    rng = random.Random(f'{seed}:{phase}')
    jobs = []
    for repeat in range(1, 2 if pilot else 3):
        order = ['Q61', 'Q73'] if pilot else sorted(queries)
        rng.shuffle(order)
        for qid in order:
            methods = ['full', 'uniform']
            rng.shuffle(methods)
            for method in methods:
                run_key = f'{phase}/{repeat:02d}/{qid}/{method}'
                job_seed = int.from_bytes(hashlib.sha256(
                    f'{seed}:{run_key}'.encode()).digest()[:4], 'big')
                jobs.append({'run_key': run_key, 'phase': phase, 'repeat': repeat,
                             'query_id': qid, 'quadrant': 'Q4',
                             'question': queries[qid], 'method': method,
                             'seed': job_seed})
    if len({job['seed'] for job in jobs}) != len(jobs):
        raise ValueError('Seed collision; choose a different schedule seed before freezing')
    return jobs
