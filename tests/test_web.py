import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_workspace_is_served_with_local_assets_and_private_page_headers(monkeypatch):
    monkeypatch.delenv("SUPPORTED_TAX_YEARS", raising=False)
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["referrer-policy"] == "no-referrer"
    assert '<option value="2025">2025</option>' in response.text
    assert '<script src="/assets/app.js" defer></script>' in response.text
    assert "Securities income is not calculated" in response.text
    for asset in ("app.js", "app.css", "mark.svg"):
        assert client.get(f"/assets/{asset}").status_code == 200
    assert client.get("/assets/../main.py").status_code == 404


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("2024,2025,2024", ["2025", "2024"]),
        ("2024, <script>,2025,1999,2101,２０２５", ["2025", "2024"]),
        ("", []),
    ],
)
def test_tax_year_options_follow_supported_configuration(
    monkeypatch, configured, expected
):
    monkeypatch.setenv("SUPPORTED_TAX_YEARS", configured)
    response = client.get("/")
    assert re.findall(r'<option value="(\d+)">', response.text) == expected
    assert "<script>" not in response.text


def test_bundled_example_is_the_verified_fictional_fixture():
    fixture = Path(__file__).parent / "fixtures/ibkr_synthetic.xml"
    response = client.get("/assets/ibkr-synthetic-2025.xml")
    assert response.status_code == 200
    assert response.content == fixture.read_bytes()
    assert b"U0000000" in response.content


def test_existing_api_contract_still_available():
    assert client.get("/health").json() == {"status": "ok"}
    assert "/v1/statements" in client.get("/openapi.json").json()["paths"]
