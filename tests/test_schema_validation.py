import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from opensteuerauszug.model.ech0196 import TaxStatement

import app.main as api


def test_real_schema_validation_accepts_output_and_rejects_invalid_canton(tmp_path):
    root = Path(__file__).resolve().parent.parent
    xml_output = tmp_path / "statement.xml"
    result = subprocess.run(
        [
            str(Path(sys.executable).parent / "opensteuerauszug"),
            "process",
            str(root / "tests/fixtures/ibkr_synthetic.xml"),
            "--importer",
            "ibkr",
            "--tax-calculation-level",
            "minimal",
            "--tax-year",
            "2025",
            "--kursliste-dir",
            str(root / "tests/fixtures/kursliste"),
            "--xml-output",
            str(xml_output),
            "-o",
            str(tmp_path / "statement.pdf"),
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "XSD validation successful." in result.stderr
    assert "Skipping validation" not in result.stderr

    statement = TaxStatement.from_xml_file(str(xml_output))
    # Assignment bypasses parsing constraints so the XSD must reject this value.
    statement.canton = "XX"
    with pytest.raises(ValueError, match="XSD validation failed"):
        statement.validate_model()


def test_api_rejects_missing_schemas(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "PROJECT_ROOT", tmp_path)
    response = TestClient(api.app).post(
        "/v1/statements",
        data={"tax_year": "2025"},
        files={"statement": ("statement.xml", b"<xml />", "application/xml")},
    )
    assert response.status_code == 503
    assert "schemas are missing" in response.json()["detail"]
