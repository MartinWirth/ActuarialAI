# Phase 38 - Model Deployment and Lifecycle

Only APPROVED forecast candidates can be activated by an authenticated REVIEWER. The local SQLite deployment history records actor, model ID, previous model ID, decision reason, timestamp, action, and hash-chain evidence.

An approved model can be activated, replaced by another approved model, or restored with an explicit rollback action if it was previously active. The dashboard displays the active champion, approved challengers, validation MAE/RMSE/MAPE, and deployment history.

This phase records a controlled **deployment selection**. It does not yet route the Phase 35 forecasting computation through the selected model, nor deploy a production service. Comparisons use each candidate's stored validation dataset, which can differ between registrations. They should not be treated as a fair head-to-head benchmark without identical holdouts.

Local audit hashes detect partial tampering but cannot protect against an attacker with full SQLite write access. The registry and deployment database require filesystem access controls.

Run locally:

```powershell
clear
git pull
ruff check .
python -m pytest -q
streamlit run app.py
```
