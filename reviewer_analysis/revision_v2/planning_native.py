"""Native KG/search execution with a shared, UQ-independent control loop.

This experiment changes planning selection, retrieval parallelism and stopping;
it is not a full-default-system ablation. Tokens are measured, not hard capped.
"""
from __future__ import annotations

import json
from pathlib import Path
import random
import time
from types import MethodType, SimpleNamespace

from .common import write_json
from .planning_codex import BudgetExceeded as ModelBudgetExceeded
from .planning_control import Candidate, neutral_planning_view, select_target
from .runner import native_failure_flags


def parse_json(text):
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    return json.loads(text)


class ControlledPlanner:
    def __init__(self, delegate, *, method, seed, trace_dir, action_factory=None):
        self.delegate = delegate
        self.llm = delegate.llm  # native target-resolution path uses planner.llm
        self.method = method
        self.rng = random.Random(seed)
        self.trace = Path(trace_dir)
        self.trace.mkdir(parents=True, exist_ok=True)
        self.action_factory = action_factory

    def analyze_query(self, query, kg):
        return self.delegate.analyze_query(query, kg)

    def generate_actions(self, query, kg, completed_actions, iteration, **unused):
        history = [a.to_dict() for a in completed_actions]
        view = neutral_planning_view(kg.to_dict(), history)
        prompt = ('Generate current valid investigation targets to answer the question. '
                  'Use only question, graph facts and completed-goal history below. '
                  'Propose up to 3 distinct targets still requiring investigation; '
                  'each description is a concrete web research goal. Preserve product, '
                  'time, market, planned/actual and other factual qualifications. '
                  'Do not repeat completed goals; a new evidence-seeking angle for the '
                  'same concept is allowed. Do not assign confidence, uncertainty, '
                  'priority, scores or rankings. Return [] only if no further '
                  'question-relevant investigation is needed. Return ONLY a JSON array '
                  'of {"target":"KG node name or Source --relation--> Target",'
                  '"description":"research goal"}.\n\nQuestion:\n'+query+
                  '\n\nFacts and history:\n'+json.dumps(view, ensure_ascii=False, sort_keys=True))
        response = self.delegate.llm.chat([SimpleNamespace(role='user', content=prompt)])
        data = parse_json(response.content)
        if not isinstance(data, list) or len(data) > 3:
            raise ValueError('Planner must return an array of 0–3 candidates')
        candidates = []
        for row in data:
            if not isinstance(row, dict) or set(row) != {'target', 'description'}:
                raise ValueError('Candidate must contain only target and description')
            candidates.append(Candidate(row['target'], row['description']))
        completed = {Candidate(a.target_concept, a.description).goal_key
                     for a in completed_actions
                     if a.agent_type == 'web_search' and a.status == 'done'
                     and a.result and a.result.get('success') is True
                     and a.target_concept}
        scores = {}
        def score(candidate):
            result = self.delegate.uq.estimate_uncertainty_reduction(
                kg.memory_uncertainty, candidate.description,
                kg.get_high_uncertainty_facts()) / 3.0
            scores[candidate.goal_key] = result
            return result
        selected = select_target(candidates, self.method, self.rng, score, completed)
        write_json(self.trace/f'selection_{iteration:03d}.json', {
            'method': self.method, 'iteration': iteration, 'neutral_context': view,
            'candidates': data,
            'uq_scores': [{'goal': list(key), 'score': value} for key, value in scores.items()],
            'selected': None if selected is None else {
                'target': selected.target, 'description': selected.description}})
        if selected is None:
            return []
        factory = self.action_factory
        if factory is None:
            from helicase.agent.action_planner import Action
            factory = Action
        search_id, coding_id = f'iter_{iteration}_search', f'iter_{iteration}_kg'
        return [factory(id=search_id, description=selected.description,
                        agent_type='web_search', target_concept=selected.target,
                        iteration=iteration, cost=3.0, priority=0.0, depends_on=[]),
                factory(id=coding_id, description='Integrate this investigation into the KG, preserving facts and citations.',
                        agent_type='coding', target_concept=selected.target,
                        depends_on=[search_id], iteration=iteration, cost=.5, priority=0.0)]


def require_query_variants(queries, n):
    if (not isinstance(queries, list) or len(queries) != n
            or any(not isinstance(q, str) or not q.strip() for q in queries)
            or len({' '.join(q.casefold().split()) for q in queries}) != n):
        raise ValueError('Fixed parallelism requires exactly n distinct nonempty queries')
    return queries


def configure_native(adapter, *, method, seed, trace_dir, fixed_n=2, max_iterations=3):
    from helicase.agent.config import HelicaseConfig
    from helicase.agent.helicase_orchestrator import HelicaseOrchestrator
    config = HelicaseConfig(web_search_min_parallel_queries=fixed_n,
                            web_search_max_parallel_queries=fixed_n,
                            max_iterations=max_iterations, action_max_workers=1,
                            search_max_results=5, reader_max_workers=4,
                            prefilter_max_workers=2, neo4j_enabled=False)
    role = adapter.for_role
    native = HelicaseOrchestrator(
        role('main'), reader_llm=role('reader'), prefilter_llm=role('prefilter'),
        coding_llm=role('kg_update'), query_variant_llm=role('query_variant'),
        uq_summarizer_llm=role('uq_summary'), uq_consensus_llm=role('uq_consensus'),
        config=config, language='en', search_engine='serper')
    native.planner.llm = role('planner')
    native.report_generator.llm = role('final_answer')
    native.planner = ControlledPlanner(native.planner, method=method, seed=seed,
                                       trace_dir=Path(trace_dir)/'planning')
    # Bypass the UQ-dependent branch AND its extra decision-model invocation.
    native.web_search_agent._decide_n = MethodType(lambda self, *a, **kw: fixed_n,
                                                  native.web_search_agent)
    generate_variants = native.web_search_agent._generate_query_variants
    def variants(self, description, context, n):
        return require_query_variants(generate_variants(description, context, n), fixed_n)
    native.web_search_agent._generate_query_variants = MethodType(variants, native.web_search_agent)
    original_context = native._build_action_context
    def context(self, query, action):
        result = original_context(query, action)
        result['kg_summary'] = json.dumps(neutral_planning_view(self.kg.to_dict(), []),
                                          ensure_ascii=False, sort_keys=True)
        result.pop('high_uncertainty_facts', None)
        # Native KG updates still propagate UQ in both arms; this value cannot
        # select n because the selection method above is replaced.
        return result
    native._build_action_context = MethodType(context, native)
    return native


def run_native(native, query, *, calls, retrieval, output_dir):
    """Fresh state only; same stop rule for both arms and one reserved final call."""
    out = Path(output_dir)
    if native.all_actions or native.kg.nodes or native.kg.edges:
        raise ValueError('Every execution must begin with an empty KG and history')
    start = time.monotonic()
    stop = 'iteration_limit'
    issues = []
    trajectory = 1.0
    uncertainty_history, description_history = [], []
    iteration = 0
    try:
        native.planner.analyze_query(query, native.kg)
        native.kg.compute_memory_uncertainty()
        for iteration in range(1, native.config.max_iterations+1):
            if calls.exhausted or retrieval.exhausted:
                stop = 'resource_limit'
                break
            completed = [a for a in native.all_actions if a.status == 'done']
            actions = native.planner.generate_actions(query, native.kg, completed, iteration)
            if not actions:
                stop = 'no_valid_candidate'
                break
            native.all_actions.extend(actions)
            done = native._execute_actions(actions, query)
            values = [a.uncertainty for a in done if a.uncertainty is not None]
            descriptions = [a.description for a in done if a.uncertainty is not None]
            trajectory, _ = native.uq.compute_trajectory_details(
                values, descriptions, uncertainty_history, description_history)
            uncertainty_history.append(values)
            description_history.append(descriptions)
            native.kg.compute_memory_uncertainty()
            write_json(out/f'state_{iteration:03d}.json', {
                'knowledge_graph': native.kg.to_dict(),
                'actions': [a.to_dict() for a in native.all_actions],
                'ref2url': native.ref2url,
                'calls': calls.snapshot(), 'retrieval': retrieval.snapshot()})
            if not done:
                stop = 'execution_failure'
                break
            if calls.exhausted or retrieval.exhausted:
                stop = 'resource_limit'
                break
    except ModelBudgetExceeded:
        stop = 'resource_limit'
    except Exception as exc:
        stop = 'control_error'
        issues.append(f'{type(exc).__name__}: {exc}')
    calls.begin_final()
    report = native.report_generator.generate(query, native.kg, native.evidence_store,
        native.ref2url, native.all_actions, native.quality_results)
    result = {'query': query, 'report': report, 'knowledge_graph': native.kg.to_dict(),
              'actions': [a.to_dict() for a in native.all_actions],
              'ref2url': {str(k): v for k, v in native.ref2url.items()},
              'iterations': iteration, 'elapsed_seconds': time.monotonic()-start,
              'termination': stop, 'control_issues': issues,
              'uncertainty': {'final_memory': native.kg.memory_uncertainty,
                              'trajectory_last': trajectory},
              'calls': calls.snapshot(), 'retrieval': retrieval.snapshot(),
              'matched_token_budget': False}
    result['native_failure_flags'] = native_failure_flags(result, native.all_actions)
    write_json(out/'native_output.json', result)
    (out/'report.md').write_text(report, encoding='utf8')
    return result
