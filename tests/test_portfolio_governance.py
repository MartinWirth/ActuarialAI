import json

import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.portfolio_governance import governance_assessment, governance_audit_report
from actuarial_ai.reporting import report_json


def segments():
    return {"Motor": synthetic_triangle(10, seed=1),
            "Property": synthetic_triangle(9, seed=2)}


def test_diagnostic_checks_and_status():
    result = governance_assessment(segments())
    assert len(result["checks"]) == 3
    assert result["status"] in {"DIAGNOSTIC_PASS", "REVIEW_REQUIRED"}
    assert result["status"] == (
        "DIAGNOSTIC_PASS" if all(c["passed"] for c in result["checks"])
        else "REVIEW_REQUIRED"
    )


def test_strict_threshold_forces_review():
    result = governance_assessment(segments(), min_valuations=100)
    assert result["status"] == "REVIEW_REQUIRED"
    assert not result["checks"][0]["passed"]


def test_report_is_reproducible_except_timestamp_and_serializable():
    first = governance_audit_report(segments())
    second = governance_audit_report(segments())
    first.pop("generated_at_utc")
    second.pop("generated_at_utc")
    assert first == second
    assert len(first["input_sha256"]) == 64
    assert json.loads(report_json(first)) == first
    assert first["human_approval"] == "NOT_PERFORMED"


def test_fingerprint_changes_with_input():
    modified = segments()
    modified["Motor"].iat[0, 0] *= 1.01
    assert governance_audit_report(segments())["input_sha256"] != (
        governance_audit_report(modified)["input_sha256"]
    )


@pytest.mark.parametrize("kwargs", [
    {"min_valuations": 0}, {"min_valuations": True},
    {"max_mae_ratio": 0}, {"max_mae_ratio": float("nan")},
    {"max_underprediction_rate": -0.1},
    {"max_underprediction_rate": 1.1},
])
def test_invalid_thresholds(kwargs):
    with pytest.raises(ValueError):
        governance_assessment(segments(), **kwargs)
