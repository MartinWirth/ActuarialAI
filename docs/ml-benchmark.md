# Phase 2 — experimental ML reserving

## Approach

A random forest regressor learns observed age-to-age development factors from development age and cumulative paid claims. The fitted model recursively predicts future cumulative paid values. At development ages with fewer than three observed pairs, it uses classical volume-weighted chain-ladder factors.

## Validation

The one-step holdout removes the latest observed calendar diagonal from the training pairs and predicts the withheld cumulative values from preceding paid values. It reports mean absolute error (MAE) on cumulative paid claims. This prevents training on the withheld outcomes but does not establish out-of-sample superiority.

## Important limitations

- The synthetic data do not represent real claim settlement dynamics.
- The random forest is a proof of concept and is not guaranteed to outperform chain ladder.
- This is not a full reserving backtest; only one calendar diagonal is held out.
- No uncertainty intervals, hyperparameter search, tail factors, exposure adjustments, inflation, or claims-level covariates.
- A stronger evaluation should compare both methods over several rolling valuation dates, with identical available information and reserve/ultimate error metrics.
- Do not use results for regulatory, accounting, or financial decisions.
