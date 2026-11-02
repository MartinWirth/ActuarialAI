import numpy as np
import pandas as pd
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.risk_sensitivity import portfolio_risk_sensitivity


def segments():
    return {"Motor": synthetic_triangle(6, seed=1),
            "Property": synthetic_triangle(7, seed=2)}


def test_grid_shape_and_reproducibility():
    kwargs = {"volatilities": (0.0, 0.2), "correlations": (0.0, 0.8),
              "simulations": 200, "seed": 9}
    first = portfolio_risk_sensitivity(segments(), **kwargs)
    second = portfolio_risk_sensitivity(segments(), **kwargs)
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 4
    np.testing.assert_array_less(
        first["var"].to_numpy(),
        first["expected_shortfall"].to_numpy() + 1e-8,
    )
    assert first["baseline_reserve"].nunique() == 1


def test_zero_volatility_has_no_simulation_risk():
    grid = portfolio_risk_sensitivity(
        segments(), volatilities=(0.0,), correlations=(0.0, 1.0),
        simulations=100,
    )
    np.testing.assert_allclose(grid["var"], grid["baseline_reserve"])
    np.testing.assert_allclose(grid["expected_shortfall"], grid["baseline_reserve"])


@pytest.mark.parametrize("kwargs", [
    {"volatilities": ()}, {"correlations": ()},
    {"volatilities": (-0.1,)}, {"volatilities": (float("nan"),)},
    {"volatilities": (2.1,)}, {"correlations": (-0.1,)},
    {"correlations": (float("inf"),)}, {"correlations": (1.1,)},
    {"simulations": 20},
])
def test_invalid_inputs(kwargs):
    with pytest.raises(ValueError):
        portfolio_risk_sensitivity(segments(), **kwargs)
