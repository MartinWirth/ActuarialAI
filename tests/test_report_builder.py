from io import BytesIO
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

from actuarial_ai import synthetic_triangle
from actuarial_ai.report_builder import (
    ReportOptions,
    configurable_portfolio_pdf,
    report_identity,
)


def sample():
    triangle = pd.read_csv(Path(__file__).parent / "fixtures" / "raa_triangle.csv", index_col=0)
    triangle = triangle.cummax(axis=1)
    return {"Motor": triangle, "Property": triangle * 1.2}


def test_report_sections_chart_and_version():
    pdf, version = configurable_portfolio_pdf(
        sample(), "example.csv", ReportOptions(simulations=100),
    )
    assert pdf.startswith(b"%PDF")
    assert len(version) == 64
    text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
    for heading in ("Executive dashboard", "Segment reserves",
                    "Illustrative portfolio risk", "Model governance", "Limitations"):
        assert heading in text
    assert "example.csv" in text
    assert version in text


def test_configured_sections_can_be_omitted():
    pdf, _ = configurable_portfolio_pdf(
        sample(), options=ReportOptions(
            include_segments=False, include_risk=False,
            include_governance=False, include_charts=False,
        ),
    )
    text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
    assert "Executive dashboard" in text
    assert "Segment reserves" not in text
    assert "Illustrative portfolio risk" not in text
    assert "Model governance" not in text


def test_version_tracks_input_and_configuration():
    original = sample()
    identity = report_identity(original, ReportOptions())
    assert identity == report_identity(sample(), ReportOptions())
    assert identity != report_identity(sample(), ReportOptions(include_risk=False))
    modified = sample()
    modified["Motor"].iat[0, 0] *= 1.01
    assert identity != report_identity(modified, ReportOptions())


def test_optional_mack_section_in_pdf():
    pdf, version = configurable_portfolio_pdf(
        sample(), options=ReportOptions(
            include_mack=True, include_risk=False,
            include_governance=False, simulations=100,
        ),
    )
    text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
    assert "Mack Chain-Ladder prediction uncertainty" in text
    assert "Mack S.E." in text
    assert "Normal intervals are" in text
    assert "aggregated Mack S.E." in text
    assert version != report_identity(sample(), ReportOptions(
        include_mack=False, include_risk=False,
        include_governance=False, simulations=100,
    ))


def test_mack_section_reports_unavailable_segment():
    segments = {"Too short": synthetic_triangle(3), "Motor": synthetic_triangle(8)}
    pdf, _ = configurable_portfolio_pdf(
        segments, options=ReportOptions(
            include_mack=True, include_risk=False, include_governance=False,
        ),
    )
    text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
    assert "Too short: Mack unavailable" in text
    assert "Motor" in text


def test_mack_correlation_changes_report_identity_and_pdf():
    a = ReportOptions(
        include_mack=True, mack_correlation=0,
        include_risk=False, include_governance=False,
    )
    b = ReportOptions(
        include_mack=True, mack_correlation=0.75,
        include_risk=False, include_governance=False,
    )
    assert report_identity(sample(), a) != report_identity(sample(), b)
    pdf, _ = configurable_portfolio_pdf(sample(), options=b)
    text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
    assert "0.75" in text
    assert "aggregated Mack S.E." in text


def test_optional_mack_sensitivity_pdf_and_version():
    base = ReportOptions(
        include_mack=True, include_risk=False, include_governance=False,
    )
    enabled = ReportOptions(
        include_mack=True, include_mack_sensitivity=True,
        include_risk=False, include_governance=False,
    )
    assert report_identity(sample(), base) != report_identity(sample(), enabled)
    pdf, _ = configurable_portfolio_pdf(sample(), options=enabled)
    text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    assert "Mack correlation sensitivity" in text
    assert "Diversification" in text
    assert "0.75" in text


def test_pairwise_mack_matrix_pdf_and_identity():
    base = ReportOptions(
        include_mack=True, include_risk=False, include_governance=False,
    )
    custom = ReportOptions(
        include_mack=True, include_risk=False, include_governance=False,
        mack_matrix=((1.0, 0.4), (0.4, 1.0)),
    )
    assert report_identity(sample(), base) != report_identity(sample(), custom)
    pdf, _ = configurable_portfolio_pdf(sample(), options=custom)
    text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    assert "Pairwise correlation matrix" in text
    assert "aggregated Mack S.E." in text


def test_pairwise_mack_sensitivity_pdf_and_version():
    base = ReportOptions(
        include_mack=True, include_risk=False, include_governance=False,
        mack_matrix=((1.0, 0.3), (0.3, 1.0)),
    )
    enabled = ReportOptions(
        include_mack=True, include_risk=False, include_governance=False,
        mack_matrix=((1.0, 0.3), (0.3, 1.0)),
        include_mack_matrix_sensitivity=True,
    )
    assert report_identity(sample(), base) != report_identity(sample(), enabled)
    pdf, _ = configurable_portfolio_pdf(sample(), options=enabled)
    text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    assert "Pairwise Mack matrix sensitivity" in text
    assert "Delta S.E." in text


def test_mack_attribution_pdf_and_report_identity():
    base = ReportOptions(
        include_mack=True, include_risk=False, include_governance=False,
        mack_matrix=((1.0, 0.3), (0.3, 1.0)),
    )
    enabled = ReportOptions(
        include_mack=True, include_mack_attribution=True,
        include_risk=False, include_governance=False,
        mack_matrix=((1.0, 0.3), (0.3, 1.0)),
    )
    assert report_identity(sample(), base) != report_identity(sample(), enabled)
    pdf, _ = configurable_portfolio_pdf(sample(), options=enabled)
    text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    assert "Mack portfolio risk attribution" in text
    assert "Pairwise cross-variance contributions" in text
    assert "Euler S.E." in text


def test_consolidated_risk_dashboard_pdf_and_identity():
    base = ReportOptions(
        include_mack=True, include_risk=False, include_governance=False,
    )
    enabled = ReportOptions(
        include_mack=True, include_risk_dashboard=True,
        include_risk=False, include_governance=False,
    )
    assert report_identity(sample(), base) != report_identity(sample(), enabled)
    pdf, _ = configurable_portfolio_pdf(sample(), options=enabled)
    text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    assert "Consolidated Mack risk dashboard" in text
    assert "Alternative common-correlation scenarios" in text
    assert "Euler S.E." in text


def test_mack_risk_limits_pdf_and_report_identity():
    base = ReportOptions(
        include_mack=True, include_risk=False, include_governance=False,
    )
    enabled = ReportOptions(
        include_mack=True, include_risk_limits=True,
        risk_limit_warning=100000.0, risk_limit_critical=200000.0,
        include_risk=False, include_governance=False,
    )
    assert report_identity(sample(), base) != report_identity(sample(), enabled)
    pdf, _ = configurable_portfolio_pdf(sample(), options=enabled)
    text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    assert "Mack risk limits and early warnings" in text
    assert "Overall diagnostic status" in text
