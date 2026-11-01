"""Export actuarial analysis as an auditable, machine-readable JSON report."""
import json
from datetime import datetime, timezone

import pandas as pd

from .reserving import chain_ladder


def analysis_report(triangle: pd.DataFrame, source: str = "synthetic") -> dict:
    """Build report using the same validated chain-ladder calculation as dashboard."""
    result = chain_ladder(triangle)
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "method": "volume_weighted_chain_ladder",
        "origin_periods": len(triangle),
        "development_periods": int(triangle.shape[1]),
        "total_reserve": float(result["total_reserve"]),
        "development_factors": [float(v) for v in result["factors"]],
        "origin_summary": [
            {"origin": str(index), "latest_paid": float(row["latest_paid"]),
             "ultimate": float(row["ultimate"]), "reserve": float(row["reserve"])}
            for index, row in result["summary"].iterrows()
        ],
        "limitations": [
            "No tail factor or discounting",
            "Assumes historical development factors represent future development",
            "Requires independent actuarial review before decision-making",
        ],
    }


def report_json(report: dict) -> bytes:
    """Serialize report, rejecting NaN/Infinity rather than emitting invalid JSON."""
    return json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
