# Architecture

`synthetic_triangle()` → pandas cumulative claims triangle → `chain_ladder()` → development factors, completed triangle and reserve summary → Streamlit presentation.

Business logic is isolated in `src/actuarial_ai/reserving.py` for unit testing and future API integration. No external services, credentials or network data sources are required. Future phases can add validated ingestion, model comparison, uncertainty quantification and governance.
