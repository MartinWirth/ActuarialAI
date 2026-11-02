import json

import pytest

from actuarial_ai.approval_workflow import (
    audit_events,
    audit_export,
    report_status,
    transition_report,
    verify_audit_chain,
)
from actuarial_ai.report_builder import ReportOptions
from actuarial_ai.report_history import save_report


@pytest.fixture
def archive(tmp_path):
    db = tmp_path / "reports.sqlite3"
    report_id = save_report(
        db, version="version", source="example.csv",
        portfolio_csv=b"csv", pdf=b"%PDF-test",
        options=ReportOptions(), summary={"baseline_reserve": 1.0},
    )
    return db, report_id


def test_full_review_and_rejection_cycle(archive):
    db, report_id = archive
    assert report_status(db, report_id) == "DRAFT"
    transition_report(db, report_id, "Alice", "IN_REVIEW", "Ready for review")
    transition_report(db, report_id, "Bob", "REJECTED", "Missing explanation")
    transition_report(db, report_id, "Alice", "IN_REVIEW", "Updated notes")
    transition_report(db, report_id, "Bob", "APPROVED", "Reviewed")
    assert report_status(db, report_id) == "APPROVED"
    events = audit_events(db, report_id)
    assert len(events) == 4
    assert verify_audit_chain(events)
    exported = json.loads(audit_export(db, report_id))
    assert exported["chain_valid"] is True
    assert len(exported["events"]) == 4


@pytest.mark.parametrize("target", ["APPROVED", "REJECTED", "DRAFT"])
def test_invalid_initial_transitions(archive, target):
    db, report_id = archive
    with pytest.raises(ValueError):
        transition_report(db, report_id, "Reviewer", target, "Notes")
    assert audit_events(db, report_id) == []


def test_approval_terminal_and_required_actor_reason(archive):
    db, report_id = archive
    with pytest.raises(ValueError):
        transition_report(db, report_id, "", "IN_REVIEW", "Reason")
    with pytest.raises(ValueError):
        transition_report(db, report_id, "Alice", "IN_REVIEW", " ")
    transition_report(db, report_id, "Alice", "IN_REVIEW", "Review")
    transition_report(db, report_id, "Bob", "APPROVED", "Accepted")
    with pytest.raises(ValueError):
        transition_report(db, report_id, "Alice", "IN_REVIEW", "Reopen")


def test_tampering_detected(archive):
    db, report_id = archive
    transition_report(db, report_id, "Alice", "IN_REVIEW", "Original")
    import sqlite3

    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE approval_events SET reason = ? WHERE report_id = ?",
            ("Altered", report_id),
        )
    assert not verify_audit_chain(audit_events(db, report_id))
    with pytest.raises(ValueError, match="integrity"):
        transition_report(db, report_id, "Bob", "APPROVED", "Accept")


def test_unknown_report(archive):
    db, _ = archive
    with pytest.raises(ValueError, match="Unknown report"):
        transition_report(db, 9999, "Alice", "IN_REVIEW", "Review")
