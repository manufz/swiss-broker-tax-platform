# Microsoft Entra sign-in

Entra authentication and external HTTPS are deployed. Unauthenticated ingress
checks passed, and the downloaded browser-test PDF was verified against the
synthetic fixture.

## What this checkpoint adds

`terraform/environments/dev/authentication.tf` creates a single-tenant Entra app
registration, its service principal, a client credential and a rotation timestamp.
AzAPI manages the Container Apps `authConfigs/current` child resource because
the pinned AzureRM Container App resource does not expose authentication settings.
The Container App receives the credential as the `entra-client-secret` secret.

Container Apps authentication handles browser sign-in before requests reach
FastAPI. The issuer is restricted to the current Entra tenant and the permitted
token audience is this app's client ID. Its authorization policy allows only
the user object IDs in `allowed_user_object_ids`, initially the developer's Azure
user. An empty allowlist is rejected during Terraform validation. This user
identity is separate from the managed identity that pulls images from ACR.

Unauthenticated app requests return HTTP 401. The explicit sign-in URL uses
`/.auth/login/aad` and returns to the workspace at `/`, deployed on 2026-10-15.
The Entra homepage also targets `/`; `/docs` remains available for developers.
No Graph permissions to read user files or mail are requested.
Tokens are not persisted in an EasyAuth token store; browser
session cookies still authenticate requests.

The registration enables ID-token issuance for the built-in hybrid OpenID Connect
flow, which uses the server-side client secret. Implicit access-token issuance is
disabled. The callback uses the future external HTTPS hostname, derived from the
environment's default domain; the app's current internal hostname is different.

## First checkpoint: authentication configured

The initial apply used internal ingress (`external_enabled = false`) and the
following commands:

```bash
export ARM_SUBSCRIPTION_ID="$(az account show --query id --output tsv)"
terraform -chdir=terraform/environments/dev init
terraform -chdir=terraform/environments/dev apply
```

That plan showed `5 to add, 1 to change, 0 to destroy`: five authentication
resources were added and the existing Container App received a secret. Its image
digest stayed the same and no API rebuild was required. The configuration now
prepares the separate external-ingress checkpoint below; a new deployment should
complete this internal checkpoint before changing ingress to external.

Directory permissions are distinct from Azure subscription permissions. Entra
must permit this Azure user to register applications and create the associated
service principal. If Graph rejects creation, keep ingress internal and inspect
that specific directory permission error before retrying.

The deployed configuration was verified: authentication enabled, HTTPS required,
unauthenticated action `Return401`, expected tenant/client ID, and the single
developer user allowlist. The registration has the matching HTTPS callback and
single-tenant audience. Unauthenticated `GET /docs` and `POST /v1/statements`
through internal ingress both returned HTTP 401. Direct localhost requests inside
the container bypass ingress authentication and do not prove that the access
policy works.

## Second checkpoint: external HTTPS and browser verification

The separate ingress change was applied with `external_enabled = true`:

```bash
terraform -chdir=terraform/environments/dev apply
```

The external `/docs` request below returned 401 without a session:

```bash
api_url=$(terraform -chdir=terraform/environments/dev output -raw api_url)
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' "$api_url/docs"
```

Then get the browser sign-in URL:

```bash
terraform -chdir=terraform/environments/dev output -raw api_sign_in_url
```

Sign in with the allowlisted Azure user, confirm the workspace at `/` loads, then submit
`tests/fixtures/ibkr_synthetic.xml` with tax year `2025`. Verify the downloaded PDF
contains the synthetic account and year. Sign out through `/.auth/logout` and
confirm access is denied again. If another tenant user is available for testing,
confirm their authenticated request is forbidden by the identity allowlist.
Sign-out behavior and rejection of an authenticated user outside the allowlist
remain additional access-control checks; they were not observed in this checkpoint.

Alternatively, open Swagger UI at `/docs`, expand `POST /v1/statements`, choose **Try it out**, select the
synthetic XML, enter `2025`, and choose **Execute**. A successful response is HTTP
200 with PDF content; use **Download file** to save it. The PDF should include
account `U0000000` and tax year `2025`. The initial browser checks should use this
synthetic fixture before testing personal documents.

### Verified browser-test result

The user supplied the downloaded `steuerauszug-2025.pdf` after the browser test.
Its 19,328-byte, five-page output was opened, text-extracted and rendered for visual
inspection. It contains Example Person, account `U0000000`, canton ZH, tax year
2025 and a CHF 1,000.00 year-end balance, matching the synthetic fixture. All five
pages render legibly, including the bank-account table and barcode page. The
document identifies itself as minimal mode and says no tax calculations were
performed; this validates delivery and basic input preservation, not realistic
portfolio calculations or a tax-software import.

Azure reports external ingress enabled, insecure ingress disabled and provisioning
succeeded. The previously recorded internal FQDN was refreshed in Terraform state
after Azure returned the external FQDN. The user's PDF remains outside the repository.

## Credential lifetime

The credential expires after 180 days. `time_rotating.auth_secret` proposes
rotation after 150 days; rotation happens only when Terraform is run and applied.
It is not a background scheduler. A replacement password is created before the
old one is deleted, and the Container App secret is updated in the same apply.
Verify sign-in after each rotation; monitor the expiry output and apply the
rotation before expiry. Automated rotation/expiry notifications are operations
work still on the roadmap.

```bash
terraform -chdir=terraform/environments/dev output auth_client_secret_expires_at
```

Terraform stores the generated credential in the restricted remote state. Its
value is sensitive and is not an output. Never copy it into source files,
screenshots, logs or Git. Tenant IDs, client IDs and user object IDs are identifiers,
not credentials. Backend access controls also protect retained state versions.

References: [Microsoft Entra authentication for Container Apps](https://learn.microsoft.com/azure/container-apps/authentication-entra),
[Container Apps authentication policy schema](https://learn.microsoft.com/azure/templates/microsoft.app/2025-07-01/containerapps/authconfigs),
[Terraform rotation timing](https://github.com/hashicorp/terraform-provider-time/blob/main/docs/resources/rotating.md).
