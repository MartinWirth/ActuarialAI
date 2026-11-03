import pytest

from actuarial_ai.risk_forecast_validation import validate_risk_forecasts


def trend(values):
    return [{"total_se": value} for value in values]


def test_linear_trend_prefers_linear_model():
    result = validate_risk_forecasts(trend([10, 20, 30, 40, 50, 60]))
    assert result["model_version"] == "36.1"
    assert result["best_model_by_mae"] == "linear"
    assert result["metrics"][0]["mae"] == pytest.approx(0)
    assert all(row["holdouts"] == 3 for row in result["metrics"])
    assert len(result["backtest"]) == 9


def test_constant_series_no_drift_and_zero_mape():
    result = validate_risk_forecasts(trend([0] * 8))
    assert not result["drift_detected"]
    assert all(row["mape_pct"] is None for row in result["metrics"])


def test_structural_shift_is_detected():
    result = validate_risk_forecasts(
        trend([10, 10, 10, 100, 100, 100]), window=3,
    )
    assert result["drift_detected"]
    assert result["drift_score"] is None


@pytest.mark.parametrize(
    ("values", "kwargs"),
    [
        ([1, 2, 3], {}),
        ([1, 2, 3, 4, 5], {"window": 3}),
        ([1, 2, 3, 4, float("nan"), 6], {}),
        ([1, 2, 3, 4, -5, 6], {}),
        ([1, 2, 3, 4, 5, 6], {"window": 1}),
        ([1, 2, 3, 4, 5, 6], {"drift_threshold": 0}),
    ],
)
def test_invalid_inputs(values, kwargs):
    with pytest.raises(ValueError):
        validate_risk_forecasts(trend(values), **kwargs)
