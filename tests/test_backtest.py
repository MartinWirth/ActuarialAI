import numpy as np
import pandas as pd
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.backtest import backtest_metrics, rolling_backtest


def test_backtest_is_reproducible():
    triangle = synthetic_triangle(10, seed=7)
    pd.testing.assert_frame_equal(rolling_backtest(triangle), rolling_backtest(triangle))


def test_same_holdout_for_both_models():
    predictions = rolling_backtest(synthetic_triangle(10))
    assert not predictions.empty
    assert np.isfinite(predictions[["actual", "chain_ladder", "random_forest"]]).all().all()
    metrics = backtest_metrics(predictions)
    assert metrics.loc["chain_ladder", "n"] == metrics.loc["random_forest", "n"]
    assert (metrics[["MAE", "RMSE"]] >= 0).all().all()


def test_no_future_leakage_from_holdout_changes():
    original = synthetic_triangle(10)
    altered = original.copy()
    # The last calendar diagonal is not available to any training snapshot.
    for i in range(10):
        altered.iat[i, 9 - i] *= 2
    a = rolling_backtest(original)
    b = rolling_backtest(altered)
    pd.testing.assert_frame_equal(a.drop(columns=['actual']), b.drop(columns=['actual']))


def test_insufficient_holdout_raises():
    with pytest.raises(ValueError):
        backtest_metrics(pd.DataFrame())
