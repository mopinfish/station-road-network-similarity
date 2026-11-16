"""Independent small numerical contracts; no real data loaded."""
import numpy as np
import pytest
from paper1.sensitivity import normalize, transform, top, distance_matrix, describe, dominance, compare_value


def test_transform_and_normalize():
    z = transform(np.array([[3., 4.], [1., 0.]]), [1., 0.], [2., 1.])
    u, norm = normalize(z[:1])
    np.testing.assert_allclose(u, [[1 / np.sqrt(17), 4 / np.sqrt(17)]])
    np.testing.assert_allclose(norm, [np.sqrt(17)])
    tiny, _ = normalize(np.array([[1e-200, 0.]]))
    assert tiny.tolist() == [[1., 0.]]
    with pytest.raises(ValueError):
        normalize(z[1:])
    drop, _ = normalize(z[:1, :1])
    assert drop.tolist() == [[1.]]


def test_neighbors_ties_threshold_and_replenishment():
    ids = ['a', 'b', 'c', 'd', 'e']
    values = np.array([1., .9, .8, .8, .7])
    result = top(values, ids, np.array([False, True, True, True, True]), 2)
    assert result['ids'] == ['b', 'c'] and result['boundary_tie']
    assert result['kth_ties'] == 2
    distances = np.array([0, 1600, 1700, 1800, 1900])
    result = top(values, ids, distances > 1600, 2)
    assert result['ids'] == ['c', 'd'] and not result['boundary_tie']
    with pytest.raises(ValueError):
        top(values, ids, distances > 1800, 2)


def test_distance_join_is_exact():
    records = [{'g_i': 'a', 'g_j': 'b', 'd_origin_plane_m': '2'}]
    assert distance_matrix(['a', 'b'], records)[1, 0] == 2
    with pytest.raises(ValueError):
        distance_matrix(['a', 'b'], [])
    with pytest.raises(ValueError):
        distance_matrix(['a', 'b'], records * 2)


def test_quantiles_dominance_and_reference_failures():
    assert describe([0, 1, 2, 3])['q1'] == .75
    labels, bins, s = dominance(np.array([[2., 1.], [1., .1]]), ['a', 'b'])
    assert labels == ['a', 'a'] and bins == ['ge_0_8', 'ge_0_8']
    assert s[0] == .8
    with pytest.raises(ValueError):
        dominance(np.array([[1., -1.]]), ['a', 'b'])
    assert compare_value(1., 1. + 1e-13)
    assert not compare_value(1, 2)
    assert not compare_value(['a'], ['b'])


def test_ids_rank_ties_and_output_preservation(tmp_path):
    from paper1.sensitivity import pair_values, run
    assert compare_value('00123', '00123')
    assert not compare_value('00123', '123')
    a=np.array([[1.,1.,1.],[1.,1.,2.],[1.,2.,1.]])
    b=np.array([[1.,2.,2.],[2.,1.,1.],[2.,1.,1.]])
    assert pair_values(a,b)['spearman'] == pytest.approx(-1.)
    with pytest.raises(FileExistsError):
        run(tmp_path/'absent',tmp_path)
