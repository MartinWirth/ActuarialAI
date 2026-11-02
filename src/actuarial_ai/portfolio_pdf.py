"""PDF management report for illustrative multi-segment actuarial analysis."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from .portfolio import portfolio_report
from .portfolio_governance import governance_assessment
from .portfolio_risk import simulate_portfolio_risk


def portfolio_pdf_report(
    segments: dict,
    source: str = "portfolio_csv",
    simulations: int = 2000,
    confidence: float = 0.95,
    seed: int = 42,
) -> bytes:
    """Build a management summary; risk metrics are assumption-driven."""
    portfolio = portfolio_report(segments)
    risk = simulate_portfolio_risk(
        segments, simulations=simulations, confidence=confidence, seed=seed,
    )
    try:
        governance = governance_assessment(segments)
    except ValueError:
        governance = None

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=(595, 842), leftMargin=44, rightMargin=44,
        topMargin=44, bottomMargin=44,
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("ActuarialAI | Portfolio Management Report", styles["Title"]),
        Paragraph("Illustrative analysis - NOT for actuarial sign-off", styles["Heading3"]),
        Paragraph(f"Source: {escape(str(source))}", styles["Normal"]),
        Spacer(1, 16),
        Paragraph("Executive summary", styles["Heading2"]),
        Paragraph(
            f"Segments: {len(segments)}. Baseline outstanding reserve: "
            f"{portfolio['totals']['baseline_reserve']:,.2f}. "
            "Figures use deterministic Chain-Ladder reserving and an "
            "assumption-driven simulation.", styles["Normal"],
        ),
        Spacer(1, 12),
        Paragraph("Portfolio segment reserves", styles["Heading2"]),
    ]
    rows = [["Segment", "Latest paid", "Baseline reserve", "Reserve share"]]
    for _, row in portfolio["segments"].iterrows():
        rows.append([
            Paragraph(escape(str(row["segment"])), styles["Normal"]),
            f"{row['latest_paid']:,.0f}",
            f"{row['baseline_reserve']:,.0f}",
            f"{row['baseline_reserve_share']:.1%}",
        ])
    table = Table(rows, colWidths=[145, 116, 130, 106], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6EDF5")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([
        table, Spacer(1, 14),
        Paragraph("Illustrative portfolio risk", styles["Heading2"]),
        Paragraph(
            f"Simulations: {simulations:,}; confidence: {confidence:.0%}; "
            f"assumed volatility: {risk['volatility']:.0%}; "
            f"latent correlation: {risk['correlation']:.0%}.",
            styles["Normal"],
        ),
        Paragraph(
            f"Simulated mean: {risk['mean']:,.2f}; "
            f"VaR: {risk['var']:,.2f}; "
            f"Expected Shortfall: {risk['expected_shortfall']:,.2f}.",
            styles["Normal"],
        ),
        Spacer(1, 12),
        Paragraph("Model governance and historical validation", styles["Heading2"]),
    ])
    if governance is None:
        story.append(Paragraph(
            "Historical validation unavailable for this portfolio. "
            "Governance status: NOT ASSESSED.", styles["Normal"],
        ))
    else:
        story.append(Paragraph(
            f"Diagnostic status: {governance['status']}; "
            f"common valuation periods: {governance['common_valuations']}.",
            styles["Normal"],
        ))
        for check in governance["checks"]:
            story.append(Paragraph(
                f"{escape(check['check'])}: "
                f"{'PASS' if check['passed'] else 'REVIEW'} "
                f"(observed {check['observed']}, limit {check['threshold']})",
                styles["Normal"],
            ))
        for metric in governance["metrics"]:
            story.append(Paragraph(
                f"{escape(metric['model'])}: MAE {metric['mae']:,.2f}; "
                f"RMSE {metric['rmse']:,.2f}; bias {metric['bias']:,.2f}.",
                styles["Normal"],
            ))
    story.extend([
        Spacer(1, 14), Paragraph("Limitations", styles["Heading2"]),
        Paragraph(
            "Synthetic/illustrative model. Historical metrics measure one-step "
            "cumulative-paid forecasts, not ultimate reserve accuracy. "
            "Monte Carlo volatility and correlation are assumed, not calibrated. "
            "VaR and Expected Shortfall are not regulatory capital estimates. "
            "Diagnostic pass is not model approval. Independent actuarial "
            "review is required.", styles["Normal"],
        ),
    ])
    document.build(story)
    return buffer.getvalue()
