# Phase 39 - Active Model Execution

The active approved model is loaded from the Phase 38 deployment registry and executed against a supplied Mack standard-error monitoring history. The runtime supports linear trend extrapolation, recursive moving average, and naive last-value forecasts. Predictions are by observation index, not by calendar date.

The execution fails closed if no model is active, the model or deployment audit is invalid, inputs are invalid, or the active deployment changes before persistence. A registered-but-not-activated model cannot run. Execution requires an authenticated user with read_reports permission.

Each run stores its actor, timestamp, model ID, model version, hashed input values, result JSON and result hash in SQLite. History checks result hashes for accidental tampering. Raw observations are not persisted in the execution log. The hash is not a defense against full database compromise.

There is no external HTTP API or unattended job runner in this phase; the Python function is the application interface. Runtime quality evaluation against later actuals and production service integration remain future work. No fallback model is silently selected.

Local checks:

```powershell
clear
git pull
ruff check .
python -m pytest -q
streamlit run app.py
```
