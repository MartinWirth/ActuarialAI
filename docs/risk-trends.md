# Phase 30: Historical Mack risk monitoring and trend analysis

The **Monitor Mack risk limits** section accepts a previously exported
JSONL history and appends a fresh on-demand snapshot. The new historical
analysis displays:

- Chronologically ordered Mack S.E. and change since the previous snapshot
- Percentage change per observation and configurable growth warning
- Segment risk check values over time
- Consecutive yellow/red limit breaches per check, with configurable run length
- Trend table CSV and cumulative JSONL history exports

The JSONL parser validates timestamp timezone, numeric metrics, status
values, check labels, and duplicate timestamps. Imported records are sorted
by their timestamps. Missing observations are not assumed green. A change
is **per observation**, not an annualized growth rate. Repeated breach counts
refer to observed consecutive snapshots for the same check, not calendar
days. These are diagnostics under user-provided limits and correlations.

The configurable PDF report has an **Include historical Mack risk trends**
option with a separate JSONL upload. It summarizes observations, first
and latest Mack S.E., growth warnings, repeated breaches, and up to 15
recent observations. The uploaded history is included in the report
configuration fingerprint. PDF generation does not silently add an
unrecorded snapshot.

Monitoring remains **on demand**: no scheduled polling, notifications,
server-side historical storage or authenticated audit trail is added.

Run:

```powershell
git pull
ruff check .
python -m pytest -q
streamlit run app.py
```
