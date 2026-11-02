import numpy as np
import pandas as pd
import pytest

from actuarial_ai import chain_ladder, synthetic_triangle
from actuarial_ai.mack import mack_chain_ladder


def test_mack_matches_deterministic_point_estimate():
    triangle = synthetic_triangle(8, seed=42)
    result = mack_chain_ladder(triangle)
    assert result["total_reserve"] == pytest.approx(
        chain_ladder(triangle)["total_reserve"]
    )
    assert np.isfinite(result["total_se"])
    assert result["total_se"] > 0
    assert len(result["sigma2"]) == 7
    assert (result["summary"]["mack_se"] >= 0).all()
    assert result["summary"].iloc[0]["mack_se"] == pytest.approx(0)


def test_confidence_controls_interval_width():
    triangle = synthetic_triangle(8, seed=11)
    narrow = mack_chain_ladder(triangle, confidence=0.8)
    wide = mack_chain_ladder(triangle, confidence=0.99)
    assert wide["total_upper"] > narrow["total_upper"]
    assert wide["total_se"] == pytest.approx(narrow["total_se"])


def test_invalid_inputs():
    triangle = synthetic_triangle(6)
    with pytest.raises(ValueError, match="confidence"):
        mack_chain_ladder(triangle, confidence=1)
    with pytest.raises(ValueError, match="four"):
        mack_chain_ladder(synthetic_triangle(3))


def test_zero_variance_extrapolation_is_explicit():
    triangle = pd.DataFrame([
        [100., 150., 180., 200.],
        [120., 180., 216., np.nan],
        [130., 195., np.nan, np.nan],
        [140., np.nan, np.nan, np.nan],
    ])
    with pytest.raises(ValueError, match="extrapolate"):
        mack_chain_ladder(triangle)
