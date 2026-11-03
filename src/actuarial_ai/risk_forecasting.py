"""Exploratory Mack standard-error trend projections and walk-forward validation."""
import math

import numpy as np


def _line(values: np.ndarray) -> tuple[float, float, float]:
    x = np.arange(len(values), dtype=float)
    slope, intercept = np.polyfit(x, values, 1)
    residuals = values - (intercept + slope * x)
    sigma = float(np.std(residuals, ddof=2)) if len(values) > 2 else 0.0
    return float(intercept), float(slope), sigma


def forecast_mack_risk(
    trend: list[dict], *, horizon: int = 3, warning: float | None = None,
    critical: float | None = None, stress_pct: float = 0.2,
) -> dict:
    """Forecast by monitoring observation, not calendar date.

    Intervals are heuristic residual bands, NOT calibrated prediction intervals.
    Walk-forward MAE uses only prior observations for each prediction.
    """
    if not isinstance(horizon, int) or isinstance(horizon, bool) or not 1 <= horizon <= 24:
        raise ValueError("horizon must be an integer between 1 and 24")
    if not math.isfinite(stress_pct) or not 0 <= stress_pct <= 2:
        raise ValueError("stress_pct must be finite and between 0 and 2")
    if (warning is None) != (critical is None):
        raise ValueError("Provide both warning and critical thresholds")
    if warning is not None and (
        not all(math.isfinite(v) for v in (warning, critical))
        or not 0 <= warning < critical
    ):
        raise ValueError("Require 0 <= warning < critical")
    if len(trend) < 4:
        raise ValueError("At least four monitoring observations are required")
    try:
        values = np.asarray([float(row["total_se"]) for row in trend], dtype=float)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid risk trend observations") from exc
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Mack standard errors must be finite and nonnegative")
    intercept, slope, sigma = _line(values)
    errors = []
    for end in range(3, len(values)):
        past_intercept, past_slope, _ = _line(values[:end])
        prediction = max(0.0, past_intercept + past_slope * end)
        errors.append(abs(prediction - values[end]))
    forecast = []
    for step in range(1, horizon + 1):
        point = max(0.0, intercept + slope * (len(values) - 1 + step))
        # Widen the empirical residual band with projection horizon.
        band = 1.96 * sigma * math.sqrt(1 + step / len(values))
        status = "unconfigured"
        if warning is not None:
            status = (
                "red" if point >= critical else
                "yellow" if point >= warning else "green"
            )
        forecast.append({
            "step": step, "estimate": round(point, 4),
            "lower": round(max(0.0, point - band), 4),
            "upper": round(point + band, 4),
            "optimistic": round(max(0.0, point * (1 - stress_pct)), 4),
            "stressed": round(point * (1 + stress_pct), 4),
            "projected_status": status,
            "early_warning": bool(
                warning is not None and point < warning <= point + band
            ),
        })
    return {
        "observations": len(values),
        "trend": "rising" if slope > 1e-9 else (
            "falling" if slope < -1e-9 else "flat"
        ),
        "slope_per_observation": round(slope, 4),
        "walk_forward_mae": round(float(np.mean(errors)), 4),
        "forecast": forecast,
        "assumptions": (
            "Linear extrapolation over successive monitoring observations, "
            "not calendar periods. Bands use historical in-sample residuals "
            "and are NOT calibrated confidence or prediction intervals. "
            "Projected thresholds are diagnostic; scenario shocks are illustrative."
        ),
    }
