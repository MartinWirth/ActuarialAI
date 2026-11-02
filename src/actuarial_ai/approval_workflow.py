"""Append-only local governance decisions with a tamper-evident hash chain.

This is a demonstration workflow, not authenticated approval or a secure audit log.
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

from .report_history import _connect

TRANSITIONS = {
    "DRAFT": {"IN_REVIEW"},
    "IN_REVIEW": {"APPROVED", "REJECTED"},
    "REJECTED": {"IN_REVIEW"},
    "APPROVED": set(),
}


def _canonical(event: dict) -> bytes:
    return json.dumps(
        event, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _setup(connection):
    connection.execute("""
        CREATE TABLE IF NOT EXISTS approval_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL REFERENCES reports(id),
            created_utc TEXT NOT NULL,
            actor TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT NOT NULL,
            reason TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            event_hash TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_approval_events_report
        ON approval_events(report_id, id)
    """)


def _rows(connection, report_id):
    connection.row_factory = sqlite3.Row
    return [dict(row) for row in connection.execute(
        "SELECT * FROM approval_events WHERE report_id = ? ORDER BY id",
        (report_id,),
    )]


def audit_events(db_path, report_id: int) -> list[dict]:
    with _connect(db_path) as connection:
        _setup(connection)
        return _rows(connection, report_id)


def verify_audit_chain(events: list[dict]) -> bool:
    previous = "GENESIS"
    for row in events:
        if row["previous_hash"] != previous:
            return False
        payload = {key: row[key] for key in (
            "report_id", "created_utc", "actor", "from_status",
            "to_status", "reason", "previous_hash",
        )}
        expected = hashlib.sha256(_canonical(payload)).hexdigest()
        if expected != row["event_hash"]:
            return False
        previous = expected
    return True


def transition_report(
    db_path, report_id: int, actor: str, to_status: str, reason: str,
) -> dict:
    """Append a valid transition in one SQLite write transaction."""
    actor = actor.strip()
    reason = reason.strip()
    if not actor or not reason:
        raise ValueError("Reviewer and reason are required")
    if to_status not in {"IN_REVIEW", "APPROVED", "REJECTED"}:
        raise ValueError("Invalid target status")
    with _connect(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        _setup(connection)
        exists = connection.execute(
            "SELECT 1 FROM reports WHERE id = ?", (report_id,),
        ).fetchone()
        if exists is None:
            raise ValueError("Unknown report")
        events = _rows(connection, report_id)
        if not verify_audit_chain(events):
            raise ValueError("Audit chain integrity check failed")
        current = events[-1]["to_status"] if events else "DRAFT"
        if to_status not in TRANSITIONS[current]:
            raise ValueError(f"Transition {current} -> {to_status} not permitted")
        previous_hash = events[-1]["event_hash"] if events else "GENESIS"
        payload = {
            "report_id": report_id,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "actor": actor, "from_status": current,
            "to_status": to_status, "reason": reason,
            "previous_hash": previous_hash,
        }
        event_hash = hashlib.sha256(_canonical(payload)).hexdigest()
        connection.execute(
            """INSERT INTO approval_events
               (report_id, created_utc, actor, from_status, to_status,
                reason, previous_hash, event_hash)
               VALUES (:report_id, :created_utc, :actor, :from_status,
                       :to_status, :reason, :previous_hash, :event_hash)""",
            {**payload, "event_hash": event_hash},
        )
    return {**payload, "event_hash": event_hash}


def report_status(db_path, report_id: int) -> str:
    events = audit_events(db_path, report_id)
    if not verify_audit_chain(events):
        raise ValueError("Audit chain integrity check failed")
    return events[-1]["to_status"] if events else "DRAFT"


def audit_export(db_path, report_id: int) -> str:
    events = audit_events(db_path, report_id)
    valid = verify_audit_chain(events)
    return json.dumps(
        {"report_id": report_id, "chain_valid": valid, "events": events},
        indent=2, ensure_ascii=False,
    )
