"""Illustrative Mack (1993) chain-ladder prediction errors, no tail factor."""
from statistics import NormalDist

import numpy as np
import pandas as pd

from .data_io import validate_triangle
from .reserving import chain_ladder


def mack_chain_ladder(triangle: pd.DataFrame, confidence: float = 0.95) -> dict:
    """Return Mack distribution-free mean squared prediction errors.

    Last age variance is extrapolated from earlier ages because only one
    development pair is available. Normal intervals are illustrative, not
    guaranteed probability coverage.
    """
    if not 0.5 < confidence < 1:
        raise ValueError("confidence must be strictly between 0.5 and 1")
    t = validate_triangle(triangle)
    n = len(t)
    if n < 4:
        raise ValueError("Mack needs at least four origin periods for variance estimation")
    arr = t.to_numpy(dtype=float)
    deterministic = chain_ladder(t)
    factors = deterministic["factors"].to_numpy(dtype=float)
    completed = deterministic["completed"].to_numpy(dtype=float)
    sigma2 = np.full(n - 1, np.nan)
    volume = np.empty(n - 1)
    for j in range(n - 1):
        count = n - j - 1
        base = arr[:count, j]
        volume[j] = base.sum()
        if count >= 2:
            if np.any(base <= 0):
                raise ValueError("Mack requires positive observed claim amounts")
            residuals = arr[:count, j + 1] / base - factors[j]
            sigma2[j] = float(np.sum(base * residuals**2) / (count - 1))
    if not np.isfinite(sigma2[:-1]).all():
        raise ValueError("Insufficient observations for Mack variances")
    # Conventional Mack extrapolation for the final (single-pair) age.
    # The last two estimable variances must be positive.
    if sigma2[-2] <= 0 or sigma2[-3] <= 0:
        raise ValueError("Cannot extrapolate final Mack variance from zero variance")
    sigma2[-1] = min(
        sigma2[-2] ** 2 / sigma2[-3],
        sigma2[-2],
        sigma2[-3],
    )
    # Recursive process + parameter error for each accident year.
    mse = np.zeros(n)
    for i in range(n):
        for j in range(n - i - 1, n - 1):
            c = completed[i, j]
            mse[i] = (
                mse[i] * factors[j] ** 2
                + sigma2[j] * c
                + sigma2[j] * c**2 / volume[j]
            )
    # Covariance from shared estimated development factors (Mack total MSEP).
    covariance = 0.0
    for i in range(n):
        for k in range(i + 1, n):
            # Older origin i and younger origin k share future factors
            # beginning at development age n-i-1.
            for j in range(n - i - 1, n - 1):
                covariance += (
                    completed[i, -1] * completed[k, -1]
                    * sigma2[j] / (factors[j] ** 2 * volume[j])
                )
    total_mse = float(mse.sum() + 2 * covariance)
    if total_mse < 0:
        raise ValueError("Negative aggregate mean squared prediction error")
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    summary = deterministic["summary"].copy()
    summary["mack_se"] = np.sqrt(np.maximum(mse, 0))
    summary["lower"] = np.maximum(0, summary["reserve"] - z * summary["mack_se"])
    summary["upper"] = summary["reserve"] + z * summary["mack_se"]
    reserve = deterministic["total_reserve"]
    total_se = float(np.sqrt(total_mse))
    return {
        "summary": summary,
        "sigma2": pd.Series(sigma2, index=t.columns[:-1], name="mack_sigma2"),
        "total_reserve": reserve,
        "total_se": total_se,
        "total_mse": total_mse,
        "confidence": confidence,
        "total_lower": max(0.0, reserve - z * total_se),
        "total_upper": reserve + z * total_se,
        "assumptions": (
            "Mack conditional variance proportional to cumulative paid; "
            "independent origin periods; final sigma squared extrapolated; "
            "normal approximation truncated at zero; no tail factor."
        ),
    }
