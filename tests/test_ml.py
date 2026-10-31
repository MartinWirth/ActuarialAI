import numpy as np
import pandas as pd
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.ml import development_samples, holdout_last_diagonal, ml_reserving


def test_samples_only_use_observed_pairs():
    triangle = synthetic_triangle(8)
    samples = development_samples(triangle)
    assert len(samples) == sum(range(1, 8))
    assert np.isfinite(samples["factor"]).all()


def test_ml_reserves_are_nonnegative():
    result = ml_reserving(synthetic_triangle(8))
    assert result["training_pairs"] == 28
    assert (result["summary"]["reserve"] >= -1e-8).all()


def test_ml_reproducible():
    triangle = synthetic_triangle(8, seed=21)
    a = ml_reserving(triangle)
    b = ml_reserving(triangle)
    pd.testing.assert_frame_equal(a["summary"], b["summary"])


def test_holdout_no_future_observations():
    result = holdout_last_diagonal(synthetic_triangle(8))
    assert np.isfinite(result["mae"])
    assert result["mae"] >= 0
    assert len(result["predictions"]) > 0


def test_sparse_data_rejected():
    with pytest.raises(ValueError):
        ml_reserving(synthetic_triangle(3))
