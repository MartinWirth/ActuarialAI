from io import BytesIO

from pypdf import PdfReader

from actuarial_ai import synthetic_triangle
from actuarial_ai.report_builder import (
    ReportOptions,
    configurable_portfolio_pdf,
    report_identity,
)


def sample():
    return {"Motor": synthetic_triangle(10, seed=1),
            "Property": synthetic_triangle(9, seed=2)}


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
    from actuarial_ai import synthetic_triangle

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
