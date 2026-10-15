"""Synthetic-only localhost HTTP checks; works with the standard library."""

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def request(base, path, body=None, headers=None):
    try:
        response = urlopen(Request(base + path, body, headers or {}), timeout=150)
    except HTTPError as error:
        response = error
    with response:
        return response.status, dict(response.headers), response.read()


def upload(base, xml, year):
    boundary = "synthetic-check"
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="tax_year"\r\n\r\n{year}\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="statement"; filename="synthetic.xml"\r\n'
            "Content-Type: application/xml\r\n\r\n"
        ).encode()
        + xml
        + f"\r\n--{boundary}--\r\n".encode()
    )
    return request(
        base,
        "/v1/statements",
        body,
        {"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--output", type=Path, help="Optional synthetic basic PDF output"
    )
    args = parser.parse_args()
    assert args.base_url.startswith(("http://127.0.0.1:", "http://localhost:")), (
        "Use localhost; Entra is tested separately."
    )
    for path in ("/health", "/ready"):
        status, _, body = request(args.base_url, path)
        assert status == 200, (path, status)
        print(path, json.loads(body))
    status, headers, page = request(args.base_url, "/")
    assert status == 200
    assert b"Start with your report" in page
    assert headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    for asset in ("app.css", "app.js", "mark.svg", "ibkr-synthetic-2025.xml"):
        status, _, content = request(args.base_url, f"/assets/{asset}")
        assert status == 200 and content, asset
    print("Browser workspace and bundled assets PASS")
    xml = Path("tests/fixtures/ibkr_synthetic.xml").read_bytes()
    assert upload(args.base_url, b"<broken", 2025)[0] == 400
    assert upload(args.base_url, xml, 2024)[0] == 422
    status, headers, pdf = upload(args.base_url, xml, 2025)
    assert status == 200, status
    assert pdf.startswith(b"%PDF-")
    assert headers["content-type"] == "application/pdf"
    assert headers["cache-control"] == "no-store"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(pdf)
    print("Synthetic PDF, invalid XML and wrong-year checks PASS")


if __name__ == "__main__":
    main()
