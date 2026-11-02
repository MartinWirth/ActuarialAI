import numpy as np
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.portfolio_risk import simulate_portfolio_risk


def segments():
    return {"Motor": synthetic_triangle(6, seed=1),
            "Property": synthetic_triangle(7, seed=2)}


def test_deterministic_seed_and_tail_metrics():
    first = simulate_portfolio_risk(segments(), simulations=1000, seed=7)
    second = simulate_portfolio_risk(segments(), simulations=1000, seed=7)
    np.testing.assert_array_equal(first["portfolio_samples"], second["portfolio_samples"])
    assert first["expected_shortfall"] >= first["var"]
    assert first["var"] > 0


def test_zero_volatility_matches_baseline():
    result = simulate_portfolio_risk(segments(), simulations=100, volatility=0)
    np.testing.assert_allclose(result["portfolio_samples"], result["baseline_total_reserve"])
    assert result["var"] == pytest.approx(result["baseline_total_reserve"])
    assert result["expected_shortfall"] == pytest.approx(result["baseline_total_reserve"])


def test_segment_sums_equal_portfolio_samples():
    result = simulate_portfolio_risk(segments(), simulations=200)
    np.testing.assert_allclose(
        result["samples"].sum(axis=1), result["portfolio_samples"]
    )


def test_correlation_one_gives_common_multiplier():
    result = simulate_portfolio_risk(segments(), simulations=500, correlation=1)
    data = result["samples"].to_numpy()
    base = result["segment_summary"]["baseline_reserve"].to_numpy()
    np.testing.assert_allclose(data[:, 0] / base[0], data[:, 1] / base[1])


@pytest.mark.parametrize("kwargs", [
    {"simulations": 50}, {"volatility": -0.1}, {"volatility": np.nan},
    {"correlation": -0.1}, {"correlation": 1.1}, {"confidence": 1},
    {"confidence": 0}, {"seed": -1},
])
def test_invalid_parameters(kwargs):
    with pytest.raises(ValueError):
        simulate_portfolio_risk(segments(), **kwargs)


def test_single_segment_supported():
    result = simulate_portfolio_risk({"Motor": synthetic_triangle(6)})
    assert result["samples"].shape[1] == 1
