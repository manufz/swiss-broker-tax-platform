from fastapi.testclient import TestClient

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