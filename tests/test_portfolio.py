import subprocess
import sys
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from opensteuerauszug.model.ech0196 import TaxStatement
from pypdf import PdfReader

from app.main import app

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests/fixtures"


def test_portfolio_amounts_and_minimal_mode_limitations(tmp_path, decode_barcode_xml):
    xml_output = tmp_path / "statement.xml"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.engine",
            "process",
            str(FIXTURES / "ibkr_portfolio_synthetic.xml"),
            "--importer",
            "ibkr",
            "--tax-calculation-level",
            "minimal",
            "--tax-year",
            "2025",
            "--config",
            str(tmp_path / "empty-config.toml"),
            "--kursliste-dir",
            str(FIXTURES / "kursliste_portfolio"),
            "--debug-dump",
            str(tmp_path / "debug"),
            "--xml-output",
            str(xml_output),
            "-o",
            str(tmp_path / "statement.pdf"),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "XSD validation successful." in result.stderr
    assert "Errors: 0" in result.stdout
    barcode_xml = decode_barcode_xml(PdfReader(tmp_path / "statement.pdf"))
    assert barcode_xml == xml_output.read_bytes()

    imported = TaxStatement.from_xml_file(str(tmp_path / "debug/portfolio_import.xml"))
    imported_security = imported.listOfSecurities.depot[0].security[0]
    assert [(p.amountCurrency, p.amount) for p in imported_security.payment] == [
        ("USD", Decimal(20)),
        ("USD", Decimal(-3)),
    ]

    statement = TaxStatement.from_xml_file(str(xml_output))
    assert statement.taxPeriod == 2025
    assert statement.canton == "ZH"
    accounts = {
        account.bankAccountCurrency: account
        for account in statement.listOfBankAccounts.bankAccount
    }
    assert set(accounts) == {"CHF", "USD"}
    assert accounts["CHF"].taxValue.value == Decimal(1000)
    usd = accounts["USD"]
    assert usd.taxValue.balance == Decimal(843)
    assert usd.taxValue.exchangeRate == Decimal("0.90")
    assert usd.taxValue.value == Decimal("758.70")
    assert len(usd.payment) == 1
    interest = usd.payment[0]
    assert interest.paymentDate == date(2025, 6, 16)
    assert interest.amountCurrency == "USD"
    assert interest.amount == Decimal(1)
    assert interest.exchangeRate == Decimal("0.92")
    assert interest.grossRevenueB == Decimal("0.92")

    securities = statement.listOfSecurities.depot[0].security
    assert len(securities) == 1
    security = securities[0]
    assert security.isin == "US0000000001"
    assert security.country == "US"
    assert security.currency == "USD"
    assert [(s.referenceDate, s.mutation, s.quantity) for s in security.stock] == [
        (date(2025, 1, 1), False, Decimal(5)),
        (date(2025, 3, 3), True, Decimal(10)),
        (date(2025, 8, 1), True, Decimal(-5)),
    ]
    assert security.taxValue.quantity == Decimal(10)
    assert security.taxValue.balance == Decimal(500)
    assert security.taxValue.exchangeRate == Decimal("0.90")
    assert security.taxValue.value == Decimal(450)
    # Broker valuation converted to CHF is explicitly not an official tax value.
    assert security.taxValue.undefined is True
    # Minimal mode deliberately clears calculated securities income in eCH XML.
    assert security.payment == []
    assert statement.listOfSecurities.totalGrossRevenueB == Decimal(0)
    assert statement.totalTaxValue == Decimal("2208.70")
    assert statement.totalGrossRevenueB == Decimal("0.92")


def test_api_portfolio_pdf_includes_holdings_and_broker_reconciliation(
    monkeypatch, decode_barcode_xml, tmp_path
):
    monkeypatch.setenv("KURSLISTE_DIR", str(FIXTURES / "kursliste_portfolio"))
    response = TestClient(app).post(
        "/v1/statements",
        data={"tax_year": "2025"},
        files={
            "statement": (
                "portfolio.xml",
                (FIXTURES / "ibkr_portfolio_synthetic.xml").read_bytes(),
                "application/xml",
            )
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "no-store"
    text = "\n".join(
        page.extract_text() for page in PdfReader(BytesIO(response.content)).pages
    )
    assert "Synthetic Company (ZZTEST)" in text
    assert "US0000000001" in text
    assert "758.70" in text
    assert "450.00" in text
    assert "20.00 USD" in text
    assert "3.00 USD" in text
    assert "Dieses Minimaldokument" in text
    barcode_path = tmp_path / "barcode.xml"
    barcode_path.write_bytes(decode_barcode_xml(PdfReader(BytesIO(response.content))))
    imported = TaxStatement.from_xml_file(str(barcode_path))
    assert imported.totalTaxValue == Decimal("2208.70")
    assert imported.listOfSecurities.depot[0].security[0].taxValue.quantity == Decimal(
        10
    )
