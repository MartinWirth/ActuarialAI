# Phase 9 — Portfolio Monte Carlo risk

The portfolio dashboard can run a seeded Monte Carlo simulation after uploading a valid multi-segment CSV. It displays simulated mean reserve, empirical Value at Risk (VaR), Expected Shortfall, a histogram, segment-level summaries, and downloadable simulation draws.

## Method

Each segment's deterministic Chain-Ladder reserve is multiplied by a lognormal random factor. Gaussian latent shocks combine a shared component and a segment-specific component. The shared component has user-selected latent correlation from 0 to 1; the multiplier's log-scale volatility is also user-selected. Multipliers are mean-one by construction. Portfolio reserve equals the sum of simulated segment reserves for each draw.

VaR is the empirical reserve quantile at the selected confidence level. Expected Shortfall is the average simulated reserve at or above that empirical quantile. Both refer to total outstanding reserve levels, not loss relative to baseline. The same seed and inputs reproduce the same draws.

## Limitations

This is an educational assumption-driven sensitivity model, not an empirically calibrated predictive reserve distribution. The input correlation is for latent Gaussian shocks, not necessarily the Pearson correlation of final reserve amounts. No historical correlation estimation, parameter or process uncertainty calibration, regulatory capital interpretation, tail factors, currency conversion, or diversification validation is provided. VaR and Expected Shortfall should not be used for pricing, solvency or financial reporting without independent actuarial validation. Uploaded data is processed by the running Streamlit environment; avoid sensitive data on untrusted deployments.
