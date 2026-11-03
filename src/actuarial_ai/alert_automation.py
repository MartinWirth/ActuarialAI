"""Automated recovery and overdue escalation of local monitoring alerts."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .alert_management import _setup
from .risk_monitor import _audit, _connect

_VALID_STATES = {"new", "acknowledged"}


def process_alert_automation(
    path: str | Path, *, critical_after_hours: float = 24,
    actor: str = "system", now: datetime | None = None,
) -> dict:
    """Resolve recovered checks and escalate overdue unacknowledged red alerts.

    Idempotent per alert: escalation is recorded only once. Does not send email.
    """
    if not 0 < critical_after_hours <= 8760:
        raise ValueError("critical_after_hours must be in (0, 8760]")
    if not actor.strip():
        raise ValueError("actor must not be empty")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now must be timezone aware")
    current = current.astimezone(timezone.utc)
    cutoff = current - timedelta(hours=critical_after_hours)
    with _connect(path) as db:
        _setup(db)
        db.execute("""
            CREATE TABLE IF NOT EXISTS alert_escalations (
                alert_id INTEGER PRIMARY KEY REFERENCES monitoring_alerts(id),
                escalated_utc TEXT NOT NULL
            )
        """)
        db.execute("BEGIN IMMEDIATE")
        latest = db.execute(
            "SELECT snapshot_json FROM monitoring_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if latest is None:
            return {"resolved": [], "escalated": []}
        import json

        checks = {
            (c["scope"], c["name"]): c["status"]
            for c in json.loads(latest[0])["checks"]
        }
        rows = db.execute("""
            SELECT a.id,a.scope,a.name,a.status,r.created_utc,
                   COALESCE(w.state,'new'),e.alert_id
            FROM monitoring_alerts a
            JOIN monitoring_runs r ON r.id=a.run_id
            LEFT JOIN alert_workflow w ON w.alert_id=a.id
            LEFT JOIN alert_escalations e ON e.alert_id=a.id
            ORDER BY a.id
        """).fetchall()
        resolved = []
        escalated = []
        timestamp = current.isoformat()
        for alert_id, scope, name, severity, created, state, escalated_id in rows:
            if state not in _VALID_STATES:
                continue
            # Absent checks are not evidence of recovery.
            if checks.get((scope, name)) == "green":
                db.execute(
                    "INSERT INTO alert_workflow(alert_id,state,actor,updated_utc) "
                    "VALUES(?,?,?,?) ON CONFLICT(alert_id) DO UPDATE SET "
                    "state=excluded.state,actor=excluded.actor,"
                    "updated_utc=excluded.updated_utc",
                    (alert_id, "resolved", actor, timestamp),
                )
                _audit(db, "alert_auto_resolved", {
                    "alert_id": alert_id, "from": state, "to": "resolved",
                    "actor": actor, "updated_utc": timestamp,
                })
                resolved.append(alert_id)
            elif (
                state == "new" and severity == "red" and escalated_id is None
                and datetime.fromisoformat(created).astimezone(timezone.utc) <= cutoff
            ):
                db.execute(
                    "INSERT INTO alert_escalations(alert_id,escalated_utc) "
                    "VALUES(?,?)", (alert_id, timestamp),
                )
                _audit(db, "alert_overdue_escalation", {
                    "alert_id": alert_id, "actor": actor,
                    "escalated_utc": timestamp,
                    "critical_after_hours": critical_after_hours,
                })
                escalated.append(alert_id)
        return {"resolved": resolved, "escalated": escalated}


def alert_automation_overview(
    path: str | Path, *, now: datetime | None = None,
) -> list[dict]:
    """Return open-alert age, state, and escalation marker."""
    from .alert_management import list_managed_alerts

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now must be timezone aware")
    with _connect(path) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS alert_escalations (
                alert_id INTEGER PRIMARY KEY REFERENCES monitoring_alerts(id),
                escalated_utc TEXT NOT NULL
            )
        """)
        times = {
            row[0]: (row[1], row[2])
            for row in db.execute("""
                SELECT a.id,r.created_utc,e.escalated_utc
                FROM monitoring_alerts a
                JOIN monitoring_runs r ON r.id=a.run_id
                LEFT JOIN alert_escalations e ON e.alert_id=a.id
            """).fetchall()
        }
    result = []
    for alert in list_managed_alerts(path):
        created, escalated = times[alert["alert_id"]]
        age = max(0.0, (
            current - datetime.fromisoformat(created)
        ).total_seconds() / 3600)
        result.append({
            **alert, "age_hours": round(age, 2),
            "escalated_utc": escalated,
        })
    return result
