import pytest

from actuarial_ai.approval_workflow import (
    authenticated_transition,
    audit_events,
    report_status,
)
from actuarial_ai.auth import (
    create_user,
    identity,
    list_users,
    login,
    logout,
    require_permission,
)
from actuarial_ai.report_builder import ReportOptions
from actuarial_ai.report_history import save_report


@pytest.fixture
def setup_accounts(tmp_path):
    db = tmp_path / "auth.sqlite3"
    create_user(db, "admin", "very-long-admin-password", "ADMIN")
    admin = login(db, "admin", "very-long-admin-password")
    create_user(
        db, "actuary", "very-long-actuary-password", "ACTUARY",
        admin_token=admin,
    )
    create_user(
        db, "reviewer", "very-long-reviewer-password", "REVIEWER",
        admin_token=admin,
    )
    create_user(
        db, "auditor", "very-long-auditor-password", "AUDITOR",
        admin_token=admin,
    )
    report_id = save_report(
        db, version="v1", source="sample.csv", portfolio_csv=b"csv",
        pdf=b"%PDF-example", options=ReportOptions(), summary={},
    )
    return db, report_id, admin


def test_login_and_logout(setup_accounts):
    db, _, admin = setup_accounts
    assert identity(db, admin)["role"] == "ADMIN"
    assert len(list_users(db, admin)) == 4
    with pytest.raises(PermissionError):
        login(db, "admin", "incorrect-password")
    logout(db, admin)
    assert identity(db, admin) is None


def test_role_permissions(setup_accounts):
    db, _, admin = setup_accounts
    auditor = login(db, "auditor", "very-long-auditor-password")
    reviewer = login(db, "reviewer", "very-long-reviewer-password")
    assert require_permission(db, auditor, "read_reports")["role"] == "AUDITOR"
    assert require_permission(db, reviewer, "approve_reports")["role"] == "REVIEWER"
    with pytest.raises(PermissionError):
        require_permission(db, auditor, "save_reports")
    with pytest.raises(PermissionError):
        create_user(
            db, "unauthorized", "long-enough-password", "ADMIN",
            admin_token=auditor,
        )
    assert identity(db, admin) is not None


def test_review_separation_of_duties(setup_accounts):
    db, report_id, admin = setup_accounts
    actuary = login(db, "actuary", "very-long-actuary-password")
    reviewer = login(db, "reviewer", "very-long-reviewer-password")
    authenticated_transition(db, report_id, actuary, "IN_REVIEW", "Ready")
    with pytest.raises(PermissionError):
        authenticated_transition(db, report_id, admin, "APPROVED", "Approve")
    with pytest.raises(PermissionError):
        authenticated_transition(db, report_id, actuary, "APPROVED", "Approve")
    authenticated_transition(db, report_id, reviewer, "APPROVED", "Verified")
    assert report_status(db, report_id) == "APPROVED"
    assert [event["actor"] for event in audit_events(db, report_id)] == [
        "actuary", "reviewer",
    ]


def test_admin_cannot_approve_own_submission(setup_accounts):
    db, report_id, admin = setup_accounts
    authenticated_transition(db, report_id, admin, "IN_REVIEW", "Review")
    reviewer = login(db, "reviewer", "very-long-reviewer-password")
    authenticated_transition(db, report_id, reviewer, "REJECTED", "Fix")
    authenticated_transition(db, report_id, admin, "IN_REVIEW", "Updated")
    assert report_status(db, report_id) == "IN_REVIEW"


def test_bootstrap_validation(tmp_path):
    db = tmp_path / "new.sqlite3"
    with pytest.raises(PermissionError):
        create_user(db, "actuary", "long-enough-password", "ACTUARY")
    with pytest.raises(ValueError):
        create_user(db, "admin", "short", "ADMIN")
