import numpy as np
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.mack import mack_chain_ladder
from actuarial_ai.portfolio_mack import aggregate_mack


def sample():
    return {"Motor": synthetic_triangle(8, seed=1),
            "Property": synthetic_triangle(9, seed=2)}


def test_independent_segments_sum_variances():
    result = aggregate_mack(sample(), correlation=0)
    individual = [mack_chain_ladder(t) for t in sample().values()]
    assert result["total_reserve"] == pytest.approx(
        sum(x["total_reserve"] for x in individual)
    )
    assert result["total_mse"] == pytest.approx(
        sum(x["total_se"] ** 2 for x in individual)
    )
    assert result["total_se"] == pytest.approx(result["independent_se"])


def test_perfect_positive_correlation_sums_standard_errors():
    result = aggregate_mack(sample(), correlation=1)
    assert result["total_se"] == pytest.approx(result["sum_segment_se"])
    assert result["diversification_benefit"] == pytest.approx(0, abs=1e-7)


def test_partial_correlation_between_extremes():
    low = aggregate_mack(sample(), correlation=0)
    mid = aggregate_mack(sample(), correlation=0.5)
    high = aggregate_mack(sample(), correlation=1)
    assert low["total_se"] < mid["total_se"] < high["total_se"]
    assert mid["lower"] <= mid["total_reserve"] <= mid["upper"]


def test_invalid_inputs_and_incomplete_portfolio():
    with pytest.raises(ValueError, match="At least one"):
        aggregate_mack({})
    with pytest.raises(ValueError, match="correlation"):
        aggregate_mack(sample(), correlation=1.1)
    with pytest.raises(ValueError, match="confidence"):
        aggregate_mack(sample(), confidence=1)
    with pytest.raises(ValueError, match="unavailable"):
        aggregate_mack({"short": synthetic_triangle(3), **sample()})


def test_negative_equicorrelation_bound():
    segments = sample()
    segments["Third"] = sample()["Motor"] * 1.1
    valid = aggregate_mack(segments, correlation=-0.5)
    assert np.isfinite(valid["total_se"])
    with pytest.raises(ValueError, match="correlation"):
        aggregate_mack(segments, correlation=-0.6)
