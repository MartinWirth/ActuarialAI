# Phase 28: Consolidated Mack portfolio risk dashboard

In the multi-segment Streamlit view, select **Show consolidated portfolio
risk dashboard**. The dashboard uses the custom positive-semidefinite
correlation matrix when enabled, otherwise the common-correlation slider.

The overview contains:

- Current portfolio Mack standard error and independent benchmark
- Absolute and percentage diversification benefit
- Segment ranking by Euler standard-error contribution
- Pairwise covariance contributions, including negative values
- Alternative equicorrelation scenarios (0, 0.25, 0.50, 0.75, 1.00)
- Consolidated JSON export with metrics, tables, matrix and assumptions

Enable **Include consolidated Mack risk dashboard** under the configurable
PDF report to add a summary, segment ranking and scenario comparison.
This option is included in the report configuration fingerprint.

The current portfolio calculation uses the selected matrix. The scenario
table compares separate **uniform-correlation alternatives**, not
perturbations of the current matrix. The model does not estimate or
calibrate segment correlations. Negative Euler contributions may be
valid; these are not regulatory capital allocations.

Run locally:

```powershell
git pull
ruff check .
python -m pytest -q
streamlit run app.py
```
