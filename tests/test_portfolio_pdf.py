from io import BytesIO

import pytest
from pypdf import PdfReader

from actuarial_ai import synthetic_triangle
from actuarial_ai.portfolio_pdf import portfolio_pdf_report


def test_pdf_contains_management_sections():
    segments = {
        "Motor": synthetic_triangle(10, seed=1),
        "Property": synthetic_triangle(9, seed=2),
    }
    result = portfolio_pdf_report(segments, source="sample.csv", simulations=100)
    assert result.startswith(b"%PDF")
    reader = PdfReader(BytesIO(result))
    content = "\n".join(page.extract_text() for page in reader.pages)
    assert "Executive summary" in content
    assert "Portfolio segment reserves" in content
    assert "Illustrative portfolio risk" in content
    assert "Model governance" in content
    assert "Motor" in content
    assert "Property" in content
    assert "sample.csv" in content
    assert "Limitations" in content


def test_invalid_simulations_rejected():
    with pytest.raises(ValueError):
        portfolio_pdf_report({"Motor": synthetic_triangle(10)}, simulations=99)
