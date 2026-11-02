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


def test_raa_published_reference_regression():
    """Cross-check Mack alpha=1, est.sigma='Mack' against R ChainLadder RAA."""
    from pathlib import Path

    path = Path(__file__).parent / "fixtures" / "raa_triangle.csv"
    triangle = pd.read_csv(path, index_col=0)
    result = mack_chain_ladder(triangle, confidence=0.95)
    summary = result["summary"]

    # R ChainLadder vignette, MackChainLadder(RAA, est.sigma="Mack"):
    # total IBNR 52135.23, total Mack S.E. 26909.01.
    assert result["total_reserve"] == pytest.approx(52135.23, abs=0.02)
    assert result["total_se"] == pytest.approx(26909.01, abs=0.02)
    assert result["total_mse"] == pytest.approx(result["total_se"] ** 2)
    assert result["total_mse"] > float((summary["mack_se"] ** 2).sum())

    # Published origin-level reserve and S.E., rounded to whole units.
    expected_reserve = [0, 154, 617, 1636, 2747, 3649, 5435, 10907, 10650, 16339]
    expected_se = [0, 206, 623, 747, 1469, 2002, 2209, 5358, 6333, 24566]
    np.testing.assert_allclose(summary["reserve"], expected_reserve, atol=0.51)
    np.testing.assert_allclose(summary["mack_se"], expected_se, atol=0.51)
    np.testing.assert_allclose(
        summary["reserve"],
        chain_ladder(triangle, allow_decrease=True)["summary"]["reserve"],
        rtol=1e-12,
        atol=1e-9,
    )
    assert np.isfinite(result["sigma2"]).all()
    assert (result["sigma2"] >= 0).all()
    assert (summary["lower"] >= 0).all()
    assert (summary["upper"] >= summary["reserve"]).all()


def test_raa_confidence_changes_only_intervals():
    from pathlib import Path

    path = Path(__file__).parent / "fixtures" / "raa_triangle.csv"
    triangle = pd.read_csv(path, index_col=0)
    narrow = mack_chain_ladder(triangle, confidence=0.8)
    wide = mack_chain_ladder(triangle, confidence=0.99)
    assert narrow["total_reserve"] == pytest.approx(wide["total_reserve"])
    assert narrow["total_se"] == pytest.approx(wide["total_se"])
    assert narrow["total_mse"] == pytest.approx(wide["total_mse"])
    assert wide["total_upper"] > narrow["total_upper"]
    assert wide["total_lower"] <= narrow["total_lower"]
