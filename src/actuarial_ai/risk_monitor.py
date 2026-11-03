"""Local SQLite monitoring store, alert transitions, and append-only audit log."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .risk_trends import monitoring_trends

_SEVERITY = {"green": 0, "yellow": 1, "red": 2}


def _canonical(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _connect(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path), timeout=10)
    connection.execute("PRAGMA busy_timeout=10000")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS monitoring_runs (
            id INTEGER PRIMARY KEY,
            created_utc TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            fingerprint TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS monitoring_alerts (
            id INTEGER PRIMARY KEY,
            run_id INTEGER NOT NULL REFERENCES monitoring_runs(id),
            scope TEXT NOT NULL,
            name TEXT NOT NULL,
            previous_status TEXT NOT NULL,
            status TEXT NOT NULL,
            transition TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS monitoring_audit (
            id INTEGER PRIMARY KEY,
            created_utc TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            event_hash TEXT NOT NULL
        );
    """)
    return connection


def _audit(connection: sqlite3.Connection, event: str, payload: dict) -> None:
    previous = connection.execute(
        "SELECT event_hash FROM monitoring_audit ORDER BY id DESC LIMIT 1"
    ).fetchone()
    previous_hash = previous[0] if previous else "GENESIS"
    created = datetime.now(timezone.utc).isoformat()
    serialized = _canonical(payload)
    digest = hashlib.sha256(
        f"{previous_hash}|{created}|{event}|{serialized}".encode()
    ).hexdigest()
    connection.execute(
        "INSERT INTO monitoring_audit "
        "(created_utc,event_type,payload_json,previous_hash,event_hash) "
        "VALUES (?,?,?,?,?)",
        (created, event, serialized, previous_hash, digest),
    )


def save_monitoring_run(path: str | Path, snapshot: dict) -> dict:
    """Persist a snapshot once; emit alerts only on new or worsened breaches."""
    monitoring_trends([snapshot])
    serialized = _canonical(snapshot)
    fingerprint = hashlib.sha256(serialized.encode()).hexdigest()
    with _connect(path) as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT id FROM monitoring_runs WHERE fingerprint=?", (fingerprint,)
        ).fetchone()
        if existing:
            return {"run_id": existing[0], "created": False, "alerts": []}
        previous = db.execute(
            "SELECT snapshot_json FROM monitoring_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        previous_checks = {}
        if previous:
            for check in json.loads(previous[0])["checks"]:
                previous_checks[(check["scope"], check["name"])] = check["status"]
        now = datetime.now(timezone.utc).isoformat()
        cursor = db.execute(
            "INSERT INTO monitoring_runs(created_utc,snapshot_json,fingerprint) "
            "VALUES (?,?,?)",
            (now, serialized, fingerprint),
        )
        run_id = cursor.lastrowid
        alerts = []
        for check in snapshot["checks"]:
            key = (check["scope"], check["name"])
            old = previous_checks.get(key, "green")
            new = check["status"]
            if _SEVERITY[new] > _SEVERITY[old]:
                transition = "new_breach" if old == "green" else "escalation"
                alert = {
                    "scope": key[0], "name": key[1], "previous_status": old,
                    "status": new, "transition": transition,
                }
                alerts.append(alert)
                db.execute(
                    "INSERT INTO monitoring_alerts "
                    "(run_id,scope,name,previous_status,status,transition) "
                    "VALUES (?,?,?,?,?,?)",
                    (run_id, key[0], key[1], old, new, transition),
                )
        _audit(db, "monitoring_run", {
            "run_id": run_id, "fingerprint": fingerprint, "alert_count": len(alerts),
        })
        for alert in alerts:
            _audit(db, "monitoring_alert", {"run_id": run_id, **alert})
        return {"run_id": run_id, "created": True, "alerts": alerts}


def load_monitoring_runs(path: str | Path) -> list[dict]:
    """Return persisted snapshots in insertion order."""
    with _connect(path) as db:
        rows = db.execute(
            "SELECT snapshot_json FROM monitoring_runs ORDER BY id"
        ).fetchall()
    return [json.loads(row[0]) for row in rows]


def load_monitoring_alerts(path: str | Path) -> list[dict]:
    with _connect(path) as db:
        rows = db.execute(
            "SELECT run_id,scope,name,previous_status,status,transition "
            "FROM monitoring_alerts ORDER BY id"
        ).fetchall()
    return [
        dict(zip(
            ("run_id", "scope", "name", "previous_status", "status", "transition"),
            row,
        ))
        for row in rows
    ]


def verify_monitoring_audit(path: str | Path) -> bool:
    """Verify the local hash chain; not protection against database rewriting."""
    with _connect(path) as db:
        rows = db.execute(
            "SELECT created_utc,event_type,payload_json,previous_hash,event_hash "
            "FROM monitoring_audit ORDER BY id"
        ).fetchall()
    previous = "GENESIS"
    for created, event, payload, prior, digest in rows:
        expected = hashlib.sha256(
            f"{previous}|{created}|{event}|{payload}".encode()
        ).hexdigest()
        if prior != previous or digest != expected:
            return False
        previous = digest
    return True
