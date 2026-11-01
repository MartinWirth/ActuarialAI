import pandas as pd
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.backtest import rolling_backtest
from actuarial_ai.governance import monitoring_report


def test_monitoring_is_reproducible_and_counts_observations():
    predictions = rolling_backtest(synthetic_triangle(10))
    report = monitoring_report(predictions)
    assert report["overall"].loc["chain_ladder", "n"] == len(predictions)
    assert report["by_valuation"]["observations"].sum() == len(predictions)
    assert report["alert_count"] >= 0
    pd.testing.assert_frame_equal(report["by_valuation"],
                                  monitoring_report(predictions)["by_valuation"])


def test_alert_detects_degraded_candidate():
    predictions = pd.DataFrame({
        "valuation": [3, 3], "actual": [100., 120.],
        "chain_ladder": [100., 120.], "random_forest": [130., 150.],
    })
    assert monitoring_report(predictions)["alert_count"] == 1


def test_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        monitoring_report(pd.DataFrame())
    with pytest.raises(ValueError):
        monitoring_report(pd.DataFrame({"valuation": [1], "actual": [1],
                                        "chain_ladder": [1], "random_forest": [1]}),
                          alert_ratio=0)
