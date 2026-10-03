import math
import pytest

from reviewer_analysis.revision_v2 import planning_statistics as p


def fixture():
    return [{'phase': 'formal', 'query_id': f'Q{i}', 'method': m, 'repeat': r,
             'answer_precision': v, 'answer_recall': v, 'answer_f1': v,
             'status': 'complete'}
            for i in range(61, 81) for m in ('full', 'uniform') for r in (1, 2)
            for v in ([.8 if r == 1 else .4] if m == 'full' else [.4])]


def test_pairing_averages_repeats_before_resampling_queries():
    result = p.analyse_repeats(fixture(), n_boot=200, seed=1)
    assert result['n_queries'] == 20
    assert result['n_executions'] == 80
    assert result['f1_difference'] == pytest.approx(.2)
    assert result['paired_95ci'] == pytest.approx([.2, .2])
    full = result['methods']['full']
    assert full['answer_f1'] == pytest.approx(.6)
    assert full['repeat_f1_means'] == pytest.approx([.8, .4])
    assert full['repeat_f1_sample_sd'] == pytest.approx(math.sqrt(.08))


def test_no_answer_failure_kept_in_fixed_denominator():
    rows = fixture()
    rows[0].update(status='no_answer', answer_precision=0, answer_recall=0, answer_f1=0)
    result = p.analyse_repeats(rows, n_boot=100, seed=1)
    assert result['methods']['full']['answer_f1'] == pytest.approx(.58)
    assert result['methods']['full']['status_counts']['no_answer'] == 1
    with pytest.raises(ValueError):
        p.analyse_repeats(rows[1:])


@pytest.mark.parametrize('change', [
    {'phase': 'pilot'}, {'answer_f1': float('nan')}, {'answer_f1': 1.1},
    {'repeat': 3}, {'method': 'react'}, {'query_id': 'Q60'},
    {'status': 'no_answer', 'answer_f1': .8}, {'answer_precision': .1},
])
def test_invalid_or_mixed_protocol_rows_rejected(change):
    rows = fixture()
    rows[0].update(change)
    with pytest.raises(ValueError):
        p.analyse_repeats(rows, n_boot=100)
