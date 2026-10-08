import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from datetime import date
from pathlib import Path
from xml.etree.ElementTree import ParseError

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from fastapi import HTTPException
from opensteuerauszug.importers.common.client import parse_swiss_canton

logger = logging.getLogger(__name__)
PROCESS_TIMEOUT_SECONDS = 120
# One engine process per API worker. The deployment currently has one worker/replica.
PROCESSING_SLOTS = threading.BoundedSemaphore(1)
SUPPORTED_ASSETS = {"STK", "OPT", "FUT", "BOND", "ETF", "FUND", "FOP", "CASH"}


def validate_statement(contents: bytes, tax_year: int) -> None:
    try:
        root = ElementTree.fromstring(
            contents, forbid_dtd=True, forbid_entities=True, forbid_external=True
        )
    except (ParseError, DefusedXmlException, ValueError):
        raise HTTPException(
            400, "The uploaded file must be well-formed XML without DTDs or entities."
        ) from None

    statements = root.findall("./FlexStatements/FlexStatement")
    if root.tag != "FlexQueryResponse" or not statements:
        raise HTTPException(
            422, "An IBKR Flex report containing account statements is required."
        )

    cantons = set()
    account_ids = set()
    for statement in statements:
        account_id = statement.get("accountId", "").strip()
        if not account_id or account_id in account_ids:
            raise HTTPException(
                422, "Each account must have one statement with a unique accountId."
            )
        account_ids.add(account_id)
        try:
            dates = []
            for field in ("fromDate", "toDate"):
                value = statement.get(field, "")
                if len(value) != 8 or not value.isascii() or not value.isdigit():
                    raise ValueError
                dates.append(date(int(value[:4]), int(value[4:6]), int(value[6:])))
        except ValueError:
            raise HTTPException(
                422,
                "Each statement requires valid fromDate and toDate values (YYYYMMDD).",
            ) from None
        if (
            dates[0].year != tax_year
            or dates[1].year != tax_year
            or dates[0] > dates[1]
        ):
            raise HTTPException(
                422, "Statement dates must be ordered and match the requested tax year."
            )

        if dates != [date(tax_year, 1, 1), date(tax_year, 12, 31)]:
            raise HTTPException(
                422,
                "A complete calendar-year Flex report (1 January to 31 December) is required.",
            )

        account = statement.find("AccountInformation")
        canton = parse_swiss_canton(
            account.get("stateResidentialAddress") if account is not None else None
        )
        if not canton:
            raise HTTPException(
                422,
                "Each account requires a valid Swiss canton in AccountInformation.stateResidentialAddress.",
            )
        cantons.add(canton)
        for record in statement.iter():
            if (
                record.get("levelOfDetail", "").upper() == "SUMMARY"
                or record.get("accountId") == "-"
            ):
                continue
            if (
                record.get("accountId") is not None
                and record.get("accountId", "").strip() != account_id
            ):
                raise HTTPException(
                    422, "Account identifiers must be consistent within each statement."
                )
            if (
                record.tag in {"Trade", "OpenPosition"}
                and record.get("assetCategory") not in SUPPORTED_ASSETS
            ):
                raise HTTPException(
                    422, "The report contains a missing or unsupported asset category."
                )
            if (
                record.tag == "OpenPosition"
                and record.get("reportDate") != f"{tax_year}1231"
            ):
                raise HTTPException(
                    422,
                    "Open positions must be a snapshot from 31 December of the requested year.",
                )
        if not any(
            statement.find(path) is not None
            for path in (
                "CashReport/CashReportCurrency",
                "OpenPositions/OpenPosition",
                "Trades/Trade",
            )
        ):
            raise HTTPException(
                422, "Each account must contain cash balances, positions or trades."
            )
    if len(cantons) != 1:
        raise HTTPException(
            422, "All accounts in one report must use the same Swiss canton."
        )


def process_statement(contents: bytes, tax_year: int, project_root: Path) -> bytes:
    if not PROCESSING_SLOTS.acquire(blocking=False):
        logger.info("statement_processing outcome=busy status=503")
        raise HTTPException(
            503,
            "Statement processing is busy. Retry shortly.",
            headers={"Retry-After": "5"},
        )

    started = time.monotonic()
    status = 500
    try:
        validate_statement(contents, tax_year)
        kursliste_dir = Path(
            os.environ.get("KURSLISTE_DIR", project_root / "data/kursliste")
        ).resolve()
        # Canonical names are produced by the documented download/release workflow.
        if not any(
            (path := kursliste_dir / f"kursliste_{tax_year}.{extension}").is_file()
            and path.stat().st_size > 0
            for extension in ("sqlite", "xml")
        ):
            raise HTTPException(
                503, "Kursliste reference data is unavailable for the requested year."
            )

        # This entire lifetime belongs to the worker, not the HTTP coroutine.
        # Cancelling a request cannot remove files from underneath a running CLI.
        with tempfile.TemporaryDirectory(prefix="tax-statement-") as tmp:
            workdir = Path(tmp)
            input_path = workdir / "statement.xml"
            output_path = workdir / "steuerauszug.pdf"
            config_path = workdir / "config.toml"
            identifiers_path = workdir / "identifiers.csv"
            input_path.write_bytes(contents)
            # Do not inherit a developer's personal engine configuration.
            config_path.write_text("", encoding="utf-8")
            identifiers_path.write_text("", encoding="utf-8")
            command = [
                sys.executable,
                "-m",
                "app.engine",
                "process",
                str(input_path),
                "--importer",
                "ibkr",
                "--tax-calculation-level",
                "minimal",
                "--tax-year",
                str(tax_year),
                "--config",
                str(config_path),
                "--identifiers-csv-path",
                str(identifiers_path),
                "--kursliste-dir",
                str(kursliste_dir),
                "-o",
                str(output_path),
            ]
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    check=False,
                    timeout=PROCESS_TIMEOUT_SECONDS,
                    cwd=project_root,
                )
            except subprocess.TimeoutExpired:
                # subprocess.run kills and waits for the child before raising.
                raise HTTPException(504, "Statement processing timed out.") from None

            if result.returncode != 0:
                raise HTTPException(
                    422,
                    "The statement could not be processed. Check required IBKR fields and currency data.",
                )
            if not output_path.is_file():
                raise HTTPException(500, "Statement processing did not produce a PDF.")
            pdf = output_path.read_bytes()
            if not pdf.startswith(b"%PDF-"):
                raise HTTPException(
                    500, "Statement processing produced an invalid PDF."
                )

        status = 200
        return pdf
    except HTTPException as exc:
        status = exc.status_code
        raise
    except OSError:
        status = 503
        raise HTTPException(
            503, "Statement processing is temporarily unavailable."
        ) from None
    finally:
        PROCESSING_SLOTS.release()
        # Never log CLI output, exception text, filenames, XML, or account data.
        logger.info(
            "statement_processing status=%d duration_ms=%d",
            status,
            round((time.monotonic() - started) * 1000),
        )
