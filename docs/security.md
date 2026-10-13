# Security model and limitations

| Boundary / risk | Control | Verification / remaining limitation |
| --- | --- | --- |
| Unauthenticated uploads | HTTPS-only ingress, single-tenant Entra, explicit user-object-ID allowlist | External `/docs` and upload return 401; check a different signed-in identity and logout manually |
| XML entities / parser abuse | defusedxml forbids DTD/entities/external references | UTF-16 and malformed-input tests; no runtime schema network fetch |
| Disk/memory exhaustion | 12 MiB request and 10 MiB file limits; one engine job; 120-second timeout | Multipart/chunked/concurrency/cleanup tests; not designed for anonymous public load |
| Leakage in diagnostics | Capture child stdout/stderr; expose static errors; log only outcome/status/duration | Private-marker tests and deployed log inspection |
| Persistent financial files | Temporary per-job directory, no-store PDF response | Success/failure/cancellation cleanup tests; downloaded browser copies remain local |
| Image credentials | Scoped managed identity with AcrPull; registry admin disabled | Successful digest-pinned deployment |
| Deployment credentials | GitHub OIDC, exact environment subject, resource-scoped roles | Enabled only after repository exists; never grant federation to pull requests |
| State credentials | Entra-authenticated private blobs, separate bootstrap/dev state, leases, versioning | State contains the Azure Files mount key and sign-in secret; never publish state/plans |
| Reference-data tampering | Local SQLite check, provenance/SHA-256, immutable version directory, read-only runtime mount | Upload transfer MD5 and metadata checks; only authenticated maintainers upload data |
| Calculation confidence | Synthetic expected values, schema and decoded-barcode tests | Minimal mode omits securities income; actual tax-software import/recalculation remains required |

The host receives financial data in plaintext inside the authenticated workload.
There is no independent security audit, malware scanning, multi-user separation,
queue, private VNet or high-availability guarantee. The environment uses public
authenticated Azure service endpoints. A read-only SMB mount is authenticated by
a storage key stored in Terraform state; image pulls use a different identity.

Apply Terraform before the sign-in secret's expiry; declaring a rotation resource
does not run Terraform on a schedule. See [operations](operations.md). Keep broker
exports and personal PDFs in ignored `private/` or `statements/` paths. Use
synthetic data in issues, screenshots, logs and CI. Report issues to the maintainer
privately; after publication enable GitHub private vulnerability reporting.
