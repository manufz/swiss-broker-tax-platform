# Terraform development deployment

The current configuration manages Switzerland North resources: resource group,
Basic ACR (admin disabled), scoped AcrPull identity, Container Apps environment
and API, Log Analytics, read-only Azure Files data, Entra sign-in/allowlist,
credential rotation, cost budget and processing alert. Optional GitHub federation
is enabled only when the exact repository environment subject is supplied.

All `.tf` files under `environments/dev` form one configuration. The independent
`bootstrap` root owns private state storage. State/plan files and local `.tfvars`
are ignored; provider lockfiles are committed. State includes the SMB key and
sign-in credential, so never print/upload it in CI. See [state recovery](remote-state.md).

## Validate locally without Azure access

Install Terraform 1.16.4 (compatible range 1.9–<2), Python 3.12 and Azure CLI.
From the repo root:

```bash
terraform fmt -check -recursive terraform
for root in terraform/bootstrap terraform/environments/dev; do
  task_data=$(mktemp -d)
  TF_DATA_DIR="$task_data" terraform -chdir="$root" init -backend=false -lockfile=readonly
  TF_DATA_DIR="$task_data" terraform -chdir="$root" validate
  rm -rf "$task_data"
done
```

Use a separate provider directory for backend-free validation so it does not
disturb the initialized working backend. These checks create no Azure resources.

## Work on this existing environment

`allowed_user_object_ids` is required and has no default. Set it in ignored
`environments/dev/dev.auto.tfvars` before planning. For a new checkout, copy
`environments/dev/dev.auto.tfvars.example` and replace the placeholder with the
authorized Entra user object ID. Existing checkouts should preserve their private
settings rather than overwriting the file. Obtain the current user's ID with:

```bash
az ad signed-in-user show --query id --output tsv
```

Use the developer Azure identity with backend access and directory permissions:

```bash
az login
az account set --subscription YOUR_SUBSCRIPTION_ID
export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
terraform -chdir=terraform/environments/dev init -lockfile=readonly
terraform -chdir=terraform/environments/dev plan
terraform -chdir=terraform/environments/dev apply
```

Inspect the fresh plan before confirming. `No changes` means nothing needs
deployment. Saved `.tfplan` files are optional; keep them private, use a freshly
reviewed one once, and regenerate after state changes. Never disable state locking.

| Input | Purpose |
| --- | --- |
| `api_image_digest` | Verified ACR image to deploy; digest validation enforced |
| `allowed_user_object_ids` | Nonempty explicit Entra user allowlist |
| `kursliste_directory` | Immutable data directory within the read-only mount |
| `min_replicas` | 0 normally, 1 temporarily for CLI diagnostic access |
| `monthly_budget` | Notification budget in billing currency, not a spending cap |
| `notification_email` | Optional private email for budget/error delivery |
| `github_oidc_subject` | Exact azure-dev environment subject; null disables identity |

Use ignored `environments/dev/dev.auto.tfvars` for persistent private choices.
Environment overrides use `TF_VAR_<name>`. Keep these choices present on every
future plan; removing an OIDC/email override can plan deletion of its resources.
GitHub's image workflow reads the committed image default rather than local
private overrides. See [release setup](../docs/github-release.md).

Azure providers are explicitly registered by the developer; automatic registration
is disabled. Required namespaces include Microsoft.Storage, ContainerRegistry,
ManagedIdentity, App, OperationalInsights, Insights and Consumption. Entra app
registration permissions are separate from Azure resource/role permissions.

## Deploy in a different Azure subscription

The committed backend names target the reference development environment;
they are not portable credentials. A new maintainer must create their own backend,
allowlist and ACR image. Local synthetic checks need none of these Azure resources.

1. Copy the `bootstrap` root into an ignored private working directory **without
   its `backend.tf`**. Initialize/apply there using local state and your own Azure
   identity. It creates your subscription-derived state account, private container
   and scoped Blob Data Contributor role. Protect the local state.
2. Set each root's backend `storage_account_name` to your new account (or use
   backend configuration overrides). Keep the bootstrap/dev blob keys separate.
   Add the backend to the working bootstrap copy and run `init -migrate-state`,
   preserving its existing local state. Copy configuration changes back deliberately.
3. Obtain your Entra user object ID with `az ad signed-in-user show --query id -o
   tsv`, set `allowed_user_object_ids` privately, and register service providers.
4. Create/push your own tested amd64 image into your registry before the runtime
   is applied. For the initial registry/identity stage, a deliberately scoped
   bootstrap apply targeting their resources can break this first-image dependency;
   then return to full plans. Do not use routine targeting for later changes.
5. Download/verify official public data and upload a release after storage exists.
   Review the full development plan. Ensure its image/directory selects your own
   verified artifacts before accepting the runtime. Set a stable budget start
   date to the first day of your current billing month for a new deployment.
6. Verify managed-identity pulls, readiness, Entra login/denial, synthetic PDFs and
   a clean full plan. Provisioning an empty share alone does not provide data.

Do not connect a new subscription's configuration to the author's backend or
create fresh empty state for already managed resources. The
[bootstrap guide](bootstrap/README.md) explains state storage setup and migration.

## Operations

HTTPS is external but access remains single-tenant and allowlisted. The API uses
0–1 replicas, 0.5 vCPU, 1 GiB memory, process health and data/schema readiness.
Kursliste is read-only at `/data/kursliste`; image pulls use managed identity,
while the SMB mount uses a storage key protected in remote state.

[Data releases](../docs/data-releases.md) · [Operations/rollback](../docs/operations.md)
· [Local checks](../README.md#checks) · [Authentication](../docs/authentication.md)
