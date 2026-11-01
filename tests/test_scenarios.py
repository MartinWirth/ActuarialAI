import numpy as np
import pandas as pd
import pytest

from actuarial_ai import chain_ladder, synthetic_triangle
from actuarial_ai.scenarios import (
    scenario_comparison,
    sensitivity_grid,
    stress_reserves,
)


def test_zero_stress_equals_baseline():
    triangle = synthetic_triangle(8)
    outcome = stress_reserves(triangle)
    assert outcome["total_reserve"] == pytest.approx(chain_ladder(triangle)["total_reserve"])
    assert outcome["reserve_delta"] == pytest.approx(0)
    pd.testing.assert_frame_equal(outcome["completed"], chain_ladder(triangle)["completed"])


def test_observed_cells_unchanged():
    triangle = synthetic_triangle(8)
    outcome = stress_reserves(triangle, inflation=0.1, factor_stress=0.2)
    for i in range(len(triangle)):
        np.testing.assert_allclose(
            outcome["completed"].iloc[i, : len(triangle) - i],
            triangle.iloc[i, : len(triangle) - i],
        )


def test_stress_monotonicity():
    triangle = synthetic_triangle(8)
    results = scenario_comparison(triangle)
    assert list(results["scenario"]) == ["Best case", "Base case", "Worst case"]
    assert results["total_reserve"].is_monotonic_increasing


def test_sensitivity_grid_and_reproducibility():
    triangle = synthetic_triangle(7)
    first = sensitivity_grid(triangle)
    second = sensitivity_grid(triangle)
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 9


@pytest.mark.parametrize("kwargs", [
    {"inflation": -1.0}, {"inflation": np.nan},
    {"factor_stress": -1.0}, {"factor_stress": np.inf},
])
def test_invalid_stress_rejected(kwargs):
    with pytest.raises(ValueError):
        stress_reserves(synthetic_triangle(6), **kwargs)


def test_scenario_magnitude_validation():
    with pytest.raises(ValueError):
        scenario_comparison(synthetic_triangle(6), inflation=-0.1)
