# Swiss Broker Tax Platform

Terraform setup is documented in [terraform/README.md](terraform/README.md).
Terraform state is stored in Azure using identity authentication; see the
[remote-state guide](terraform/remote-state.md).
Image publishing is documented in [docs/publishing-image.md](docs/publishing-image.md).
The remaining release steps are tracked in [docs/roadmap.md](docs/roadmap.md).
Sign-in and the verified browser flow are documented in [docs/authentication.md](docs/authentication.md).

A FastAPI wrapper around the pinned `opensteuerauszug` engine. Accepts IBKR
Flex XML and returns a Swiss tax statement PDF. A development instance is deployed
to Azure Container Apps with Entra authentication and external HTTPS. The browser
test produced a downloaded PDF matching the synthetic fixture.
It uses a read-only Azure Files mount of the official 2025 Kursliste database.
A synthetic upload has produced a readable PDF in Azure. See
[data provenance](docs/kursliste-provenance.md) for the verified export and checksums.

## Local setup

```bash
uv sync --frozen
uv run opensteuerauszug kursliste download --year 2025 --destination data/kursliste
KURSLISTE_DIR="$PWD/data/kursliste" uv run uvicorn app.main:app --reload
```

The download command fetches the official ICTax export and converts it to
SQLite for faster processing. Run it for each tax year you need. Re-running
checks the upstream export metadata and refreshes changed data.
Downloaded XML and SQLite files are excluded from Git and Docker builds.

Open http://localhost:8000/docs and submit a Flex XML to `POST /v1/statements`
with the matching `tax_year`. The XML must include the Swiss canton in
`AccountInformation.stateResidentialAddress`; there is currently no API override.
Use a complete calendar-year report with 31 December open positions and one
statement per account. All accounts must use the same Swiss canton.

## Run in Docker

After downloading Kursliste data locally:

```bash
docker build -t swiss-tax-statement-api .
docker run --rm -p 127.0.0.1:8000:8000 \
  -v "$PWD/data/kursliste:/data/kursliste:ro" \
  -e KURSLISTE_DIR=/data/kursliste \
  swiss-tax-statement-api
```

The volume provides the official data to the container without baking it into
the image. The `:ro` suffix makes it read-only during request processing.

## Checks and current limits

```bash
uv run python -m pytest -q
uv run ruff check app tests
```

Tests use synthetic CHF cash and a USD securities portfolio with synthetic
Kursliste rates; they require no download. They check holdings, transactions,
cash conversions and broker-payment reconciliation. eCH-0196 schemas in `specs/`
validate generated XML.
Missing schemas stop API processing. See `specs/README.md` for provenance.
The API runs one processing job per worker; competing requests return 503 with
`Retry-After: 5`. Engine jobs time out after 120 seconds and clean up temporary
files. It uses `app/engine.py` to correct the pinned renderer's barcode capacity;
running the upstream CLI directly bypasses that adapter.

The API currently uses `minimal` calculation mode to create an import document.
Securities dividends and withholding appear in PDF reconciliation but are not
calculated securities payments in the eCH XML. See the
[processing checkpoint](docs/processing-correctness.md) for expected amounts and
mode limitations. Successful processing and schema validation do not establish
tax-calculation correctness or acceptance
by a tax authority. The hardened code passes local tests; deployment, browser
access checks and an actual tax-software import remain on the
[phase 1 acceptance checklist](docs/phase-1-acceptance.md). Keep personal broker
exports in the ignored `private/` or
`statements/` directories.
