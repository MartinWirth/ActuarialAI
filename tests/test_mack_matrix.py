import numpy as np
import pandas as pd
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.mack_matrix import aggregate_mack_matrix, validate_correlation_matrix
from actuarial_ai.portfolio_mack import aggregate_mack


def sample():
    return {"Motor": synthetic_triangle(8, seed=1),
            "Property": synthetic_triangle(9, seed=2)}


def matrix(rho):
    return pd.DataFrame([[1.0, rho], [rho, 1.0]],
                        index=["Motor", "Property"], columns=["Motor", "Property"])


@pytest.mark.parametrize("rho", [0.0, 0.3, 1.0, -1.0])
def test_matrix_matches_equicorrelation(rho):
    actual = aggregate_mack_matrix(sample(), matrix(rho))
    expected = aggregate_mack(sample(), correlation=rho)
    assert actual["total_se"] == pytest.approx(expected["total_se"])
    assert actual["total_mse"] == pytest.approx(expected["total_mse"])


def test_reorders_labels():
    reversed_matrix = matrix(0.4).loc[["Property", "Motor"], ["Property", "Motor"]]
    assert np.allclose(validate_correlation_matrix(reversed_matrix, sorted(sample())),
                       matrix(0.4).to_numpy())


@pytest.mark.parametrize("values", [
    [[1, 0.2], [0.3, 1]],
    [[1, 1.2], [1.2, 1]],
    [[0.9, 0], [0, 1]],
    [[1, float("nan")], [float("nan"), 1]],
])
def test_rejects_invalid_matrix(values):
    with pytest.raises(ValueError):
        validate_correlation_matrix(pd.DataFrame(values, index=["Motor", "Property"],
                                                  columns=["Motor", "Property"]),
                                    sorted(sample()))


def test_rejects_non_psd_three_segment_matrix():
    names = ["A", "B", "C"]
    values = [[1, 0.9, 0.9], [0.9, 1, -0.9], [0.9, -0.9, 1]]
    with pytest.raises(ValueError, match="positive semidefinite"):
        validate_correlation_matrix(pd.DataFrame(values, index=names, columns=names),
                                    names)


def test_rejects_missing_segment():
    with pytest.raises(ValueError, match="labels"):
        validate_correlation_matrix(matrix(0), ["Motor", "Property", "Third"])
