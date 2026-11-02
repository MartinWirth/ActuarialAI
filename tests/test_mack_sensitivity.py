import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.mack_sensitivity import mack_correlation_sensitivity
from actuarial_ai.portfolio_mack import aggregate_mack


def sample():
    a = synthetic_triangle(8, seed=1)
    return {
        "Motor": a,
        "Property": synthetic_triangle(9, seed=2),
    }


def test_sensitivity_matches_aggregation_and_is_monotonic():
    grid = mack_correlation_sensitivity(sample())
    assert len(grid) == 5
    assert grid["total_se"].is_monotonic_increasing
    assert grid["diversification_benefit"].is_monotonic_decreasing
    for _, row in grid.iterrows():
        actual = aggregate_mack(sample(), correlation=row["correlation"])
        for key in ("total_reserve", "total_se", "lower", "upper",
                    "diversification_benefit"):
            assert row[key] == pytest.approx(actual[key])


def test_custom_scenarios_preserve_order():
    grid = mack_correlation_sensitivity(sample(), correlations=(1, 0, 0.5))
    assert grid["correlation"].tolist() == [1, 0, 0.5]


@pytest.mark.parametrize("values", [(), (0, 0), (0, 1.1), (float("nan"),)])
def test_invalid_scenarios(values):
    with pytest.raises(ValueError):
        mack_correlation_sensitivity(sample(), correlations=values)


def test_unestimable_segment_is_not_silently_dropped():
    with pytest.raises(ValueError, match="unavailable"):
        mack_correlation_sensitivity({"short": synthetic_triangle(3), **sample()})
