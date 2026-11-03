"""Walk-forward validation and drift diagnostics for exploratory Mack SE forecasts."""
import math

import numpy as np

from .risk_forecasting import _line

MODEL_VERSION = "36.1"
_MODELS = ("linear", "moving_average", "naive")


def validate_risk_forecasts(
    trend: list[dict], *, window: int = 3, drift_threshold: float = 2.0,
) -> dict:
    """Compare one-step forecasts without training on future observations.

    MAPE excludes zero actuals and is None when no nonzero actual exists.
    Drift uses recent versus prior mean, scaled by prior sample std.
    """
    if not isinstance(window, int) or isinstance(window, bool) or not 2 <= window <= 24:
        raise ValueError("window must be an integer between 2 and 24")
    if not math.isfinite(drift_threshold) or drift_threshold <= 0:
        raise ValueError("drift_threshold must be finite and positive")
    try:
        values = np.asarray([float(row["total_se"]) for row in trend], dtype=float)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid risk trend observations") from exc
    if len(values) < max(5, 2 * window):
        raise ValueError("At least max(5, 2 * window) observations are required")
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Risk values must be finite and nonnegative")
    records = []
    for index in range(3, len(values)):
        past = values[:index]
        intercept, slope, _ = _line(past)
        predictions = {
            "linear": max(0.0, intercept + slope * index),
            "moving_average": float(np.mean(past[-window:])),
            "naive": float(past[-1]),
        }
        for model, predicted in predictions.items():
            records.append({
                "observation": index + 1, "model": model,
                "actual": float(values[index]),
                "predicted": float(predicted),
                "absolute_error": float(abs(values[index] - predicted)),
            })
    metrics = []
    for model in _MODELS:
        subset = [row for row in records if row["model"] == model]
        errors = np.asarray(
            [row["actual"] - row["predicted"] for row in subset],
            dtype=float,
        )
        actuals = np.asarray([row["actual"] for row in subset], dtype=float)
        positive = actuals > 0
        metrics.append({
            "model": model,
            "mae": round(float(np.mean(np.abs(errors))), 4),
            "rmse": round(float(np.sqrt(np.mean(errors**2))), 4),
            "mape_pct": (
                round(float(np.mean(
                    np.abs(errors[positive] / actuals[positive])
                ) * 100), 4) if positive.any() else None
            ),
            "holdouts": len(subset),
        })
    recent = values[-window:]
    prior = values[-2 * window:-window]
    prior_std = float(np.std(prior, ddof=1))
    difference = float(np.mean(recent) - np.mean(prior))
    # A constant baseline with any change is a detectable shift.
    drift_score = abs(difference) / prior_std if prior_std > 0 else (
        math.inf if difference != 0 else 0.0
    )
    drift = bool(drift_score >= drift_threshold)
    best = min(metrics, key=lambda row: (row["mae"], _MODELS.index(row["model"])))
    return {
        "model_version": MODEL_VERSION,
        "observations": len(values),
        "window": window,
        "drift_threshold": drift_threshold,
        "drift_score": round(drift_score, 4) if math.isfinite(drift_score) else None,
        "drift_detected": drift,
        "best_model_by_mae": best["model"],
        "metrics": metrics,
        "backtest": records,
        "assumptions": (
            "One-step expanding-window holdout evaluation; minimum three "
            "training observations. Moving average uses up to window past "
            "observations. MAPE excludes zero actuals. Drift compares the "
            "last two nonoverlapping windows using the earlier window's "
            "sample standard deviation. Zero baseline variance with a "
            "nonzero mean shift is flagged. These are diagnostic heuristics, "
            "not calibrated production model controls."
        ),
    }
