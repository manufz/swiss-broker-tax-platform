locals {
  # Registry names must be globally unique and contain only letters and numbers.
  registry_name = "acrswisstaxdev${substr(sha256(azurerm_resource_group.platform.id), 0, 8)}"
}

resource "azurerm_container_registry" "api" {
  name                = local.registry_name
  resource_group_name = azurerm_resource_group.platform.name
  location            = azurerm_resource_group.platform.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = azurerm_resource_group.platform.tags

  # Required for Container Apps to authenticate image pulls with managed identity.
  azuread_authentication_as_arm_policy_enabled = true
}
