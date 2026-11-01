# Phase 7 — Scenario analysis and stress testing

The model starts from the volume-weighted Chain-Ladder completed triangle. Observed cumulative payments are never changed. For each future development cell, the baseline **incremental** payment is multiplied by `(1 + development_increment_stress) * (1 + inflation_stress) ** future_step`, where future_step starts at 1 for the next projected cell. The stressed increments are accumulated from the latest observed payment to calculate ultimate claims and outstanding reserves.

The dashboard offers symmetric best/base/worst scenarios and a 3-by-3 sensitivity grid. The base case exactly reproduces Chain-Ladder. CSV exports contain assumptions, stressed total reserves and reserve changes relative to baseline.

These are deterministic sensitivities, not statistical confidence intervals, probabilities, or calibrated best/worst forecasts. Inflation and development shocks may overlap economically; their independent multiplication is an illustrative assumption. No tail factor, discounting, calendar-year trend estimation, or regulatory capital treatment is included. Review scenarios with an actuary before making decisions.
