import json

import pandas as pd
import pytest

from actuarial_ai.risk_trends import monitoring_trends, parse_monitoring_history


def snapshot(day, se, status="green", segment="Motor"):
    return {
        "schema_version": "1.0",
        "as_of_utc": f"2026-11-{day:02d}T12:00:00+00:00",
        "overall_status": status,
        "metrics": {"total_se": se, "diversification_pct": 0.2},
        "checks": [{
            "scope": "segment", "name": segment,
            "status": status, "value": 0.5,
        }],
    }


def test_sorted_growth_and_recurring_breaches():
    records = [
        snapshot(3, 130, "red"),
        snapshot(1, 100, "green"),
        snapshot(2, 110, "yellow"),
    ]
    result = monitoring_trends(records, growth_warning=0.1)
    timeline = result["timeline"]
    assert timeline["total_se"].tolist() == [100, 110, 130]
    assert result["growth_warnings"] == 2
    assert result["repeated_breach_warnings"] == 1
    assert result["breaches"]["consecutive_breaches"].tolist() == [0, 1, 2]
    assert len(result["segment_trends"]) == 3


def test_jsonl_roundtrip():
    records = [snapshot(1, 100), snapshot(2, 110)]
    raw = "\n".join(json.dumps(item) for item in records) + "\n"
    assert parse_monitoring_history(raw.encode("utf-8")) == records


def test_empty_history_is_supported():
    result = monitoring_trends([])
    assert result["timeline"].empty
    assert result["breaches"].empty
    assert result["growth_warnings"] == 0


@pytest.mark.parametrize("records", [
    [snapshot(1, 100), snapshot(1, 110)],
    [snapshot(1, -1)],
    [{**snapshot(1, 100), "overall_status": "unknown"}],
    [{**snapshot(1, 100), "as_of_utc": "2026-11-01"}],
    [{**snapshot(1, 100), "metrics": {"total_se": float("nan"),
                                     "diversification_pct": 0.2}}],
])
def test_invalid_snapshots_rejected(records):
    with pytest.raises((ValueError, TypeError)):
        monitoring_trends(records)


def test_missing_segment_observations_are_not_counted_as_green():
    records = [snapshot(1, 100, "yellow"), snapshot(2, 101, "yellow", "Property")]
    result = monitoring_trends(records)
    assert result["repeated_breach_warnings"] == 0


def test_timezone_order_and_growth_threshold():
    records = [snapshot(1, 100), snapshot(2, 110)]
    result = monitoring_trends(records, growth_warning=0.1)
    assert pd.notna(result["timeline"].iloc[0]["as_of_utc"])
    assert result["timeline"].iloc[1]["se_change"] == pytest.approx(10)


def test_invalid_jsonl_rejected():
    with pytest.raises(ValueError):
        parse_monitoring_history('{"bad":')
