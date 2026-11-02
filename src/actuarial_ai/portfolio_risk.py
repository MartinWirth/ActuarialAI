"""Illustrative correlated Monte Carlo reserve risk by insurance segment.

Lognormal multipliers are applied to deterministic Chain-Ladder reserves.
This is a user-assumption scenario model, not a calibrated predictive distribution.
"""
import numpy as np
import pandas as pd

from .portfolio import portfolio_report


def simulate_portfolio_risk(
    segments: dict[str, pd.DataFrame],
    simulations: int = 5000,
    volatility: float = 0.20,
    correlation: float = 0.25,
    confidence: float = 0.95,
    seed: int = 42,
) -> dict:
    """Return correlated reserve simulations, VaR and upper-tail expected shortfall."""
    if isinstance(simulations, bool) or not isinstance(simulations, int) or simulations < 100:
        raise ValueError("simulations must be an integer >= 100")
    if not np.isfinite(volatility) or not 0 <= volatility <= 2:
        raise ValueError("volatility must be finite and between 0 and 2")
    if not np.isfinite(correlation) or not 0 <= correlation <= 1:
        raise ValueError("correlation must be finite and between 0 and 1")
    if not np.isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError("confidence must be strictly between 0 and 1")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    baseline = portfolio_report(segments)
    names = baseline["segments"]["segment"].tolist()
    reserves = baseline["segments"]["baseline_reserve"].to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    shared = rng.standard_normal((simulations, 1))
    independent = rng.standard_normal((simulations, len(names)))
    shocks = np.sqrt(correlation) * shared + np.sqrt(1 - correlation) * independent
    multipliers = np.exp(volatility * shocks - 0.5 * volatility**2)
    segment_draws = multipliers * reserves[None, :]
    portfolio_draws = segment_draws.sum(axis=1)
    var = float(np.quantile(portfolio_draws, confidence))
    # Tail conditional on simulated losses at/above the empirical VaR threshold.
    tail = portfolio_draws[portfolio_draws >= var]
    expected_shortfall = float(tail.mean())
    return {
        "samples": pd.DataFrame(segment_draws, columns=names),
        "portfolio_samples": portfolio_draws,
        "segment_summary": pd.DataFrame({
            "segment": names,
            "baseline_reserve": reserves,
            "simulated_mean": segment_draws.mean(axis=0),
            "simulated_std": segment_draws.std(axis=0),
        }),
        "baseline_total_reserve": float(reserves.sum()),
        "mean": float(portfolio_draws.mean()),
        "std": float(portfolio_draws.std()),
        "var": var,
        "expected_shortfall": expected_shortfall,
        "confidence": confidence,
        "correlation": correlation,
        "volatility": volatility,
    }
