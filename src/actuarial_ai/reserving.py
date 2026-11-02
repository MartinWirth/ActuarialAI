"""Deterministic chain-ladder for cumulative paid claims."""
import numpy as np
import pandas as pd


def synthetic_triangle(n: int = 8, seed: int = 42) -> pd.DataFrame:
    """Generate a reproducible, upper-left cumulative paid claims triangle."""
    if n < 2:
        raise ValueError("At least two origin periods are required")
    rng = np.random.default_rng(seed)
    development = np.array([0.42 + 0.58 * (1 - np.exp(-0.55 * (j + 1))) for j in range(n)])
    ultimate = rng.lognormal(mean=13.5, sigma=0.20, size=n)
    values = np.full((n, n), np.nan)
    for i in range(n):
        cumulative = ultimate[i] * development * rng.uniform(0.98, 1.02)
        cumulative = np.maximum.accumulate(cumulative)
        values[i, : n - i] = cumulative[: n - i]
    return pd.DataFrame(values, index=[f"AY{2026-n+i}" for i in range(n)], columns=[f"D{j+1}" for j in range(n)])


def chain_ladder(triangle: pd.DataFrame, *, allow_decrease: bool = False) -> dict:
    """Volume-weighted chain ladder; returns factors, completed triangle and reserves."""
    arr = triangle.to_numpy(dtype=float)
    n, m = arr.shape
    if n < 2 or n != m:
        raise ValueError("Expected a square triangle of at least size 2")
    for i in range(n):
        expected = n - i
        if not np.all(np.isfinite(arr[i, :expected])) or not np.all(np.isnan(arr[i, expected:])):
            raise ValueError("Expected contiguous observed cells and missing future cells")
        if np.any(arr[i, :expected] < 0) or (not allow_decrease and np.any(np.diff(arr[i, :expected]) < 0)):
            raise ValueError("Cumulative claims must be nonnegative and nondecreasing")
    factors = []
    for j in range(m - 1):
        count = n - j - 1
        denominator = arr[:count, j].sum()
        numerator = arr[:count, j + 1].sum()
        if denominator <= 0:
            raise ValueError("Cannot estimate development factor from zero volume")
        factors.append(numerator / denominator)
    completed = arr.copy()
    for i in range(n):
        for j in range(n - i, m):
            completed[i, j] = completed[i, j - 1] * factors[j - 1]
    latest = np.array([arr[i, n - i - 1] for i in range(n)])
    ultimate = completed[:, -1]
    reserves = ultimate - latest
    return {
        "factors": pd.Series(factors, index=triangle.columns[:-1], name="LDF"),
        "completed": pd.DataFrame(completed, index=triangle.index, columns=triangle.columns),
        "summary": pd.DataFrame({"latest_paid": latest, "ultimate": ultimate, "reserve": reserves}, index=triangle.index),
        "total_reserve": float(reserves.sum()),
    }
