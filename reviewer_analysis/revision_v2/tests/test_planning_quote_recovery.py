import json

import pytest

from reviewer_analysis.revision_v2.quote_case_recovery import reconcile_article_case


def fixture(text, quote):
    task = {'payload': {'reports': [{'source_id': 's', 'text': text}]},
            'source_map': {'s': {'method': 'full', 'query_id': 'Q1', 'run_id': 'r'}}}
    response = {'reports': [{'source_id': 's', 'answers': [
        {'label': 'Example', 'claim': 'Example supplies material.', 'status': 'actual',
         'quotes': [quote]}], 'excluded': []}]}
    return json.dumps(response), task


def test_recovers_unique_leading_article_case_without_changing_answer():
    raw, task = fixture('Context: the supplier is Example.', 'The supplier is Example.')
    derived, result, changes = reconcile_article_case(raw, task)
    answer = json.loads(derived)['reports'][0]['answers'][0]
    assert answer == {'label': 'Example', 'claim': 'Example supplies material.',
                      'status': 'actual', 'quotes': ['the supplier is Example.']}
    assert result['groups'][0]['units'][0]['quote_locations'][0]['occurrences'] == [9]
    assert changes[0]['source_offset'] == 9
    assert json.loads(raw)['reports'][0]['answers'][0]['quotes'] == ['The supplier is Example.']


def test_exact_response_is_returned_byte_for_byte():
    raw, task = fixture('The supplier is Example.', 'The supplier is Example.')
    derived, result, changes = reconcile_article_case(raw, task)
    assert derived == raw
    assert changes == []


@pytest.mark.parametrize('text,quote', [
    ('the supplier is Example. the supplier is Example.', 'The supplier is Example.'),
    ('apple supplies material.', 'Apple supplies material.'),
    ('the supplier is example.', 'The supplier is Example.'),
    ('the supplier is not Example.', 'The supplier is Example.'),
])
def test_rejects_ambiguous_names_interior_case_and_substantive_changes(text, quote):
    raw, task = fixture(text, quote)
    with pytest.raises(ValueError):
        reconcile_article_case(raw, task)
