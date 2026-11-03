"""Recalculate Mack risk directly from a portfolio CSV and explicit assumptions."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .portfolio_io import load_portfolio_csv
from .risk_dashboard import portfolio_risk_dashboard
from .risk_limits import assess_risk_limits, risk_snapshot


def calculate_monitoring_snapshot(
    portfolio_path: str | Path,
    *,
    correlation: float = 0.0,
    portfolio_warning: float = 100000.0,
    portfolio_critical: float = 200000.0,
    segment_share_warning: float = 0.4,
    segment_share_critical: float = 0.6,
    diversification_warning: float = 0.1,
    diversification_critical: float = 0.0,
) -> dict:
    """Create reproducible snapshot for unchanged CSV bytes and settings.

    Timestamp represents source-file modification time, not valuation date.
    """
    source = Path(portfolio_path)
    data = source.read_bytes()
    segments = load_portfolio_csv(data)
    names = sorted(segments)
    matrix = pd.DataFrame(
        [[1.0 if a == b else float(correlation) for b in names] for a in names],
        index=names, columns=names,
    )
    dashboard = portfolio_risk_dashboard(segments, matrix)
    assessment = assess_risk_limits(
        dashboard,
        portfolio_warning=portfolio_warning,
        portfolio_critical=portfolio_critical,
        segment_share_warning=segment_share_warning,
        segment_share_critical=segment_share_critical,
        diversification_warning=diversification_warning,
        diversification_critical=diversification_critical,
    )
    assumptions = {
        "correlation": correlation,
        "portfolio_warning": portfolio_warning,
        "portfolio_critical": portfolio_critical,
        "segment_share_warning": segment_share_warning,
        "segment_share_critical": segment_share_critical,
        "diversification_warning": diversification_warning,
        "diversification_critical": diversification_critical,
    }
    source_digest = hashlib.sha256(data).hexdigest()
    settings_digest = hashlib.sha256(
        json.dumps(assumptions, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()
    # Stable timestamp for unchanged data and configuration, avoiding
    # redundant monitoring runs on every polling cycle.
    as_of = datetime.fromtimestamp(
        source.stat().st_mtime, tz=timezone.utc
    ).isoformat()
    snapshot = risk_snapshot(assessment, dashboard, as_of=as_of)
    snapshot["source_sha256"] = source_digest
    snapshot["settings_sha256"] = settings_digest
    return snapshot
