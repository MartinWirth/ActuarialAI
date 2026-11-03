import json

import pandas as pd
import pytest

from actuarial_ai import synthetic_triangle
from actuarial_ai.risk_dashboard import portfolio_risk_dashboard
from actuarial_ai.risk_limits import assess_risk_limits, risk_snapshot


def dashboard():
    segments = {
        "Motor": synthetic_triangle(8, seed=1),
        "Property": synthetic_triangle(9, seed=2),
    }
    names = sorted(segments)
    matrix = pd.DataFrame(
        [[1.0, 0.3], [0.3, 1.0]], index=names, columns=names,
    )
    return portfolio_risk_dashboard(segments, matrix)


def test_green_limits_and_snapshot():
    d = dashboard()
    result = assess_risk_limits(
        d, portfolio_warning=1e12, portfolio_critical=2e12,
        segment_share_warning=2.0, segment_share_critical=3.0,
        diversification_warning=0.0, diversification_critical=-0.1,
    )
    assert result["status"] == "green"
    snapshot = risk_snapshot(result, d, as_of="2026-11-03T00:00:00+00:00")
    assert snapshot["overall_status"] == "green"
    assert snapshot["as_of_utc"] == "2026-11-03T00:00:00+00:00"
    assert json.loads(json.dumps(snapshot))["checks"]


def test_yellow_and_red_portfolio():
    d = dashboard()
    se = d["metrics"]["total_se"]
    yellow = assess_risk_limits(
        d, portfolio_warning=se * 0.9, portfolio_critical=se * 1.1,
        segment_share_warning=2.0, segment_share_critical=3.0,
        diversification_warning=0.0, diversification_critical=-0.1,
    )
    assert yellow["status"] == "yellow"
    red = assess_risk_limits(
        d, portfolio_warning=se * 0.5, portfolio_critical=se * 0.9,
        segment_share_warning=2.0, segment_share_critical=3.0,
        diversification_warning=0.0, diversification_critical=-0.1,
    )
    assert red["status"] == "red"


def test_concentration_breach():
    d = dashboard()
    result = assess_risk_limits(
        d, portfolio_warning=1e12, portfolio_critical=2e12,
        segment_share_warning=0.0, segment_share_critical=0.01,
        diversification_warning=0.0, diversification_critical=-0.1,
    )
    assert result["status"] == "red"
    assert (result["checks"]["scope"] == "segment").sum() == 2


@pytest.mark.parametrize("warning,critical", [(2, 1), (1, 1), (-1, 2)])
def test_reject_invalid_portfolio_limits(warning, critical):
    with pytest.raises(ValueError, match="limits"):
        assess_risk_limits(
            dashboard(), portfolio_warning=warning, portfolio_critical=critical,
        )
