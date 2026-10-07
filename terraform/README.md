# Terraform: first development environment

This step declares one Azure resource group, `rg-swiss-tax-statement-dev`,
in `switzerlandnorth`. A resource group holds related Azure resources; the API,
registry, and storage will be added in later steps.

## Files

All `.tf` files in `environments/dev/` form one Terraform configuration.
Splitting them by purpose helps us read them; file names do not control order.

- `versions.tf`: Terraform and AzureRM provider version constraints.
- `providers.tf`: configures the provider that communicates with Azure.
- `variables.tf`: inputs, starting with the Azure region.
- `main.tf`: the resource we want Terraform to manage.
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

Review the plan before applying. We expect one resource group to be added.
The AzureRM 4.x provider requires an explicit subscription ID; the environment
variable supplies it without embedding account details in the configuration.
Automatic resource-provider registration is disabled for this resource-group-only
step. When adding services later, we will register the providers those services need.

Terraform currently uses local state in this directory. State and plan files
are ignored by Git. A remote backend will be a separate step before CI/CD.
