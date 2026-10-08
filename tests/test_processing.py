import asyncio
import copy
import logging
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pypdf import PdfReader

import app.main as api
from app import processing

FIXTURES = Path(__file__).parent / "fixtures"
SYNTHETIC = (FIXTURES / "ibkr_synthetic.xml").read_bytes()
PORTFOLIO = (FIXTURES / "ibkr_portfolio_synthetic.xml").read_bytes()


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("KURSLISTE_DIR", str(FIXTURES / "kursliste_portfolio"))
    monkeypatch.setattr(processing.tempfile, "tempdir", str(tmp_path))
    with TestClient(api.app) as client:
        yield client
    assert list(tmp_path.glob("tax-statement-*")) == []


def upload(client, contents=SYNTHETIC, year="2025"):
    return client.post(
        "/v1/statements",
        data={"tax_year": year},
        files={"statement": ("private-account.xml", contents, "application/xml")},
    )


@pytest.mark.parametrize("contents", [b"", b"not xml", b"<FlexQueryResponse>"])
def test_malformed_xml_is_rejected_before_engine(client, monkeypatch, contents):
    monkeypatch.setattr(
        processing.subprocess, "run", lambda *a, **kw: pytest.fail("Engine started")
    )
    assert upload(client, contents).status_code == 400


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_dtd_and_external_entities_are_rejected(
    client, monkeypatch, tmp_path, encoding
):
    secret = tmp_path / "private.txt"
    secret.write_text("PRIVATE_SENTINEL")
    xml = f'<?xml version="1.0" encoding="{encoding}"?><!DOCTYPE FlexQueryResponse [<!ENTITY x SYSTEM "{secret.as_uri()}">]><FlexQueryResponse>&x;</FlexQueryResponse>'
    monkeypatch.setattr(
        processing.subprocess, "run", lambda *a, **kw: pytest.fail("Engine started")
    )
    response = upload(client, xml.encode(encoding))
    assert response.status_code == 400
    assert "PRIVATE_SENTINEL" not in response.text


@pytest.mark.parametrize("year", ["1999", "2101", "not-a-year"])
def test_invalid_year_is_rejected(client, year):
    assert upload(client, year=year).status_code == 422


@pytest.mark.parametrize(
    "change",
    [
        "missing-canton",
        "invalid-canton",
        "missing-account",
        "missing-date",
        "invalid-date",
        "reversed-dates",
        "wrong-year",
        "empty-account",
        "duplicate-account",
        "different-cantons",
    ],
)
def test_invalid_report_fields_are_rejected_before_engine(client, monkeypatch, change):
    root = ElementTree.fromstring(SYNTHETIC)
    statements = root.find("FlexStatements")
    statement = statements.find("FlexStatement")
    account = statement.find("AccountInformation")
    if change == "missing-canton":
        del account.attrib["stateResidentialAddress"]
    elif change == "invalid-canton":
        account.set("stateResidentialAddress", "XX")
    elif change == "missing-account":
        del statement.attrib["accountId"]
    elif change == "missing-date":
        del statement.attrib["fromDate"]
    elif change == "invalid-date":
        statement.set("fromDate", "20250230")
    elif change == "reversed-dates":
        statement.set("fromDate", "20251231")
        statement.set("toDate", "20250101")
    elif change == "wrong-year":
        statement.set("fromDate", "20240101")
    elif change == "empty-account":
        statement.remove(statement.find("CashReport"))
    elif change == "duplicate-account":
        statements.append(copy.deepcopy(statement))
    elif change == "different-cantons":
        other = copy.deepcopy(statement)
        other.set("accountId", "U0000001")
        other.find("AccountInformation").set("stateResidentialAddress", "GE")
        statements.append(other)
    monkeypatch.setattr(
        processing.subprocess, "run", lambda *a, **kw: pytest.fail("Engine started")
    )
    assert upload(client, ElementTree.tostring(root)).status_code == 422


@pytest.mark.parametrize(
    "contents",
    [b"<xml />", b"<FlexQueryResponse><FlexStatements /></FlexQueryResponse>"],
)
def test_other_xml_and_empty_reports_are_rejected(client, contents):
    assert upload(client, contents).status_code == 422


def test_exact_upload_limit_is_accepted_but_one_extra_byte_is_rejected(client):
    # Whitespace after the root is legal XML and exercises the actual upload read.
    contents = SYNTHETIC + b" " * (api.MAX_UPLOAD_SIZE - len(SYNTHETIC))
    assert upload(client, contents).status_code == 200
    assert upload(client, contents + b" ").status_code == 413


@pytest.mark.parametrize("missing", ["directory", "year", "empty-file"])
def test_missing_reference_data_is_service_unavailable(
    client, monkeypatch, tmp_path, missing
):
    directory = tmp_path / "reference"
    if missing != "directory":
        directory.mkdir()
        filename = "kursliste_2024.xml" if missing == "year" else "kursliste_2025.xml"
        (directory / filename).write_bytes(b"")
    monkeypatch.setenv("KURSLISTE_DIR", str(directory))
    assert upload(client).status_code == 503


def test_missing_required_trade_field_fails_without_leaking_cli_output(client, caplog):
    root = ElementTree.fromstring(PORTFOLIO)
    del root.find("./FlexStatements/FlexStatement/Trades/Trade").attrib["conid"]
    with caplog.at_level(logging.INFO):
        response = upload(client, ElementTree.tostring(root))
    assert response.status_code == 422
    assert "status=422" in caplog.text
    for private in ("U0000000", "Example Person", "ZZTEST", "private-account.xml"):
        assert private not in response.text
        assert private not in caplog.text


def test_missing_exchange_rate_fails_instead_of_returning_incomplete_pdf(
    client, monkeypatch
):
    monkeypatch.setenv("KURSLISTE_DIR", str(FIXTURES / "kursliste"))
    assert upload(client, PORTFOLIO).status_code == 422


def test_interim_report_cannot_be_used_as_a_year_end_report(client):
    root = ElementTree.fromstring(SYNTHETIC)
    root.find("./FlexStatements/FlexStatement").set("toDate", "20250630")
    assert upload(client, ElementTree.tostring(root)).status_code == 422


@pytest.mark.parametrize(
    "change", ["stale-position", "unsupported-asset", "mixed-account"]
)
def test_report_cannot_silently_drop_or_mislabel_holdings(client, monkeypatch, change):
    root = ElementTree.fromstring(PORTFOLIO)
    position = root.find("./FlexStatements/FlexStatement/OpenPositions/OpenPosition")
    if change == "stale-position":
        position.set("reportDate", "20250630")
    elif change == "unsupported-asset":
        position.set("assetCategory", "CRYPTO")
    else:
        position.set("accountId", "U0000001")
    monkeypatch.setattr(
        processing.subprocess, "run", lambda *a, **kw: pytest.fail("Engine started")
    )
    assert upload(client, ElementTree.tostring(root)).status_code == 422


def test_multiple_accounts_keep_separate_balances(client, decode_barcode_xml):
    root = ElementTree.fromstring(SYNTHETIC)
    statements = root.find("FlexStatements")
    other = copy.deepcopy(statements.find("FlexStatement"))
    for node in other.iter():
        if "accountId" in node.attrib:
            node.set("accountId", "U0000001")
    cash = other.find("CashReport/CashReportCurrency")
    cash.set("startingCash", "500")
    cash.set("endingCash", "500")
    statements.append(other)
    statements.set("count", "2")
    response = upload(client, ElementTree.tostring(root))
    assert response.status_code == 200
    output = ElementTree.fromstring(
        decode_barcode_xml(PdfReader(BytesIO(response.content)))
    )
    accounts = output.findall("./{*}listOfBankAccounts/{*}bankAccount")
    assert {
        a.get("bankAccountNumber"): Decimal(a.find("{*}taxValue").get("value"))
        for a in accounts
    } == {
        "U0000000-CHF": Decimal(1000),
        "U0000001-CHF": Decimal(500),
    }
    assert Decimal(output.get("totalTaxValue")) == Decimal(1500)


def test_multiple_securities_keep_separate_holdings(client, decode_barcode_xml):
    root = ElementTree.fromstring(PORTFOLIO)
    positions = root.find("./FlexStatements/FlexStatement/OpenPositions")
    other = copy.deepcopy(positions.find("OpenPosition"))
    other.attrib.update(
        conid="999000002",
        symbol="ZZOTHER",
        description="Synthetic Other",
        isin="US0000000002",
        position="4",
        markPrice="25",
        positionValue="100",
    )
    positions.append(other)
    response = upload(client, ElementTree.tostring(root))
    assert response.status_code == 200
    output = ElementTree.fromstring(
        decode_barcode_xml(PdfReader(BytesIO(response.content)))
    )
    securities = output.findall("./{*}listOfSecurities/{*}depot/{*}security")
    assert {
        s.get("isin"): Decimal(s.find("{*}taxValue").get("quantity"))
        for s in securities
    } == {
        "US0000000001": Decimal(10),
        "US0000000002": Decimal(4),
    }
    assert Decimal(output.get("totalTaxValue")) == Decimal("2298.70")


def test_holding_bought_during_year_has_no_invented_opening_shares(
    client, decode_barcode_xml
):
    root = ElementTree.fromstring(PORTFOLIO)
    statement = root.find("./FlexStatements/FlexStatement")
    trades = statement.find("Trades")
    trades.remove(trades.findall("Trade")[1])
    statement.find("CashReport/CashReportCurrency[@currency='USD']").set(
        "endingCash", "618"
    )
    response = upload(client, ElementTree.tostring(root))
    assert response.status_code == 200
    output = ElementTree.fromstring(
        decode_barcode_xml(PdfReader(BytesIO(response.content)))
    )
    security = output.find("./{*}listOfSecurities/{*}depot/{*}security")
    opening = security.find("{*}stock[@referenceDate='2025-01-01']")
    assert opening is None or Decimal(opening.get("quantity")) == 0
    assert Decimal(security.find("{*}taxValue").get("quantity")) == 10
    assert Decimal(output.get("totalTaxValue")) == Decimal("2006.20")


@pytest.mark.parametrize(
    "failure, expected",
    [("exit", 422), ("no-output", 500), ("invalid-output", 500), ("os-error", 503)],
)
def test_engine_failure_cleans_files_releases_capacity_and_keeps_logs_private(
    client, monkeypatch, caplog, failure, expected
):
    paths = []

    def failed_engine(command, **kwargs):
        input_path = Path(command[command.index("process") + 1])
        paths.append(input_path.parent)
        assert input_path.exists()
        assert input_path.parent.stat().st_mode & 0o777 == 0o700
        if failure == "os-error":
            raise OSError("PRIVATE_ENGINE_ERROR")
        if failure == "invalid-output":
            Path(command[command.index("-o") + 1]).write_bytes(b"PRIVATE_ENGINE_ERROR")
        return subprocess.CompletedProcess(
            command,
            1 if failure == "exit" else 0,
            b"PRIVATE_ENGINE_OUTPUT",
            b"PRIVATE_ENGINE_ERROR",
        )

    monkeypatch.setattr(processing.subprocess, "run", failed_engine)
    with caplog.at_level(logging.INFO):
        assert upload(client).status_code == expected
        # A second job must reach the engine, rather than leak a busy slot.
        response = upload(client)
    assert response.status_code == expected
    assert len(paths) == 2
    assert all(not path.exists() for path in paths)
    assert "PRIVATE_ENGINE" not in caplog.text + response.text
    assert "private-account.xml" not in caplog.text


def test_real_process_timeout_kills_child_and_removes_partial_output(
    client, monkeypatch, tmp_path
):
    real_run = subprocess.run
    pid_file = tmp_path / "pid"
    paths = []

    def stalled_engine(command, **kwargs):
        paths.append(Path(command[command.index("-o") + 1]).parent)
        Path(command[command.index("-o") + 1]).write_bytes(b"%PDF-partial")
        script = "import os, pathlib, sys, time; pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)"
        return real_run([sys.executable, "-c", script, str(pid_file)], **kwargs)

    monkeypatch.setattr(processing, "PROCESS_TIMEOUT_SECONDS", 1)
    monkeypatch.setattr(processing.subprocess, "run", stalled_engine)
    assert upload(client).status_code == 504
    with pytest.raises(ProcessLookupError):
        os.kill(int(pid_file.read_text()), 0)
    assert all(not path.exists() for path in paths)
    assert processing.PROCESSING_SLOTS.acquire(blocking=False)
    processing.PROCESSING_SLOTS.release()


def test_concurrent_upload_is_rejected_while_health_remains_available(
    client, monkeypatch
):
    entered = threading.Event()
    release = threading.Event()

    def slow_engine(command, **kwargs):
        entered.set()
        assert release.wait(5)
        Path(command[command.index("-o") + 1]).write_bytes(b"%PDF-test")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(processing.subprocess, "run", slow_engine)
    with ThreadPoolExecutor(max_workers=1) as executor:
        first = executor.submit(upload, client)
        try:
            assert entered.wait(5)
            second = upload(client)
            assert second.status_code == 503
            assert second.headers["retry-after"] == "5"
            assert client.get("/health").status_code == 200
        finally:
            release.set()
        assert first.result(timeout=5).status_code == 200
    assert upload(client).status_code == 200


def test_cancelled_request_keeps_files_and_capacity_until_worker_finishes(
    client, monkeypatch
):
    entered = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    paths = []
    semaphore = threading.BoundedSemaphore(1)

    class TrackedSlots:
        def acquire(self, blocking):
            return semaphore.acquire(blocking=blocking)

        def release(self):
            semaphore.release()
            finished.set()

    def slow_engine(command, **kwargs):
        paths.append(Path(command[command.index("-o") + 1]).parent)
        entered.set()
        assert release.wait(5)
        assert paths[0].exists()
        Path(command[command.index("-o") + 1]).write_bytes(b"%PDF-test")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(processing, "PROCESSING_SLOTS", TrackedSlots())
    monkeypatch.setattr(processing.subprocess, "run", slow_engine)

    async def scenario():
        task = asyncio.create_task(
            asyncio.to_thread(
                processing.process_statement, SYNTHETIC, 2025, api.PROJECT_ROOT
            )
        )
        try:
            assert await asyncio.to_thread(entered.wait, 5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert paths[0].exists()
            with pytest.raises(HTTPException) as exc:
                processing.process_statement(SYNTHETIC, 2025, api.PROJECT_ROOT)
            assert exc.value.status_code == 503
        finally:
            release.set()
        assert await asyncio.to_thread(finished.wait, 5)
        assert not paths[0].exists()

    asyncio.run(scenario())
