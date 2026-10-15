# Kursliste reference-data provenance

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

The database was converted from the [official ICTax 2025 archive](https://www.ictax.admin.ch/extern/api/download/4341535/8ee0b5146770a5e39663b1d1dd568634/kursliste_2025.zip)
using the pinned OpenSteuerAuszug downloader. Archive and SQLite checksums refer
to different files; reconverting the same export can change the SQLite binary
checksum. A local SQLite `quick_check`, MD5-validated upload ranges and remote byte
count verified the data release. The application mounts public reference data
read-only, separately from temporary broker exports and generated PDFs. Refresh
it through [immutable data releases](data-releases.md), retaining the previous
version for rollback.
