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

## Phase 10 — model validation and governance

Enable **Run model validation** in Streamlit to compare Chain-Ladder and Random Forest on identical rolling holdouts. View overall and valuation-level errors, threshold alerts, and download a reproducible JSON report with a SHA-256 input fingerprint and model specifications. See [methodology and limitations](docs/model-validation.md).

## Phase 11 — portfolio risk sensitivity

With a portfolio CSV loaded, enable **Run portfolio risk sensitivity grid** to compare Monte Carlo portfolio reserve VaR and Expected Shortfall over volatility assumptions (10%, 20%, 30%) and cross-segment latent correlation assumptions (0%, 25%, 75%). All grid cells use the same random seed and simulation count for a consistent illustrative comparison. The grid and a VaR pivot table are displayed and the full results can be downloaded as CSV. The results are assumption-driven, not empirically calibrated; they must not be interpreted as regulatory capital estimates.

## Phase 12 — historical portfolio backtesting

With a portfolio CSV uploaded, enable **Run historical portfolio backtest** to compare aggregate one-step cumulative-paid predictions from Chain-Ladder and Random Forest on common historical valuation periods. Review bias, MAE, RMSE and underprediction rates; inspect segment details and download CSV results. These metrics do **not** calibrate the assumption-driven reserve-risk simulation. See [historical portfolio backtesting](docs/portfolio-backtesting.md).

## Phase 13 — portfolio model governance

Enable **Run portfolio model governance assessment** after uploading a portfolio CSV. Configure minimum historical valuation periods, maximum Random Forest / Chain-Ladder MAE ratio and maximum underprediction rate. The dashboard shows diagnostic check outcomes and exports a JSON audit report with an input SHA-256 fingerprint. A diagnostic pass is **not** model approval or actuarial sign-off. See [governance criteria and limitations](docs/portfolio-governance.md).

## Example portfolio CSV

Use [`example/portfolio_example.csv`](example/portfolio_example.csv) to try the multi-segment upload in Streamlit. It contains **synthetic** cumulative paid claims for Motor, Property and Liability (10 origin periods per segment, 165 long-form records). Upload it using **Portfolio CSV** to explore portfolio reserving, Monte Carlo, sensitivity, historical backtesting and governance. No real claims or personal data are included.

## Phase 14 — PDF portfolio management report

Upload a portfolio CSV (for example [`example/portfolio_example.csv`](example/portfolio_example.csv)), then enable **Generate portfolio management PDF report**. Download a PDF with executive summary, segment reserves, illustrative Monte Carlo VaR/Expected Shortfall, historical model comparisons, diagnostic governance status and limitations. The PDF uses ReportLab (installed with the project). PDF content tests use pypdf from the dev extra. This report is illustrative and does not constitute actuarial approval or calibrated capital analysis.

## Phase 15 — configurable, versioned executive PDF reporting

After uploading a portfolio CSV, enable **Generate configurable portfolio PDF report**. Choose whether to include segment tables, an embedded reserve bar chart, Monte Carlo risk metrics and model governance. Set the simulation count and confidence level. The executive dashboard always includes segment count, latest paid and baseline reserve. The downloaded PDF embeds a SHA-256 report version derived from the complete input triangles and configuration, and the filename includes the version prefix. Repeating the same inputs/settings produces the same version fingerprint, though PDF bytes may differ because the generation timestamp changes. Versions are not stored server-side; there is no report registry or approval workflow. The output remains illustrative and requires independent actuarial review.

## Phase 16 — local SQLite report history

Generate a configured PDF from a portfolio CSV and click **Save report snapshot to local history**. Each click appends a new SQLite record in `data/actuarialai_reports.sqlite3` containing the PDF, original CSV, report fingerprint, configuration, executive summary and available governance results. **Saved portfolio report history** lists snapshots, permits PDF/source CSV downloads and compares the baseline reserves of two saved runs. Database files are excluded from Git. The archive is local to the Streamlit server, has no authentication, encryption, retention policy or approval workflow, and must not be exposed to untrusted users or used for sensitive production claims without additional controls. The SHA-256 fingerprint identifies input/configuration, not the unique saved run or PDF bytes.
