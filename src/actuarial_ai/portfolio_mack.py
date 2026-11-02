"""Assumption-driven aggregation of segment Mack prediction errors.

Cross-segment correlations are user scenarios, not estimated by Mack.
"""
from statistics import NormalDist

import numpy as np
import pandas as pd

from .mack import mack_chain_ladder


def aggregate_mack(
    segments: dict[str, pd.DataFrame],
    correlation: float = 0.0,
    confidence: float = 0.95,
) -> dict:
    """Aggregate segment Mack standard errors under equicorrelation.

    Only complete portfolios are aggregated: if one segment cannot be estimated,
    ValueError is raised instead of silently dropping its reserve.
    """
    if not segments:
        raise ValueError("At least one segment is required")
    if not np.isfinite(correlation):
        raise ValueError("correlation must be finite")
    if not np.isfinite(confidence) or not 0.5 < confidence < 1:
        raise ValueError("confidence must be strictly between 0.5 and 1")
    n = len(segments)
    lower_bound = -1 / (n - 1) if n > 1 else -1
    if not lower_bound <= correlation <= 1:
        raise ValueError("correlation outside positive-semidefinite equicorrelation range")
    estimates = []
    for name, triangle in sorted(segments.items()):
        try:
            result = mack_chain_ladder(triangle, confidence=confidence)
        except ValueError as exc:
            raise ValueError(f"Mack unavailable for segment {name}: {exc}") from exc
        estimates.append((name, result["total_reserve"], result["total_se"]))
    names = [x[0] for x in estimates]
    reserves = np.array([x[1] for x in estimates], dtype=float)
    se = np.array([x[2] for x in estimates], dtype=float)
    independent_variance = float(np.dot(se, se))
    covariance = float(correlation * (se.sum() ** 2 - independent_variance))
    variance = max(0.0, independent_variance + covariance)
    total_se = float(np.sqrt(variance))
    reserve = float(reserves.sum())
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    standalone_sum = float(se.sum())
    return {
        "segments": pd.DataFrame({"segment": names, "reserve": reserves, "mack_se": se}),
        "total_reserve": reserve,
        "total_se": total_se,
        "total_mse": variance,
        "independent_se": float(np.sqrt(independent_variance)),
        "sum_segment_se": standalone_sum,
        "diversification_benefit": standalone_sum - total_se,
        "correlation": float(correlation),
        "confidence": float(confidence),
        "lower": max(0.0, reserve - z * total_se),
        "upper": reserve + z * total_se,
        "assumptions": (
            "User-assumed common pairwise correlation between segment prediction errors; "
            "not estimated by Mack; no cross-segment calibration; "
            "normal approximation truncated at zero; no tail factor."
        ),
    }
