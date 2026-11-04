"""Execute only the currently approved and activated forecasting model."""
import json
from datetime import datetime, timezone

import numpy as np

from .auth import require_permission
from .forecast_deployment import active_forecast_model
from .forecast_model_registry import _connect, _digest
from .risk_forecasting import _line


def _setup(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS forecast_executions (
            id INTEGER PRIMARY KEY, created_utc TEXT NOT NULL,
            actor TEXT NOT NULL, model_id INTEGER NOT NULL
                REFERENCES forecast_models(id),
            model_name TEXT NOT NULL, model_version TEXT NOT NULL,
            input_hash TEXT NOT NULL, result_json TEXT NOT NULL,
            result_hash TEXT NOT NULL
        )
    """)


def execute_active_forecast(path, token, trend, *, horizon=3):
    """Fail closed without an active model; never silently use a draft."""
    actor = require_permission(path, token, "read_reports")["username"]
    if not isinstance(horizon, int) or isinstance(horizon, bool):
        raise TypeError("horizon must be an integer")
    if not 1 <= horizon <= 24:
        raise ValueError("horizon must be between 1 and 24")
    if not isinstance(trend, list) or len(trend) < 4:
        raise ValueError("At least four observations are required")
    try:
        values = np.asarray([float(row["total_se"]) for row in trend], dtype=float)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid risk observations") from exc
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Risk observations must be finite and nonnegative")
    active = active_forecast_model(path, token)
    if active is None:
        raise ValueError("No approved active forecast model; execution blocked")
    name = active["model_name"]
    window = active["parameters"]["window"]
    if name == "linear":
        intercept, slope, _ = _line(values)
        predictions = [
            max(0.0, intercept + slope * (len(values) - 1 + step))
            for step in range(1, horizon + 1)
        ]
    elif name == "moving_average":
        # Recursive multi-step moving average using prior forecasts.
        history = list(values)
        predictions = []
        for _ in range(horizon):
            point = float(np.mean(history[-window:]))
            predictions.append(point)
            history.append(point)
    elif name == "naive":
        predictions = [float(values[-1])] * horizon
    else:
        raise ValueError("Unsupported registered model")
    result = {
        "model_id": active["model_id"],
        "model_name": name,
        "model_version": active["model_version"],
        "horizon": horizon,
        "observations": len(values),
        "forecast": [
            {"step": step, "estimate": round(float(value), 4)}
            for step, value in enumerate(predictions, start=1)
        ],
        "assumptions": (
            "Observation-indexed point forecasts, not calendar dates. "
            "No calibrated uncertainty intervals. Approved model selection "
            "does not imply external production deployment."
        ),
    }
    with _connect(path) as db:
        db.execute("BEGIN IMMEDIATE")
        _setup(db)
        # Detect deployment change before writing execution record.
        current = db.execute(
            "SELECT model_id FROM forecast_deployments "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if current is None or current[0] != active["model_id"]:
            raise ValueError("Active deployment changed during execution")
        db.execute(
            "INSERT INTO forecast_executions "
            "(created_utc,actor,model_id,model_name,model_version,"
            "input_hash,result_json,result_hash) VALUES (?,?,?,?,?,?,?,?)",
            (
                datetime.now(timezone.utc).isoformat(), actor,
                active["model_id"], name, active["model_version"],
                _digest({"values": values.tolist(), "horizon": horizon}),
                json.dumps(result, sort_keys=True), _digest(result),
            ),
        )
    return result


def forecast_execution_history(path, token, *, limit=100):
    require_permission(path, token, "read_reports")
    if not isinstance(limit, int) or isinstance(limit, bool):
        raise TypeError("limit must be an integer")
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    with _connect(path) as db:
        _setup(db)
        rows = db.execute(
            "SELECT id,created_utc,actor,model_id,model_name,"
            "model_version,input_hash,result_json,result_hash "
            "FROM forecast_executions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    keys = ("id", "created_utc", "actor", "model_id", "model_name",
            "model_version", "input_hash", "result_json", "result_hash")
    result = []
    for row in rows:
        record = dict(zip(keys, row))
        try:
            record["integrity_valid"] = (
                _digest(json.loads(record["result_json"])) == record["result_hash"]
            )
        except (ValueError, TypeError):
            record["integrity_valid"] = False
        result.append(record)
    return result
