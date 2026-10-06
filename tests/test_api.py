from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfReader
from pytest import MonkeyPatch

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rejects_non_xml_upload() -> None:
    response = client.post(
        "/v1/statements",
        data={"tax_year": "2025"},
        files={
            "statement": (
                "statement.txt",
                b"not xml",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400


def test_generates_pdf_from_synthetic_ibkr_statement(monkeypatch: MonkeyPatch) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    monkeypatch.setenv("KURSLISTE_DIR", str(fixtures / "kursliste"))

    response = client.post(
        "/v1/statements",
        data={"tax_year": "2025"},
        files={
            "statement": (
                "statement.xml",
                (fixtures / "ibkr_synthetic.xml").read_bytes(),
                "application/xml",
            )
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "no-store"
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="steuerauszug-2025.pdf"'
    )
    pdf = PdfReader(BytesIO(response.content))
    text = "\n".join(page.extract_text() for page in pdf.pages)
    assert "2025" in text
    assert "U0000000" in text
