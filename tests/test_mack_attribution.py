import numpy as np
import pandas as pd
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.mack_attribution import mack_risk_attribution
from actuarial_ai.mack_matrix import aggregate_mack_matrix


def sample():
    a = synthetic_triangle(8, seed=1)
    b = synthetic_triangle(9, seed=2)
    return {"Motor": a, "Property": b}


def matrix(rho):
    return pd.DataFrame(
        [[1.0, rho], [rho, 1.0]],
        index=["Motor", "Property"], columns=["Motor", "Property"],
    )


@pytest.mark.parametrize("rho", [-0.5, 0.0, 0.4, 1.0])
def test_euler_contributions_reconcile(rho):
    segments = sample()
    result = mack_risk_attribution(segments, matrix(rho))
    aggregate = aggregate_mack_matrix(segments, matrix(rho))
    assert result["total_se"] == pytest.approx(aggregate["total_se"])
    assert result["segments"]["variance_contribution"].sum() == pytest.approx(
        result["total_variance"],
    )
    assert result["segments"]["euler_se_contribution"].sum() == pytest.approx(
        result["total_se"], abs=1e-7,
    )
    assert result["segments"]["se_share"].sum() == pytest.approx(1.0)
    assert result["standalone_variance"] + result["total_cross_variance"] == (
        pytest.approx(result["total_variance"])
    )


def test_pairwise_contribution_formula():
    result = mack_risk_attribution(sample(), matrix(0.4))
    se = result["segments"]["standalone_se"].to_numpy()
    assert result["pairs"].iloc[0]["cross_variance"] == pytest.approx(
        2 * 0.4 * se[0] * se[1],
    )


def test_negative_pair_contribution_is_preserved():
    result = mack_risk_attribution(sample(), matrix(-0.3))
    assert result["pairs"].iloc[0]["cross_variance"] < 0


def test_three_segment_pair_count():
    segments = {**sample(), "Liability": synthetic_triangle(8, seed=1) * 1.3}
    names = sorted(segments)
    correlation = pd.DataFrame(np.eye(3), index=names, columns=names)
    result = mack_risk_attribution(segments, correlation)
    assert len(result["segments"]) == 3
    assert len(result["pairs"]) == 3
    assert result["pairs"]["cross_variance"].eq(0).all()


def test_invalid_matrix_rejected():
    with pytest.raises(ValueError, match="symmetric"):
        mack_risk_attribution(
            sample(),
            pd.DataFrame(
                [[1, 0.2], [0.3, 1]],
                index=["Motor", "Property"], columns=["Motor", "Property"],
            ),
        )
