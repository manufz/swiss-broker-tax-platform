# Development Kursliste data

The development file share contains only public tax reference data. Broker
exports and generated PDFs are not stored there.

The pinned `opensteuerauszug` downloader fetched the official ICTax 2025 export
and converted it to SQLite. The database records this source metadata:

| Field | Value |
| --- | --- |
| Tax year | 2025 |
| Export file ID | `4341535` |
| Archive | `kursliste_2025.zip` |
| Export type | `THIRD.INIT.220` |
| Upstream archive hash | `8ee0b5146770a5e39663b1d1dd568634` |
| SQLite filename | `kursliste_2025.sqlite` |
| SQLite bytes | `577601536` |
| SQLite SHA-256 | `77a29260f56c3a8b5f642d1ffcd07a80a15b48e3b57413d52414f2125aa9e2c9` |
| SQLite MD5, base64 | `DBxXzaEDncxF2A8ujmXDng==` |

Source: [official ICTax archive](https://www.ictax.admin.ch/extern/api/download/4341535/8ee0b5146770a5e39663b1d1dd568634/kursliste_2025.zip).
The upstream archive hash and converted database checksums refer to different
files. Recreating SQLite can change its binary checksum even when the source
export is identical.

The upload used per-range MD5 validation and set the file's MD5 property. Azure
reported the expected size and MD5 after upload. The application mounts the share
read-only at `/data/kursliste`.

Inside the deployed container, the mounted database's size, export file ID and
archive hash matched the values above. Posting the repository's synthetic IBKR
fixture to the API returned HTTP 200 and a readable five-page PDF (19,328 bytes)
containing the synthetic account and tax year. Processing took 26.67 seconds.
The full SQLite integrity scan over SMB was stopped because it was slow; this
checkpoint verifies metadata and API processing, not a completed integrity scan
or realistic portfolio calculations.

For future data releases, upload a new version into a separate directory, verify
it, and change the app's `KURSLISTE_DIR` to that directory. Retain the previous
version for rollback. Avoid overwriting a database while a running replica reads
it. Versioned release automation and refresh checks remain on the roadmap.
