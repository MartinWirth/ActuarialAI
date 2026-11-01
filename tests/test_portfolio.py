import pandas as pd
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.portfolio import portfolio_report, portfolio_scenarios
from actuarial_ai.portfolio_io import load_portfolio_csv


def sample_segments():
    return {"Motor": synthetic_triangle(6, seed=1),
            "Property": synthetic_triangle(7, seed=2)}


def test_portfolio_totals_equal_segment_sums():
    report = portfolio_report(sample_segments())
    table = report["segments"]
    assert report["totals"]["baseline_reserve"] == pytest.approx(
        table["baseline_reserve"].sum()
    )
    assert report["totals"]["reserve_delta"] == pytest.approx(0)
    assert table["baseline_reserve_share"].sum() == pytest.approx(1)


def test_portfolio_stress_increases_reserves():
    segments = sample_segments()
    stressed = portfolio_report(segments, inflation=0.05, factor_stress=0.1)
    base = portfolio_report(segments)
    assert stressed["totals"]["stressed_reserve"] > base["totals"]["baseline_reserve"]
    cases = portfolio_scenarios(segments)
    assert cases["stressed_reserve"].is_monotonic_increasing


def test_empty_portfolio_rejected():
    with pytest.raises(ValueError):
        portfolio_report({})


def test_portfolio_csv_roundtrip():
    records = []
    for name, triangle in sample_segments().items():
        for origin, row in triangle.iterrows():
            for development, value in row.items():
                if pd.notna(value):
                    records.append({"segment": name, "origin": origin,
                                    "development": development,
                                    "cumulative_paid": value})
    data = pd.DataFrame(records).to_csv(index=False).encode()
    loaded = load_portfolio_csv(data)
    assert set(loaded) == {"Motor", "Property"}
    for name, triangle in sample_segments().items():
        pd.testing.assert_frame_equal(loaded[name], triangle, check_dtype=False,
                                      check_names=False)


def test_duplicate_portfolio_records_rejected():
    data = b"segment,origin,development,cumulative_paid\nA,AY1,D1,100\nA,AY1,D1,100\n"
    with pytest.raises(ValueError, match="Duplicate"):
        load_portfolio_csv(data)
