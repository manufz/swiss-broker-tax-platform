# Browser upload workspace

The FastAPI application serves the workspace at `/`, with its HTML, CSS,
JavaScript and fictional sample bundled inside the existing container. It uses
the same-origin `POST /v1/statements` endpoint; `/docs` remains the developer API
interface. There is no separate frontend deployment or external asset service.

## Try it

From the repository root:

```bash
KURSLISTE_DIR="$PWD/tests/fixtures/kursliste" uv run --frozen uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`. Choose **Try a synthetic example**, generate the
statement and download the PDF. Expect a fictional 2025 account and CHF 1,000 cash.
You can browse for an XML file or drop one into the upload area instead.

The year selector follows `SUPPORTED_TAX_YEARS` (default `2025`). Keep that
configuration aligned with mounted reference data. The built-in example is
available only when 2025 is configured. Synthetic local data is for testing;
use the documented official Kursliste release for personal processing.

## Behavior and boundaries

- The browser checks extension, empty files and the 10 MiB limit before upload.
  Server validation remains authoritative.
- Processing displays elapsed time, without claiming a percentage or invented
  intermediate completion. The controls prevent duplicate submissions.
- API errors appear as text, including an expired-session sign-in link for 401.
  A busy service can be retried manually; documents are not resubmitted silently.
- PDFs are held in browser memory until reset, input changes or page departure.
  Downloading explicitly saves the user's copy. No local/session storage,
  analytics, remote fonts or broker credentials are used.
- A restrictive content-security policy permits only local assets and requests;
  the page is served with `Cache-Control: no-store` and no-referrer policy.
- Keyboard focus, file-picker access, live status announcements, reduced motion
  and a stacked mobile layout are included.

The illustration is an output-format illustration, not a preview of the user's
actual PDF. The PDF must be downloaded and reviewed. The existing minimal-mode
securities-income and valuation limitations remain visible in the interface.
Direct IBKR retrieval is explicitly marked planned and is not implemented.

## Release status

Implemented and tested locally on 2026-10-15. The new page has not been deployed
to Azure. Terraform's sign-in return URL and Entra homepage now target `/` in
source; the existing callback and authorization policy are unchanged.

For deployment, commit the tested source, follow the existing image publishing
and digest-promotion workflow, review the Terraform plan and apply it. Verify
that signed-in users reach `/`, and that unauthenticated `/`, `/assets/app.js`
and `POST /v1/statements` remain denied. Repeat the upload/download and same-tenant
allowlist checks; local testing cannot prove Azure ingress authorization.

Automated route tests cover page security headers, bundled assets, configured
years, fictional sample parity and preservation of the API contract. The existing
processing tests cover the actual PDF generation and validation boundary.

Browser checks on 2026-10-15 confirmed the desktop layout (1366 px), stacked
mobile layout (390 px) without horizontal overflow, synthetic example selection,
real PDF generation/download and a visible malformed-XML error. The updated
Linux amd64 container includes the page/assets and runs the existing processing
checks as the non-root application user. These are local checks, not evidence of
an Azure browser session.
