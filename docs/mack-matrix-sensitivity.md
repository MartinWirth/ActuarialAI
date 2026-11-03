# Phase 26: Pairwise Mack matrix sensitivity

Enable **Use custom pairwise Mack correlation matrix**, enter a valid
symmetric positive-semidefinite matrix, and select **Run pairwise Mack
matrix sensitivity**.

The stress grid changes **one symmetric segment pair at a time** by
-2h, -h, 0, +h, +2h, with configurable step h. All other correlations
remain fixed. The table reports the resulting correlation, PSD validity,
portfolio Mack standard error, change from the base matrix, interval,
and diversification. Invalid (non-PSD or out-of-range) matrices are
**not repaired**: their risk outputs are missing. The heatmap uses only
valid scenarios; the CSV retains all scenarios and their validity flags.

To include the same pairwise stress table in the configurable PDF,
enable **Include pairwise Mack matrix sensitivity**. The matrix,
inclusion setting, and stress step are part of the report configuration
fingerprint. The original Phase 24 common-correlation sensitivity
remains a separate analysis.

**Interpretation:** These are hypothetical dependency assumptions, not
estimated correlations or regulatory capital. Positive-semidefinite
constraints can prevent an isolated pair change even when its new value
is between -1 and 1. Reserve estimates are unchanged; only the
portfolio uncertainty changes.

Run locally:

```powershell
git pull
ruff check .
python -m pytest -q
streamlit run app.py
```
