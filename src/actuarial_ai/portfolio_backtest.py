"""Historical portfolio one-step diagnostics, not ultimate-reserve risk calibration."""
import numpy as np
import pandas as pd

from .backtest import rolling_backtest


def portfolio_backtest(segments: dict[str, pd.DataFrame]) -> dict:
    """Aggregate identical valuation-period holdouts without future leakage.

    Only valuation periods present in *every* segment are compared. The
    resulting errors concern next-diagonal cumulative paid, not ultimate
    reserves or the distribution of reserve risk.
    """
    if not segments:
        raise ValueError("At least one segment is required")
    rows = []
    for name, triangle in segments.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Segment names must be nonempty strings")
        predictions = rolling_backtest(triangle)
        if predictions.empty:
            raise ValueError(f"No historical holdouts for segment {name}")
        for valuation, group in predictions.groupby("valuation", sort=True):
            rows.append({
                "segment": name,
                "valuation": int(valuation),
                "observations": len(group),
                "actual": float(group["actual"].sum()),
                "chain_ladder": float(group["chain_ladder"].sum()),
                "random_forest": float(group["random_forest"].sum()),
            })
    by_segment = pd.DataFrame(rows)
    common = set.intersection(*(
        set(group["valuation"]) for _, group in by_segment.groupby("segment")
    ))
    if not common:
        raise ValueError("No common historical valuation periods across segments")
    comparable = by_segment[by_segment["valuation"].isin(common)].copy()
    portfolio = comparable.groupby("valuation", as_index=False)[
        ["observations", "actual", "chain_ladder", "random_forest"]
    ].sum()
    metrics = []
    for model in ("chain_ladder", "random_forest"):
        error = portfolio[model].to_numpy() - portfolio["actual"].to_numpy()
        metrics.append({
            "model": model, "valuations": len(error),
            "bias": float(np.mean(error)),
            "mae": float(np.mean(np.abs(error))),
            "rmse": float(np.sqrt(np.mean(error ** 2))),
            "underprediction_rate": float(np.mean(error < 0)),
        })
        portfolio[f"{model}_error"] = error
    return {
        "by_segment": comparable.reset_index(drop=True),
        "portfolio": portfolio,
        "metrics": pd.DataFrame(metrics),
        "common_valuations": len(common),
        "limitations": (
            "One-step aggregate cumulative-paid forecast errors do not "
            "calibrate reserve volatility, correlation, VaR or Expected Shortfall."
        ),
    }
