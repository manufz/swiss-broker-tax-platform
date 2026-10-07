output "resource_group_name" {
  description = "Name of the development resource group."
  value       = azurerm_resource_group.platform.name
}

output "resource_group_id" {
  description = "Azure resource ID of the development resource group."
  value       = azurerm_resource_group.platform.id
}

output "container_registry_name" {
  description = "Registry name used by az acr login."
  value       = azurerm_container_registry.api.name
}

output "container_registry_login_server" {
  description = "Registry hostname used to tag and push Docker images."
  value       = azurerm_container_registry.api.login_server
}

output "registry_pull_identity_id" {
  description = "Managed identity resource ID to attach to the future Container App."
  value       = azurerm_user_assigned_identity.registry_pull.id
}

output "registry_pull_identity_principal_id" {
  description = "Microsoft Entra principal ID granted AcrPull on the registry."
  value       = azurerm_user_assigned_identity.registry_pull.principal_id
}
