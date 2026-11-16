"""Small hand-checkable scientific-contract examples."""
import importlib
import numpy as np
import pandas as pd
import pytest


def module():
    return importlib.import_module('paper1.main_analysis')


def test_selection_clips_constant_and_breaks_equal_variance_by_column():
    frame = pd.DataFrame({'b': [0., 1., 2., 3., 4.], 'a': [0., 1., 2., 3., 4.],
                          'constant': [1., 1., 1., 1., 99.]})
    result = module().select_features(frame)
    assert result['selection_order'] == ['b']
    assert result['steps'][0]['removed_features'] == ['a']
    assert result['preprocessing'][2]['score'] == 0


def test_eligibility_does_not_inherit_candidate_missing():
    frame = pd.DataFrame({'a': [1., 2.], 'b': [np.nan, 3.]}, index=['01', '02'])
    quality = pd.DataFrame({'status': ['ok', 'ok'], 'quality_hold': ['', '']}, index=frame.index)
    assert module().eligible(frame, quality, ['a', 'b']) == ['02']
    assert module().eligible(frame, quality, ['a']) == ['01', '02']
    with pytest.raises(ValueError):
        module().eligible(frame.rename(index={'02': '01'}), quality, ['a'])


def test_raw_fit_clip_shares_scale_and_tiny_vectors_survive():
    x = np.array([[0., 0.], [1., 2.], [2., 4.], [3., 6.], [100., 200.]])
    fit = module().fit_vectors(x)
    np.testing.assert_allclose(fit['scale'], [2., 4.])
    np.testing.assert_allclose(fit['main_z'][-1], [49., 49.])
    np.testing.assert_allclose(fit['clip_z'][-1], [3.5, 3.5])
    row = module().normalize(np.array([[1e-200, 1e-200], [0., 0.]]))
    assert row['zero'].tolist() == [False, True]
    assert row['dominance'][0] == .5
    assert row['max_index'].tolist() == [0, -1]
    with pytest.raises(ValueError):
        module().fit_vectors(np.ones((4, 2)))
    with pytest.raises(ValueError):
        module().normalize(np.array([[np.inf]]))


def test_neighbor_ties_use_string_ids_and_exclude_self():
    c = np.ones((3, 3))
    assert module().neighbors(c, ['b', 'a', 'c'], 1).tolist() == [[1], [0], [1]]


def test_fixed_pair_bands_and_constant_undefined():
    c = np.array([[1., .8, .2], [.8, 1., -.5], [.2, -.5, 1.]])
    result = module().fixed_pairs(['a', 'b', 'c'], c)
    assert [p['rank'] for p in result['picks']] == [1, 2, 3]
    assert [p['level'] for p in result['picks']] == ['high', 'middle', 'low']
    assert module().fixed_pairs(['a', 'b', 'c'], np.ones((3, 3)))['status'] == 'undetermined'


def test_existing_output_refused_before_input_access(tmp_path):
    with pytest.raises(FileExistsError):
        module().run(tmp_path / 'missing-input', tmp_path)


def test_near_tie_diagnostic_records_swapped_ids_without_waiver():
    a = np.array([[1., .5+1e-13, .5], [.5+1e-13, 1., 0.], [.5, 0., 1.]])
    b = np.array([[1., .5, .5+1e-13], [.5, 1., 0.], [.5+1e-13, 0., 1.]])
    info = module().ranking_diagnostics(a, b, ['a','b','c'], ks=(1,))
    assert info[0]['actual_ids'] == ['b']
    assert info[0]['expected_ids'] == ['c']
    assert info[0]['near_tie'] is True
    assert module().compare(['b'], ['c'])['passed'] is False


def test_exact_neighbor_order_rejects_tolerated_swap_with_unchanged_overlap():
    # Swapping near-equal candidates leaves the main/Clip intersections identical
    # when both conditions undergo the swap, but must still fail saved-ID checks.
    n = 22
    ids = [f'{i:02d}' for i in range(n)]
    reference = np.eye(n)
    reference[0, 1:] = reference[1:, 0] = np.linspace(.9, .1, n-1)
    reference[0, 6] = reference[6, 0] = reference[0, 5]-1e-13
    changed = reference.copy()
    changed[0, 5], changed[0, 6] = reference[0, 6], reference[0, 5]
    changed[5, 0], changed[6, 0] = changed[0, 5], changed[0, 6]
    assert np.allclose(changed, reference, atol=1e-12, rtol=1e-12)
    exposed = np.zeros(n, dtype=bool)
    before = module().clip_comparison(reference, reference, ids, exposed)
    after = module().clip_comparison(changed, changed, ids, exposed)
    assert before == after
    check = module().verify_rankings(changed, reference, ids)
    assert check['passed'] is False
    assert check['differences'][0]['near_tie'] is True
