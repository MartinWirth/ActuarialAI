"""Auditable, out-of-time monitoring of experimental reserving predictions."""
import numpy as np
import pandas as pd

from .backtest import backtest_metrics


def monitoring_report(predictions: pd.DataFrame, alert_ratio: float = 1.10) -> dict:
    """Compare out-of-time model errors, including per-valuation diagnostics.

    Alerts flag a relative increase in ML MAE over chain-ladder. No automated
    deployment decisions are made; threshold is illustrative, not calibrated.
    """
    if alert_ratio <= 0:
        raise ValueError("alert_ratio must be positive")
    required = {"valuation", "actual", "chain_ladder", "random_forest"}
    if not required.issubset(predictions.columns):
        raise ValueError("Missing monitoring columns")
    if predictions.empty:
        raise ValueError("No observations to monitor")
    if not np.isfinite(predictions[["actual", "chain_ladder", "random_forest"]].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite monitoring values")
    overall = backtest_metrics(predictions)
    rows = []
    for valuation, group in predictions.groupby("valuation", sort=True):
        metrics = backtest_metrics(group)
        baseline = float(metrics.loc["chain_ladder", "MAE"])
        candidate = float(metrics.loc["random_forest", "MAE"])
        rows.append({
            "valuation": valuation,
            "observations": len(group),
            "chain_ladder_mae": baseline,
            "random_forest_mae": candidate,
            "alert": candidate > baseline * alert_ratio if baseline > 0 else candidate > 0,
        })
    return {"overall": overall, "by_valuation": pd.DataFrame(rows),
            "alert_count": sum(row["alert"] for row in rows),
            "alert_ratio": alert_ratio}
