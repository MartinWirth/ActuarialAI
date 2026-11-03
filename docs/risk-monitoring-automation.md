# Phase 31: Local automated risk monitoring and alerts

The multi-segment Streamlit section **Monitor Mack risk limits** now offers
**Persist monitoring run and evaluate alerts**. Each run is stored in a
local SQLite database (default `mack_monitoring.sqlite3`). The UI can
load stored snapshots, display alert transitions and verify the audit chain.

## Alert engine

Each saved snapshot is validated and deduplicated by its canonical SHA-256
fingerprint. For every risk check, an alert is generated only when its
status worsens: green to yellow/red (new breach) or yellow to red
(escalation). Unchanged red checks do not generate duplicate alerts.
Checks absent from the previous snapshot are treated as green.
Snapshots, alerts and append-only audit events are stored transactionally.

The audit log has a SHA-256 hash chain that detects accidental or
unsophisticated edits. It is **not** tamper-proof against a privileged
attacker able to rewrite the database and hashes.

## Local polling

An optional local process periodically reads a snapshot JSON file
produced by the app and ingests it into SQLite:

```powershell
python -m actuarial_ai.risk_monitor_cli --snapshot mack_risk_monitoring_snapshot.json --database mack_monitoring.sqlite3 --interval-seconds 300
```

Use `--interval-seconds 0` for one run. In snapshot mode, each polling cycle reads the file again; unchanged
snapshots are deduplicated. For direct triangle recalculation use the
`--portfolio` mode below. The runner does not send email or start
automatically when Streamlit launches.
Console alerts are emitted on new/worsened breaches. Stop with Ctrl+C.

SQLite data stays on the machine running Streamlit/CLI. Protect its
directory and do not place it in a shared public location. The current
UI accepts a database path from a trusted operator; do not expose this
capability to untrusted users. For unattended deployment, use OS task
scheduling or a process supervisor to launch the CLI.

Run:

```powershell
git pull
ruff check .
python -m pytest -q
streamlit run app.py
```

## Automatic Mack recalculation directly from CSV

A snapshot file is **no longer required**. To calculate from a portfolio
CSV containing `segment,origin,development,cumulative_paid`, run:

```powershell
python -m actuarial_ai.risk_monitor_cli --portfolio portfolio.csv --database mack_monitoring.sqlite3 --interval-seconds 300
```

For explicit thresholds and correlation, create `risk-monitor-config.json`:

```json
{
  "correlation": 0.25,
  "portfolio_warning": 100000,
  "portfolio_critical": 200000,
  "segment_share_warning": 0.4,
  "segment_share_critical": 0.6,
  "diversification_warning": 0.1,
  "diversification_critical": 0.0
}
```

Then run:

```powershell
python -m actuarial_ai.risk_monitor_cli --portfolio portfolio.csv --config risk-monitor-config.json --interval-seconds 300
```

Each polling cycle reads the current CSV, recalculates Mack portfolio
uncertainty and user-defined limit checks, and persists a snapshot.
The source CSV modification time is used as the snapshot timestamp
(**not** an actuarial valuation date). Identical source bytes, settings,
and timestamp are deduplicated. Rewriting the same CSV can create a
new observation if its modification time changes.

The legacy `--snapshot` mode remains supported. Only one of
`--portfolio` and `--snapshot` may be used. The monitoring process
must remain running for periodic recalculation; it does not install
itself as an operating-system service. Inputs must be trusted local
files. No email or network notifications are sent.
