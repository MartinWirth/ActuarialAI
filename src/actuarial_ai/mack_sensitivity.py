"""Correlation sensitivity for assumption-driven portfolio Mack aggregation."""
from statistics import NormalDist

import numpy as np
import pandas as pd

from .portfolio_mack import aggregate_mack


def mack_correlation_sensitivity(
    segments: dict[str, pd.DataFrame],
    correlations=(0.0, 0.25, 0.5, 0.75, 1.0),
    confidence: float = 0.95,
) -> pd.DataFrame:
    """Compare aggregate Mack uncertainty across assumed equicorrelations.

    All segments must be estimable. Each scenario has identical segment inputs.
    """
    values = tuple(correlations)
    if not values:
        raise ValueError("At least one correlation scenario is required")
    if any(not np.isfinite(rho) for rho in values):
        raise ValueError("Correlations must be finite")
    if len(set(values)) != len(values):
        raise ValueError("Correlation scenarios must be unique")
    baseline = aggregate_mack(segments, correlation=0.0, confidence=confidence)
    se = baseline["segments"]["mack_se"].to_numpy(dtype=float)
    variance_independent = float(np.dot(se, se))
    cross = float(se.sum() ** 2 - variance_independent)
    reserve = baseline["total_reserve"]
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    n = len(se)
    lower_bound = -1 / (n - 1) if n > 1 else -1.0
    rows = []
    for rho in values:
        if not lower_bound <= rho <= 1:
            raise ValueError("Correlation outside positive-semidefinite range")
        total_se = float(np.sqrt(max(0.0, variance_independent + rho * cross)))
        rows.append({
            "correlation": float(rho),
            "total_reserve": reserve,
            "total_se": total_se,
            "lower": max(0.0, reserve - z * total_se),
            "upper": reserve + z * total_se,
            "diversification_benefit": float(se.sum()) - total_se,
        })
    return pd.DataFrame(rows)
