from collections import Counter
from copy import deepcopy
import json
import random

import pytest

from reviewer_analysis.revision_v2 import planning_control as p


def test_uniform_never_reads_uq_and_has_no_duplicate_target_weight():
    candidates = [p.Candidate('A', 'Investigate A'),
                  p.Candidate('B', 'Investigate B')]
    duplicate = candidates+[p.Candidate('A', 'Investigate A')]*20
    def forbidden(_):
        raise AssertionError('Uniform planning read UQ')
    for seed in range(50):
        first = p.select_target(candidates, 'uniform', random.Random(seed), forbidden)
        second = p.select_target(duplicate[::-1], 'uniform', random.Random(seed), forbidden)
        assert first == second
    observed = {p.select_target(candidates, 'uniform', random.Random(s), forbidden).target
                for s in range(50)}
    assert observed == {'A', 'B'}


def test_full_uses_score_and_completed_goals_are_not_selected():
    candidates = [p.Candidate('A', 'Investigate A'), p.Candidate('B', 'Investigate B')]
    score = lambda c: {'A': .1, 'B': .9}[c.target]
    assert p.select_target(candidates, 'full', random.Random(1), score).target == 'B'
    assert p.select_target(candidates, 'full', random.Random(1), score,
                           completed={('b', 'investigate b')}).target == 'A'
    assert p.select_target([], 'uniform', random.Random(1), score) is None
    with pytest.raises(ValueError):
        p.select_target(candidates, 'react', random.Random(1), score)


def test_neutral_view_is_uq_invariant_and_preserves_fact_qualifiers():
    graph = {'nodes': {
        'a': {'id': 'a', 'name': 'A', 'node_type': 'company', 'uncertainty': .9,
              'properties': {'status': '计划供货，尚未确认', 'capacity': 30,
                             'priority': 100}, 'sources': [2]},
        'b': {'id': 'b', 'name': 'B', 'node_type': 'company', 'uncertainty': .1}},
        'edges': {'e': {'id': 'e', 'source_id': 'a', 'target_id': 'b',
                       'relation_type': 'planned_supplier', 'uncertainty': .8,
                       'properties': {'market': 'Europe', 'year': 2027},
                       'evidence_refs': [2]}}, 'memory_uncertainty': .7}
    history = [{'description': 'Investigate planned supply', 'target_concept': 'A',
                'status': 'done', 'uncertainty': .9, 'priority': 10,
                'result': {'metadata': {'best_angle': 'UQ-derived suggestion'}}}]
    before = p.neutral_planning_view(graph, history)
    changed = deepcopy(graph)
    changed['nodes'] = dict(reversed(list(changed['nodes'].items())))
    changed['nodes']['a']['uncertainty'] = 0
    changed['nodes']['a']['properties']['priority'] = -100
    changed['edges']['e']['uncertainty'] = 0
    changed['memory_uncertainty'] = 0
    history[0]['uncertainty'] = 0
    history[0]['priority'] = 0
    assert p.neutral_planning_view(changed, history) == before
    text = json.dumps(before, ensure_ascii=False)
    assert '计划供货，尚未确认' in text and '2027' in text and 'Europe' in text
    assert 'uncertainty' not in text and 'priority' not in text
    assert 'UQ-derived suggestion' not in text
    assert before['nodes'][0]['properties']['capacity'] == 30


def test_schedule_has_80_fresh_adjacent_jobs_and_does_not_pass_reference():
    rows = [{'query_id': f'Q{i}', 'quadrant': 'Q4', 'question': f'question {i}',
             'reference': 'DO NOT PASS'} for i in range(61, 81)]
    schedule = p.make_schedule(rows, seed=20261004)
    assert len(schedule) == 80
    assert len({job['run_key'] for job in schedule}) == 80
    assert len({job['seed'] for job in schedule}) == 80
    assert set(Counter((j['query_id'], j['method']) for j in schedule).values()) == {2}
    for left, right in zip(schedule[::2], schedule[1::2]):
        assert (left['query_id'], left['repeat']) == (right['query_id'], right['repeat'])
        assert {left['method'], right['method']} == {'full', 'uniform'}
    assert 'DO NOT PASS' not in json.dumps(schedule)
    assert p.make_schedule(rows[::-1], seed=20261004) == schedule
    pilots = p.make_schedule(rows, seed=20261004, pilot=True)
    assert len(pilots) == 4
    assert {j['query_id'] for j in pilots} == {'Q61', 'Q73'}
    assert not {j['run_key'] for j in pilots} & {j['run_key'] for j in schedule}
    assert not {j['seed'] for j in pilots} & {j['seed'] for j in schedule}
    with pytest.raises(ValueError):
        p.make_schedule(rows[:-1], seed=1)
    rows[0]['quadrant'] = 'Q3'
    with pytest.raises(ValueError):
        p.make_schedule(rows, seed=1)
