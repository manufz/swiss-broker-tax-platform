from fastapi.testclient import TestClient

from app.main import app
from app.security import MAX_REQUEST_BYTES


def test_readiness_requires_configured_years_and_schemas(monkeypatch, tmp_path):
    monkeypatch.setenv("KURSLISTE_DIR", str(tmp_path))
    monkeypatch.setenv("SUPPORTED_TAX_YEARS", "2025,2024")
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 503
    for year in (2025, 2024):
        (tmp_path / f"kursliste_{year}.xml").write_text("synthetic nonempty marker")
    assert client.get("/ready").json() == {"status": "ready"}
    monkeypatch.setattr("app.main.PROJECT_ROOT", tmp_path)
    assert client.get("/ready").status_code == 503


def test_advertised_oversized_body_rejected_before_processing():
    response = TestClient(app).post(
        "/v1/statements",
        content=b"",
        headers={"Content-Length": str(MAX_REQUEST_BYTES + 1)},
    )
    assert response.status_code == 413


def test_chunked_multipart_body_limit(monkeypatch):
    def body():
        yield b'--test\r\nContent-Disposition: form-data; name="statement"; filename="synthetic.xml"\r\n\r\n'
        for _ in range(13):
            yield b" " * (1024 * 1024)
        yield b"\r\n--test--\r\n"

    monkeypatch.setattr("app.main.process_statement", lambda *args: None)
    response = TestClient(app).post(
        "/v1/statements",
        content=body(),
        headers={"Content-Type": "multipart/form-data; boundary=test"},
    )
    assert response.status_code == 413
