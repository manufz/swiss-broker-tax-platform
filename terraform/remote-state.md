# Remote Terraform state

Both Terraform roots now store state in the private `tfstate` container of
`stswisstfdev6f89f856`, in `rg-swiss-tax-state-dev` (Switzerland North).

| Terraform root | Blob key | Managed resources at migration |
| --- | --- | --- |
| `environments/dev` | `dev.terraform.tfstate` | 10 |
| `bootstrap` | `bootstrap.terraform.tfstate` | 4 |

Each root has its own state and lock. Bootstrap manages the state-storage
resources; development manages the application, registry and reference-data
storage. Deleting the application's resources does not include backend storage.

## Authentication and recovery

The backend uses `use_azuread_auth = true` and `use_cli = true`: your Azure CLI
login authenticates directly to Blob Storage. The bootstrap grants its applying
identity `Storage Blob Data Contributor` on the container. Anonymous blob access
and Shared Key authentication are disabled. The public HTTPS endpoint remains
reachable from your laptop; identity and role checks control access.

State contains sensitive infrastructure values, including the Azure Files mount
key. Backend names and blob keys in `.tf` files are configuration identifiers;
credentials are not embedded there. Never publish state or print its contents in
CI. Blob versioning and seven-day soft deletion provide recovery options; older
versions also contain sensitive values and incur storage charges.

## Migration performed

Before migration, the original development and bootstrap state files were copied
into `private/terraform-state-backups/20261007T130101692500Z/`, with owner-only
file permissions. That directory is ignored by Git. The backup includes a
manifest of lineages, serials and checksums. Retain it as a protected recovery
copy, not as a second active state.

After checking identity access and confirming that the destination was empty,
each root received its `backend.tf` and ran:

```bash
terraform -chdir=terraform/environments/dev init -migrate-state
terraform -chdir=terraform/bootstrap init -migrate-state
```

The migration prompts were answered `yes` to copy the existing states. Both
remote states were compared with their backups: all resource records, outputs
and lineages matched. State serials advanced from 16 to 17 for development and
5 to 6 for bootstrap. Serial changes record a state write; they do not mean that
Azure resources were redeployed.

The Azure backend acquires blob leases for state locking. A contention check
temporarily leased the development state blob: Terraform rejected a second
operation with `Error acquiring the state lock`. The diagnostic lease was then
released. Fresh plans for both roots returned exit code 0 and `No changes`,
verifying that migration preserved the managed infrastructure.

Use `-migrate-state` when moving an existing state to another backend.
`-reconfigure` updates backend settings without copying old state; it is not a
replacement for migration. Do not restore a local backup while continuing to
operate on remote state. Recovery should deliberately select one authoritative
state, preserve its lineage and check the resulting plan before an apply.

## Normal workflow

From this checkout, use the same Azure user that created the bootstrap:

```bash
export ARM_SUBSCRIPTION_ID="$(az account show --query id --output tsv)"
terraform -chdir=terraform/environments/dev plan
terraform -chdir=terraform/environments/dev apply
```

Review the fresh plan before approving an apply. Run commands in `bootstrap`
only when changing backend infrastructure or access. A new authorized checkout
uses ordinary `terraform init` in each root; it connects to the existing blobs.
The committed backend names target this development deployment. Creating a new
deployment requires bootstrapping its storage first, without a backend block,
then configuring its account name and migrating that local bootstrap state.

Keep default state locking enabled. On a lock error, check whether another
Terraform process is running and wait for it to finish. Do not force-unlock a
state used by an active process. Commit configuration and lock files; state,
saved plans, local recovery copies and `.terraform/` remain ignored.

References: [AzureRM backend authentication and locking](https://developer.hashicorp.com/terraform/language/backend/azurerm),
[Terraform state migration](https://developer.hashicorp.com/terraform/cli/commands/init#backend-initialization).
