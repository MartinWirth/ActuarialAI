import json

import pandas as pd
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.risk_monitor import save_monitoring_run
from actuarial_ai.risk_recalculation import calculate_monitoring_snapshot


def portfolio_csv(tmp_path):
    rows = []
    for name, seed in [("Motor", 1), ("Property", 2)]:
        triangle = synthetic_triangle(8, seed=seed)
        for origin, row in triangle.iterrows():
            for development, value in row.items():
                if pd.notna(value):
                    rows.append({
                        "segment": name,
                        "origin": str(origin),
                        "development": str(development),
                        "cumulative_paid": value,
                    })
    path = tmp_path / "portfolio.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_recalculation_and_sqlite_dedup(tmp_path):
    path = portfolio_csv(tmp_path)
    snapshot = calculate_monitoring_snapshot(path)
    assert snapshot["schema_version"] == "1.0"
    assert snapshot["metrics"]["total_se"] >= 0
    assert len(snapshot["checks"]) == 4
    assert snapshot["source_sha256"]
    assert snapshot == calculate_monitoring_snapshot(path)
    db = tmp_path / "risk.db"
    assert save_monitoring_run(db, snapshot)["created"]
    assert not save_monitoring_run(db, calculate_monitoring_snapshot(path))["created"]


def test_changed_limits_recalculate_alerts(tmp_path):
    path = portfolio_csv(tmp_path)
    normal = calculate_monitoring_snapshot(
        path, portfolio_warning=1e12, portfolio_critical=2e12,
        segment_share_warning=2, segment_share_critical=3,
    )
    severe = calculate_monitoring_snapshot(
        path, portfolio_warning=1, portfolio_critical=2,
    )
    assert normal["settings_sha256"] != severe["settings_sha256"]
    assert severe["overall_status"] == "red"
    db = tmp_path / "risk.db"
    save_monitoring_run(db, normal)
    assert save_monitoring_run(db, severe)["alerts"]


def test_invalid_limits_rejected(tmp_path):
    path = portfolio_csv(tmp_path)
    with pytest.raises(ValueError):
        calculate_monitoring_snapshot(
            path, portfolio_warning=200, portfolio_critical=100,
        )


def test_config_is_serializable(tmp_path):
    path = portfolio_csv(tmp_path)
    result = calculate_monitoring_snapshot(path, correlation=0.25)
    assert json.loads(json.dumps(result))["metrics"]["total_se"] > 0
