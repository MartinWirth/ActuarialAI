# Phase 10 — Model validation and governance

Enable **Run model validation** in Streamlit to compare Chain-Ladder and Random Forest on identical rolling, out-of-time, one-step cumulative-paid holdout cells. The dashboard displays MAE, RMSE, per-valuation MAE, a threshold-based ML deterioration alert, and the model with lower observed overall MAE. A downloadable JSON report includes the evaluation method, model hyperparameters, alert threshold, input-data SHA-256 fingerprint, timestamp, and limitations.

## Reproducibility

The input fingerprint is calculated from origin/development labels and numeric triangle cells (including missing future cells). It identifies the exact data values used for a report, not the Git commit or software package version. The Random Forest uses a fixed seed of 42. The report timestamp changes between runs; the remaining fields are deterministic for identical data and software versions. Store the Git commit SHA and Python dependency versions alongside reports when a formal audit trail is required.

## Interpretation

This evaluation measures one-step errors on cumulative paid claims, **not** reserve adequacy or ultimate reserve accuracy. Rolling holdouts can be small and overlapping; a lower MAE is descriptive and does not establish statistical superiority. The ML alert threshold is illustrative, not a calibrated risk tolerance. No automatic model approval, production promotion, or regulatory sign-off is performed. Independent actuarial validation remains necessary.
