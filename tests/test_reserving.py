import pandas as pd
import pytest
from actuarial_ai import chain_ladder, synthetic_triangle


def test_reproducible_triangle():
    pd.testing.assert_frame_equal(synthetic_triangle(seed=12), synthetic_triangle(seed=12))


def test_triangle_pattern():
    t = synthetic_triangle(6)
    assert [int(t.iloc[i].notna().sum()) for i in range(6)] == [6, 5, 4, 3, 2, 1]


def test_known_factors_and_reserve():
    t = pd.DataFrame([[100., 150., 180.], [120., 180., np.nan], [130., np.nan, np.nan]])
    result = chain_ladder(t)
    assert result["factors"].to_list() == pytest.approx([1.5, 1.2])
    assert result["summary"].loc[2, "ultimate"] == pytest.approx(234.)
    assert result["total_reserve"] == pytest.approx(140.)


def test_invalid_triangle_rejected():
    with pytest.raises(ValueError):
        chain_ladder(pd.DataFrame([[10., 9.], [5., np.nan]]))


def test_zero_volume_rejected():
    with pytest.raises(ValueError):
        chain_ladder(pd.DataFrame([[0., 0.], [1., np.nan]]))


def test_synthetic_reserves_nonnegative():
    result = chain_ladder(synthetic_triangle())
    assert (result["summary"]["reserve"] >= -1e-8).all()
