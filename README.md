# Swiss Broker Tax Platform

Terraform setup is documented in [terraform/README.md](terraform/README.md).
Image publishing is documented in [docs/publishing-image.md](docs/publishing-image.md).

A FastAPI wrapper around the pinned `opensteuerauszug` engine. Accepts IBKR
Flex XML and returns a Swiss tax statement PDF. Infrastructure is not yet deployed.

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
uv run pytest -q
uv run ruff check app tests
```

Tests use a synthetic CHF-only account and a synthetic Kursliste fixture;
they require no download. eCH-0196 schemas in `specs/` validate generated XML.
Missing schemas stop API processing. See `specs/README.md` for provenance.

The API currently uses `minimal` calculation mode. Successful processing and
schema validation do not establish tax-calculation correctness or acceptance
by a tax authority. Authentication, deployment and real portfolio validation
are still pending. Keep personal broker exports in the ignored `private/` or
`statements/` directories.
