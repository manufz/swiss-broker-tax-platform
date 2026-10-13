import asyncio
import logging
import os
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.processing import process_statement
from app.security import BodySizeLimitMiddleware

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

app = FastAPI(
    title="Swiss Broker Tax Platform",
    version="0.1.0",
)
app.add_middleware(BodySizeLimitMiddleware)

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MiB
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILES = (
    "eCH-0196-2-2.xsd",
    "eCH-0007-6-0.xsd",
    "eCH-0008-3-0.xsd",
    "eCH-0010-7-0.xsd",
    "eCH-0097-4-0.xsd",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    """Check prerequisites without reading the large database over SMB."""
    directory = Path(os.environ.get("KURSLISTE_DIR", PROJECT_ROOT / "data/kursliste"))
    years = os.environ.get("SUPPORTED_TAX_YEARS", "2025").split(",")
    valid_years = all(year.isdigit() and len(year) == 4 for year in years)
    schemas_present = all(
        (PROJECT_ROOT / "specs" / name).is_file() for name in SCHEMA_FILES
    )
    data_present = valid_years and all(
        any(
            (path := directory / f"kursliste_{year}.{extension}").is_file()
            and path.stat().st_size > 0
            for extension in ("sqlite", "xml")
        )
        for year in years
    )
    if not schemas_present or not data_present:
        raise HTTPException(503, "Required schemas or reference data are unavailable.")
    return {"status": "ready"}


@app.post("/v1/statements")
async def generate_statement(
    statement: Annotated[UploadFile, File()],
    tax_year: Annotated[int, Form(ge=2000, le=2100)],
) -> Response:
    if not statement.filename or not statement.filename.lower().endswith(".xml"):
        raise HTTPException(
            status_code=400,
            detail="An IBKR Flex XML file is required.",
        )

    try:
        contents = await statement.read(MAX_UPLOAD_SIZE + 1)
    finally:
        await statement.close()

    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Statement exceeds the 10 MiB upload limit.",
        )

    if any(not (PROJECT_ROOT / "specs" / name).is_file() for name in SCHEMA_FILES):
        raise HTTPException(
            status_code=503,
            detail="Statement validation is unavailable: required schemas are missing.",
        )

    pdf = await asyncio.to_thread(process_statement, contents, tax_year, PROJECT_ROOT)

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="steuerauszug-{tax_year}.pdf"',
            "Cache-Control": "no-store",
        },
    )
