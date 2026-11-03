"""Local model registry, controlled review and tamper-evident decision history."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .auth import require_permission
from .risk_forecast_validation import validate_risk_forecasts

_STATES = {"DRAFT": {"IN_REVIEW"}, "IN_REVIEW": {"APPROVED", "REJECTED"},
           "REJECTED": {"IN_REVIEW"}, "APPROVED": set()}


def _connect(path):
    db = sqlite3.connect(str(path), timeout=10)
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=10000")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS forecast_models (
            id INTEGER PRIMARY KEY, created_utc TEXT NOT NULL,
            submitter TEXT NOT NULL, model_name TEXT NOT NULL,
            model_version TEXT NOT NULL, parameters_json TEXT NOT NULL,
            validation_json TEXT NOT NULL, content_hash TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'DRAFT'
        );
        CREATE TABLE IF NOT EXISTS forecast_model_events (
            id INTEGER PRIMARY KEY, model_id INTEGER NOT NULL
                REFERENCES forecast_models(id), created_utc TEXT NOT NULL,
            actor TEXT NOT NULL, from_status TEXT NOT NULL,
            to_status TEXT NOT NULL, reason TEXT NOT NULL,
            previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL
        );
    """)
    return db


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False, ensure_ascii=False)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def register_forecast_model(
    path: str | Path, token: str, trend: list[dict], *,
    model_name: str = "linear", window: int = 3,
    drift_threshold: float = 2.0,
) -> dict:
    """Validate current history and register immutable model evidence."""
    actor = require_permission(path, token, "submit_review")["username"]
    validation = validate_risk_forecasts(
        trend, window=window, drift_threshold=drift_threshold,
    )
    models = {row["model"] for row in validation["metrics"]}
    if model_name not in models:
        raise ValueError("Unknown forecast model")
    parameters = {"window": window, "drift_threshold": drift_threshold}
    evidence = {"model_name": model_name,
                "model_version": validation["model_version"],
                "parameters": parameters, "validation": validation}
    digest = _digest(evidence)
    with _connect(path) as db:
        db.execute("BEGIN IMMEDIATE")
        cursor = db.execute(
            "INSERT INTO forecast_models "
            "(created_utc,submitter,model_name,model_version,parameters_json,"
            "validation_json,content_hash) VALUES (?,?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), actor, model_name,
             validation["model_version"], _canonical(parameters),
             _canonical(validation), digest),
        )
        return {"model_id": cursor.lastrowid, "status": "DRAFT",
                "content_hash": digest}


def list_forecast_models(path: str | Path, token: str) -> list[dict]:
    require_permission(path, token, "read_reports")
    with _connect(path) as db:
        rows = db.execute(
            "SELECT id,created_utc,submitter,model_name,model_version,"
            "parameters_json,validation_json,content_hash,status "
            "FROM forecast_models ORDER BY id DESC"
        ).fetchall()
    keys = ("model_id", "created_utc", "submitter", "model_name",
            "model_version", "parameters_json", "validation_json",
            "content_hash", "status")
    return [dict(zip(keys, row)) for row in rows]


def model_audit_events(path: str | Path, token: str, model_id: int) -> list[dict]:
    require_permission(path, token, "read_reports")
    with _connect(path) as db:
        rows = db.execute(
            "SELECT model_id,created_utc,actor,from_status,to_status,"
            "reason,previous_hash,event_hash FROM forecast_model_events "
            "WHERE model_id=? ORDER BY id", (model_id,),
        ).fetchall()
    keys = ("model_id", "created_utc", "actor", "from_status",
            "to_status", "reason", "previous_hash", "event_hash")
    return [dict(zip(keys, row)) for row in rows]


def verify_model_audit(path: str | Path, token: str, model_id: int) -> bool:
    require_permission(path, token, "read_reports")
    with _connect(path) as db:
        model = db.execute(
            "SELECT model_name,model_version,parameters_json,validation_json,"
            "content_hash,status FROM forecast_models WHERE id=?",
            (model_id,),
        ).fetchone()
        if model is None:
            raise ValueError("Unknown model")
        events = db.execute(
            "SELECT model_id,created_utc,actor,from_status,to_status,"
            "reason,previous_hash,event_hash FROM forecast_model_events "
            "WHERE model_id=? ORDER BY id", (model_id,),
        ).fetchall()
    try:
        evidence = {"model_name": model[0], "model_version": model[1],
                    "parameters": json.loads(model[2]),
                    "validation": json.loads(model[3])}
        if _digest(evidence) != model[4]:
            return False
    except (ValueError, TypeError):
        return False
    previous, state = "GENESIS", "DRAFT"
    for row in events:
        payload = dict(zip(
            ("model_id", "created_utc", "actor", "from_status",
             "to_status", "reason", "previous_hash"), row[:-1],
        ))
        if (row[-2] != previous or row[3] != state
                or row[4] not in _STATES[state]
                or row[-1] != _digest(payload)):
            return False
        previous, state = row[-1], row[4]
    return state == model[5]


def transition_forecast_model(
    path: str | Path, token: str, model_id: int,
    target: str, reason: str,
) -> dict:
    """Require reviewer separation and verify audit integrity before transition."""
    if target not in {"IN_REVIEW", "APPROVED", "REJECTED"}:
        raise ValueError("Invalid target status")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Reason is required")
    permission = "submit_review" if target == "IN_REVIEW" else "approve_reports"
    actor = require_permission(path, token, permission)["username"]
    # Verification is repeated inside the write transaction by serializing
    # transitions; avoid nested database writes during verification.
    if not verify_model_audit(path, token, model_id):
        raise ValueError("Model evidence or audit chain integrity failed")
    with _connect(path) as db:
        db.execute("BEGIN IMMEDIATE")
        model = db.execute(
            "SELECT submitter,status FROM forecast_models WHERE id=?",
            (model_id,),
        ).fetchone()
        if model is None:
            raise ValueError("Unknown model")
        submitter, current = model
        if target not in _STATES[current]:
            raise ValueError("Invalid model status transition")
        if target in {"APPROVED", "REJECTED"} and actor == submitter:
            raise PermissionError("Self-review is prohibited")
        prior = db.execute(
            "SELECT event_hash FROM forecast_model_events WHERE model_id=? "
            "ORDER BY id DESC LIMIT 1", (model_id,),
        ).fetchone()
        payload = {
            "model_id": model_id, "created_utc": datetime.now(timezone.utc).isoformat(),
            "actor": actor, "from_status": current, "to_status": target,
            "reason": reason.strip(),
            "previous_hash": prior[0] if prior else "GENESIS",
        }
        digest = _digest(payload)
        db.execute(
            "INSERT INTO forecast_model_events "
            "(model_id,created_utc,actor,from_status,to_status,reason,"
            "previous_hash,event_hash) VALUES (?,?,?,?,?,?,?,?)",
            (*payload.values(), digest),
        )
        db.execute("UPDATE forecast_models SET status=? WHERE id=?",
                   (target, model_id))
    return {**payload, "event_hash": digest}
