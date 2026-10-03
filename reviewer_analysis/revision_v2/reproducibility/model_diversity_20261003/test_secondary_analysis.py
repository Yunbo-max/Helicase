import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('secondary_analysis', Path(__file__).with_name('analyse_secondary.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_agreement_denominators_and_primary_strata():
    p = {'a': {'truth_status': 'supported'}, 'b': {'truth_status': 'unresolved'}, 'c': {'truth_status': 'unresolved'}}
    s = {'a': {'truth_status': 'supported'}, 'b': {'truth_status': 'supported'}, 'c': {'truth_status': 'unresolved'}}
    result = m.agreement(['a', 'b'], p, s)
    assert result['agreement'] == .5 and result['n'] == 2
    assert result['primary_strata']['supported']['agreement'] == 1
    assert result['primary_strata']['unresolved']['agreement'] == 0
    assert result['primary_strata']['contradicted']['agreement'] is None
    assert m.agreement(['a', 'b', 'c'], p, s)['agreement'] == 2/3


def test_common_binary_uses_same_facts_and_signed_difference():
    facts = [dict(fact_id='a', query_id='q1', confidence=.9), dict(fact_id='b', query_id='q2', confidence=.2),
             dict(fact_id='c', query_id='q3', confidence=.99)]
    p = {'a': {'truth_status': 'supported'}, 'b': {'truth_status': 'contradicted'}, 'c': {'truth_status': 'supported'}}
    s = {'a': {'truth_status': 'contradicted'}, 'b': {'truth_status': 'supported'}, 'c': {'truth_status': 'unresolved'}}
    result = m.paired_calibration(facts, p, s, n_boot=100)
    assert result['fact_ids'] == ['a', 'b'] and result['n_queries'] == 2
    assert result['primary']['brier'] == pytest.approx(.025)
    assert result['secondary']['brier'] == pytest.approx(.725)
    assert result['secondary_minus_primary']['brier'] == pytest.approx(.7)
    assert result['secondary_minus_primary']['ece'] == pytest.approx(.7)
    assert result['query_cluster_bootstrap_95ci']['brier'] == pytest.approx([.6, .8])
    identical = m.paired_calibration(facts, p, p, n_boot=30)
    assert all(v == 0 for v in identical['secondary_minus_primary'].values())
    assert all(v == [0, 0] for v in identical['query_cluster_bootstrap_95ci'].values())


def test_no_binary_intersection_is_not_zero_error():
    f = [dict(fact_id='a', query_id='q', confidence=.5)]
    p = {'a': {'truth_status': 'supported'}}
    s = {'a': {'truth_status': 'unresolved'}}
    result = m.paired_calibration(f, p, s)
    assert result['n'] == 0 and result['metrics'] is None
    assert result['query_cluster_bootstrap_95ci'] is None
