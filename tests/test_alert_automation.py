from datetime import datetime, timedelta, timezone

import pytest

from actuarial_ai.alert_automation import (
    alert_automation_overview,
    process_alert_automation,
)
from actuarial_ai.alert_management import list_managed_alerts, transition_alert
from actuarial_ai.risk_monitor import save_monitoring_run, verify_monitoring_audit


def snapshot(status, timestamp):
    return {
        "schema_version": "1.0",
        "as_of_utc": timestamp,
        "overall_status": status,
        "metrics": {"total_se": 120, "diversification_pct": 0.2},
        "checks": [
            {"scope": "portfolio", "name": "Mack standard error",
             "status": status, "value": 120},
        ],
    }


def test_auto_resolve_and_idempotency(tmp_path):
    db = tmp_path / "risk.sqlite3"
    save_monitoring_run(db, snapshot("red", "2026-11-01T00:00:00+00:00"))
    alert_id = list_managed_alerts(db)[0]["alert_id"]
    save_monitoring_run(db, snapshot("green", "2026-11-02T00:00:00+00:00"))
    first = process_alert_automation(db)
    assert first["resolved"] == [alert_id]
    assert process_alert_automation(db) == {"resolved": [], "escalated": []}
    assert list_managed_alerts(db)[0]["state"] == "resolved"
    assert verify_monitoring_audit(db)


def test_escalation_once_and_acknowledgement(tmp_path):
    db = tmp_path / "risk.sqlite3"
    save_monitoring_run(db, snapshot("red", "2026-11-01T00:00:00+00:00"))
    alert_id = list_managed_alerts(db)[0]["alert_id"]
    now = datetime.now(timezone.utc) + timedelta(hours=25)
    result = process_alert_automation(db, now=now)
    assert result["escalated"] == [alert_id]
    assert process_alert_automation(db, now=now)["escalated"] == []
    assert alert_automation_overview(db, now=now)[0]["escalated_utc"]
    transition_alert(db, alert_id, "acknowledged", "operator")
    assert process_alert_automation(db, now=now)["escalated"] == []
    assert verify_monitoring_audit(db)


def test_missing_check_does_not_auto_resolve(tmp_path):
    db = tmp_path / "risk.sqlite3"
    save_monitoring_run(db, snapshot("yellow", "2026-11-01T00:00:00+00:00"))
    save_monitoring_run(db, {
        "schema_version": "1.0",
        "as_of_utc": "2026-11-02T00:00:00+00:00",
        "overall_status": "green",
        "metrics": {"total_se": 120, "diversification_pct": 0.2},
        "checks": [
            {"scope": "segment", "name": "New",
             "status": "green", "value": 0},
        ],
    })
    assert process_alert_automation(db)["resolved"] == []
    assert list_managed_alerts(db)[0]["state"] == "new"


def test_reject_invalid_escalation_threshold(tmp_path):
    with pytest.raises(ValueError):
        process_alert_automation(tmp_path / "risk.db", critical_after_hours=0)
