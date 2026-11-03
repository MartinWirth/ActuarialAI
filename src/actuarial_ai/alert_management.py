"""Operational alert lifecycle layered on the existing monitoring SQLite store."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .risk_monitor import _audit, _connect

_STATES = {"new", "acknowledged", "resolved"}
_ALLOWED = {"new": {"acknowledged", "resolved"}, "acknowledged": {"resolved"}, "resolved": set()}


def _setup(db: sqlite3.Connection) -> None:
    db.executescript("""
        CREATE TABLE IF NOT EXISTS alert_workflow (
            alert_id INTEGER PRIMARY KEY REFERENCES monitoring_alerts(id),
            state TEXT NOT NULL DEFAULT 'new',
            actor TEXT,
            updated_utc TEXT
        );
    """)


def list_managed_alerts(path: str | Path, state: str | None = None) -> list[dict]:
    """List alerts including legacy rows, highest severity first."""
    if state is not None and state not in _STATES:
        raise ValueError("Unknown alert state")
    with _connect(path) as db:
        _setup(db)
        rows = db.execute("""
            SELECT a.id,a.run_id,a.scope,a.name,a.previous_status,a.status,
                   a.transition,COALESCE(w.state,'new'),w.actor,w.updated_utc
            FROM monitoring_alerts a
            LEFT JOIN alert_workflow w ON w.alert_id=a.id
            ORDER BY CASE a.status WHEN 'red' THEN 0
                      WHEN 'yellow' THEN 1 ELSE 2 END, a.id DESC
        """).fetchall()
    fields = ("alert_id", "run_id", "scope", "name", "previous_status",
              "severity", "transition", "state", "actor", "updated_utc")
    return [dict(zip(fields, row)) for row in rows if state is None or row[7] == state]


def transition_alert(
    path: str | Path, alert_id: int, new_state: str, actor: str,
) -> dict:
    """Advance an alert's state once, atomically recording actor and audit event."""
    if new_state not in _STATES:
        raise ValueError("Unknown target alert state")
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError("Actor must not be empty")
    if not isinstance(alert_id, int) or isinstance(alert_id, bool) or alert_id < 1:
        raise ValueError("Alert ID must be a positive integer")
    with _connect(path) as db:
        _setup(db)
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT COALESCE(w.state,'new') FROM monitoring_alerts a "
            "LEFT JOIN alert_workflow w ON w.alert_id=a.id WHERE a.id=?",
            (alert_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Alert does not exist")
        old_state = row[0]
        if new_state not in _ALLOWED[old_state]:
            raise ValueError(f"Invalid alert transition: {old_state} -> {new_state}")
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "INSERT INTO alert_workflow(alert_id,state,actor,updated_utc) "
            "VALUES(?,?,?,?) ON CONFLICT(alert_id) DO UPDATE SET "
            "state=excluded.state,actor=excluded.actor,"
            "updated_utc=excluded.updated_utc",
            (alert_id, new_state, actor.strip(), now),
        )
        event = {
            "alert_id": alert_id, "from": old_state, "to": new_state,
            "actor": actor.strip(), "updated_utc": now,
        }
        _audit(db, "alert_transition", event)
        return event
