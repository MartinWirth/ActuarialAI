# Phase 4 — Model governance and monitoring

## Purpose and model inventory

- **Baseline:** deterministic volume-weighted Chain-Ladder.
- **Candidate:** Random Forest predicting age-to-age cumulative paid development factors.
- **Use:** educational prototype using synthetic triangles only.
- **Owner / approver:** not assigned; no production approval.
- **Training data:** observed cumulative paid development pairs, never held-out future diagonals.
- **Target:** next observed cumulative paid amount, **not** final ultimate reserve error.
- **Validation:** rolling calendar-time holdouts, comparing identical cells for both models.

## Monitoring policy (demonstration)

For each valuation diagonal, calculate Chain-Ladder and Random-Forest MAE on the same held-out cells. Raise an illustrative alert when Random-Forest MAE exceeds baseline MAE by more than 10%. If baseline MAE is zero, any positive candidate MAE triggers an alert. The dashboard displays aggregate metrics, period-level results, and alert counts. This is a diagnostic only; no model is promoted or blocked automatically.

## Explainability

The dashboard already reports in-sample permutation importance of the development-age and cumulative-paid features. This is a model-agnostic approximation, **not SHAP** and not a causal explanation. SHAP may be added after explicit compatibility and numerical validation across supported Python versions.

## Limitations and approval checklist

- Synthetic triangles do not represent a real insurer's claim mix or calendar-year trends.
- Backtests evaluate one-step cumulative paid forecasts, not reserve ultimate error.
- Sparse development ages and repeated origin-period observations limit reliability.
- No independent validation sample, model registry, drift reference distribution, or governance sign-off.
- Before real use: approved data lineage, documented assumptions, stress scenarios, independent actuarial validation, privacy review, monitoring ownership, and reproducible model artifacts.

## Optional SHAP integration

Install with `pip install -e '.[explain]'`, then enable **Compute SHAP explanations** in Streamlit. A TreeExplainer attributes the experimental random forest's **predicted age-to-age factor** to development age and paid amount. The implementation checks that baseline plus SHAP contributions reconstruct the model prediction. Mean absolute contributions summarize the observed training pairs (capped at 100 rows). These are in-sample, feature-correlated, and not causal; they do not explain ultimate reserves. The optional SHAP test runs in CI after installing the explain extra.
