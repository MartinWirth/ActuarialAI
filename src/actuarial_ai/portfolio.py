"""Multi-segment portfolio reserving and deterministic stress aggregation."""
import numpy as np
import pandas as pd

from .data_io import validate_triangle
from .scenarios import stress_reserves


def portfolio_report(segments: dict[str, pd.DataFrame], inflation: float = 0.0,
                     factor_stress: float = 0.0) -> dict:
    """Aggregate independent segment projections; no diversification assumed."""
    if not segments:
        raise ValueError("At least one segment is required")
    if any(not isinstance(name, str) or not name.strip() for name in segments):
        raise ValueError("Segment names must be nonempty strings")
    rows = []
    details = {}
    for name, triangle in segments.items():
        clean = validate_triangle(triangle)
        outcome = stress_reserves(clean, inflation, factor_stress)
        baseline = outcome["baseline_total_reserve"]
        stressed = outcome["total_reserve"]
        latest_paid = float(outcome["summary"]["latest_paid"].sum())
        rows.append({
            "segment": name,
            "origin_periods": len(clean),
            "latest_paid": latest_paid,
            "baseline_reserve": baseline,
            "stressed_reserve": stressed,
            "reserve_delta": stressed - baseline,
            "reserve_to_paid": baseline / latest_paid if latest_paid > 0 else np.nan,
        })
        details[name] = outcome
    table = pd.DataFrame(rows)
    totals = {
        "latest_paid": float(table["latest_paid"].sum()),
        "baseline_reserve": float(table["baseline_reserve"].sum()),
        "stressed_reserve": float(table["stressed_reserve"].sum()),
        "reserve_delta": float(table["reserve_delta"].sum()),
    }
    total_paid = totals["latest_paid"]
    totals["reserve_to_paid"] = (
        totals["baseline_reserve"] / total_paid if total_paid > 0 else float("nan")
    )
    table["baseline_reserve_share"] = (
        table["baseline_reserve"] / totals["baseline_reserve"]
        if totals["baseline_reserve"] > 0 else 0.0
    )
    return {"segments": table, "totals": totals, "details": details,
            "inflation": inflation, "factor_stress": factor_stress}


def portfolio_scenarios(segments: dict[str, pd.DataFrame],
                        inflation: float = 0.05,
                        factor_stress: float = 0.10) -> pd.DataFrame:
    """Symmetric stress comparison aggregated across all segments."""
    if not np.isfinite(inflation) or not np.isfinite(factor_stress):
        raise ValueError("Scenario magnitudes must be finite")
    if not 0 <= inflation < 1 or not 0 <= factor_stress < 1:
        raise ValueError("Scenario magnitudes must be in [0, 1)")
    rows = []
    for label, sign in [("Best case", -1), ("Base case", 0), ("Worst case", 1)]:
        report = portfolio_report(segments, sign * inflation, sign * factor_stress)
        rows.append({"scenario": label, "inflation": sign * inflation,
                     "factor_stress": sign * factor_stress, **report["totals"]})
    return pd.DataFrame(rows)
