import asyncio
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

app = FastAPI(
    title="Swiss Broker Tax Platform",
    version="0.1.0",
)

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

    contents = await statement.read(MAX_UPLOAD_SIZE + 1)

    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Statement exceeds the 10 MiB upload limit.",
        )

    if not contents.lstrip().startswith(b"<"):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file does not appear to be XML.",
        )

    if any(not (PROJECT_ROOT / "specs" / name).is_file() for name in SCHEMA_FILES):
        raise HTTPException(
            status_code=503,
            detail="Statement validation is unavailable: required schemas are missing.",
        )

    with tempfile.TemporaryDirectory(prefix="tax-statement-") as tmp:
        workdir = Path(tmp)

        input_path = workdir / "statement.xml"
        output_path = workdir / "steuerauszug.pdf"

        input_path.write_bytes(contents)

        command = [
            "opensteuerauszug",
            "process",
            str(input_path),
            "--importer",
            "ibkr",
            "--tax-calculation-level",
            "minimal",
            "--tax-year",
            str(tax_year),
            "-o",
            str(output_path),
        ]

        if kursliste_dir := os.environ.get("KURSLISTE_DIR"):
            command.extend(["--kursliste-dir", kursliste_dir])

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                command,
                capture_output=True,
                check=False,
                timeout=120,
                cwd=PROJECT_ROOT,
            )
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(
                status_code=504,
                detail="Statement processing timed out.",
            ) from exc

        if result.returncode != 0 or not output_path.exists():
            # Intentionally do not return CLI stderr to the caller.
            # Financial/account information could appear there.
            raise HTTPException(
                status_code=422,
                detail="The statement could not be processed.",
            )

        pdf = output_path.read_bytes()

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="steuerauszug-{tax_year}.pdf"',
            "Cache-Control": "no-store",
        },
    )
