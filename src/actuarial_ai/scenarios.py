"""Deterministic reserve scenarios and stress tests on future development only."""
import numpy as np
import pandas as pd

from .reserving import chain_ladder


def stress_reserves(triangle: pd.DataFrame, inflation: float = 0.0,
                    factor_stress: float = 0.0) -> dict:
    """Project outstanding claims under stressed future incremental payments.

    Each future increment is scaled by (1+inflation)**future_step and
    (1+factor_stress). Observed payments remain unchanged.
    """
    if not np.isfinite(inflation) or inflation <= -1:
        raise ValueError("inflation must be finite and greater than -1")
    if not np.isfinite(factor_stress) or factor_stress <= -1:
        raise ValueError("factor_stress must be finite and greater than -1")
    baseline = chain_ladder(triangle)
    completed = baseline["completed"].to_numpy(dtype=float).copy()
    n = len(triangle)
    latest = baseline["summary"]["latest_paid"].to_numpy(dtype=float)
    for i in range(n):
        first_future = n - i
        for j in range(first_future, n):
            baseline_increment = (baseline["completed"].iat[i, j]
                                  - baseline["completed"].iat[i, j - 1])
            step = j - first_future + 1
            stressed_increment = baseline_increment * (1 + factor_stress) * (
                (1 + inflation) ** step
            )
            completed[i, j] = completed[i, j - 1] + stressed_increment
    ultimate = completed[:, -1]
    reserve = ultimate - latest
    summary = pd.DataFrame({
        "latest_paid": latest, "ultimate": ultimate, "reserve": reserve,
        "baseline_reserve": baseline["summary"]["reserve"].to_numpy(dtype=float),
    }, index=triangle.index)
    return {
        "summary": summary,
        "completed": pd.DataFrame(completed, index=triangle.index, columns=triangle.columns),
        "total_reserve": float(reserve.sum()),
        "baseline_total_reserve": baseline["total_reserve"],
        "reserve_delta": float(reserve.sum() - baseline["total_reserve"]),
        "inflation": inflation,
        "factor_stress": factor_stress,
    }


def scenario_comparison(triangle: pd.DataFrame, inflation: float = 0.05,
                        factor_stress: float = 0.10) -> pd.DataFrame:
    """Compare symmetric illustrative favorable/base/adverse assumptions."""
    if inflation < 0 or inflation >= 1 or factor_stress < 0 or factor_stress >= 1:
        raise ValueError("Scenario magnitudes must be in [0, 1)")
    rows = []
    for name, sign in [("Best case", -1), ("Base case", 0), ("Worst case", 1)]:
        outcome = stress_reserves(triangle, sign * inflation, sign * factor_stress)
        rows.append({
            "scenario": name,
            "inflation": sign * inflation,
            "factor_stress": sign * factor_stress,
            "total_reserve": outcome["total_reserve"],
            "reserve_delta": outcome["reserve_delta"],
        })
    return pd.DataFrame(rows)


def sensitivity_grid(triangle: pd.DataFrame,
                     inflation_values=(-0.05, 0.0, 0.05),
                     factor_values=(-0.10, 0.0, 0.10)) -> pd.DataFrame:
    """Compute reserve response over a user-specified assumption grid."""
    rows = []
    for inflation in inflation_values:
        for factor_stress in factor_values:
            result = stress_reserves(triangle, float(inflation), float(factor_stress))
            rows.append({"inflation": float(inflation), "factor_stress": float(factor_stress),
                         "total_reserve": result["total_reserve"],
                         "reserve_delta": result["reserve_delta"]})
    return pd.DataFrame(rows)
