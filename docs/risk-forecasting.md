# Phase 35 - Exploratory Risk Forecasting & Early Warning

The Phase 35 Streamlit section uses the persisted Phase 34 risk trend
(`total_se` from monitoring runs) to project Mack portfolio standard
error over the next 1–12 **observations**. The number of days between
observations is not modeled.

## Method

- Fits a simple linear trend to the full series (minimum four observations)
- Reports slope and rising/falling/flat trend
- Shows a nonnegative point forecast and widening residual-based bands
- Compares forecast estimates against configurable warning/critical limits
- Marks an early warning when the point estimate remains below the warning
  limit but the upper exploratory band reaches it
- Shows illustrative optimistic and stressed scenarios using a percentage
  adjustment to each point estimate
- Calculates walk-forward mean absolute error: each historical holdout
  observation is predicted from preceding observations only

The displayed bands are **not calibrated confidence or prediction
intervals**. The trend and thresholds are diagnostic and not regulatory
capital estimates, actuarial reserve guarantees, or a production-grade
early warning model. Sparse, irregular or structural-break series can
produce misleading extrapolations. A low walk-forward MAE does not
guarantee future performance.

The forecasting implementation is read-only. It does not automatically
create monitoring alerts or send notifications.

## Run checks

```powershell
clear
git pull
ruff check .
python -m pytest -q
streamlit run app.py
```
