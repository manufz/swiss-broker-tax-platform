# Bootstrap Terraform state storage

This independent Terraform root creates the storage needed before the application
configuration can use a remote backend. Keeping it in a separate resource group
also keeps state storage outside the application's normal cleanup lifecycle.

It creates four resources:

- `rg-swiss-tax-state-dev` in Switzerland North.
- A Standard LRS Blob storage account with a stable subscription-derived suffix.
- A private `tfstate` container.
- `Storage Blob Data Contributor` for the applying Azure identity, scoped to that
  container. Run this bootstrap using the same Azure user on subsequent applies.
  CI deployment identities use separate role assignments.

Anonymous blob access and Shared Key authentication are disabled. The HTTPS
endpoint is reachable from your laptop; access requires Microsoft Entra identity
authentication and a role assignment. This setup does not use a private endpoint
or IP firewall. Blob versioning and seven-day blob/container soft deletion provide
recovery options. Storage and retained versions are metered.

The bootstrap provider uses Resource Manager APIs for storage creation and skips
legacy queue/static-website data-plane reads. This avoids requiring blob access
before the container and its role assignment exist. Backend blob authentication
uses Microsoft Entra through the Azure CLI, independently of resource creation.

`prevent_destroy` blocks planned deletion or replacement of the resource group,
account and container while those resource blocks remain in configuration. It is
a Terraform guard, not an Azure resource lock; it does not protect manual deletion
or removal of those resource blocks.

## Create state storage

For a new subscription, prepare a private copy of this root without `backend.tf`,
as described in the [deployment guide](../README.md#deploy-in-a-different-azure-subscription).
Run the initial storage creation from that working copy using the authorized
Azure CLI login and subscription:

```bash
export ARM_SUBSCRIPTION_ID="$(az account show --query id --output tsv)"
terraform init
terraform plan
terraform apply
```

Review the fresh plan before typing `yes`. The first apply should show
`4 to add, 0 to change, 0 to destroy`. The applying identity needs permission to
create resources and role assignments. Register `Microsoft.Storage` before
creating the storage resources.

For an existing deployment, the committed configuration connects to its backend
during `terraform -chdir=terraform/bootstrap init`. Review a normal plan before
applying changes; do not create fresh local state for existing resources.
Commit the `.tf` files and this root's `.terraform.lock.hcl`. State stays out of Git.

## Backend migration

Both roots use the `azurerm` backend with
`use_azuread_auth = true` and `use_cli = true`, and separate blob keys:
`dev.terraform.tfstate` for application state and `bootstrap.terraform.tfstate`
for this root's state. Verify state locking and release any diagnostic lease
afterward. See the
[remote-state guide](../remote-state.md) for backups and verification details.

Migration must preserve resource records, outputs, lineages and resource addresses. Use
`terraform init -migrate-state` after adding each backend block, then check that
both plans report no changes. Back up the local files into an ignored directory
before migration. Do not use `-reconfigure` as a substitute for migrating local
state, or create a fresh empty application state.

Azure role assignments can take time to propagate. If newly assigned blob access
returns 403, wait and retry with the same login.

References: [AzureRM backend authentication and locking](https://developer.hashicorp.com/terraform/language/backend/azurerm),
[AzureRM storage container management API](https://github.com/hashicorp/terraform-provider-azurerm/blob/v4.81.0/website/docs/r/storage_container.html.markdown).
