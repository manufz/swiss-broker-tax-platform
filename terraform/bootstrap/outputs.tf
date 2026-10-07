output "state_resource_group_name" {
  description = "Resource group that holds Terraform state storage."
  value       = azurerm_resource_group.state.name
}

output "state_storage_account_name" {
  description = "Storage account to use in the AzureRM backend configuration."
  value       = azurerm_storage_account.state.name
}

output "state_container_name" {
  description = "Private blob container for Terraform state."
  value       = azurerm_storage_container.state.name
}
