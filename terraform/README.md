# Terraform: development environment

The configuration declares the resource group `rg-swiss-tax-statement-dev`
in `switzerlandnorth` and a Basic Azure Container Registry for the API image.
The API runtime and storage will be added in later steps.

## Files

All `.tf` files in `environments/dev/` form one Terraform configuration.
Splitting them by purpose helps us read them; file names do not control order.

- `versions.tf`: Terraform and AzureRM provider version constraints.
- `providers.tf`: configures the provider that communicates with Azure.
- `variables.tf`: inputs, starting with the Azure region.
- `main.tf`: the resource we want Terraform to manage.
- `registry.tf`: the image registry and its deterministic name suffix.
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

Review the plan before applying. From the existing resource-group checkpoint,
we expect one registry to be added and the resource group to remain unchanged.
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
