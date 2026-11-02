from dataclasses import replace

import pytest

from actuarial_ai.report_builder import ReportOptions
from actuarial_ai.report_history import get_report, list_reports, save_report


def test_save_list_retrieve_and_compare(tmp_path):
    db = tmp_path / "reports.sqlite3"
    options = ReportOptions()
    payload = {
        "version": "abc123", "source": "example.csv",
        "portfolio_csv": b"segment,origin,development,cumulative_paid\n",
        "pdf": b"%PDF-1.4\ntest",
        "options": options,
        "summary": {"baseline_reserve": 100.0, "segments": 1},
        "governance": {"status": "REVIEW_REQUIRED"},
    }
    first = save_report(db, **payload)
    second = save_report(
        db, **{**payload, "version": "def456",
               "options": replace(options, include_risk=False),
               "summary": {"baseline_reserve": 120.0, "segments": 1}},
    )
    assert second > first
    entries = list_reports(db)
    assert [item["id"] for item in entries] == [second, first]
    assert entries[0]["summary"]["baseline_reserve"] == 120.0
    assert entries[1]["governance"]["status"] == "REVIEW_REQUIRED"
    saved = get_report(db, first)
    assert saved["pdf"] == payload["pdf"]
    assert saved["portfolio_csv"] == payload["portfolio_csv"]
    assert saved["options"]["include_risk"] is True
    assert len(saved["input_sha256"]) == 64
    assert get_report(db, 9999) is None


def test_invalid_payload_does_not_save(tmp_path):
    db = tmp_path / "archive.sqlite3"
    with pytest.raises(ValueError):
        save_report(
            db, version="x", source="x.csv", portfolio_csv=b"csv",
            pdf=b"not pdf", options=ReportOptions(), summary={},
        )
    assert list_reports(db) == []


def test_limit_validation(tmp_path):
    with pytest.raises(ValueError):
        list_reports(tmp_path / "db.sqlite3", limit=0)
