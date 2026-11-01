# Phase 8 — Multi-segment portfolio analysis

Upload a UTF-8 CSV with columns `segment,origin,development,cumulative_paid`. Include only observed cumulative payments, one row per combination. Every segment must form a square upper-left triangle, with origin and development labels that sort chronologically/according to development age. For example, use `AY2020` and `D01` through `D12`; avoid `D1` to `D12` because lexical sorting puts `D10` before `D2`.

Each segment is independently validated and projected using volume-weighted Chain-Ladder. Portfolio baseline and stressed reserves are **sums** of segment reserves. Reserve-to-latest-paid and share-of-baseline-reserve provide descriptive indicators, not calibrated risk measures. Stress assumptions are applied consistently across segments, with CSV exports of segment-level results and portfolio best/base/worst comparisons.

No diversification credit, cross-segment dependence, uncertainty calibration, currency conversion, tail factor, or discounting is modeled. All amounts must be in a common currency and compatible valuation basis. Portfolio uploads are processed in the Streamlit runtime; do not submit confidential data to untrusted deployments.
