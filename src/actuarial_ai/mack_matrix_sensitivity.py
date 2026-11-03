"""Scenario analysis of individually assumed Mack segment correlations.

Invalid non-PSD single-pair shocks are explicitly marked, not silently repaired.
"""
from statistics import NormalDist

import numpy as np
import pandas as pd

from .mack_matrix import validate_correlation_matrix
from .portfolio_mack import aggregate_mack


def mack_matrix_sensitivity(
    segments: dict[str, pd.DataFrame],
    matrix: pd.DataFrame,
    shocks: tuple[float, ...] = (-0.2, -0.1, 0.0, 0.1, 0.2),
    confidence: float = 0.95,
) -> pd.DataFrame:
    """Change one symmetric correlation pair at a time, holding others fixed.

    Each row reports whether the stressed matrix is positive semidefinite.
    Invalid scenarios have missing risk results, never repaired correlations.
    """
    names = sorted(segments)
    baseline_matrix = validate_correlation_matrix(matrix, names)
    if not shocks or any(not np.isfinite(x) for x in shocks):
        raise ValueError("Shocks must be a nonempty sequence of finite numbers")
    baseline = aggregate_mack(segments, confidence=confidence)
    se = baseline["segments"]["mack_se"].to_numpy(dtype=float)
    reserve = float(baseline["total_reserve"])
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    baseline_se = float(np.sqrt(max(0.0, se @ baseline_matrix @ se)))
    rows = []
    for i, left in enumerate(names):
        for j in range(i + 1, len(names)):
            for shock in shocks:
                candidate = baseline_matrix.copy()
                candidate[i, j] += shock
                candidate[j, i] += shock
                valid = True
                try:
                    validate_correlation_matrix(
                        pd.DataFrame(candidate, index=names, columns=names), names,
                    )
                except ValueError:
                    valid = False
                total_se = (
                    float(np.sqrt(max(0.0, se @ candidate @ se))) if valid else np.nan
                )
                rows.append({
                    "segment_a": left,
                    "segment_b": names[j],
                    "shock": float(shock),
                    "correlation": float(candidate[i, j]),
                    "valid_psd": valid,
                    "total_reserve": reserve,
                    "total_se": total_se,
                    "delta_se": total_se - baseline_se if valid else np.nan,
                    "lower": max(0.0, reserve - z * total_se) if valid else np.nan,
                    "upper": reserve + z * total_se if valid else np.nan,
                    "diversification_benefit": float(se.sum()) - total_se if valid else np.nan,
                })
    return pd.DataFrame(rows, columns=[
        "segment_a", "segment_b", "shock", "correlation", "valid_psd",
        "total_reserve", "total_se", "delta_se", "lower", "upper",
        "diversification_benefit",
    ])
