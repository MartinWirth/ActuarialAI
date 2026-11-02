# ActuarialAI

[![CI](https://github.com/MartinWirth/ActuarialAI/actions/workflows/ci.yml/badge.svg)](https://github.com/MartinWirth/ActuarialAI/actions/workflows/ci.yml)

**Phase 1–2 — Explainable Insurance Reserving and experimental ML benchmark.** A reproducible educational implementation of volume-weighted deterministic chain-ladder reserving, including a Streamlit dashboard, synthetic data, tests and CI.

## Quick start

Requires Python 3.10+.

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
pytest -q
streamlit run app.py
```

## Method

For development period j, the volume-weighted link ratio is f_j = sum(C[i,j+1]) / sum(C[i,j]), summing only over origin years with both values observed. Future cumulative paid claims are projected by multiplying the latest observed cumulative amount by successive link ratios. Outstanding reserve equals estimated ultimate less latest paid.

## Scope and limitations

- All data are synthetic; no confidential insurance records are used.
- The synthetic generator is illustrative, not a calibrated insurance loss model.
- No tail factor, inflation adjustment, case reserves, stochastic reserve uncertainty, regulatory capital or IFRS 17 treatment is included.
- The method assumes historical development patterns are representative of future development.
- This prototype is **not** suitable for financial reporting or actuarial sign-off.

See [requirements](docs/requirements.md) and [architecture](docs/architecture.md).

## Phase 2 — experimental ML benchmark

The dashboard compares classical Chain-Ladder with random-forest development-factor forecasts, and shows a withheld-calendar-diagonal one-step MAE. This is an educational proof of concept; it does not claim improved predictive accuracy. See [ML benchmark methodology](docs/ml-benchmark.md).

## Phase 3 — uncertainty and explainability

The dashboard now includes bootstrap development-factor sensitivity and in-sample permutation importance for the experimental random forest. These are educational diagnostics, **not** calibrated predictive confidence intervals or causal explanations. See [methodology and limitations](docs/uncertainty-and-explainability.md).

## Phase 4 — model governance

The rolling calendar-time comparison now includes per-valuation MAE monitoring and an illustrative underperformance alert when Random Forest exceeds Chain-Ladder MAE by more than 10%. See [model governance, explainability and limitations](docs/model-governance.md). Existing permutation importance is not SHAP; this phase does not claim SHAP support.

## Phase 5 — import and reporting

Upload a cumulative paid claims triangle in **wide** CSV or XLSX format. The first column must contain unique origin labels; subsequent columns are development ages ordered from earliest to latest. For an `n × n` triangle, row 1 must contain `n` observed values, row 2 `n-1`, down to the final row with one observed value. Leave future cells blank. Observed amounts must be numeric, finite, nonnegative and nondecreasing; each development age must have positive volume.

Install Excel support with `pip install -e '.[excel]'`. In the Streamlit sidebar, upload a file; the dashboard validates it before calculating reserves. Download a validated CSV and a JSON Chain-Ladder analysis report. The report includes a timestamp, source filename, method, factors, origin-level reserves and limitations.

**Privacy:** Uploaded data is processed in the environment where Streamlit runs. Do not upload sensitive claims information to an untrusted hosted deployment. The application does not implement authentication, encrypted storage, or data retention controls. Outputs are illustrative and require actuarial review.

## Phase 6 — quality diagnostics

The dashboard provides a quality summary, age-specific robust outlier screening, and downloadable pair-level CSV diagnostics. Sparse development ages are marked unassessable. Flags do not alter calculations. See [methodology](docs/data-quality.md).

## Phase 7 — scenario analysis

Interactive best/base/worst reserve stress tests and a 3×3 inflation/development sensitivity grid are available in Streamlit, with CSV downloads. Observed payments remain unchanged; shocks affect future projected incremental payments only. See [scenario methodology](docs/scenario-analysis.md).

## Phase 8 — multi-segment portfolio

Upload long-form portfolio CSVs to aggregate independently validated segment reserves, compare baseline and stressed totals, review segment reserve shares and reserve-to-paid indicators, and export results. See [portfolio data schema and limitations](docs/portfolio-analysis.md).

## Phase 9 — portfolio Monte Carlo risk

With a validated multi-segment CSV uploaded, enable **Run portfolio Monte Carlo** in Streamlit to explore assumed reserve volatility and latent cross-segment correlation. Review simulated reserve VaR and Expected Shortfall, a distribution chart, and segment-level outcomes. Download simulated reserves as CSV. This is an educational assumption-driven model, not a calibrated actuarial capital model. See [methodology and limitations](docs/portfolio-risk.md).
