resource "azurerm_user_assigned_identity" "registry_pull" {
  name                = "id-swiss-tax-statement-pull-dev"
  resource_group_name = azurerm_resource_group.platform.name
  location            = azurerm_resource_group.platform.location
  tags                = azurerm_resource_group.platform.tags
}

resource "azurerm_role_assignment" "registry_pull" {
  scope                = azurerm_container_registry.api.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.registry_pull.principal_id
  principal_type       = "ServicePrincipal"

  # A newly created identity may not yet be visible in Microsoft Entra's directory.
  skip_service_principal_aad_check = true
}
