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
from .portfolio import portfolio_report
from .portfolio_governance import governance_assessment
from .portfolio_mack import aggregate_mack
from .portfolio_risk import simulate_portfolio_risk


@dataclass(frozen=True)
class ReportOptions:
    include_segments: bool = True
    include_risk: bool = True
    include_governance: bool = True
    include_charts: bool = True
    include_mack: bool = False
    mack_correlation: float = 0.0
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
                f"Assumed cross-segment correlation: {options.mack_correlation:.2f}. "
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
            aggregate = aggregate_mack(
                segments, correlation=options.mack_correlation,
                confidence=options.confidence,
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
