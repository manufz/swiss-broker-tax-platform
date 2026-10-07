output "resource_group_name" {
  description = "Name of the development resource group."
  value       = azurerm_resource_group.platform.name
}

output "resource_group_id" {
  description = "Azure resource ID of the development resource group."
  value       = azurerm_resource_group.platform.id
}
