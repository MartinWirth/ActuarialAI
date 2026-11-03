"""Consolidated, assumption-driven Mack portfolio risk dashboard data."""
from statistics import NormalDist

import numpy as np
import pandas as pd

from .mack_attribution import mack_risk_attribution
from .mack_matrix import validate_correlation_matrix


def portfolio_risk_dashboard(
    segments: dict[str, pd.DataFrame],
    matrix: pd.DataFrame,
    confidence: float = 0.95,
    scenario_correlations: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0),
) -> dict:
    """Calculate a consistent overview, ranking and equicorrelation scenarios.

    Current risk uses the supplied full matrix; scenarios are independent
    equicorrelation alternatives, not perturbations of the supplied matrix.
    """
    names = sorted(segments)
    correlation = validate_correlation_matrix(matrix, names)
    if not scenario_correlations or any(
        not np.isfinite(rho) for rho in scenario_correlations
    ):
        raise ValueError("Scenario correlations must be finite and nonempty")
    lower_bound = -1 / (len(names) - 1) if len(names) > 1 else -1.0
    if any(not lower_bound <= rho <= 1 for rho in scenario_correlations):
        raise ValueError("Scenario correlation outside PSD range")
    attribution = mack_risk_attribution(segments, matrix, confidence=confidence)
    ranked = attribution["segments"].sort_values(
        "euler_se_contribution", ascending=False,
    ).reset_index(drop=True)
    ranked.insert(0, "rank", np.arange(1, len(ranked) + 1))
    errors = attribution["segments"]["standalone_se"].to_numpy(dtype=float)
    standalone_sum = float(errors.sum())
    variance_independent = float(errors @ errors)
    cross = float(standalone_sum**2 - variance_independent)
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    scenarios = []
    for rho in scenario_correlations:
        se = float(np.sqrt(max(0.0, variance_independent + rho * cross)))
        scenarios.append({
            "correlation": float(rho),
            "total_se": se,
            "diversification_benefit": standalone_sum - se,
        })
    current_se = attribution["total_se"]
    return {
        "metrics": {
            "total_se": current_se,
            "total_variance": attribution["total_variance"],
            "independent_se": float(np.sqrt(variance_independent)),
            "sum_standalone_se": standalone_sum,
            "diversification_benefit": standalone_sum - current_se,
            "diversification_pct": (
                (standalone_sum - current_se) / standalone_sum
                if standalone_sum > 0 else 0.0
            ),
            "confidence": confidence,
            "interval_half_width": z * current_se,
        },
        "ranking": ranked,
        "pairs": attribution["pairs"].sort_values(
            "cross_variance", ascending=False,
        ).reset_index(drop=True),
        "scenarios": pd.DataFrame(scenarios),
        "matrix": pd.DataFrame(correlation, index=names, columns=names),
        "assumptions": (
            "Mack uncertainty and Euler allocation under user-assumed "
            "correlations; equicorrelation scenarios are alternatives to the "
            "current matrix, not calibrated forecasts or regulatory capital."
        ),
    }
