# Phase 33: Automated risk alert follow-up

The monitoring CLI now evaluates alert automation on **every polling cycle**,
including cycles where the snapshot has not changed.

## Recovery

An unresolved alert is automatically marked `resolved` only if its
(scope, name) check is explicitly `green` in the latest saved monitoring
snapshot. Missing checks do **not** imply recovery. Both `new` and
`acknowledged` alerts may auto-resolve. The transition is recorded in
the monitoring SHA-256 audit chain with actor `system`.

## Overdue escalation

A `red` alert still in `new` state is escalated once when its
monitoring run's insertion time exceeds the configured age. Escalation
does not modify the alert's lifecycle state; it records an escalation
marker and audit event. Acknowledged or resolved alerts do not escalate.

Use the CLI:

```powershell
clear
python -m actuarial_ai.risk_monitor_cli --portfolio portfolio.csv --interval-seconds 300 --escalate-after-hours 24
```

Escalations are recorded locally, **not automatically emailed**. The
existing `--email-critical` option continues to notify on new red
breaches only. The Streamlit Phase 33 section displays alert age,
escalation markers, and a manual `Run alert automation now` button.
Periodic automation requires a running CLI process.

The escalation age uses the server's monitoring insertion timestamp,
not the source portfolio's valuation timestamp. Alert handling is
local and assumes trusted operators. SQLite and the hash chain do not
provide tamper-proof or authenticated audit guarantees.

## Validation

```powershell
clear
git pull
ruff check .
python -m pytest -q
streamlit run app.py
```
