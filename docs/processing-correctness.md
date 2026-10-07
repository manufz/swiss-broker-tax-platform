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

## Still to verify

- Malformed XML, missing canton/required fields/reference data, year mismatch and upload limits.
- Processing failure, timeout, concurrency limits and temporary-file cleanup.
- Diagnostics that expose useful outcomes without logging account or transaction data.
- Broader portfolio cases: multiple securities/accounts, partial-year holdings,
  corporate actions and applicable broker corrections.
- Barcode decoding and an actual import into the intended tax software.

This synthetic checkpoint verifies the tested mappings and known limitations. It
does not close the full processing-correctness roadmap step.
