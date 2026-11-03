import pytest

from actuarial_ai.risk_forecasting import forecast_mack_risk


def history(values):
    return [{"total_se": value} for value in values]


def test_rising_forecast_warning_and_backtest():
    result = forecast_mack_risk(
        history([100, 110, 120, 130, 140]),
        horizon=3, warning=145, critical=165,
    )
    assert result["trend"] == "rising"
    assert result["walk_forward_mae"] == pytest.approx(0)
    assert len(result["forecast"]) == 3
    assert result["forecast"][0]["projected_status"] == "yellow"
    assert result["forecast"][2]["projected_status"] == "red"
    assert all(r["lower"] <= r["estimate"] <= r["upper"]
               for r in result["forecast"])


def test_falling_trend_is_clamped_nonnegative():
    result = forecast_mack_risk(history([50, 40, 30, 20]), horizon=5)
    assert result["trend"] == "falling"
    assert result["forecast"][-1]["estimate"] == 0
    assert result["forecast"][0]["projected_status"] == "unconfigured"


def test_early_warning_from_residual_band():
    result = forecast_mack_risk(
        history([100, 105, 110, 130, 125, 140]),
        warning=150, critical=200,
    )
    assert any(row["early_warning"] for row in result["forecast"])


@pytest.mark.parametrize(
    ("values", "kwargs"),
    [
        ([1, 2, 3], {}),
        ([1, 2, 3, float("nan")], {}),
        ([1, -2, 3, 4], {}),
        ([1, 2, 3, 4], {"horizon": 0}),
        ([1, 2, 3, 4], {"warning": 10}),
        ([1, 2, 3, 4], {"warning": 20, "critical": 10}),
        ([1, 2, 3, 4], {"stress_pct": -1}),
    ],
)
def test_invalid_inputs(values, kwargs):
    with pytest.raises(ValueError):
        forecast_mack_risk(history(values), **kwargs)
