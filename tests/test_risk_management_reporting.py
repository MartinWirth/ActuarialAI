from datetime import datetime, timedelta, timezone
from io import BytesIO

from pypdf import PdfReader

from actuarial_ai.alert_automation import process_alert_automation
from actuarial_ai.alert_management import list_managed_alerts, transition_alert
from actuarial_ai.risk_management_reporting import (
    report_csv,
    report_pdf,
    risk_management_report,
)
from actuarial_ai.risk_monitor import save_monitoring_run


def snapshot(status, when):
    return {
        "schema_version": "1.0", "as_of_utc": when,
        "overall_status": status,
        "metrics": {"total_se": 100.0, "diversification_pct": 0.1},
        "checks": [{
            "scope": "portfolio", "name": "Mack standard error",
            "status": status, "value": 100.0,
        }],
    }


def test_reporting_kpis_sla_and_exports(tmp_path):
    db = tmp_path / "risk.sqlite3"
    now = datetime.now(timezone.utc)
    save_monitoring_run(db, snapshot("red", "2026-11-01T00:00:00+00:00"))
    alert_id = list_managed_alerts(db)[0]["alert_id"]
    report = risk_management_report(
        db, sla_hours=1, now=now + timedelta(hours=2),
    )
    assert report["kpis"]["open_alerts"] == 1
    assert report["kpis"]["critical_open"] == 1
    assert report["kpis"]["sla_breaches"] == 1
    assert report["kpis"]["monitoring_runs"] == 1
    assert b"alert_id" in report_csv(report)
    pdf = report_pdf(report)
    assert PdfReader(BytesIO(pdf)).pages

    process_alert_automation(db, critical_after_hours=1, now=now + timedelta(hours=2))
    escalated = risk_management_report(db, now=now + timedelta(hours=2))
    assert escalated["kpis"]["escalated_open"] == 1
    transition_alert(db, alert_id, "resolved", "reviewer")
    closed = risk_management_report(db, now=now + timedelta(hours=2))
    assert closed["kpis"]["resolved_alerts"] == 1
    assert closed["kpis"]["open_alerts"] == 0
    assert closed["kpis"]["mean_resolution_hours"] is not None


def test_empty_database_reports(tmp_path):
    report = risk_management_report(tmp_path / "empty.db")
    assert report["kpis"]["total_alerts"] == 0
    assert report["risk_trend"] == []
    assert report_pdf(report).startswith(b"%PDF")
    assert b"alert_id" in report_csv(report)
