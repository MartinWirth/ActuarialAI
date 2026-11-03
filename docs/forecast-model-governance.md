# Phase 37: Forecast Model Governance

Model candidates are validated using Phase 36 walk-forward evaluation before registration. The SQLite registry stores model identity, parameters, validation metrics, drift results, and a content digest.

ACTUARY and ADMIN may register and submit models. REVIEWER may approve or reject a submitted model. AUDITOR may read records. Submitters cannot approve their own submissions.

Workflow: DRAFT -> IN_REVIEW -> APPROVED or REJECTED. Rejected models may be resubmitted. Every transition is recorded in a hash-chained audit history. Hashes provide local tamper evidence, not protection against full database replacement.

Approving a model does not deploy it. Re-register after collecting more monitoring observations to retain new validation evidence.

Local verification: run git pull, ruff check ., python -m pytest -q, and streamlit run app.py.
