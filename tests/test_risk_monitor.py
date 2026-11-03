import json
import sqlite3

from actuarial_ai.risk_monitor import (
    load_monitoring_alerts,
    load_monitoring_runs,
    save_monitoring_run,
    verify_monitoring_audit,
)


def snapshot(day, status="green"):
    return {
        "schema_version": "1.0",
        "as_of_utc": f"2026-11-{day:02d}T12:00:00+00:00",
        "overall_status": status,
        "metrics": {"total_se": 100.0 + day, "diversification_pct": 0.2},
        "checks": [
            {"scope": "portfolio", "name": "Mack standard error",
             "status": status, "value": 100.0 + day},
        ],
    }


def test_persistence_and_deduplication(tmp_path):
    path = tmp_path / "monitor.db"
    first = save_monitoring_run(path, snapshot(1))
    assert first["created"]
    again = save_monitoring_run(path, snapshot(1))
    assert not again["created"]
    assert again["run_id"] == first["run_id"]
    assert len(load_monitoring_runs(path)) == 1
    assert verify_monitoring_audit(path)


def test_alert_transition_and_escalation(tmp_path):
    path = tmp_path / "monitor.db"
    save_monitoring_run(path, snapshot(1))
    yellow = save_monitoring_run(path, snapshot(2, "yellow"))
    assert yellow["alerts"][0]["transition"] == "new_breach"
    red = save_monitoring_run(path, snapshot(3, "red"))
    assert red["alerts"][0]["transition"] == "escalation"
    save_monitoring_run(path, snapshot(4, "red"))
    assert len(load_monitoring_alerts(path)) == 2
    assert verify_monitoring_audit(path)


def test_audit_detects_tampering(tmp_path):
    path = tmp_path / "monitor.db"
    save_monitoring_run(path, snapshot(1, "yellow"))
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE monitoring_audit SET payload_json=? WHERE id=1",
            (json.dumps({"tampered": True}),),
        )
    assert not verify_monitoring_audit(path)


def test_new_check_alerts_from_green(tmp_path):
    path = tmp_path / "monitor.db"
    save_monitoring_run(path, snapshot(1))
    changed = snapshot(2)
    changed["checks"].append({
        "scope": "segment", "name": "Motor",
        "status": "red", "value": 0.8,
    })
    result = save_monitoring_run(path, changed)
    assert result["alerts"][0]["name"] == "Motor"
