"""Configurable, versioned portfolio PDF reports with embedded charts."""
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .mack import mack_chain_ladder
from .mack_attribution import mack_risk_attribution
from .mack_matrix import aggregate_mack_matrix
from .mack_matrix_sensitivity import mack_matrix_sensitivity
from .mack_sensitivity import mack_correlation_sensitivity
from .portfolio import portfolio_report
from .portfolio_governance import governance_assessment
from .portfolio_mack import aggregate_mack
from .portfolio_risk import simulate_portfolio_risk
from .risk_dashboard import portfolio_risk_dashboard
from .risk_limits import assess_risk_limits
from .risk_trends import monitoring_trends, parse_monitoring_history


@dataclass(frozen=True)
class ReportOptions:
    include_segments: bool = True
    include_risk: bool = True
    include_governance: bool = True
    include_charts: bool = True
    include_mack: bool = False
    include_risk_dashboard: bool = False
    include_risk_limits: bool = False
    include_risk_trends: bool = False
    risk_history_jsonl: str = ""
    risk_limit_warning: float = 100000.0
    risk_limit_critical: float = 200000.0
    include_mack_attribution: bool = False
    include_mack_sensitivity: bool = False
    mack_correlation: float = 0.0
    mack_matrix: tuple[tuple[float, ...], ...] | None = None
    include_mack_matrix_sensitivity: bool = False
    mack_matrix_shock: float = 0.1
    simulations: int = 2000
    confidence: float = 0.95
    seed: int = 42


def report_identity(segments: dict, options: ReportOptions) -> str:
    """Stable SHA-256 for report input and configuration, not the PDF bytes."""
    from dataclasses import asdict

    canonical = {
        "options": asdict(options),
        "segments": {
            name: {
                "index": [str(x) for x in triangle.index],
                "columns": [str(x) for x in triangle.columns],
                "values": [[None if pd.isna(v) else float(v) for v in row]
                           for row in triangle.to_numpy(dtype=float)],
            }
            for name, triangle in sorted(segments.items())
        },
    }
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


def _reserve_chart(summary):
    values = summary["baseline_reserve"].tolist()
    labels = summary["segment"].astype(str).tolist()
    drawing = Drawing(490, 210)
    chart = VerticalBarChart()
    chart.x, chart.y = 52, 40
    chart.width, chart.height = 415, 135
    chart.data = [values]
    chart.categoryAxis.categoryNames = [
        label[:15] for label in labels
    ]
    chart.categoryAxis.labels.fontSize = 8
    chart.valueAxis.valueMin = 0
    chart.bars[0].fillColor = colors.HexColor("#2764A5")
    drawing.add(chart)
    drawing.add(String(55, 188, "Baseline reserve by segment", fontSize=11))
    return drawing


def configurable_portfolio_pdf(
    segments: dict,
    source: str = "portfolio_csv",
    options: ReportOptions | None = None,
) -> tuple[bytes, str]:
    """Create a report and deterministic version fingerprint."""
    options = options or ReportOptions()
    portfolio = portfolio_report(segments)
    identity = report_identity(segments, options)
    risk = None
    if options.include_risk:
        risk = simulate_portfolio_risk(
            segments, simulations=options.simulations,
            confidence=options.confidence, seed=options.seed,
        )
    governance = None
    if options.include_governance:
        try:
            governance = governance_assessment(segments)
        except ValueError:
            pass
    styles = getSampleStyleSheet()
    story = [
        Paragraph("ActuarialAI | Executive Portfolio Report", styles["Title"]),
        Paragraph("Illustrative - not for actuarial sign-off", styles["Heading3"]),
        Paragraph(f"Source: {escape(str(source))}", styles["Normal"]),
        Paragraph(
            f"Generated UTC: {datetime.now(timezone.utc).isoformat()}", styles["Normal"]
        ),
        Paragraph(f"Report version (SHA-256): {identity}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Executive dashboard", styles["Heading2"]),
        Paragraph(
            f"Segments: {len(segments)} | Baseline reserve: "
            f"{portfolio['totals']['baseline_reserve']:,.2f} | "
            f"Latest paid: {portfolio['totals']['latest_paid']:,.2f}",
            styles["Normal"],
        ),
    ]
    if options.include_segments:
        story.extend([Spacer(1, 10), Paragraph("Segment reserves", styles["Heading2"])])
        rows = [["Segment", "Latest paid", "Reserve", "Share"]]
        for _, row in portfolio["segments"].iterrows():
            rows.append([
                Paragraph(escape(str(row["segment"])), styles["Normal"]),
                f"{row['latest_paid']:,.0f}",
                f"{row['baseline_reserve']:,.0f}",
                f"{row['baseline_reserve_share']:.1%}",
            ])
        table = Table(rows, colWidths=[145, 120, 125, 100], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6EDF5")),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(table)
        if options.include_charts:
            story.append(_reserve_chart(portfolio["segments"]))
    if options.include_mack:
        story.extend([
            Spacer(1, 10),
            Paragraph("Mack Chain-Ladder prediction uncertainty", styles["Heading2"]),
            Paragraph(
                f"Nominal normal-approximation interval: {options.confidence:.0%}. "
                + ("Assumed pairwise correlation matrix. "
                   if options.mack_matrix is not None else
                   f"Assumed cross-segment correlation: {options.mack_correlation:.2f}. ") + 
                "Portfolio aggregation is assumption-driven.", styles["Normal"],
            ),
        ])
        mack_rows = [["Segment", "Reserve", "Mack S.E.", "Lower", "Upper"]]
        for name, triangle in sorted(segments.items()):
            try:
                estimate = mack_chain_ladder(triangle, confidence=options.confidence)
            except ValueError as exc:
                story.append(Paragraph(
                    f"{escape(str(name))}: Mack unavailable - {escape(str(exc))}",
                    styles["Normal"],
                ))
                continue
            mack_rows.append([
                Paragraph(escape(str(name)), styles["Normal"]),
                f"{estimate['total_reserve']:,.0f}",
                f"{estimate['total_se']:,.0f}",
                f"{estimate['total_lower']:,.0f}",
                f"{estimate['total_upper']:,.0f}",
            ])
        if len(mack_rows) > 1:
            mack_table = Table(
                mack_rows, colWidths=[140, 90, 90, 85, 85], repeatRows=1,
            )
            mack_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6EDF5")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(mack_table)
        try:
            if options.mack_matrix is None:
                aggregate = aggregate_mack(
                    segments, correlation=options.mack_correlation,
                    confidence=options.confidence,
                )
            else:
                names = sorted(segments)
                matrix = pd.DataFrame(options.mack_matrix, index=names, columns=names)
                aggregate = aggregate_mack_matrix(
                    segments, matrix, confidence=options.confidence,
                )
        except ValueError as exc:
            story.append(Paragraph(
                f"Portfolio Mack aggregation unavailable: {escape(str(exc))}",
                styles["Normal"],
            ))
        else:
            story.append(Paragraph(
                f"Portfolio reserve: {aggregate['total_reserve']:,.2f}; "
                f"aggregated Mack S.E.: {aggregate['total_se']:,.2f}; "
                f"interval: [{aggregate['lower']:,.2f}, "
                f"{aggregate['upper']:,.2f}]; "
                f"independent S.E.: {aggregate['independent_se']:,.2f}; "
                f"diversification versus sum of standalone S.E.: "
                f"{aggregate['diversification_benefit']:,.2f}.",
                styles["Normal"],
            ))
        if options.include_risk_trends:
            story.append(Spacer(1, 8))
            story.append(Paragraph(
                "Historical Mack risk trends", styles["Heading3"],
            ))
            try:
                records = parse_monitoring_history(options.risk_history_jsonl)
                if not records:
                    raise ValueError("Upload historical monitoring snapshots first")
                analysis = monitoring_trends(records)
            except (ValueError, TypeError) as exc:
                story.append(Paragraph(
                    f"Risk trend analysis unavailable: {escape(str(exc))}",
                    styles["Normal"],
                ))
            else:
                timeline = analysis["timeline"]
                first = timeline.iloc[0]
                last = timeline.iloc[-1]
                story.append(Paragraph(
                    f"Observations: {len(timeline)}; "
                    f"first Mack S.E.: {first['total_se']:,.0f}; "
                    f"latest Mack S.E.: {last['total_se']:,.0f}; "
                    f"growth warnings: {analysis['growth_warnings']}; "
                    f"recurring breach warnings: "
                    f"{analysis['repeated_breach_warnings']}.",
                    styles["Normal"],
                ))
                rows = [["As of (UTC)", "Status", "Mack S.E.", "Change"]]
                for _, item in timeline.tail(15).iterrows():
                    change = item["se_change"]
                    rows.append([
                        item["as_of_utc"].strftime("%Y-%m-%d %H:%M"),
                        str(item["status"]).upper(),
                        f"{item['total_se']:,.0f}",
                        f"{change:,.0f}" if pd.notna(change) else "-",
                    ])
                table = Table(rows, colWidths=[160, 85, 125, 120], repeatRows=1)
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6EDF5")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ]))
                story.append(table)
                story.append(Paragraph(
                    "History is supplied by the report user; no automatic "
                    "server-side persistence or scheduled monitoring. "
                    "Changes are per observation, not annualized.",
                    styles["Normal"],
                ))
        if options.include_risk_limits:
            story.append(Spacer(1, 8))
            story.append(Paragraph(
                "Mack risk limits and early warnings", styles["Heading3"],
            ))
            try:
                names = sorted(segments)
                if options.mack_matrix is None:
                    matrix = pd.DataFrame(
                        [[1.0 if a == b else options.mack_correlation
                          for b in names] for a in names],
                        index=names, columns=names,
                    )
                else:
                    matrix = pd.DataFrame(
                        options.mack_matrix, index=names, columns=names,
                    )
                dashboard = portfolio_risk_dashboard(
                    segments, matrix, confidence=options.confidence,
                )
                monitoring = assess_risk_limits(
                    dashboard,
                    portfolio_warning=options.risk_limit_warning,
                    portfolio_critical=options.risk_limit_critical,
                )
            except ValueError as exc:
                story.append(Paragraph(
                    f"Risk limits unavailable: {escape(str(exc))}",
                    styles["Normal"],
                ))
            else:
                story.append(Paragraph(
                    f"Overall diagnostic status: {monitoring['status'].upper()}",
                    styles["Normal"],
                ))
                rows = [["Scope", "Check", "Observed", "Warning", "Critical", "Status"]]
                for _, item in monitoring["checks"].iterrows():
                    rows.append([
                        str(item["scope"]),
                        Paragraph(escape(str(item["name"])), styles["Normal"]),
                        f"{item['value']:,.2f}",
                        f"{item['warning']:,.2f}",
                        f"{item['critical']:,.2f}",
                        str(item["status"]).upper(),
                    ])
                table = Table(
                    rows, colWidths=[65, 120, 80, 80, 80, 65], repeatRows=1,
                )
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6EDF5")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ]))
                story.append(table)
                story.append(Paragraph(
                    "Limits are user-defined diagnostics. Segment concentration "
                    "uses absolute Euler shares. No automated alert delivery.",
                    styles["Normal"],
                ))
        if options.include_risk_dashboard:
            story.append(Spacer(1, 8))
            story.append(Paragraph(
                "Consolidated Mack risk dashboard", styles["Heading3"],
            ))
            try:
                names = sorted(segments)
                if options.mack_matrix is None:
                    matrix = pd.DataFrame(
                        [[1.0 if a == b else options.mack_correlation
                          for b in names] for a in names],
                        index=names, columns=names,
                    )
                else:
                    matrix = pd.DataFrame(
                        options.mack_matrix, index=names, columns=names,
                    )
                dashboard = portfolio_risk_dashboard(
                    segments, matrix, confidence=options.confidence,
                )
            except ValueError as exc:
                story.append(Paragraph(
                    f"Risk dashboard unavailable: {escape(str(exc))}",
                    styles["Normal"],
                ))
            else:
                metrics = dashboard["metrics"]
                story.append(Paragraph(
                    f"Portfolio Mack S.E.: {metrics['total_se']:,.0f}; "
                    f"independent S.E.: {metrics['independent_se']:,.0f}; "
                    f"diversification: {metrics['diversification_benefit']:,.0f} "
                    f"({metrics['diversification_pct']:.1%}).",
                    styles["Normal"],
                ))
                rows = [["Rank", "Segment", "Euler S.E.", "S.E. share"]]
                for _, item in dashboard["ranking"].iterrows():
                    rows.append([
                        str(int(item["rank"])),
                        Paragraph(escape(str(item["segment"])), styles["Normal"]),
                        f"{item['euler_se_contribution']:,.0f}",
                        f"{item['se_share']:.1%}",
                    ])
                table = Table(rows, colWidths=[55, 185, 130, 120], repeatRows=1)
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6EDF5")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ]))
                story.append(table)
                story.append(Paragraph(
                    "Alternative common-correlation scenarios", styles["Heading3"],
                ))
                rows = [["Correlation", "Portfolio S.E.", "Diversification"]]
                for _, item in dashboard["scenarios"].iterrows():
                    rows.append([
                        f"{item['correlation']:.2f}",
                        f"{item['total_se']:,.0f}",
                        f"{item['diversification_benefit']:,.0f}",
                    ])
                table = Table(rows, colWidths=[130, 180, 180], repeatRows=1)
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6EDF5")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ]))
                story.append(table)
                story.append(Paragraph(
                    "Risk contributions and correlations are assumption-driven. "
                    "Scenarios use uniform pairwise correlations rather than "
                    "changes to the selected matrix. Not calibrated capital.",
                    styles["Normal"],
                ))
        if options.include_mack_attribution:
            story.append(Spacer(1, 8))
            story.append(Paragraph(
                "Mack portfolio risk attribution", styles["Heading3"],
            ))
            try:
                names = sorted(segments)
                if options.mack_matrix is None:
                    matrix = pd.DataFrame(
                        [[1.0 if a == b else options.mack_correlation
                          for b in names] for a in names],
                        index=names, columns=names,
                    )
                else:
                    matrix = pd.DataFrame(
                        options.mack_matrix, index=names, columns=names,
                    )
                attribution = mack_risk_attribution(
                    segments, matrix, confidence=options.confidence,
                )
            except ValueError as exc:
                story.append(Paragraph(
                    f"Attribution unavailable: {escape(str(exc))}",
                    styles["Normal"],
                ))
            else:
                rows = [[
                    "Segment", "Standalone S.E.", "Variance share", "Euler S.E.",
                ]]
                for _, item in attribution["segments"].iterrows():
                    rows.append([
                        Paragraph(escape(str(item["segment"])), styles["Normal"]),
                        f"{item['standalone_se']:,.0f}",
                        f"{item['se_share']:.1%}",
                        f"{item['euler_se_contribution']:,.0f}",
                    ])
                table = Table(rows, colWidths=[145, 125, 105, 115], repeatRows=1)
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6EDF5")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ]))
                story.append(table)
                story.append(Paragraph(
                    "Pairwise cross-variance contributions", styles["Heading3"],
                ))
                pair_rows = [["Pair", "Corr.", "Cross-variance", "Variance share"]]
                for _, item in attribution["pairs"].iterrows():
                    pair_rows.append([
                        Paragraph(
                            escape(f"{item['segment_a']} / {item['segment_b']}"),
                            styles["Normal"],
                        ),
                        f"{item['correlation']:.2f}",
                        f"{item['cross_variance']:,.0f}",
                        f"{item['share_of_variance']:.1%}",
                    ])
                if len(pair_rows) > 1:
                    table = Table(
                        pair_rows, colWidths=[175, 65, 130, 120],
                        repeatRows=1,
                    )
                    table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6EDF5")),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                    ]))
                    story.append(table)
                story.append(Paragraph(
                    "Euler contributions sum to portfolio Mack S.E.; "
                    "pairwise cross-variance contributions sum to covariance "
                    "effects only. Negative allocations are possible. "
                    "Correlations are user assumptions, not estimates.",
                    styles["Normal"],
                ))
        if options.include_mack_sensitivity:
            story.append(Spacer(1, 8))
            story.append(Paragraph(
                "Mack correlation sensitivity", styles["Heading3"],
            ))
            try:
                sensitivity = mack_correlation_sensitivity(
                    segments, confidence=options.confidence,
                )
            except ValueError as exc:
                story.append(Paragraph(
                    f"Sensitivity unavailable: {escape(str(exc))}",
                    styles["Normal"],
                ))
            else:
                sensitivity_rows = [[
                    "Corr.", "Portfolio S.E.", "Lower", "Upper", "Diversification",
                ]]
                for _, item in sensitivity.iterrows():
                    sensitivity_rows.append([
                        f"{item['correlation']:.2f}",
                        f"{item['total_se']:,.0f}",
                        f"{item['lower']:,.0f}",
                        f"{item['upper']:,.0f}",
                        f"{item['diversification_benefit']:,.0f}",
                    ])
                sensitivity_table = Table(
                    sensitivity_rows, colWidths=[65, 100, 100, 100, 125],
                    repeatRows=1,
                )
                sensitivity_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6EDF5")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ]))
                story.append(sensitivity_table)
                story.append(Paragraph(
                    "Illustrative scenarios: common pairwise correlations "
                    "0, 0.25, 0.50, 0.75, 1.00; not empirically calibrated.",
                    styles["Normal"],
                ))
        if options.mack_matrix is not None:
            story.append(Paragraph(
                "Pairwise correlation matrix (assumed, not calibrated)",
                styles["Heading3"],
            ))
            names = sorted(segments)
            rows = [["Segment", *names]]
            for name, values in zip(names, options.mack_matrix):
                rows.append([name, *(f"{v:.2f}" for v in values)])
            story.append(Table(rows, repeatRows=1))
        if options.include_mack_matrix_sensitivity:
            story.append(Spacer(1, 8))
            story.append(Paragraph(
                "Pairwise Mack matrix sensitivity", styles["Heading3"],
            ))
            if options.mack_matrix is None:
                story.append(Paragraph(
                    "Pairwise sensitivity unavailable: no correlation matrix supplied.",
                    styles["Normal"],
                ))
            else:
                try:
                    names = sorted(segments)
                    matrix = pd.DataFrame(
                        options.mack_matrix, index=names, columns=names,
                    )
                    step = options.mack_matrix_shock
                    scenarios = mack_matrix_sensitivity(
                        segments, matrix,
                        shocks=(-2 * step, -step, 0.0, step, 2 * step),
                        confidence=options.confidence,
                    )
                except ValueError as exc:
                    story.append(Paragraph(
                        f"Pairwise sensitivity unavailable: {escape(str(exc))}",
                        styles["Normal"],
                    ))
                else:
                    rows = [["Pair", "Shock", "Corr.", "PSD", "Mack S.E.", "Delta S.E."]]
                    for _, item in scenarios.iterrows():
                        rows.append([
                            Paragraph(
                                escape(f"{item['segment_a']} / {item['segment_b']}"),
                                styles["Normal"],
                            ),
                            f"{item['shock']:+.2f}",
                            f"{item['correlation']:.2f}",
                            "Yes" if item["valid_psd"] else "No",
                            f"{item['total_se']:,.0f}" if item["valid_psd"] else "N/A",
                            f"{item['delta_se']:+,.0f}" if item["valid_psd"] else "N/A",
                        ])
                    table = Table(
                        rows, colWidths=[130, 55, 55, 45, 100, 100],
                        repeatRows=1,
                    )
                    table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6EDF5")),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                    ]))
                    story.append(table)
                    story.append(Paragraph(
                        "Each scenario changes one symmetric pair; non-PSD "
                        "scenarios are reported as unavailable, not repaired.",
                        styles["Normal"],
                    ))
        story.append(Paragraph(
            "Assumptions: independent origin periods within each segment; "
            "conditional variance proportional to cumulative paid; final-age "
            "variance extrapolated; no tail factor. Normal intervals are "
            "illustrative, truncated at zero, and not calibrated. "
            "Cross-segment dependence is user-assumed, not estimated.",
            styles["Normal"],
        ))
    if risk is not None:
        story.extend([
            Spacer(1, 10), Paragraph("Illustrative portfolio risk", styles["Heading2"]),
            Paragraph(
                f"Simulations: {options.simulations}; confidence: "
                f"{options.confidence:.0%}; assumed volatility: "
                f"{risk['volatility']:.0%}; latent correlation: "
                f"{risk['correlation']:.0%}.",
                styles["Normal"],
            ),
            Paragraph(
                f"Mean: {risk['mean']:,.2f} | VaR: {risk['var']:,.2f} | "
                f"Expected Shortfall: {risk['expected_shortfall']:,.2f}",
                styles["Normal"],
            ),
        ])
    if options.include_governance:
        story.extend([
            Spacer(1, 10), Paragraph("Model governance", styles["Heading2"]),
        ])
        if governance is None:
            story.append(Paragraph("NOT ASSESSED: insufficient historical evidence.", styles["Normal"]))
        else:
            story.append(Paragraph(
                f"Diagnostic status: {governance['status']}; "
                f"common valuations: {governance['common_valuations']}.",
                styles["Normal"],
            ))
            for check in governance["checks"]:
                story.append(Paragraph(
                    f"{escape(check['check'])}: "
                    f"{'PASS' if check['passed'] else 'REVIEW'}",
                    styles["Normal"],
                ))
            for metric in governance["metrics"]:
                story.append(Paragraph(
                    f"{escape(metric['model'])}: MAE {metric['mae']:,.2f}; "
                    f"RMSE {metric['rmse']:,.2f}; bias {metric['bias']:,.2f}.",
                    styles["Normal"],
                ))
    story.extend([
        Spacer(1, 12), Paragraph("Limitations", styles["Heading2"]),
        Paragraph(
            "One-step paid-claims diagnostics do not validate ultimate reserves. "
            "Monte Carlo volatility and correlation are assumed, not calibrated. "
            "VaR/Expected Shortfall are not regulatory capital. Diagnostic status "
            "does not imply approval. Mack normal intervals are not calibrated "
            "and Mack cross-segment correlation is assumed, not calibrated. "
            "Independent actuarial review is required.",
            styles["Normal"],
        ),
    ])
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=(595, 842), leftMargin=44, rightMargin=44,
        topMargin=44, bottomMargin=44,
    )
    doc.build(story)
    return buffer.getvalue(), identity
