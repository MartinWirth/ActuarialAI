import json

import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.reporting import report_json
from actuarial_ai.validation import validate_models, validation_report


def test_validation_compares_same_holdouts():
    result = validate_models(synthetic_triangle(10, seed=4))
    metrics = result["metrics"]
    assert metrics.loc["chain_ladder", "n"] == metrics.loc["random_forest", "n"]
    assert result["preferred_by_mae"] in {"chain_ladder", "random_forest"}
    assert result["alert_count"] == int(result["by_valuation"]["ml_alert"].sum())


def test_validation_report_is_reproducible_except_timestamp():
    triangle = synthetic_triangle(10, seed=4)
    first = validation_report(triangle)
    second = validation_report(triangle)
    first.pop("generated_at_utc")
    second.pop("generated_at_utc")
    assert first == second
    assert len(first["input_sha256"]) == 64
    assert json.loads(report_json(first)) == first


def test_fingerprint_changes_when_data_changes():
    triangle = synthetic_triangle(10, seed=4)
    modified = triangle.copy()
    modified.iat[0, 0] *= 1.01
    assert validation_report(triangle)["input_sha256"] != validation_report(
        modified
    )["input_sha256"]


@pytest.mark.parametrize("ratio", [0, -1, float("nan"), float("inf")])
def test_invalid_alert_ratio(ratio):
    with pytest.raises(ValueError):
        validate_models(synthetic_triangle(10), alert_ratio=ratio)
