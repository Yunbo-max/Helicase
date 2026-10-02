import pytest


def test_whitespace_only_repair_restores_literal_report_span():
    from reviewer_analysis.revision_v2.quote_repair import recover_quote
    report='Intro. A supplies B:\n\n  - product X. End.'
    assert recover_quote('A supplies B: - product X.',report)=='A supplies B:\n\n  - product X.'


@pytest.mark.parametrize('quote,report',[
    ('A supplies B','A does not supply B'),
    ('A supplies B','A supplies C'),
    ('A supplies B','A\n supplies B; A  supplies B'),
    ('nickel-manganese-cobalt (NMC) chemistries','nickel-manganese-cobalt (NMC) cells'),
])
def test_repair_rejects_changed_words_or_ambiguous_match(quote,report):
    from reviewer_analysis.revision_v2.quote_repair import recover_quote
    assert recover_quote(quote,report) is None


def test_graph_repair_preserves_claims_and_revalidates():
    from reviewer_analysis.revision_v2.quote_repair import repair_graph_quotes
    graph={'nodes':[{'id':'n','name':'A','node_type':'company','quote':'Company A'}],'edges':[]}
    repaired,changes=repair_graph_quotes(graph,'Company\nA')
    assert repaired['nodes'][0]['quote']=='Company\nA'
    assert changes[0]['old_quote']=='Company A'
    assert graph['nodes'][0]['quote']=='Company A'
