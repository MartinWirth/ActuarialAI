import numpy as np
import pandas as pd
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.mack_matrix import aggregate_mack_matrix
from actuarial_ai.mack_matrix_sensitivity import mack_matrix_sensitivity


def sample():
    return {"Motor": synthetic_triangle(8, seed=1),
            "Property": synthetic_triangle(9, seed=2)}


def matrix(rho=0.3):
    return pd.DataFrame(
        [[1.0, rho], [rho, 1.0]],
        index=["Motor", "Property"], columns=["Motor", "Property"],
    )


def test_zero_shock_matches_baseline():
    baseline = aggregate_mack_matrix(sample(), matrix())
    result = mack_matrix_sensitivity(sample(), matrix(), shocks=(0.0,))
    assert len(result) == 1
    assert bool(result.iloc[0]["valid_psd"])
    assert result.iloc[0]["total_se"] == pytest.approx(baseline["total_se"])
    assert result.iloc[0]["delta_se"] == pytest.approx(0.0, abs=1e-8)


def test_valid_shocks_are_monotonic_for_positive_segment_errors():
    result = mack_matrix_sensitivity(
        sample(), matrix(), shocks=(-0.1, 0.0, 0.1),
    )
    assert result["valid_psd"].all()
    assert result["total_se"].is_monotonic_increasing
    assert result["delta_se"].iloc[0] < 0
    assert result["delta_se"].iloc[-1] > 0


def test_invalid_psd_scenario_is_flagged_not_clipped():
    result = mack_matrix_sensitivity(sample(), matrix(0.9), shocks=(0.2,))
    assert not bool(result.iloc[0]["valid_psd"])
    assert result.iloc[0]["correlation"] == pytest.approx(1.1)
    assert np.isnan(result.iloc[0]["total_se"])


@pytest.mark.parametrize("shocks", [(), (float("nan"),), (float("inf"),)])
def test_rejects_invalid_shocks(shocks):
    with pytest.raises(ValueError, match="Shocks"):
        mack_matrix_sensitivity(sample(), matrix(), shocks=shocks)


def test_three_segment_pairs():
    segments = {**sample(), "Liability": synthetic_triangle(8, seed=1) * 1.3}
    names = sorted(segments)
    correlation = pd.DataFrame(
        np.eye(3), index=names, columns=names,
    )
    result = mack_matrix_sensitivity(
        segments, correlation, shocks=(0.0, 0.1),
    )
    assert len(result) == 6
    assert result["valid_psd"].all()
