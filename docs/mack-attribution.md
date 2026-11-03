# Phase 27: Mack portfolio risk attribution

Enable **Run Mack portfolio risk attribution** in the multi-segment
Streamlit view. The calculation uses the edited PSD correlation matrix
when enabled, otherwise the common-correlation slider. It reports:

- Standalone segment Mack standard error
- Euler contribution to portfolio Mack variance and standard error
- Share of portfolio variance (can be negative)
- Pairwise cross-variance and its share of portfolio variance
- Segment and pair bar charts and separate CSV downloads

The portfolio variance is `s.T @ R @ s`. Each segment receives
`s_i * (R @ s)_i` variance units; dividing by portfolio S.E. gives
its Euler S.E. contribution. These contributions sum to total portfolio
S.E. when that value is positive. Pairwise contributions
`2 * R_ij * s_i * s_j` sum to the cross-variance term; they do
**not** include standalone segment variances.

Enable **Include Mack risk attribution** in the configurable PDF
report to embed both tables. The option changes the report fingerprint.

**Caveats:** User-assumed correlations are not estimated or calibrated.
Negative contributions reflect offsetting dependence, not negative
standalone risk. These are model attribution diagnostics, not regulatory
capital allocations.

Run locally:

```powershell
git pull
ruff check .
python -m pytest -q
streamlit run app.py
```
