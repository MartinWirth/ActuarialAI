# Phase 13 — Portfolio model governance

After uploading a portfolio CSV, enable **Run portfolio model governance assessment**.

The assessment compares the experimental Random Forest against the Chain-Ladder
baseline on identical historical portfolio-level one-step cumulative-paid
holdouts. It applies three configurable checks:

1. Minimum number of common valuation periods (default: 3).
2. Maximum Random Forest / Chain-Ladder portfolio MAE ratio (default: 1.10).
3. Maximum share of valuations with ML underprediction (default: 0.75).

If Chain-Ladder MAE is zero, the ratio is zero only if ML MAE is also zero;
otherwise the ratio is undefined and the check fails. Each check reports its
observed value, configured threshold and pass/fail result.

**DIAGNOSTIC_PASS** means all three configured diagnostic checks passed.
**REVIEW_REQUIRED** means at least one failed. Neither status constitutes
actuarial sign-off, production approval or reserve-risk calibration.

The JSON audit report contains a UTC generation timestamp, SHA-256 fingerprint
of the complete input triangles (segment names, origin/development labels and
values), model metrics, thresholds, check outcomes and limitations. The
fingerprint can verify that a report was generated from a specific input
snapshot; it is not a cryptographic signature or an approval record.

## Limitations

- Only one-step aggregate cumulative-paid forecast errors are assessed.
- Holdout periods overlap and sample sizes can be small.
- No empirical coverage validation for VaR or Expected Shortfall is performed.
- Independent actuarial review and governance processes remain necessary.
