import json

import pandas as pd
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.data_io import load_triangle, triangle_csv, validate_triangle
from actuarial_ai.reporting import analysis_report, report_json


def test_csv_roundtrip():
    triangle = synthetic_triangle(8)
    restored = load_triangle(triangle_csv(triangle), "triangle.csv")
    pd.testing.assert_frame_equal(triangle, restored, check_dtype=False)


def test_invalid_future_cell_rejected():
    triangle = synthetic_triangle(6)
    triangle.iloc[-1, -1] = 100.0
    with pytest.raises(ValueError, match="Future cells"):
        validate_triangle(triangle)


def test_decreasing_claims_rejected():
    triangle = synthetic_triangle(6)
    triangle.iloc[0, 1] = 0
    with pytest.raises(ValueError, match="nondecreasing"):
        validate_triangle(triangle)


def test_non_numeric_claims_rejected():
    triangle = synthetic_triangle(6).astype(object)
    triangle.iloc[0, 0] = "not a number"
    with pytest.raises(ValueError, match="numeric"):
        validate_triangle(triangle)


def test_report_matches_chain_ladder():
    triangle = synthetic_triangle(8)
    report = analysis_report(triangle)
    decoded = json.loads(report_json(report))
    assert decoded["total_reserve"] == pytest.approx(report["total_reserve"])
    assert len(decoded["origin_summary"]) == len(triangle)


def test_unsupported_file_rejected():
    with pytest.raises(ValueError, match="Supported"):
        load_triangle(b"hello", "data.txt")


def test_excel_roundtrip():
    pytest.importorskip("openpyxl")
    from io import BytesIO

    triangle = synthetic_triangle(6)
    output = BytesIO()
    triangle.to_excel(output)
    restored = load_triangle(output.getvalue(), "triangle.xlsx")
    pd.testing.assert_frame_equal(triangle, restored, check_dtype=False)
