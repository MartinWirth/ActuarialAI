"""Validated user-assumed pairwise correlation matrix for Mack portfolio risk."""
from statistics import NormalDist

import numpy as np
import pandas as pd

from .portfolio_mack import aggregate_mack


def validate_correlation_matrix(matrix: pd.DataFrame, names: list[str]) -> np.ndarray:
    """Return a correlation array in canonical segment order or raise ValueError."""
    if not isinstance(matrix, pd.DataFrame):
        raise TypeError("Correlation matrix must be a DataFrame")
    if (matrix.index.has_duplicates or matrix.columns.has_duplicates
            or set(matrix.index) != set(names) or set(matrix.columns) != set(names)
            or len(matrix) != len(names)):
        raise ValueError("Correlation matrix labels must match all segment names exactly")
    try:
        a = matrix.loc[names, names].to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("Correlation matrix must be numeric") from exc
    if not np.isfinite(a).all():
        raise ValueError("Correlation matrix must contain finite values")
    if not np.allclose(a, a.T, atol=1e-10, rtol=0):
        raise ValueError("Correlation matrix must be symmetric")
    if not np.allclose(np.diag(a), 1.0, atol=1e-10, rtol=0):
        raise ValueError("Correlation matrix diagonal must equal one")
    if np.any(np.abs(a) > 1 + 1e-10):
        raise ValueError("Correlations must be between -1 and 1")
    if np.linalg.eigvalsh(a).min() < -1e-10:
        raise ValueError("Correlation matrix must be positive semidefinite")
    return a


def aggregate_mack_matrix(
    segments: dict[str, pd.DataFrame],
    matrix: pd.DataFrame,
    confidence: float = 0.95,
) -> dict:
    """Aggregate Mack errors with an explicitly supplied PSD correlation matrix."""
    names = sorted(segments)
    a = validate_correlation_matrix(matrix, names)
    baseline = aggregate_mack(segments, confidence=confidence)
    se = baseline["segments"]["mack_se"].to_numpy(dtype=float)
    variance = max(0.0, float(se @ a @ se))
    total_se = float(np.sqrt(variance))
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    reserve = baseline["total_reserve"]
    return {
        **baseline,
        "total_se": total_se,
        "total_mse": variance,
        "lower": max(0.0, reserve - z * total_se),
        "upper": reserve + z * total_se,
        "diversification_benefit": float(se.sum()) - total_se,
        "correlation_matrix": pd.DataFrame(a, index=names, columns=names),
        "assumptions": (
            "User-supplied positive-semidefinite pairwise correlation matrix; "
            "not estimated or calibrated; illustrative normal interval."
        ),
    }
