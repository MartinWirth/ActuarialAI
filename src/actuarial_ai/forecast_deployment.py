"""Controlled activation of approved forecast candidates (local demonstration)."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

import numpy as np

from .auth import require_permission
from .forecast_model_registry import (
    _canonical,
    _connect,
    _digest,
    verify_model_audit,
)


def _setup(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS forecast_deployments (
            id INTEGER PRIMARY KEY, created_utc TEXT NOT NULL,
            actor TEXT NOT NULL, model_id INTEGER NOT NULL
                REFERENCES forecast_models(id),
            previous_model_id INTEGER REFERENCES forecast_models(id),
            action TEXT NOT NULL, reason TEXT NOT NULL,
            previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL
        )
    """)


def deployment_history(path, token):
    require_permission(path, token, "read_reports")
    with _connect(path) as db:
        _setup(db)
        rows = db.execute(
            "SELECT id,created_utc,actor,model_id,previous_model_id,"
            "action,reason,previous_hash,event_hash "
            "FROM forecast_deployments ORDER BY id"
        ).fetchall()
    keys = ("id", "created_utc", "actor", "model_id", "previous_model_id",
            "action", "reason", "previous_hash", "event_hash")
    return [dict(zip(keys, row)) for row in rows]


def _valid_history(rows):
    previous = "GENESIS"
    active = None
    for row in rows:
        payload = {key: row[key] for key in (
            "created_utc", "actor", "model_id", "previous_model_id",
            "action", "reason", "previous_hash"
        )}
        if (row["previous_hash"] != previous
                or row["previous_model_id"] != active
                or row["action"] not in {"ACTIVATE", "ROLLBACK"}
                or row["model_id"] == active
                or _digest(payload) != row["event_hash"]):
            return False
        previous = row["event_hash"]
        active = row["model_id"]
    return True


def active_forecast_model(path, token):
    rows = deployment_history(path, token)
    if not _valid_history(rows):
        raise ValueError("Deployment audit integrity failed")
    if not rows:
        return None
    model_id = rows[-1]["model_id"]
    with _connect(path) as db:
        model = db.execute(
            "SELECT model_name,model_version,parameters_json,status "
            "FROM forecast_models WHERE id=?", (model_id,),
        ).fetchone()
    if model is None or model[3] != "APPROVED":
        raise ValueError("Active model is missing or no longer approved")
    if not verify_model_audit(path, token, model_id):
        raise ValueError("Active model evidence integrity failed")
    return {"model_id": model_id, "model_name": model[0],
            "model_version": model[1],
            "parameters": json.loads(model[2])}


def deploy_forecast_model(path, token, model_id, reason, *, rollback=False):
    """Activate an approved candidate; rollback must target a former active ID."""
    actor = require_permission(path, token, "approve_reports")["username"]
    if not isinstance(model_id, int) or isinstance(model_id, bool):
        raise ValueError("Invalid model ID")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Deployment reason is required")
    if not verify_model_audit(path, token, model_id):
        raise ValueError("Model evidence integrity failed")
    with _connect(path) as db:
        db.execute("BEGIN IMMEDIATE")
        _setup(db)
        model = db.execute(
            "SELECT status FROM forecast_models WHERE id=?", (model_id,),
        ).fetchone()
        if model is None or model[0] != "APPROVED":
            raise ValueError("Only approved models may be activated")
        columns = ("id", "created_utc", "actor", "model_id",
                   "previous_model_id", "action", "reason",
                   "previous_hash", "event_hash")
        rows = [dict(zip(columns, row)) for row in db.execute(
            "SELECT id,created_utc,actor,model_id,previous_model_id,"
            "action,reason,previous_hash,event_hash "
            "FROM forecast_deployments ORDER BY id"
        ).fetchall()]
        if not _valid_history(rows):
            raise ValueError("Deployment audit integrity failed")
        current = rows[-1]["model_id"] if rows else None
        if model_id == current:
            raise ValueError("Model is already active")
        prior_ids = {row["model_id"] for row in rows}
        if rollback and model_id not in prior_ids:
            raise ValueError("Rollback target was never active")
        if not rollback and model_id in prior_ids:
            raise ValueError("Previously active model requires rollback")
        payload = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "actor": actor, "model_id": model_id,
            "previous_model_id": current,
            "action": "ROLLBACK" if rollback else "ACTIVATE",
            "reason": reason.strip(),
            "previous_hash": rows[-1]["event_hash"] if rows else "GENESIS",
        }
        digest = _digest(payload)
        db.execute(
            "INSERT INTO forecast_deployments "
            "(created_utc,actor,model_id,previous_model_id,action,"
            "reason,previous_hash,event_hash) VALUES (?,?,?,?,?,?,?,?)",
            (*payload.values(), digest),
        )
    return {**payload, "event_hash": digest}


def champion_challenger(path, token):
    """Compare registered candidate metrics with the active champion."""
    champion = active_forecast_model(path, token)
    with _connect(path) as db:
        models = db.execute(
            "SELECT id,model_name,validation_json,status "
            "FROM forecast_models ORDER BY id"
        ).fetchall()
    result = []
    for model_id, name, serialized, status in models:
        if status != "APPROVED" and (
            champion is None or model_id != champion["model_id"]
        ):
            continue
        validation = json.loads(serialized)
        metric = next(
            (row for row in validation["metrics"] if row["model"] == name),
            None,
        )
        if metric is None:
            continue
        result.append({
            "model_id": model_id, "model_name": name,
            "role": "champion" if champion and model_id == champion["model_id"]
            else "challenger",
            "mae": metric["mae"], "rmse": metric["rmse"],
            "mape_pct": metric["mape_pct"],
            "observations": validation["observations"],
            "drift_detected": validation["drift_detected"],
        })
    return result
