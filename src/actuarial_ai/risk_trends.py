"""Analysis of portable Mack risk monitoring snapshots over time."""
from datetime import datetime
import json

import numpy as np
import pandas as pd

_STATUSES = {"green", "yellow", "red"}


def parse_monitoring_history(data: bytes | str) -> list[dict]:
    """Read and validate JSONL snapshots without silently dropping malformed rows."""
    try:
        raw = data.decode("utf-8") if isinstance(data, bytes) else data
        records = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid monitoring JSONL: {exc}") from exc
    monitoring_trends(records)
    return records


def monitoring_trends(
    records: list[dict],
    *,
    growth_warning: float = 0.1,
    consecutive_breach_warning: int = 2,
) -> dict:
    """Return chronological series, check trends and consecutive breach runs.

    Growth uses the previous *observation*, not annualized time.
    Duplicate timestamps and missing or nonfinite numeric values are rejected.
    """
    if not np.isfinite(growth_warning) or growth_warning < 0:
        raise ValueError("Growth warning must be finite and nonnegative")
    if consecutive_breach_warning < 1:
        raise ValueError("Consecutive breach warning must be at least one")
    rows = []
    checks = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Monitoring record must be an object")
        try:
            timestamp = datetime.fromisoformat(record["as_of_utc"].replace("Z", "+00:00"))
            status = record["overall_status"]
            metrics = record["metrics"]
            total_se = float(metrics["total_se"])
            diversification = float(metrics["diversification_pct"])
            observed_checks = record["checks"]
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            raise ValueError("Monitoring record has missing or invalid fields") from exc
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("Monitoring timestamps must include a timezone")
        if status not in _STATUSES or not np.isfinite(total_se) or total_se < 0:
            raise ValueError("Invalid monitoring status or Mack S.E.")
        if not np.isfinite(diversification):
            raise ValueError("Invalid diversification metric")
        if not isinstance(observed_checks, list):
            raise ValueError("Monitoring checks must be a list")
        rows.append({
            "as_of_utc": pd.Timestamp(timestamp).tz_convert("UTC"),
            "status": status,
            "total_se": total_se,
            "diversification_pct": diversification,
        })
        seen = set()
        for item in observed_checks:
            if not isinstance(item, dict):
                raise ValueError("Monitoring check must be an object")
            try:
                scope, name, check_status = item["scope"], item["name"], item["status"]
                value = float(item["value"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("Invalid monitoring check") from exc
            if not isinstance(scope, str) or not isinstance(name, str):
                raise ValueError("Invalid monitoring check label")
            if check_status not in _STATUSES or not np.isfinite(value):
                raise ValueError("Invalid monitoring check status or value")
            key = (scope, name)
            if key in seen:
                raise ValueError("Duplicate check in monitoring snapshot")
            seen.add(key)
            checks.append({
                "as_of_utc": pd.Timestamp(timestamp).tz_convert("UTC"),
                "scope": scope, "name": name, "status": check_status, "value": value,
            })
    columns = ["as_of_utc", "status", "total_se", "diversification_pct"]
    timeline = pd.DataFrame(rows, columns=columns)
    if not timeline.empty:
        timeline = timeline.sort_values("as_of_utc").reset_index(drop=True)
        if timeline["as_of_utc"].duplicated().any():
            raise ValueError("Duplicate monitoring timestamps")
    timeline["se_change"] = timeline["total_se"].diff()
    previous = timeline["total_se"].shift()
    timeline["se_growth_pct"] = timeline["se_change"].div(previous.where(previous != 0))
    timeline["growth_warning"] = timeline["se_growth_pct"] >= growth_warning
    check_table = pd.DataFrame(
        checks, columns=["as_of_utc", "scope", "name", "status", "value"],
    )
    breaches = []
    if not check_table.empty:
        check_table = check_table.sort_values(
            ["scope", "name", "as_of_utc"],
        ).reset_index(drop=True)
        for (scope, name), group in check_table.groupby(["scope", "name"], sort=True):
            run = 0
            for _, check in group.iterrows():
                run = run + 1 if check["status"] != "green" else 0
                breaches.append({
                    "as_of_utc": check["as_of_utc"],
                    "scope": scope, "name": name, "status": check["status"],
                    "consecutive_breaches": run,
                    "repeated_warning": run >= consecutive_breach_warning,
                })
    breach_table = pd.DataFrame(breaches, columns=[
        "as_of_utc", "scope", "name", "status",
        "consecutive_breaches", "repeated_warning",
    ])
    segment_trends = check_table.loc[
        check_table["scope"] == "segment"
    ].copy().reset_index(drop=True)
    return {
        "timeline": timeline,
        "segment_trends": segment_trends,
        "breaches": breach_table,
        "growth_warnings": int(timeline["growth_warning"].sum()),
        "repeated_breach_warnings": int(breach_table["repeated_warning"].sum()),
        "assumptions": (
            "Growth is relative to the previous observation, not annualized. "
            "Consecutive breaches are based on available snapshots only; "
            "missing dates are not interpreted as green. Thresholds and "
            "correlations are user-defined diagnostics."
        ),
    }
