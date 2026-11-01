"""Data quality and exploratory anomaly diagnostics for paid-claims triangles."""
import numpy as np
import pandas as pd

from .data_io import validate_triangle


def quality_report(triangle: pd.DataFrame, threshold: float = 3.5,
                   min_peers: int = 4) -> dict:
    """Flag unusual age-to-age factors using age-specific robust z-scores.

    Median/MAD comparisons are made only within the same development age.
    Insufficient peers or zero MAD yield no anomaly flag, not a clean bill of health.
    """
    if threshold <= 0 or min_peers < 3:
        raise ValueError("threshold must be positive and min_peers at least 3")
    clean = validate_triangle(triangle)
    arr = clean.to_numpy(dtype=float)
    n = len(arr)
    records = []
    for age in range(n - 1):
        factors = []
        for origin in range(n - age - 1):
            current = arr[origin, age]
            following = arr[origin, age + 1]
            if current > 0:
                factors.append((origin, following / current))
        values = np.array([factor for _, factor in factors], dtype=float)
        median = float(np.median(values)) if len(values) else float("nan")
        mad = float(np.median(np.abs(values - median))) if len(values) else float("nan")
        comparable = len(values) >= min_peers and mad > 0
        for origin, factor in factors:
            score = float(0.6745 * (factor - median) / mad) if comparable else float("nan")
            records.append({
                "origin": str(clean.index[origin]),
                "development": str(clean.columns[age]),
                "factor": factor,
                "peer_count": len(values),
                "peer_median": median,
                "robust_z": score,
                "flagged": bool(comparable and abs(score) > threshold),
                "assessable": bool(comparable),
            })
    diagnostics = pd.DataFrame(records, columns=[
        "origin", "development", "factor", "peer_count", "peer_median",
        "robust_z", "flagged", "assessable",
    ])
    observed = n * (n + 1) // 2
    summary = {
        "origin_periods": n,
        "observed_cells": observed,
        "missing_future_cells": n * n - observed,
        "valid_triangle": True,
        "development_pairs": len(diagnostics),
        "assessable_pairs": int(diagnostics["assessable"].sum()),
        "unassessable_pairs": int((~diagnostics["assessable"]).sum()),
        "flagged_pairs": int(diagnostics["flagged"].sum()),
    }
    return {"summary": summary, "diagnostics": diagnostics,
            "flags": diagnostics.loc[diagnostics["flagged"]].reset_index(drop=True)}


def quality_csv(report: dict) -> bytes:
    """Export all pair-level diagnostics for review."""
    return report["diagnostics"].to_csv(index=False).encode("utf-8")
