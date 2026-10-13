resource "azuread_application" "github_release" {
  count        = var.github_oidc_subject == null ? 0 : 1
  display_name = "swiss-tax-github-release-dev"
  owners       = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal" "github_release" {
  count     = var.github_oidc_subject == null ? 0 : 1
  client_id = azuread_application.github_release[0].client_id
  owners    = [data.azuread_client_config.current.object_id]
}

resource "azuread_application_federated_identity_credential" "github_release" {
  count          = var.github_oidc_subject == null ? 0 : 1
  application_id = azuread_application.github_release[0].id
  display_name   = "github-azure-dev"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = var.github_oidc_subject
}

resource "azurerm_role_assignment" "github_push" {
  count                = var.github_oidc_subject == null ? 0 : 1
  scope                = azurerm_container_registry.api.id
  role_definition_name = "AcrPush"
  principal_id         = azuread_service_principal.github_release[0].object_id
}

resource "azurerm_role_assignment" "github_deploy" {
  count                = var.github_oidc_subject == null ? 0 : 1
  scope                = azurerm_container_app.api.id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.github_release[0].object_id
}

resource "azurerm_role_assignment" "github_registry_read" {
  count                = var.github_oidc_subject == null ? 0 : 1
  scope                = azurerm_container_registry.api.id
  role_definition_name = "Reader"
  principal_id         = azuread_service_principal.github_release[0].object_id
}

resource "azurerm_role_assignment" "github_identity_assign" {
  count                = var.github_oidc_subject == null ? 0 : 1
  scope                = azurerm_user_assigned_identity.registry_pull.id
  role_definition_name = "Managed Identity Operator"
  principal_id         = azuread_service_principal.github_release[0].object_id
}
