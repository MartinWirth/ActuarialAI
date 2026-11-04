import sqlite3

import pytest

from actuarial_ai.auth import create_user, login
from actuarial_ai.forecast_deployment import deploy_forecast_model
from actuarial_ai.forecast_execution import (
    execute_active_forecast,
    forecast_execution_history,
)
from actuarial_ai.forecast_model_registry import (
    register_forecast_model,
    transition_forecast_model,
)


def setup_execution(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    create_user(path, "admin", "strong-password-123", "ADMIN")
    admin = login(path, "admin", "strong-password-123")
    create_user(
        path, "reviewer", "another-password-123", "REVIEWER",
        admin_token=admin,
    )
    reviewer = login(path, "reviewer", "another-password-123")
    trend = [{"total_se": value} for value in [10, 20, 30, 40, 50, 60]]
    return path, admin, reviewer, trend


@pytest.mark.parametrize("name", ["linear", "moving_average", "naive"])
def test_active_model_executes_and_logs(tmp_path, name):
    path, admin, reviewer, trend = setup_execution(tmp_path)
    with pytest.raises(ValueError, match="No approved active"):
        execute_active_forecast(path, admin, trend)
    model_id = register_forecast_model(
        path, admin, trend, model_name=name,
    )["model_id"]
    transition_forecast_model(path, admin, model_id, "IN_REVIEW", "submit")
    transition_forecast_model(path, reviewer, model_id, "APPROVED", "ok")
    deploy_forecast_model(path, reviewer, model_id, "activate")
    result = execute_active_forecast(path, admin, trend, horizon=2)
    assert result["model_name"] == name
    assert result["model_id"] == model_id
    assert len(result["forecast"]) == 2
    if name == "linear":
        assert result["forecast"][0]["estimate"] == pytest.approx(70)
    elif name == "naive":
        assert result["forecast"][0]["estimate"] == pytest.approx(60)
    else:
        assert result["forecast"][0]["estimate"] == pytest.approx(50)
    records = forecast_execution_history(path, reviewer)
    assert len(records) == 1
    assert records[0]["integrity_valid"]


def test_runtime_input_and_integrity(tmp_path):
    path, admin, reviewer, trend = setup_execution(tmp_path)
    with pytest.raises(ValueError):
        execute_active_forecast(path, admin, trend[:2])
    with pytest.raises(TypeError):
        execute_active_forecast(path, admin, trend, horizon=True)
    with pytest.raises(PermissionError):
        forecast_execution_history(path, "invalid")
    model_id = register_forecast_model(path, admin, trend)["model_id"]
    transition_forecast_model(path, admin, model_id, "IN_REVIEW", "submit")
    transition_forecast_model(path, reviewer, model_id, "APPROVED", "review")
    deploy_forecast_model(path, reviewer, model_id, "activate")
    execute_active_forecast(path, admin, trend)
    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE forecast_executions SET result_json='{}' WHERE id=1"
        )
    assert not forecast_execution_history(path, reviewer)[0]["integrity_valid"]
