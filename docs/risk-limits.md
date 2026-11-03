# Phase 29: Risk limits and early warnings

In the multi-segment Streamlit view, select **Monitor Mack risk limits**.
Monitoring is **on demand**, not a background alerting service.

Configure portfolio Mack standard-error warning and critical ceilings,
absolute segment Euler share warning and critical ceilings, and
diversification-ratio warning and critical floors. Results use green,
yellow and red statuses, with the worst check determining overall status.
Boundary comparisons are inclusive; invalid threshold ordering is rejected.

Segment concentration is the **absolute** Euler contribution divided by
portfolio standard error. A negative Euler contribution can therefore
still trigger concentration alerts. The diversification ratio is
`(sum(standalone S.E.) - portfolio S.E.) / sum(standalone S.E.)`.

Export a monitoring snapshot as JSON. For history, upload a previously
saved **JSONL** monitoring history and download the appended version.
The application does not persist monitoring history on a server; retain
the downloaded JSONL file and upload it on the next assessment.
The table shows historical date, overall status and Mack S.E.
Imported snapshots are user-provided data, not authenticated audit records.

The configurable PDF includes an optional **Mack risk limits and early
warnings** section, with separate configurable portfolio S.E. thresholds.
The PDF uses the default segment concentration and diversification floors.
Its configuration is part of the report identity.

All correlations and limits are user assumptions. Alerts are diagnostic
only, not validated risk appetite or regulatory capital assessments.

Local verification:

```powershell
git pull
ruff check .
python -m pytest -q
streamlit run app.py
```
