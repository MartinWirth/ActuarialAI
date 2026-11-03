"""Threshold-based Mack portfolio early warnings and portable snapshots."""
from datetime import datetime, timezone

import numpy as np
import pandas as pd


def _status(value: float, warning: float, critical: float, *, high_bad: bool = True) -> str:
    if not all(np.isfinite(x) for x in (value, warning, critical)):
        raise ValueError("Risk limits and observations must be finite")
    if high_bad:
        if not 0 <= warning < critical:
            raise ValueError("High-risk limits require 0 <= warning < critical")
        return "red" if value >= critical else "yellow" if value >= warning else "green"
    if not 0 <= critical < warning:
        raise ValueError("Low-risk limits require 0 <= critical < warning")
    return "red" if value <= critical else "yellow" if value <= warning else "green"


def assess_risk_limits(
    dashboard: dict,
    *,
    portfolio_warning: float,
    portfolio_critical: float,
    segment_share_warning: float = 0.4,
    segment_share_critical: float = 0.6,
    diversification_warning: float = 0.1,
    diversification_critical: float = 0.0,
) -> dict:
    """Evaluate user-defined diagnostic thresholds; never imply regulatory approval."""
    metrics = dashboard["metrics"]
    ranking = dashboard["ranking"]
    if ranking.empty:
        raise ValueError("Risk dashboard requires at least one segment")
    observations = [{
        "scope": "portfolio", "name": "Mack standard error",
        "value": float(metrics["total_se"]),
        "warning": float(portfolio_warning), "critical": float(portfolio_critical),
        "status": _status(float(metrics["total_se"]), portfolio_warning, portfolio_critical),
    }, {
        "scope": "portfolio", "name": "Diversification ratio",
        "value": float(metrics["diversification_pct"]),
        "warning": float(diversification_warning),
        "critical": float(diversification_critical),
        "status": _status(
            float(metrics["diversification_pct"]),
            diversification_warning, diversification_critical, high_bad=False,
        ),
    }]
    for _, row in ranking.iterrows():
        # Absolute Euler share: negative risk offsets are still concentration.
        value = abs(float(row["se_share"]))
        observations.append({
            "scope": "segment", "name": str(row["segment"]),
            "value": value,
            "warning": float(segment_share_warning),
            "critical": float(segment_share_critical),
            "status": _status(value, segment_share_warning, segment_share_critical),
        })
    checks = pd.DataFrame(observations)
    severity = {"green": 0, "yellow": 1, "red": 2}
    overall = max(checks["status"], key=lambda x: severity[x])
    return {
        "status": overall, "checks": checks,
        "breaches": checks.loc[checks["status"] != "green"].reset_index(drop=True),
        "assumptions": (
            "User-defined diagnostic thresholds, not calibrated risk appetite "
            "or regulatory capital. Segment concentration uses absolute Euler shares."
        ),
    }


def risk_snapshot(
    assessment: dict,
    dashboard: dict,
    *,
    as_of: str | None = None,
) -> dict:
    """Create an explicit, exportable point-in-time monitoring record."""
    timestamp = as_of or datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": "1.0",
        "as_of_utc": timestamp,
        "overall_status": assessment["status"],
        "metrics": {key: float(value) for key, value in dashboard["metrics"].items()},
        "checks": assessment["checks"].to_dict(orient="records"),
        "assumptions": assessment["assumptions"],
    }
