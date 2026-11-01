import numpy as np
import pandas as pd
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.explainability import factor_feature_importance
from actuarial_ai.uncertainty import bootstrap_reserves


def test_bootstrap_reproducible():
    triangle = synthetic_triangle(8)
    a = bootstrap_reserves(triangle, simulations=50, seed=12)
    b = bootstrap_reserves(triangle, simulations=50, seed=12)
    np.testing.assert_array_equal(a["samples"], b["samples"])
    assert a["lower"] <= a["upper"]


def test_bootstrap_rejects_invalid_settings():
    triangle = synthetic_triangle(8)
    with pytest.raises(ValueError):
        bootstrap_reserves(triangle, simulations=1)
    with pytest.raises(ValueError):
        bootstrap_reserves(triangle, confidence=1.0)


def test_importance_is_reproducible():
    triangle = synthetic_triangle(8)
    a = factor_feature_importance(triangle)
    b = factor_feature_importance(triangle)
    pd.testing.assert_frame_equal(a, b)
    assert set(a["feature"]) == {"development", "paid"}
    assert np.isfinite(a["importance_mean"]).all()
