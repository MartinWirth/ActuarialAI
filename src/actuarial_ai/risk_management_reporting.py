"""Read-only management reporting from the local monitoring database."""
import csv
import io
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from .alert_automation import alert_automation_overview
from .risk_monitor import _connect


def risk_management_report(
    path: str | Path, *, sla_hours: float = 24,
    now: datetime | None = None,
) -> dict:
    """Summarize alerts and persisted risk trends; no database mutations."""
    if not 0 < sla_hours <= 8760:
        raise ValueError("sla_hours must be in (0, 8760]")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    current = current.astimezone(timezone.utc)
    alerts = alert_automation_overview(path, now=current)
    with _connect(path) as db:
        created_by_alert = dict(db.execute(
            "SELECT a.id,r.created_utc FROM monitoring_alerts a "
            "JOIN monitoring_runs r ON r.id=a.run_id"
        ).fetchall())
        run_rows = db.execute(
            "SELECT id,created_utc,snapshot_json FROM monitoring_runs ORDER BY id"
        ).fetchall()
    trend = []
    for run_id, created, serialized in run_rows:
        snapshot = json.loads(serialized)
        trend.append({
            "run_id": run_id, "created_utc": created,
            "overall_status": snapshot["overall_status"],
            "total_se": float(snapshot["metrics"]["total_se"]),
            "diversification_pct": float(
                snapshot["metrics"]["diversification_pct"]
            ),
        })
    state_counts = Counter(a["state"] for a in alerts)
    open_alerts = [a for a in alerts if a["state"] != "resolved"]
    overdue = [
        a for a in open_alerts if a["age_hours"] > sla_hours
    ]
    resolved = [a for a in alerts if a["state"] == "resolved"]
    durations = []
    for a in resolved:
        if a["updated_utc"]:
            created = datetime.fromisoformat(created_by_alert[a["alert_id"]])
            duration = (
                datetime.fromisoformat(a["updated_utc"]) - created
            ).total_seconds() / 3600
            durations.append(max(0.0, duration))
    return {
        "as_of_utc": current.isoformat(),
        "sla_hours": sla_hours,
        "kpis": {
            "total_alerts": len(alerts),
            "open_alerts": len(open_alerts),
            "new_alerts": state_counts["new"],
            "acknowledged_alerts": state_counts["acknowledged"],
            "resolved_alerts": state_counts["resolved"],
            "critical_open": sum(a["severity"] == "red" for a in open_alerts),
            "escalated_open": sum(bool(a["escalated_utc"]) for a in open_alerts),
            "sla_breaches": len(overdue),
            "mean_resolution_hours": (
                round(sum(durations) / len(durations), 2) if durations else None
            ),
            "monitoring_runs": len(trend),
        },
        "alerts": alerts,
        "risk_trend": trend,
    }


def report_csv(data: dict) -> bytes:
    """Export alert rows with stable column order and safe spreadsheet cells."""
    columns = (
        "alert_id", "run_id", "scope", "name", "severity", "state",
        "age_hours", "escalated_utc", "actor", "updated_utc",
    )
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for alert in data["alerts"]:
        row = {}
        for key in columns:
            value = alert.get(key)
            if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
                value = "'" + value
            row[key] = value
        writer.writerow(row)
    return output.getvalue().encode("utf-8-sig")


def report_pdf(data: dict) -> bytes:
    """Export a compact PDF with KPI and recent risk trend tables."""
    output = io.BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("ActuarialAI - Risk Management Report", styles["Title"]),
        Paragraph(f"As of: {data['as_of_utc']}", styles["Normal"]),
        Paragraph(f"SLA threshold: {data['sla_hours']} hours", styles["Normal"]),
        Spacer(1, 14),
        Paragraph("Key risk indicators", styles["Heading2"]),
    ]
    kpi_rows = [["Indicator", "Value"]] + [
        [key.replace("_", " ").title(), str(value)]
        for key, value in data["kpis"].items()
    ]
    kpi_table = Table(kpi_rows, colWidths=[300, 160], repeatRows=1)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
    ]))
    story.extend([kpi_table, Spacer(1, 16)])
    story.append(Paragraph("Recent monitoring runs", styles["Heading2"]))
    trend_rows = [["Run", "Status", "Mack SE"]] + [
        [str(row["run_id"]), row["overall_status"],
         f"{row['total_se']:,.2f}"]
        for row in data["risk_trend"][-15:]
    ]
    table = Table(trend_rows, colWidths=[100, 150, 210], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
    ]))
    story.append(table)
    document.build(story)
    return output.getvalue()
