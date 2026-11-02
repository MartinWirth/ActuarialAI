"""Transparent governance checks; no automated actuarial approval."""
import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .portfolio_backtest import portfolio_backtest


def governance_assessment(
    segments: dict[str, pd.DataFrame],
    min_valuations: int = 3,
    max_mae_ratio: float = 1.10,
    max_underprediction_rate: float = 0.75,
) -> dict:
    """Assess ML against Chain-Ladder using aggregate one-step holdouts.

    PASS means only that the configured *diagnostic* gates were met.
    It is not a production model approval or reserve-risk calibration.
    """
    if isinstance(min_valuations, bool) or not isinstance(min_valuations, int) or min_valuations < 1:
        raise ValueError("min_valuations must be a positive integer")
    if not np.isfinite(max_mae_ratio) or max_mae_ratio <= 0:
        raise ValueError("max_mae_ratio must be positive and finite")
    if not np.isfinite(max_underprediction_rate) or not 0 <= max_underprediction_rate <= 1:
        raise ValueError("max_underprediction_rate must be between 0 and 1")
    history = portfolio_backtest(segments)
    metrics = history["metrics"].set_index("model")
    baseline_mae = float(metrics.loc["chain_ladder", "mae"])
    candidate_mae = float(metrics.loc["random_forest", "mae"])
    ratio = candidate_mae / baseline_mae if baseline_mae > 0 else (
        0.0 if candidate_mae == 0 else None
    )
    checks = [
        {"check": "minimum_common_valuations",
         "observed": history["common_valuations"], "threshold": min_valuations,
         "passed": history["common_valuations"] >= min_valuations},
        {"check": "ml_mae_relative_to_chain_ladder",
         "observed": ratio, "threshold": max_mae_ratio,
         "passed": ratio is not None and ratio <= max_mae_ratio},
        {"check": "ml_underprediction_rate",
         "observed": float(metrics.loc["random_forest", "underprediction_rate"]),
         "threshold": max_underprediction_rate,
         "passed": float(metrics.loc["random_forest", "underprediction_rate"])
         <= max_underprediction_rate},
    ]
    return {
        "status": "DIAGNOSTIC_PASS" if all(c["passed"] for c in checks) else "REVIEW_REQUIRED",
        "checks": checks,
        "metrics": history["metrics"].to_dict(orient="records"),
        "common_valuations": history["common_valuations"],
        "limitations": history["limitations"],
    }


def governance_audit_report(
    segments: dict[str, pd.DataFrame],
    source: str = "portfolio_csv",
    min_valuations: int = 3,
    max_mae_ratio: float = 1.10,
    max_underprediction_rate: float = 0.75,
) -> dict:
    """Export reproducible evidence and a hash of the full input portfolio."""
    assessment = governance_assessment(
        segments, min_valuations, max_mae_ratio, max_underprediction_rate
    )
    canonical = {}
    for name in sorted(segments):
        triangle = segments[name]
        canonical[name] = {
            "index": [str(x) for x in triangle.index],
            "columns": [str(x) for x in triangle.columns],
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
        "evaluation": "aggregate_one_step_cumulative_paid_common_valuations",
        "governance": assessment,
        "human_approval": "NOT_PERFORMED",
        "limitations": [
            "Diagnostic pass is not actuarial sign-off or production authorization",
            "No validation of ultimate reserves, risk calibration or regulatory capital",
            "Small overlapping holdouts limit statistical confidence",
        ],
    }
