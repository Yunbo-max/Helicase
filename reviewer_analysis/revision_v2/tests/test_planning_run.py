import json

import pytest

from reviewer_analysis.revision_v2 import planning_run as p
from reviewer_analysis.revision_v2.common import digest
from reviewer_analysis.revision_v2.planning_control import make_schedule


def test_caps_frozen_from_all_four_pilots_without_reading_scores():
    rows = [{'phase': 'pilot', 'query_id': q, 'method': m,
             'calls': {'calls_used': c},
             'retrieval': {'requests': {'search': s, 'page': r}},
             'answer_f1': .99 if m == 'uniform' else .01}
            for q in ('Q61', 'Q73') for m, c, s, r in
            [('full', 31, 11, 18), ('uniform', 40, 15, 23)]]
    caps = p.derive_formal_caps(rows)
    assert caps == {'model_calls': 50, 'search_requests': 20, 'page_requests': 30,
                    'final_calls': 1, 'max_iterations': 3, 'fixed_n': 2}
    for row in rows: row['answer_f1'] = 0
    assert p.derive_formal_caps(rows) == caps
    with pytest.raises(ValueError):
        p.derive_formal_caps(rows[:-1])


def test_failed_jobs_are_retained_and_not_rerun(tmp_path):
    path = tmp_path/'formal/01/Q61/full'
    path.mkdir(parents=True)
    (path/'status.json').write_text(json.dumps({'status': 'failed'}))
    jobs = [{'run_key': 'formal/01/Q61/full'}, {'run_key': 'formal/01/Q61/uniform'}]
    assert p.pending_jobs(tmp_path, jobs) == [jobs[1]]


def test_scoring_reference_does_not_reach_agent_query_file(tmp_path):
    dataset = tmp_path/'scpqa.jsonl'
    dataset.write_text('\n'.join(json.dumps({'id': i, 'quadrant': 'Q4',
        'question': f'Question {i}', 'answer': 'SECRET REFERENCE', 'sources': ['gold source']})
        for i in range(61,81)))
    rows = p.load_questions(dataset)
    assert len(rows) == 20
    assert 'SECRET REFERENCE' not in json.dumps(rows)
    assert 'gold source' not in json.dumps(rows)


def test_budget_stop_is_not_systemic_but_model_failure_is():
    assert not p.systemic_failure({'calls': {'calls_failed': 0},
                                  'control_issues': [], 'termination': 'resource_limit'}, 'partial')
    assert p.systemic_failure({'calls': {'calls_failed': 1},
                              'control_issues': [], 'termination': 'iteration_limit'}, 'partial')
    assert p.systemic_failure({}, 'timeout')


def test_pilot_with_failed_native_action_cannot_freeze(tmp_path):
    jobs = [{'run_key': f'pilot/01/{q}/{m}', 'query_id': q, 'method': m}
            for q in ('Q61', 'Q73') for m in ('full', 'uniform')]
    (tmp_path/'pilot_schedule.json').write_text(json.dumps(jobs))
    for job in jobs:
        d=tmp_path/job['run_key']; d.mkdir(parents=True)
        (d/'native_output.json').write_text(json.dumps({
            'report': 'Report', 'ref2url': {'0': {}}, 'knowledge_graph': {'edges': {'e': {}}},
            'calls': {'calls_failed': 0, 'calls_used': 10},
            'retrieval': {'violation': False, 'requests': {'search': 2, 'page': 2}},
            'native_failure_flags': ['action:iter_1_kg:status:failed']}))
    with pytest.raises(ValueError, match='functional review'):
        p.freeze_formal(tmp_path)


def test_worker_rejects_changed_question_or_seed(tmp_path):
    rows=[{'query_id':f'Q{i}', 'quadrant':'Q4', 'question':f'Question {i}'} for i in range(61,81)]
    (tmp_path/'questions.json').write_text(json.dumps(rows))
    freeze={'questions_sha256':digest(rows), 'seed':3}
    job=make_schedule(rows,seed=3,pilot=True)[0]
    p.validate_job_identity(tmp_path,freeze,job)
    with pytest.raises(ValueError):
        p.validate_job_identity(tmp_path,freeze,dict(job,question='different question'))
    with pytest.raises(ValueError):
        p.validate_job_identity(tmp_path,freeze,dict(job,seed=123))
    with pytest.raises(ValueError):
        p.validate_job_identity(tmp_path,freeze,dict(job,phase='Q3'))
