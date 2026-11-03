# Phase 36 - Forecast Model Validation & Governance

The Streamlit Phase 36 section validates the Phase 35 Mack standard
error projection against two simple baselines using one-step
**expanding-window walk-forward** backtesting.

## Models and metrics

- **Linear:** least-squares trend fit to all prior observations
- **Moving average:** mean of the last configured number of observations
- **Naive:** last observed value
- **MAE**, **RMSE**, and **MAPE** for each model
- **Best model:** smallest walk-forward MAE, with a deterministic tie break
- **Model version:** `36.1` recorded in the validation result

All models predict the same holdout points, beginning at observation 4.
MAPE excludes zero actuals and returns `None` if every actual is zero.

## Drift diagnostic

Compare the mean of the latest `window` observations to the preceding
non-overlapping window. Divide the difference by the earlier window's
sample standard deviation. Flag a shift at the configurable threshold.
If the earlier window is constant, any nonzero shift is flagged.

At least `max(5, 2 * window)` observations are needed. These are
exploratory diagnostics, **not** validated regulatory model controls.
No model is automatically promoted and no alert is persisted or emailed.

## Run

```powershell
clear
git pull
ruff check .
python -m pytest -q
streamlit run app.py
```
