"""Educational bootstrap of chain-ladder age-to-age factors.

Bootstrap observed development pairs within each age independently. This
illustrates parameter uncertainty only; it is NOT a full reserve distribution.
"""
import numpy as np
import pandas as pd

from .reserving import chain_ladder


def bootstrap_reserves(triangle: pd.DataFrame, simulations: int = 500,
                       seed: int = 42, confidence: float = 0.90) -> dict:
    """Estimate conditional reserve variation from resampled link ratios."""
    if simulations < 2:
        raise ValueError("simulations must be at least 2")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    chain_ladder(triangle)  # validate input and ensure conventional triangle
    arr = triangle.to_numpy(dtype=float)
    n = len(arr)
    rng = np.random.default_rng(seed)
    factor_draws = np.empty((simulations, n - 1))
    for age in range(n - 1):
        count = n - age - 1
        current = arr[:count, age]
        following = arr[:count, age + 1]
        if current.sum() <= 0:
            raise ValueError("zero development volume")
        for k in range(simulations):
            indices = rng.integers(0, count, size=count)
            denominator = current[indices].sum()
            factor_draws[k, age] = (following[indices].sum() / denominator
                                    if denominator > 0 else following.sum() / current.sum())
    reserves = np.zeros(simulations)
    for origin in range(n):
        last_age = n - origin - 1
        paid = arr[origin, last_age]
        ultimate = paid * np.prod(factor_draws[:, last_age:], axis=1)
        reserves += ultimate - paid
    alpha = (1 - confidence) / 2
    return {
        "samples": reserves,
        "mean": float(np.mean(reserves)),
        "lower": float(np.quantile(reserves, alpha)),
        "upper": float(np.quantile(reserves, 1 - alpha)),
        "confidence": confidence,
    }
