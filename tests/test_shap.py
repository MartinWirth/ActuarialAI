import numpy as np
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.shap_explain import shap_factor_explanations


def test_shap_requires_positive_rows():
    with pytest.raises(ValueError):
        shap_factor_explanations(synthetic_triangle(8), max_rows=0)


def test_shap_explanations_add_up_and_are_reproducible():
    pytest.importorskip("shap")
    triangle = synthetic_triangle(8)
    a = shap_factor_explanations(triangle, max_rows=12)
    b = shap_factor_explanations(triangle, max_rows=12)
    assert len(a["details"]) == 12
    assert set(a["importance"]["feature"]) == {"development", "paid"}
    np.testing.assert_allclose(
        a["details"]["baseline"] + a["details"]["shap_development"]
        + a["details"]["shap_paid"], a["details"]["prediction"],
        rtol=1e-4, atol=1e-5,
    )
    np.testing.assert_allclose(
        a["importance"]["mean_absolute_shap"], b["importance"]["mean_absolute_shap"]
    )
