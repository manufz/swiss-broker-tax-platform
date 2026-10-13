# Design decisions

| Decision | Reason / tradeoff |
| --- | --- |
| FastAPI wrapper around a pinned engine | Reuse tax-domain importing/rendering while owning the service boundary; document upstream attribution and mode limits |
| Synchronous subprocess, one worker/replica | Simple isolation, timeout and cleanup, predictable development cost; simultaneous jobs receive 503; a queue is a later extension |
| Minimal calculation mode | Generate import data and let tax software recalculate; PDF reconciliation is not calculated securities income in eCH XML |
| Azure Container Apps | Managed HTTPS, identity-based registry pulls, Entra authentication and consumption scaling; introduces cold starts and platform dependencies |
| Separate image/reference data | A 551 MiB database need not be baked into each image; SMB access has latency, so version and verify files separately |
| Remote Terraform state | Blob leases serialize writers and versioning supports recovery; state is sensitive and release workflows do not receive access |
| Explicit digest approval | Build/test/push, commit digest, then manually deploy it; preserves a reviewable desired image and rollback path |
| Entra allowlist | Fits a private portfolio MVP; visitors assess synthetic screenshots/source without needing access to financial processing |
| Runtime barcode adapter | Corrects capacity calculations at the service entry point without maintaining a full engine fork; round-trip decoded payload tests cover the patch |
| Scale-to-zero, max one replica | Reduces idle compute and bounds cost/concurrency; registry, storage, logging and alert resources can still incur charges |

No Kubernetes, multi-tenant accounts, asynchronous queue or payment system is
included. Such changes would require a separate access/storage/retention design.
