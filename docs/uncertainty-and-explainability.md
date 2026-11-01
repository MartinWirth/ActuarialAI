# Phase 3 — uncertainty and explainability (prototype)

## Bootstrap interval

For each development age, observed paid-claim pairs are resampled with replacement. The volume-weighted development factor is recalculated in each simulation. Simulated factors are applied to the latest observed cumulative paid values to produce a total reserve sample.

**Interpretation:** This is a pedagogical sensitivity analysis of observed development-factor estimation, not a statistically calibrated predictive reserve distribution. It does not capture process risk, dependencies between development ages, calendar-year inflation, claims inflation, or model error. Sparse ages (especially the final age with one observed pair) cannot produce meaningful empirical variation. Reported quantiles are **not** regulatory capital, Solvency II risk measures, or actuarial confidence statements.

## Feature importance

A random forest is fitted to observed development factors using development age and cumulative paid amount. Permutation importance measures the in-sample increase in prediction error when one feature is shuffled. It is descriptive, susceptible to feature correlation and overfitting, and **does not establish causality** or generalization.

## Future production prerequisites

Use real-world governed data, rolling out-of-time validation, reserve-error backtesting, claims-level exposure variables, calibrated process/parameter uncertainty, model monitoring and qualified actuarial review.
