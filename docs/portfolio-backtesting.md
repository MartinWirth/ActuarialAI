# Phase 12 — Historical portfolio backtesting

Enable **Run historical portfolio backtest** after uploading a multi-segment CSV.

Each segment is backtested using the existing rolling calendar-time one-step
holdouts. Only valuation periods available for **every** segment are included
in portfolio-level comparisons. Segment predictions and actual cumulative-paid
amounts are summed within each common valuation. Portfolio errors are measured
on those aggregate sums, not on the pooled individual observations.

Metrics for each model:
- **Bias**: mean predicted minus observed cumulative paid.
- **MAE**: mean absolute portfolio forecast error.
- **RMSE**: root mean squared portfolio forecast error.
- **Underprediction rate**: share of common valuations where prediction is below actual.

The dashboard shows a model comparison, portfolio holdout details, segment
diagnostics and a CSV export. Tests check deterministic output, aggregation,
invalid input and the exclusion of the latest held-out diagonal from training.

## Interpretation and limitations

These are one-step cumulative-paid prediction errors. They are **not** reserve
ultimate errors and do not validate the lognormal multipliers or latent
correlation used by portfolio Monte Carlo. The number of historical valuations
may be small; observations across valuation dates overlap. No empirical
calibration of volatility, correlation, VaR coverage, Expected Shortfall or
regulatory capital is claimed. A true reserve-risk calibration would require
sufficient longitudinal realised reserve outcomes and a separately specified
out-of-sample validation protocol.
