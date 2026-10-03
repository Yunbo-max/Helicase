import importlib.util
from pathlib import Path
import pytest


def module():
    path = Path(__file__).with_name('analyse_diversity.py')
    assert path.exists(), 'Three-model analysis not implemented'
    spec = importlib.util.spec_from_file_location('diversity_analysis', path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_three_model_patterns_and_mechanical_exclusion():
    # Averages across pairs cannot replace the fraction on which all three agree.
    m = module()
    models = ['p', 's', 't']
    labels = {key: {} for key in models}
    patterns = [('supported', 'supported', 'supported'), ('supported', 'unresolved', 'supported'),
                ('supported', 'contradicted', 'unresolved'), ('unresolved', 'unresolved', 'unresolved')]
    for fid, statuses in zip(['a', 'b', 'c', 'mechanical'], patterns):
        for key, status in zip(models, statuses):
            labels[key][fid] = {'truth_status': status}
    out = m.pattern_summary(['a', 'b', 'c'], labels, models)
    assert out['n'] == 3 and out['unanimous'] == 1 and out['two_agree'] == 1 and out['all_different'] == 1
    assert out['unanimous_fraction'] == pytest.approx(1/3)
    assert out['any_disagreement'] == 2
    assert sum(row['n'] for row in out['patterns']) == 3
    all_ = m.pattern_summary(['a', 'b', 'c', 'mechanical'], labels, models)
    assert all_['unanimous_fraction'] == .5


def test_pattern_summary_rejects_bad_alignment_and_labels():
    m = module()
    good = {'a': {'truth_status': 'supported'}}
    with pytest.raises(ValueError):
        m.pattern_summary(['a', 'a'], {'p': good, 's': good, 't': good}, ['p', 's', 't'])
    with pytest.raises(ValueError):
        m.pattern_summary(['a'], {'p': good, 's': {}, 't': good}, ['p', 's', 't'])
    with pytest.raises(ValueError):
        m.pattern_summary(['a'], {'p': good, 's': good, 't': {'a': {'truth_status': 'false'}}}, ['p', 's', 't'])
