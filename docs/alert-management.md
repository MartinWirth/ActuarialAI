# Phase 32: Risk Alert Management

The **Risk alert management** section in Streamlit lists stored alerts, ordered
by severity (red before yellow), and supports filtering by lifecycle state.

## Lifecycle

- `new` -> `acknowledged` -> `resolved`
- `new` -> `resolved` is also supported for immediate remediation.
- Reverse transitions and repeated transitions are rejected.
- A nonempty operator identifier is required and recorded with a UTC timestamp.
- Every transition is appended to the existing SHA-256 audit chain.
- Legacy alerts are displayed as `new` until explicitly updated.
- Each escalation event creates a separate alert; resolving one event does
  not automatically resolve other alerts for the same check.

The SQLite database remains local. The actor field is an operator-supplied
identifier, **not authenticated identity**. Use only with trusted operators;
production authorization requires integration with authenticated permissions.

## Optional critical alert email

Email is **disabled by default**. Configure environment variables in the
process running the monitoring CLI:

```powershell
$env:ACTUARIALAI_SMTP_HOST = "smtp.example.com"
$env:ACTUARIALAI_SMTP_PORT = "465"
$env:ACTUARIALAI_SMTP_USER = "account"
$env:ACTUARIALAI_SMTP_PASSWORD = "set-this-securely"
$env:ACTUARIALAI_ALERT_FROM = "alerts@example.com"
$env:ACTUARIALAI_ALERT_TO = "risk@example.com"
python -m actuarial_ai.risk_monitor_cli --portfolio portfolio.csv --interval-seconds 300 --email-critical
```

The CLI sends one TLS/SSL email per **newly saved run** containing newly
triggered red alerts. Unchanged snapshots and yellow-only alerts do not
send email. If required SMTP fields are absent, email is skipped.
SMTP delivery failure is printed to the console; it does not roll back
the already committed monitoring run, and there is **no automatic retry**.
Protect environment variables and credentials and avoid committing them.
This is an opt-in notification mechanism, not a guaranteed delivery service.

## Verification

```powershell
git pull
ruff check .
python -m pytest -q
streamlit run app.py
```
