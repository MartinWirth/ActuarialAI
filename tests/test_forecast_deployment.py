import sqlite3

import pytest

from actuarial_ai.auth import create_user, login
from actuarial_ai.forecast_deployment import (
    active_forecast_model,
    champion_challenger,
    deploy_forecast_model,
    deployment_history,
)
from actuarial_ai.forecast_model_registry import (
    register_forecast_model,
    transition_forecast_model,
)


def setup_models(tmp_path):
    path = tmp_path / "models.sqlite3"
    create_user(path, "admin", "strong-password-123", "ADMIN")
    admin = login(path, "admin", "strong-password-123")
    create_user(
        path, "reviewer", "another-password-123", "REVIEWER",
        admin_token=admin,
    )
    reviewer = login(path, "reviewer", "another-password-123")
    trend = [{"total_se": v} for v in [10, 20, 30, 40, 50, 60]]
    ids = []
    for name in ("linear", "naive"):
        model_id = register_forecast_model(
            path, admin, trend, model_name=name,
        )["model_id"]
        transition_forecast_model(path, admin, model_id, "IN_REVIEW", "submit")
        transition_forecast_model(
            path, reviewer, model_id, "APPROVED", "reviewed",
        )
        ids.append(model_id)
    return path, admin, reviewer, ids


def test_activate_compare_and_rollback(tmp_path):
    path, admin, reviewer, ids = setup_models(tmp_path)
    assert active_forecast_model(path, reviewer) is None
    with pytest.raises(PermissionError):
        deploy_forecast_model(path, admin, ids[0], "not permitted")
    deploy_forecast_model(path, reviewer, ids[0], "initial")
    assert active_forecast_model(path, reviewer)["model_id"] == ids[0]
    compare = champion_challenger(path, reviewer)
    assert {row["role"] for row in compare} == {"champion", "challenger"}
    deploy_forecast_model(path, reviewer, ids[1], "replace")
    with pytest.raises(ValueError):
        deploy_forecast_model(path, reviewer, ids[0], "old")
    deploy_forecast_model(path, reviewer, ids[0], "restore", rollback=True)
    assert active_forecast_model(path, reviewer)["model_id"] == ids[0]
    assert len(deployment_history(path, reviewer)) == 3


def test_invalid_targets_and_tampering(tmp_path):
    path, admin, reviewer, ids = setup_models(tmp_path)
    with pytest.raises(ValueError):
        deploy_forecast_model(path, reviewer, ids[1], "rollback", rollback=True)
    with pytest.raises(ValueError):
        deploy_forecast_model(path, reviewer, ids[0], "")
    with pytest.raises(ValueError):
        deploy_forecast_model(path, reviewer, 999, "unknown")
    deploy_forecast_model(path, reviewer, ids[0], "initial")
    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE forecast_deployments SET reason='altered' WHERE id=1",
        )
    with pytest.raises(ValueError):
        active_forecast_model(path, reviewer)
    with pytest.raises(ValueError):
        deploy_forecast_model(path, reviewer, ids[1], "next")
