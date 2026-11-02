"""Reproducible, descriptive model validation on rolling holdout predictions."""
import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .backtest import backtest_metrics, rolling_backtest


def validate_models(triangle: pd.DataFrame, alert_ratio: float = 1.10) -> dict:
    """Compare models on identical held-out cumulative paid observations."""
    if not np.isfinite(alert_ratio) or alert_ratio <= 0:
        raise ValueError("alert_ratio must be positive and finite")
    predictions = rolling_backtest(triangle)
    metrics = backtest_metrics(predictions)
    rows = []
    for valuation, group in predictions.groupby("valuation", sort=True):
        errors = backtest_metrics(group)
        baseline = float(errors.loc["chain_ladder", "MAE"])
        candidate = float(errors.loc["random_forest", "MAE"])
        rows.append({
            "valuation": int(valuation),
            "observations": len(group),
            "chain_ladder_mae": baseline,
            "random_forest_mae": candidate,
            "ml_alert": candidate > baseline * alert_ratio if baseline > 0 else candidate > 0,
        })
    per_valuation = pd.DataFrame(rows)
    baseline_mae = float(metrics.loc["chain_ladder", "MAE"])
    ml_mae = float(metrics.loc["random_forest", "MAE"])
    return {
        "predictions": predictions,
        "metrics": metrics,
        "by_valuation": per_valuation,
        "alert_count": int(per_valuation["ml_alert"].sum()),
        "preferred_by_mae": "chain_ladder" if baseline_mae <= ml_mae else "random_forest",
        "alert_ratio": float(alert_ratio),
    }


def validation_report(triangle: pd.DataFrame, source: str = "synthetic",
                      alert_ratio: float = 1.10) -> dict:
    """Build a traceable report with a hash of triangle contents and model specs."""
    result = validate_models(triangle, alert_ratio)
    canonical = {
        "index": [str(v) for v in triangle.index],
        "columns": [str(v) for v in triangle.columns],
        "values": [[None if pd.isna(v) else float(v) for v in row]
                   for row in triangle.to_numpy(dtype=float)],
    }
    fingerprint = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, allow_nan=False).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "input_sha256": fingerprint,
        "models": {
            "chain_ladder": "volume_weighted_age_to_age",
            "random_forest": {
                "estimator": "RandomForestRegressor",
                "n_estimators": 100,
                "min_samples_leaf": 2,
                "random_state": 42,
                "features": ["development", "paid"],
                "fallback": "chain_ladder_for_sparse_ages",
            },
        },
        "evaluation": "rolling_calendar_time_one_step_cumulative_paid",
        "overall": [
            {"model": str(name), "n": int(row["n"]),
             "MAE": float(row["MAE"]), "RMSE": float(row["RMSE"])}
            for name, row in result["metrics"].iterrows()
        ],
        "by_valuation": [
            {"valuation": int(row["valuation"]), "observations": int(row["observations"]),
             "chain_ladder_mae": float(row["chain_ladder_mae"]),
             "random_forest_mae": float(row["random_forest_mae"]),
             "ml_alert": bool(row["ml_alert"])}
            for _, row in result["by_valuation"].iterrows()
        ],
        "alert_ratio": result["alert_ratio"],
        "alert_count": result["alert_count"],
        "preferred_by_mae": result["preferred_by_mae"],
        "limitations": [
            "One-step cumulative paid errors are not ultimate reserve errors",
            "Small and overlapping calendar-time holdouts limit inference",
            "Model selection is descriptive and requires independent actuarial review",
        ],
    }
