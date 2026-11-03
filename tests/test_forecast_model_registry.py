import sqlite3

import pytest

from actuarial_ai.auth import create_user, login
from actuarial_ai.forecast_model_registry import (
    list_forecast_models,
    model_audit_events,
    register_forecast_model,
    transition_forecast_model,
    verify_model_audit,
)


def _setup(tmp_path):
    path = tmp_path / "governance.sqlite3"
    create_user(path, "admin", "strong-password-123", "ADMIN")
    admin = login(path, "admin", "strong-password-123")
    create_user(
        path, "reviewer", "another-password-123", "REVIEWER",
        admin_token=admin,
    )
    reviewer = login(path, "reviewer", "another-password-123")
    trend = [{"total_se": value} for value in [10, 20, 30, 40, 50, 60]]
    return path, admin, reviewer, trend


def test_registry_approval_and_audit(tmp_path):
    path, admin, reviewer, trend = _setup(tmp_path)
    record = register_forecast_model(path, admin, trend)
    model_id = record["model_id"]
    assert list_forecast_models(path, admin)[0]["status"] == "DRAFT"
    assert verify_model_audit(path, admin, model_id)
    with pytest.raises(PermissionError):
        transition_forecast_model(path, reviewer, model_id, "IN_REVIEW", "submit")
    transition_forecast_model(path, admin, model_id, "IN_REVIEW", "ready")
    with pytest.raises(PermissionError):
        transition_forecast_model(path, admin, model_id, "APPROVED", "self")
    transition_forecast_model(path, reviewer, model_id, "APPROVED", "validated")
    assert list_forecast_models(path, reviewer)[0]["status"] == "APPROVED"
    assert len(model_audit_events(path, reviewer, model_id)) == 2
    assert verify_model_audit(path, reviewer, model_id)
    with pytest.raises(ValueError):
        transition_forecast_model(path, reviewer, model_id, "REJECTED", "late")


def test_registry_rejects_bad_validation_and_tampering(tmp_path):
    path, admin, reviewer, trend = _setup(tmp_path)
    with pytest.raises(ValueError):
        register_forecast_model(path, admin, trend[:2])
    with pytest.raises(ValueError):
        register_forecast_model(path, admin, trend, model_name="unknown")
    model_id = register_forecast_model(path, admin, trend)["model_id"]
    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE forecast_models SET model_name='tampered' WHERE id=?",
            (model_id,),
        )
    assert not verify_model_audit(path, reviewer, model_id)
    with pytest.raises(ValueError):
        transition_forecast_model(path, admin, model_id, "IN_REVIEW", "review")


def test_requires_authenticated_permissions(tmp_path):
    path, admin, reviewer, trend = _setup(tmp_path)
    with pytest.raises(PermissionError):
        register_forecast_model(path, reviewer, trend)
    with pytest.raises(PermissionError):
        list_forecast_models(path, "invalid")
    record = register_forecast_model(path, admin, trend)
    with pytest.raises(ValueError):
        transition_forecast_model(
            path, admin, record["model_id"], "IN_REVIEW", "",
        )
