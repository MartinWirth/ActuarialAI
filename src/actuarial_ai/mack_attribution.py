"""Euler variance attribution for user-assumed Mack segment dependence."""
import numpy as np
import pandas as pd

from .mack_matrix import validate_correlation_matrix
from .portfolio_mack import aggregate_mack


def mack_risk_attribution(
    segments: dict[str, pd.DataFrame],
    matrix: pd.DataFrame,
    confidence: float = 0.95,
) -> dict:
    """Allocate portfolio Mack variance and S.E. across segments and pairs.

    Segment variance contributions s_i * (R s)_i sum to total variance.
    Euler S.E. contributions divide these by total S.E. and also sum to it.
    Pair cross-variance is 2 * R_ij * s_i * s_j, i < j.
    Negative contributions are possible and economically meaningful.
    """
    names = sorted(segments)
    correlation = validate_correlation_matrix(matrix, names)
    baseline = aggregate_mack(segments, confidence=confidence)
    errors = baseline["segments"]["mack_se"].to_numpy(dtype=float)
    covariance_times_errors = correlation @ errors
    variance_contributions = errors * covariance_times_errors
    variance = max(0.0, float(errors @ covariance_times_errors))
    portfolio_se = float(np.sqrt(variance))
    if portfolio_se > 0:
        se_contributions = variance_contributions / portfolio_se
        se_shares = se_contributions / portfolio_se
    else:
        se_contributions = np.zeros(len(names), dtype=float)
        se_shares = np.zeros(len(names), dtype=float)
    by_segment = pd.DataFrame({
        "segment": names,
        "standalone_se": errors,
        "variance_contribution": variance_contributions,
        "euler_se_contribution": se_contributions,
        "se_share": se_shares,
    })
    pairs = []
    for i, left in enumerate(names):
        for j in range(i + 1, len(names)):
            cross = float(2 * correlation[i, j] * errors[i] * errors[j])
            pairs.append({
                "segment_a": left,
                "segment_b": names[j],
                "correlation": float(correlation[i, j]),
                "cross_variance": cross,
                "share_of_variance": cross / variance if variance > 0 else 0.0,
            })
    by_pair = pd.DataFrame(pairs, columns=[
        "segment_a", "segment_b", "correlation",
        "cross_variance", "share_of_variance",
    ])
    return {
        "segments": by_segment,
        "pairs": by_pair,
        "total_variance": variance,
        "total_se": portfolio_se,
        "standalone_variance": float(errors @ errors),
        "total_cross_variance": float(by_pair["cross_variance"].sum()),
        "assumptions": (
            "Euler attribution under a user-assumed correlation matrix; "
            "negative allocations can occur. Not calibrated regulatory capital."
        ),
    }
