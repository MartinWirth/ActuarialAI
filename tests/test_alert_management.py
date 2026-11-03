import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from actuarial_ai.alert_management import list_managed_alerts, transition_alert
from actuarial_ai.alert_notifications import send_critical_alerts
from actuarial_ai.risk_monitor import save_monitoring_run, verify_monitoring_audit


def _snapshot(status):
    return {
        "schema_version": "1.0",
        "as_of_utc": "2026-11-03T04:00:00+00:00",
        "overall_status": status,
        "metrics": {"total_se": 123.0, "diversification_pct": 0.2},
        "checks": [
            {"scope": "portfolio", "name": "Mack standard error",
             "status": status, "value": 123.0},
        ],
    }


def test_lifecycle_and_audit(tmp_path):
    db = tmp_path / "alerts.sqlite3"
    save_monitoring_run(db, _snapshot("red"))
    alert = list_managed_alerts(db)[0]
    assert alert["state"] == "new"
    event = transition_alert(db, alert["alert_id"], "acknowledged", "operator-1")
    assert event["from"] == "new"
    assert list_managed_alerts(db, "acknowledged")[0]["actor"] == "operator-1"
    transition_alert(db, alert["alert_id"], "resolved", "operator-2")
    assert list_managed_alerts(db, "resolved")[0]["state"] == "resolved"
    assert verify_monitoring_audit(db)


def test_invalid_transitions_are_atomic(tmp_path):
    db = tmp_path / "alerts.sqlite3"
    save_monitoring_run(db, _snapshot("yellow"))
    alert_id = list_managed_alerts(db)[0]["alert_id"]
    with pytest.raises(ValueError):
        transition_alert(db, alert_id, "resolved", " ")
    transition_alert(db, alert_id, "resolved", "reviewer")
    with pytest.raises(ValueError):
        transition_alert(db, alert_id, "acknowledged", "reviewer")
    with pytest.raises(ValueError):
        transition_alert(db, 9999, "resolved", "reviewer")
    assert verify_monitoring_audit(db)
    with sqlite3.connect(db) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM monitoring_audit WHERE event_type='alert_transition'"
        ).fetchone()[0] == 1


def test_email_opt_in_and_critical_only(monkeypatch):
    alerts = [
        {"scope": "portfolio", "name": "SE", "previous_status": "yellow",
         "status": "red"},
        {"scope": "segment", "name": "Motor", "previous_status": "green",
         "status": "yellow"},
    ]
    monkeypatch.delenv("ACTUARIALAI_SMTP_HOST", raising=False)
    assert send_critical_alerts(alerts, run_id=1) == 0
    monkeypatch.setenv("ACTUARIALAI_SMTP_HOST", "mail.example.test")
    monkeypatch.setenv("ACTUARIALAI_ALERT_TO", "risk@example.test")
    monkeypatch.setenv("ACTUARIALAI_ALERT_FROM", "alerts@example.test")
    server = MagicMock()
    server.__enter__.return_value = server
    with patch("actuarial_ai.alert_notifications.smtplib.SMTP_SSL", return_value=server):
        assert send_critical_alerts(alerts, run_id=1) == 1
        message = server.send_message.call_args.args[0]
        assert "Motor" not in message.get_content()
        assert "SE" in message.get_content()
