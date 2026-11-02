"""Sensitivity analysis for assumption-driven portfolio Monte Carlo risk."""
import numpy as np
import pandas as pd

from .portfolio_risk import simulate_portfolio_risk


def portfolio_risk_sensitivity(
    segments: dict,
    volatilities: tuple[float, ...] = (0.10, 0.20, 0.30),
    correlations: tuple[float, ...] = (0.0, 0.25, 0.75),
    simulations: int = 2000,
    confidence: float = 0.95,
    seed: int = 42,
) -> pd.DataFrame:
    """Evaluate VaR and ES across assumptions with common random seeds.

    This grid is a scenario comparison, not parameter calibration. Every cell
    uses the same seed to reduce simulation noise between scenario comparisons.
    """
    if not volatilities or not correlations:
        raise ValueError("At least one volatility and correlation is required")
    if any(not np.isfinite(v) or v < 0 for v in volatilities):
        raise ValueError("Volatilities must be finite and nonnegative")
    if any(not np.isfinite(c) or not 0 <= c <= 1 for c in correlations):
        raise ValueError("Correlations must be finite and between 0 and 1")
    rows = []
    for volatility in volatilities:
        for correlation in correlations:
            risk = simulate_portfolio_risk(
                segments, simulations=simulations, volatility=float(volatility),
                correlation=float(correlation), confidence=confidence, seed=seed,
            )
            rows.append({
                "volatility": float(volatility),
                "correlation": float(correlation),
                "baseline_reserve": float(risk["baseline_reserve"]),
                "mean_reserve": float(risk["mean"]),
                "var": float(risk["var"]),
                "expected_shortfall": float(risk["expected_shortfall"]),
            })
    return pd.DataFrame(rows)
