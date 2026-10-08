# Processing correctness checkpoint

The API currently runs the pinned engine in `minimal` mode. Its first-release
output is an import document for tax software. A successful response means the
engine produced a PDF and validated its eCH XML; it does not mean the engine
calculated complete securities income.

## What this checkpoint verifies

`tests/fixtures/ibkr_portfolio_synthetic.xml` contains invented account data,
one invented US share, a purchase and sale, dividend, withholding and interest.
`tests/fixtures/kursliste_portfolio/` contains invented USD exchange rates.
Neither fixture is official reference data or suitable for a tax return.

The integration tests run the actual CLI and API, without downloading data:

| Input / behavior | Expected result checked by tests |
| --- | --- |
| CHF cash | CHF 1,000 retained |
| USD cash: 1,000 − 400 + 225 + 20 − 3 + 1 | USD 843; at synthetic year-end rate 0.90, CHF 758.70 |
| USD interest 1 on 16 June | CHF 0.92 using that day's synthetic rate |
| Opening 5 shares, buy 10, sell 5 | Closing 10; dated stock mutations preserved |
| Broker year-end share balance USD 500 | CHF 450, marked `undefined` for tax valuation |
| Broker dividend USD 20 and withholding USD 3 | Present in imported model and PDF reconciliation |
| Calculated securities payments in minimal mode | Absent from final eCH XML; securities income total is zero |
| Output validation and delivery | XSD validation succeeds; API returns a readable PDF with `Cache-Control: no-store` |

The final model totals are CHF 2,208.70 for balances and CHF 0.92 for income.
The income total omits the share dividend in this mode. The test checks that
limitation explicitly rather than treating these totals as a complete tax result.
The PDF displays the broker dividend and withholding in its reconciliation section,
but those entries are not calculated securities payments in the eCH payload.

## Calculation mode decision

The pinned engine exposes these four modes:

| Mode | Intended behavior |
| --- | --- |
| `none` | Skips the detailed tax-value calculator |
| `minimal` (current API) | Converts existing balances and cash interest; marks securities tax values undefined and clears calculated securities payments |
| `kursliste` | Uses reference-data security valuations and distributions; missing securities can produce warnings and incomplete results |
| `fillin` | Extends Kursliste calculation with broker-payment fallback when a security is not matched |

Keep `minimal` while the product promises an import document and validate an
actual import into the intended tax software. If the release should promise
calculated securities values and income, first test `kursliste` using matched
securities and official data, and decide how the API should handle missing matches
and reconciliation warnings. Switching the command-line flag alone does not
establish correctness.

This review uses the installed source at
[upstream commit `eeb3b3d790c5ba9c8cd2e256d228d0bae62ec572`](https://github.com/vroonhof/opensteuerauszug/tree/eeb3b3d790c5ba9c8cd2e256d228d0bae62ec572),
especially `calculate/minimal_tax_value.py` and the CLI's calculation-mode
dispatch in `steuerauszug.py`. Refresh these checks when updating the
engine.

## Phase 1 implementation and verification

The local suite now has 55 passing tests. It covers malformed XML, DTD/entity
rejection (including UTF-16 input), missing/invalid canton, required engine fields,
missing year/reference data, stale position dates, mismatched account identifiers,
unsupported asset categories and the exact 10 MiB upload boundary. It also covers
multiple accounts, multiple securities and a holding first acquired during the year.

The API accepts complete calendar-year reports, with one statement per account,
one shared Swiss canton, consistent account identifiers and 31 December position
snapshots. Interim exports are rejected rather than relabelled as year-end data.
Recognized summary/pseudo rows are left to the importer; unsupported detailed
trade/position categories are rejected before they can be silently omitted.
The deployed reference dataset currently covers 2025.

Processing runs in a worker that owns its temporary directory and a single
non-blocking capacity slot. A competing job returns 503 with `Retry-After: 5`;
`/health` remains responsive. This is a limit per API process. Keep one Uvicorn
worker per replica until scaling/concurrency sizing is reviewed in phase 3.

A 120-second subprocess timeout kills and waits for the engine. Tests exercise a
real sleeping child and check that it is gone and partial output removed. On HTTP
task cancellation, the worker continues until completion or timeout; it retains
its files and slot until cleanup finishes. Tests verify this lifetime. An abrupt
container/host crash is outside that graceful-cleanup guarantee; temporary data
is not written to the Kursliste share or another persistent document store.

The engine receives explicit empty configuration/identifier files and an explicit
Kursliste path, so local personal configuration cannot alter API results. Logs
contain processing status/duration and a busy event; stdout/stderr, filenames,
account identifiers, input XML and exception text are not logged or returned.
Failure tests assert that synthetic private markers do not escape into logs or
responses.

| Response | Meaning |
| --- | --- |
| 400 | Wrong filename or malformed/forbidden XML |
| 413 | Uploaded file exceeds 10 MiB |
| 422 | Invalid form/report fields or engine processing failure, including missing currency rates |
| 503 | Busy processor, missing schemas/year data, or an operating-system availability error |
| 504 | Engine exceeded the processing timeout |
| 500 | Engine reported success but produced missing or invalid PDF output |

The file limit is checked after FastAPI parses multipart input; it is not a total
HTTP body limit before multipart spooling. Add an ingress/body limit before
expanding beyond the current restricted single-user audience.

## Barcode capacity regression

The pinned upstream renderer occasionally overestimates the bytes that fit its
fixed 35-row, 13-column Macro PDF417 symbol. A deterministic regression test
reproduces `Not enough space in the barcode to fit the data` using the original
encoder call.

`app/engine.py` adapts only that call: it counts actual macro control words,
reserves the length descriptor, error correction, final terminator and byte-mode
latch, then caps segments to complete six-byte compaction groups. It preserves
the symbol dimensions, error correction, file identifiers and compressed XML.
The API invokes this adapter with `python -m app.engine`; directly running the
upstream CLI does not apply the fix.

Regression tests independently decode boundary-sized symbols with ZXing. The CLI
portfolio test decodes embedded PDF417 symbols, reassembles and decompresses them,
and checks byte-for-byte equality with the final eCH XML. The API test also reads
holdings and amounts from the decoded payload. The rendered synthetic barcode
page was inspected and all three symbols decoded from that page image.

## Acceptance checks remaining

The code and local tests are complete for this checkpoint. Deploy the new image
and finish the browser/tax-software checks in [phase 1 acceptance](phase-1-acceptance.md)
before marking the whole phase complete. Barcode decoding alone does not prove
acceptance by the intended tax software.

Corporate actions, derivatives, short positions and post-year-end corrections
need dedicated portfolio cases before claiming those workflows are validated.
The current API exposes one annual XML upload and does not expose the engine's
separate corrections-file option. The tested release scope is cash and ordinary
long-share holdings with minimal-mode import semantics.
