import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from reviewer_analysis.revision_v2 import planning_native as p


class KG:
    def __init__(self, u):
        self.memory_uncertainty = u
        self.u = u
    def to_dict(self):
        return {'nodes': {'a': {'id': 'a', 'name': 'A', 'uncertainty': self.u,
                                'properties': {'status': 'planned supply, not confirmed'}}},
                'edges': {}}
    def get_high_uncertainty_facts(self):
        return [{'name': 'A', 'uncertainty': self.u}]


class LLM:
    def __init__(self, content):
        self.content = content
        self.prompts = []
    def chat(self, messages):
        self.prompts.append(messages[0].content)
        return SimpleNamespace(content=self.content)


def test_uniform_prompt_and_choice_ignore_uq(tmp_path):
    llms = []
    outputs = []
    def forbidden(*args):
        raise AssertionError('Uniform read UQ scoring')
    for u in (.1, .9):
        llm = LLM('[{"target":"A", "description":"Check A"},'
                  '{"target":"B", "description":"Check B"}]')
        delegate = SimpleNamespace(llm=llm, uq=SimpleNamespace(estimate_uncertainty_reduction=forbidden))
        planner = p.ControlledPlanner(delegate, method='uniform', seed=1,
                                      trace_dir=tmp_path/str(u), action_factory=SimpleNamespace)
        assert planner.llm is llm
        actions = planner.generate_actions('Question', KG(u), [], 1)
        assert len(actions) == 2
        assert actions[1].depends_on == [actions[0].id]
        outputs.append(actions[0].description)
        llms.append(llm)
    assert outputs[0] == outputs[1]
    assert llms[0].prompts == llms[1].prompts
    assert 'planned supply, not confirmed' in llms[0].prompts[0]
    assert 'memory_uncertainty' not in llms[0].prompts[0]


def test_full_selects_original_uq_score_with_same_candidate_prompt(tmp_path):
    scores = lambda memory, desc, facts: .9 if desc == 'Check B' else .1
    llm = LLM('[{"target":"A", "description":"Check A"},'
              '{"target":"B", "description":"Check B"}]')
    delegate = SimpleNamespace(llm=llm, uq=SimpleNamespace(estimate_uncertainty_reduction=scores))
    planner = p.ControlledPlanner(delegate, method='full', seed=1, trace_dir=tmp_path,
                                  action_factory=SimpleNamespace)
    actions = planner.generate_actions('Question', KG(.9), [], 1)
    assert actions[0].description == 'Check B'
    decision = json.loads((tmp_path/'selection_001.json').read_text())
    assert len(decision['candidates']) == 2
    assert len(decision['uq_scores']) == 2


@pytest.mark.parametrize('text', ['not json', '{}', '[{"target":"A"}]'])
def test_bad_planner_output_is_error_not_convergence(tmp_path, text):
    delegate = SimpleNamespace(llm=LLM(text), uq=None)
    planner = p.ControlledPlanner(delegate, method='uniform', seed=1, trace_dir=tmp_path,
                                  action_factory=SimpleNamespace)
    with pytest.raises(ValueError):
        planner.generate_actions('Question', KG(.1), [], 1)


@pytest.mark.parametrize('queries', [['A'], ['A', ' a '], ['A', ''], ['A', None]])
def test_fixed_parallelism_rejects_missing_or_duplicate_variants(queries):
    with pytest.raises(ValueError):
        p.require_query_variants(queries, 2)


def test_fixed_parallelism_preserves_two_distinct_queries():
    assert p.require_query_variants(['A', 'B'], 2) == ['A', 'B']
