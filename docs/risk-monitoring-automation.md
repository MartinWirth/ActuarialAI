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

Use `--interval-seconds 0` for one run. Each polling cycle reads the
file again; unchanged files are deduplicated. To monitor updated risk,
a separate trusted process or user **must refresh the snapshot file**.
The polling runner does not recompute actuarial results from source
triangles, send email, or start automatically when Streamlit launches.
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
