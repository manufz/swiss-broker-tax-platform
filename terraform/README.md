# Terraform: development environment

The configuration declares the resource group `rg-swiss-tax-statement-dev`
in `switzerlandnorth`, a Basic Azure Container Registry for the API image,
and a user-assigned managed identity with `AcrPull` on that registry.
The API runtime and storage will be added in later steps.

## Files

All `.tf` files in `environments/dev/` form one Terraform configuration.
Splitting them by purpose helps us read them; file names do not control order.

- `versions.tf`: Terraform and AzureRM provider version constraints.
- `providers.tf`: configures the provider that communicates with Azure.
- `variables.tf`: inputs, starting with the Azure region.
- `main.tf`: the resource we want Terraform to manage.
- `registry.tf`: the image registry and its deterministic name suffix.
- `identity.tf`: the managed identity and its registry-scoped pull permission.
- `outputs.tf`: values Terraform shows after deployment.

We use the AzureRM 4.x series. Commit `.terraform.lock.hcl` after initialization
to record the exact provider version and checksums. Modules will be introduced
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

## Next step: inspect an Azure plan

Once the tools are installed, authenticate interactively and select the subscription:

```bash
az login
az account list --output table
az account set --subscription "YOUR_SUBSCRIPTION_ID"
export ARM_SUBSCRIPTION_ID="$(az account show --query id --output tsv)"
terraform -chdir=terraform/environments/dev plan
```

Review the plan before applying. From the existing registry checkpoint,
we expect one managed identity and one role assignment to be added. The existing
resource group and registry should remain unchanged.
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

Terraform currently uses local state in this directory. State and plan files
are ignored by Git. A remote backend will be a separate step before CI/CD.

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
