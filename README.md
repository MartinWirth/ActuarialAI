# ActuarialAI

[![CI](https://github.com/MartinWirth/ActuarialAI/actions/workflows/ci.yml/badge.svg)](https://github.com/MartinWirth/ActuarialAI/actions/workflows/ci.yml)

**Phase 1–2 — Explainable Insurance Reserving and experimental ML benchmark.** A reproducible educational implementation of volume-weighted deterministic chain-ladder reserving, including a Streamlit dashboard, synthetic data, tests and CI.

## Quick start

Requires Python 3.10+.

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
pytest -q
streamlit run app.py
```

## Method

For development period j, the volume-weighted link ratio is f_j = sum(C[i,j+1]) / sum(C[i,j]), summing only over origin years with both values observed. Future cumulative paid claims are projected by multiplying the latest observed cumulative amount by successive link ratios. Outstanding reserve equals estimated ultimate less latest paid.

## Scope and limitations

- All data are synthetic; no confidential insurance records are used.
- The synthetic generator is illustrative, not a calibrated insurance loss model.
- No tail factor, inflation adjustment, case reserves, stochastic reserve uncertainty, regulatory capital or IFRS 17 treatment is included.
- The method assumes historical development patterns are representative of future development.
- This prototype is **not** suitable for financial reporting or actuarial sign-off.

See [requirements](docs/requirements.md) and [architecture](docs/architecture.md).

## Phase 2 — experimental ML benchmark

The dashboard compares classical Chain-Ladder with random-forest development-factor forecasts, and shows a withheld-calendar-diagonal one-step MAE. This is an educational proof of concept; it does not claim improved predictive accuracy. See [ML benchmark methodology](docs/ml-benchmark.md).
