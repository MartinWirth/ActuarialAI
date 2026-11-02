# Phase 25: Segment-specific Mack correlation matrix

Under **Multi-segment portfolio analysis**, enable **Use custom pairwise
Mack correlation matrix** to edit the assumed dependence between segments.
Rows and columns are sorted alphabetically by segment name. The editor
starts from the existing common-correlation scenario.

Validation requires exact segment labels, finite numeric entries, symmetry,
ones on the diagonal, entries between -1 and 1, and a positive-semidefinite
matrix. Invalid matrices are rejected rather than automatically repaired.

For segment standard errors `s` and user-assumed correlation matrix `R`,
portfolio prediction variance is `s.T @ R @ s`. Reserves remain additive.
The resulting standard error, illustrative normal interval and
diversification comparison are shown in the dashboard and, if selected,
in the configurable PDF report. The matrix is included in the report
configuration fingerprint.

The common-correlation sensitivity from Phase 24 remains a **separate**
equicorrelation scenario analysis; it does not vary individual matrix cells.

**Limitations:** The matrix is manually assumed, not empirically calibrated.
A mathematically valid correlation matrix is not evidence that its values
describe actual segment dependence. Mack's model assumptions and normal
interval limitations still apply. These results are not regulatory capital.

Run:

```powershell
git pull
ruff check .
python -m pytest -q
streamlit run app.py
```
