# Phase 34 - Risk Management Reporting

The **Risk management reporting (Phase 34)** section of the Streamlit
Mack risk monitoring page reads the existing local SQLite database.

It shows open, critical, escalated and overdue alerts, mean resolution
time, and the trend of portfolio Mack standard error across stored
monitoring runs. Reports can be downloaded as:

- **CSV**: alert-level state, severity, age, operator and escalation
- **PDF**: management KPIs and the 15 most recent monitoring runs

The SLA is a configurable **reporting threshold** (default 24 hours)
applied to the age of still-open alerts. It is independent of the
automation escalation threshold. Age is measured from when a run was
inserted into the local database, not from the portfolio valuation date.
The resolution-time statistic uses the latest recorded workflow transition
timestamp; it is a diagnostic management measure, not a contractual SLA.

No new background service is installed. The report reflects the data
already stored in SQLite. A running monitoring CLI is required for
continuous collection. PDF and CSV are generated on demand. CSV fields
starting with spreadsheet formula characters are escaped.

## Verify locally

```powershell
clear
git pull
ruff check .
python -m pytest -q
streamlit run app.py
```
