# Terraform: development environment

The configuration declares the resource group `rg-swiss-tax-statement-dev`
in `switzerlandnorth`, a Basic Azure Container Registry for the API image,
and a user-assigned managed identity with `AcrPull` on that registry.
The configuration also declares the Container App runtime, logging workspace
and Azure Files storage for public Kursliste data. Authenticated browser access
is a later step. See `../docs/roadmap.md` for the remaining release work.

## Files

All `.tf` files in `environments/dev/` form one Terraform configuration.
Splitting them by purpose helps us read them; file names do not control order.

- `versions.tf`: Terraform and AzureRM provider version constraints.
- `backend.tf`: private Azure Blob state storage using your Azure CLI identity.
- `authentication.tf`: Entra browser sign-in, credential rotation and ingress authorization.
- `providers.tf`: configures the provider that communicates with Azure.
- `variables.tf`: inputs, starting with the Azure region.
- `main.tf`: the resource we want Terraform to manage.
- `registry.tf`: the image registry and its deterministic name suffix.
- `identity.tf`: the managed identity and its registry-scoped pull permission.
- `container_app.tf`: the logging workspace, hosting environment and API runtime.
- `storage.tf`: the reference-data account, file share and read-only environment mount.
- `outputs.tf`: values Terraform shows after deployment.

We use AzureRM 4.x for infrastructure, AzureAD 3.x for Entra registrations, AzAPI
2.x for Container Apps authentication and the time provider for credential rotation.
Commit `.terraform.lock.hcl` after initialization to record exact provider versions
and checksums. Modules will be introduced
when we have reusable infrastructure; this first step needs none.

## Local validation

Install Terraform using https://developer.hashicorp.com/terraform/install
and Azure CLI using https://learn.microsoft.com/cli/azure/install-azure-cli.
The Azure CLI is needed for login and planning, not for these local checks:

```bash
terraform -chdir=terraform/environments/dev init -backend=false
terraform -chdir=terraform/environments/dev fmt -check
terraform -chdir=terraform/environments/dev validate
```

`init` downloads the provider. `fmt` checks formatting. `validate` checks the
configuration against the provider's schema. None of these create Azure resources.

## Everyday workflow

Edit the `.tf` files, then run:

```bash
terraform -chdir=terraform/environments/dev apply
```

Terraform refreshes state and shows a fresh plan. Review it, then type `yes` if
the changes are expected. `No changes` means Azure already matches the
configuration; there is nothing to approve or deploy. Uploading files into a
share is a separate operation from creating that share.

Saved plans are optional. They are useful when you want to apply the exact plan
reviewed earlier, for example in CI. Commit `.tf` files and `.terraform.lock.hcl`;
keep `.terraform/`, `*.tfplan` and Terraform state out of Git.

## Saved plans after a successful apply

A saved plan belongs to the Terraform state snapshot used when it was generated.
A successful apply updates state, so applying that same file again reports
`Saved plan is stale`. The first successful deployment is still intact.
Generate a fresh plan to check the current deployment:

```bash
terraform -chdir=terraform/environments/dev plan
```

If it reports `No changes`, no apply is needed. For a later configuration change,
use interactive `apply` or generate and review a new saved plan.

## Next step: inspect an Azure plan

Once the tools are installed, authenticate interactively and select the subscription:

```bash
az login
az account list --output table
az account set --subscription "YOUR_SUBSCRIPTION_ID"
export ARM_SUBSCRIPTION_ID="$(az account show --query id --output tsv)"
terraform -chdir=terraform/environments/dev plan
```

Review the plan before applying. Once all the resources below are deployed,
a fresh plan should report `No changes`.
The AzureRM 4.x provider requires an explicit subscription ID; the environment
variable supplies it without embedding account details in the configuration.
Automatic resource-provider registration is disabled. Check that
`Microsoft.ContainerRegistry` is registered before creating the registry:

```bash
az provider show --namespace Microsoft.ContainerRegistry --query registrationState --output tsv
```

If it is not `Registered`, explicitly register it before applying:

```bash
az provider register --namespace Microsoft.ContainerRegistry --wait
```

This registration enables the Azure service in the selected subscription.
The registry itself is a paid resource once created. Basic is the starting
tier for this development workload. The shared registry admin account is
disabled; we will authenticate using Azure CLI and Azure roles.

The name starts with `acrswisstaxdev` and ends with eight characters derived
from the resource group's ID to reduce global name collisions. The suffix is
stable for this resource group.

To save and apply a reviewed registry plan:

```bash
terraform -chdir=terraform/environments/dev plan -out=registry.tfplan
terraform -chdir=terraform/environments/dev apply registry.tfplan
terraform -chdir=terraform/environments/dev output container_registry_name
terraform -chdir=terraform/environments/dev output container_registry_login_server
```

Creating a registry does not upload an image. Building and pushing the image
is the next step after creation.

Terraform now uses a private Azure Blob backend, authenticated through your Azure
CLI identity. The independent [bootstrap configuration](bootstrap/README.md)
manages its storage and has its own state blob. Existing local state was migrated
with resource records preserved. See [remote state](remote-state.md) for the
migration, backups and normal workflow. State and saved plans remain outside Git.

## Managed identity for image pulls

`id-swiss-tax-statement-pull-dev` is an Azure-managed application identity.
Azure manages its credentials. We will attach it to the Container App and use
it for registry authentication when adding the runtime.

The role assignment grants `AcrPull` at the registry's resource ID, allowing
image downloads from this registry without granting push or subscription-wide
permissions. The registry uses `LegacyRegistryPermissions`, where this role
applies. ARM audience authentication is explicitly enabled on the registry,
as required for Container Apps managed identity pulls.

Check that the managed identity service is registered:

```bash
az provider show --namespace Microsoft.ManagedIdentity --query registrationState --output tsv
```

If it is not `Registered`, run:

```bash
az provider register --namespace Microsoft.ManagedIdentity --wait
```

Save and review this step's plan:

```bash
terraform -chdir=terraform/environments/dev plan -out=identity.tfplan
terraform -chdir=terraform/environments/dev apply identity.tfplan
```

The account applying the plan needs permission to create role assignments at
the registry scope, such as Owner or Role Based Access Control Administrator.
Contributor alone cannot create this role assignment. New Azure role assignments
can take time to propagate; the actual managed identity image pull will be
verified when the Container App is deployed.

`registry_pull_identity_id` is the Azure resource ID used to attach the identity.
`registry_pull_identity_principal_id` identifies its Microsoft Entra principal
for permissions. These IDs serve different purposes; neither is a password.

Reference: https://learn.microsoft.com/azure/container-apps/managed-identity-image-pull

## First Container App runtime

This step creates three resources:

- `log-swiss-tax-statement-dev`: stores runtime logs with 30-day retention.
- `cae-swiss-tax-statement-dev`: hosts apps using a Consumption workload profile.
- `ca-swiss-tax-statement-api-dev`: runs the verified API image with the existing
  identity for registry pulls.

The API image is pinned by digest through `api_image_digest`. We start with one
replica, 0.5 vCPU and 1 GiB memory so the runtime remains available for CLI checks.
This incurs runtime charges while active; log ingestion is also metered.
Scale-to-zero will be configured when the access path is ready.

Ingress is internal to this Container Apps environment. Its hostname will not
serve the API to your laptop's browser. `/health` probes verify that the process
starts and responds; they do not assert that tax-processing data is installed.
Official Kursliste data is not mounted yet, so this step verifies startup and
managed identity image pulls. Statement processing in Azure is a later step.

Both Azure services below must be registered before applying:

```bash
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait
terraform -chdir=terraform/environments/dev plan -out=runtime.tfplan
terraform -chdir=terraform/environments/dev apply runtime.tfplan
```

Verify the deployed runtime:

```bash
az containerapp show --name ca-swiss-tax-statement-api-dev \
  --resource-group rg-swiss-tax-statement-dev \
  --query '{state:properties.provisioningState,revision:properties.latestReadyRevisionName}' \
  --output table
az containerapp logs show --name ca-swiss-tax-statement-api-dev \
  --resource-group rg-swiss-tax-statement-dev --type console --tail 20
```

Azure CLI may prompt to install its Container Apps extension. A ready revision
and passing health probes are the initial success criteria. Authentication and
persistent data provisioning will follow before real statements are processed.

## Persistent Kursliste storage

This step creates a Standard LRS storage account and a 5 GiB SMB file share for
public reference data. The Container App mounts it read-only at `/data/kursliste`.
The upstream reader prefers SQLite when both SQLite and XML are present; only
the converted database needs uploading. The storage account's authenticated
public network endpoint is needed for this environment without a custom VNet.

The Azure Files SMB mount uses a storage account key in the environment's storage
binding. Terraform marks the value sensitive but stores it in state and saved
plans. Those files are already ignored by Git; the next infrastructure step is
migrating state to a restricted Azure backend. No storage key is an output or a
literal in configuration. The managed identity continues to handle image pulls.

Deploy the storage configuration after reviewing the plan:

```bash
az provider register --namespace Microsoft.Storage --wait
terraform -chdir=terraform/environments/dev apply
```

An empty share does not make statement processing ready. After applying, upload
the official database downloaded during local setup:

```bash
kursliste_account=$(terraform -chdir=terraform/environments/dev output -raw reference_data_storage_account_name)
kursliste_md5=$(.venv/bin/python -c 'import base64,hashlib; f=open("data/kursliste/kursliste_2025.sqlite","rb"); print(base64.b64encode(hashlib.file_digest(f,"md5").digest()).decode())')

az storage file upload --account-name "$kursliste_account" \
  --share-name kursliste --source data/kursliste/kursliste_2025.sqlite \
  --path kursliste_2025.sqlite --auth-mode key \
  --content-md5 "$kursliste_md5" --validate-content --output none

az storage file show --account-name "$kursliste_account" \
  --share-name kursliste --path kursliste_2025.sqlite --auth-mode key \
  --query '{bytes:properties.contentLength,md5:properties.contentSettings.contentMd5}' \
  --output json
```

Azure CLI obtains the account key using your Azure login; the account needs
permission to list storage keys. The MD5 verifies transfer integrity, not source
authenticity. Record the official export metadata and a SHA-256 checksum for
release provenance. Future refreshes should upload to a versioned folder and
switch the app's data path only after verification; avoid overwriting a database
in use by the running app.

After upload, test synthetic XML inside the deployed container and confirm a
readable PDF, then compare realistic sanitized portfolio examples before claiming
tax-calculation correctness. Storage and transactions are metered Azure resources.

Reference: https://learn.microsoft.com/azure/container-apps/storage-mounts

## Authentication checkpoint

Entra sign-in and external HTTPS are deployed. Internal ingress requests and an
external `/docs` request returned 401 without authentication. The downloaded
browser-test PDF matches the synthetic fixture. See the
[authentication guide](../docs/authentication.md) for the access policy,
credential lifetime and browser verification steps. The ingress hostname output
is now `container_app_fqdn`; `api_url` supplies its external HTTPS URL.
