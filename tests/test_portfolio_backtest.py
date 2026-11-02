import numpy as np
import pandas as pd
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.portfolio_backtest import portfolio_backtest


def segments():
    return {"Motor": synthetic_triangle(10, seed=1),
            "Property": synthetic_triangle(9, seed=2)}


def test_aggregation_and_metrics():
    report = portfolio_backtest(segments())
    detail = report["by_segment"]
    totals = report["portfolio"]
    assert report["common_valuations"] > 0
    assert detail.groupby("valuation")["segment"].nunique().eq(2).all()
    expected = detail.groupby("valuation")["actual"].sum()
    np.testing.assert_allclose(totals.set_index("valuation")["actual"], expected)
    assert set(report["metrics"]["model"]) == {"chain_ladder", "random_forest"}
    assert report["metrics"]["underprediction_rate"].between(0, 1).all()


def test_reproducible_and_no_future_leakage():
    first = portfolio_backtest(segments())
    second = portfolio_backtest(segments())
    pd.testing.assert_frame_equal(first["portfolio"], second["portfolio"])
    altered = segments()
    for triangle in altered.values():
        n = len(triangle)
        for i in range(n):
            triangle.iat[i, n - 1 - i] *= 2
    changed = portfolio_backtest(altered)
    for model in ("chain_ladder", "random_forest"):
        np.testing.assert_allclose(first["portfolio"][model], changed["portfolio"][model])


def test_invalid_and_insufficient_inputs():
    with pytest.raises(ValueError):
        portfolio_backtest({})
    with pytest.raises(ValueError):
        portfolio_backtest({"": synthetic_triangle(8)})
    with pytest.raises(ValueError):
        portfolio_backtest({"short": synthetic_triangle(4)})
