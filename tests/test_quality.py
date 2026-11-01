import numpy as np
import pandas as pd
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.quality import quality_csv, quality_report


def test_summary_counts_and_csv():
    triangle = synthetic_triangle(8)
    report = quality_report(triangle)
    assert report["summary"]["observed_cells"] == 36
    assert report["summary"]["missing_future_cells"] == 28
    assert report["summary"]["development_pairs"] == 28
    assert report["summary"]["flagged_pairs"] == len(report["flags"])
    assert b"robust_z" in quality_csv(report)


def test_outlier_detected_with_sufficient_peers():
    # Construct a valid cumulative triangle with a conspicuous age-1 outlier.
    full = synthetic_triangle(7)
    for i, factor in enumerate([1.50, 1.51, 1.49, 1.52, 1.50, 5.0]):
        full.iat[i, 1] = full.iat[i, 0] * factor
        # Keep all later observed cumulative values >= the edited age-1 value.
        for j in range(2, 7 - i):
            full.iat[i, j] = max(full.iat[i, j], full.iat[i, j - 1])
    report = quality_report(full)
    assert report["summary"]["flagged_pairs"] >= 1


def test_small_triangle_is_not_assessable():
    report = quality_report(synthetic_triangle(3))
    assert report["summary"]["assessable_pairs"] == 0
    assert report["summary"]["flagged_pairs"] == 0


def test_rejects_bad_parameters_and_invalid_triangle():
    triangle = synthetic_triangle(6)
    with pytest.raises(ValueError):
        quality_report(triangle, threshold=0)
    with pytest.raises(ValueError):
        quality_report(triangle, min_peers=2)
    triangle.iloc[0, 1] = np.nan
    with pytest.raises(ValueError):
        quality_report(triangle)


def test_reproducible():
    a = quality_report(synthetic_triangle(8))
    b = quality_report(synthetic_triangle(8))
    pd.testing.assert_frame_equal(a["diagnostics"], b["diagnostics"])
