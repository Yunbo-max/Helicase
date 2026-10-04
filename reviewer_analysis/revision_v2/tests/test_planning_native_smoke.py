"""Opt-in native integration smoke with synthetic model/search transports only."""
import json
import os
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.skipif(not os.environ.get('HELICASE_NATIVE_SMOKE'),
                                reason='Native runtime/dependencies are supplied explicitly')


@pytest.mark.parametrize('method', ['full', 'uniform'])
def test_real_native_kg_loop_with_synthetic_transports(tmp_path, monkeypatch, method):
    from reviewer_analysis.revision_v2.planning_native import configure_native, run_native
    from reviewer_analysis.revision_v2.planning_codex import CallLedger
    from reviewer_analysis.revision_v2.planning_retrieval import RetrievalMeter
    from helicase.agent.search import SearcherAgent
    ledger = CallLedger(20)

    class Adapter:
        def __init__(self, role='main'):
            self.role = role
        def for_role(self, role):
            return Adapter(role)
        def chat(self, messages):
            prompt = messages[0].content
            ticket = ledger.reserve(role=self.role, input_sha256='synthetic', config={})
            if 'Analyze this research query' in prompt:
                content = json.dumps([{'name': name, 'concept_type': kind,
                                       'what_to_learn': 'Investigate supply'}
                                      for name, kind in [('Supplier Alpha', 'company'),
                                                         ('Product Beta', 'product')]])
            elif 'Generate current valid investigation targets' in prompt:
                content = '[{"target":"Supplier Alpha", "description":"Verify Alpha supplies Beta"}]'
            elif self.role == 'query_variant':
                content = 'Beta manufacturer Alpha supplier documentation'
            elif self.role == 'uq_consensus':
                content = '{"uncertainty":0.2,"reason":"Synthetic agreeing evidence"}'
            elif self.role == 'final_answer':
                content = 'Supplier Alpha supplies Product Beta [[0]].'
            else:
                content = 'Supplier Alpha supplies Product Beta.'
            ledger.finish(ticket, usage={'input_tokens': 10, 'output_tokens': 10}, output=content)
            return SimpleNamespace(content=content)

    def synthetic_search(self, **kwargs):
        return {'content': 'Supplier Alpha supplies Product Beta [[0]].',
                'ref2url': {0: {'url': 'https://example.com/evidence', 'title': 'Synthetic'}},
                'evidence_records': [{'ref_idx': 0, 'url': 'https://example.com/evidence',
                    'evidence_quote': 'Supplier Alpha supplies Product Beta.',
                    'finding_answer': 'Supplier Alpha supplies Product Beta.',
                    'criterion': 'supplier'}],
                'relations': [{'source': 'Supplier Alpha', 'target': 'Product Beta',
                    'source_type': 'company', 'target_type': 'product',
                    'relation': 'supplies', 'page_index': 0}], 'entities': []}
    monkeypatch.setattr(SearcherAgent, 'search_and_summarize', synthetic_search)
    native = configure_native(Adapter(), method=method, seed=1, trace_dir=tmp_path,
                               fixed_n=2, max_iterations=1)
    result = run_native(native, 'Who supplies Product Beta?', calls=ledger,
                        retrieval=RetrievalMeter(10, 10), output_dir=tmp_path)
    assert result['termination'] == 'iteration_limit'
    assert not result['control_issues']
    assert not result['native_failure_flags']
    assert len(result['knowledge_graph']['edges']) == 1
    assert result['ref2url']
    assert result['calls']['calls_failed'] == 0
    assert result['calls']['calls'][-1]['phase'] == 'final'
    assert native.all_actions[0].result['metadata']['n_queries'] == 2
