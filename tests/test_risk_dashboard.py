import numpy as np
import pandas as pd
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.mack_matrix import aggregate_mack_matrix
from actuarial_ai.risk_dashboard import portfolio_risk_dashboard


def sample():
    return {
        "Motor": synthetic_triangle(8, seed=1),
        "Property": synthetic_triangle(9, seed=2),
    }


def matrix(rho=0.3):
    return pd.DataFrame(
        [[1.0, rho], [rho, 1.0]],
        index=["Motor", "Property"], columns=["Motor", "Property"],
    )


def test_dashboard_reconciles_with_mack_aggregation():
    dashboard = portfolio_risk_dashboard(sample(), matrix())
    aggregate = aggregate_mack_matrix(sample(), matrix())
    assert dashboard["metrics"]["total_se"] == pytest.approx(aggregate["total_se"])
    assert dashboard["metrics"]["diversification_benefit"] == pytest.approx(
        aggregate["diversification_benefit"],
    )
    assert dashboard["ranking"]["euler_se_contribution"].sum() == pytest.approx(
        aggregate["total_se"],
    )
    assert dashboard["ranking"]["rank"].tolist() == [1, 2]
    assert dashboard["ranking"]["euler_se_contribution"].is_monotonic_decreasing


def test_scenarios_reconcile_with_independent_and_fully_correlated():
    dashboard = portfolio_risk_dashboard(sample(), matrix())
    scenarios = dashboard["scenarios"]
    assert scenarios["total_se"].is_monotonic_increasing
    assert scenarios.iloc[0]["total_se"] == pytest.approx(
        dashboard["metrics"]["independent_se"],
    )
    assert scenarios.iloc[-1]["total_se"] == pytest.approx(
        dashboard["metrics"]["sum_standalone_se"],
    )


def test_custom_matrix_scenarios_are_alternatives():
    dashboard = portfolio_risk_dashboard(sample(), matrix(-0.5))
    assert dashboard["metrics"]["total_se"] < dashboard["metrics"]["independent_se"]
    assert dashboard["scenarios"].iloc[0]["total_se"] == pytest.approx(
        dashboard["metrics"]["independent_se"],
    )


@pytest.mark.parametrize("scenarios", [(), (float("nan"),), (1.1,)])
def test_invalid_scenarios(scenarios):
    with pytest.raises(ValueError):
        portfolio_risk_dashboard(sample(), matrix(), scenario_correlations=scenarios)


def test_three_segment_dashboard():
    segments = {**sample(), "Liability": synthetic_triangle(8, seed=1) * 1.3}
    names = sorted(segments)
    correlation = pd.DataFrame(np.eye(3), index=names, columns=names)
    dashboard = portfolio_risk_dashboard(segments, correlation)
    assert len(dashboard["ranking"]) == 3
    assert len(dashboard["pairs"]) == 3
