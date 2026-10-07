resource "azurerm_storage_account" "reference_data" {
  name                     = "stswisstaxdev${substr(sha256(azurerm_resource_group.platform.id), 0, 8)}"
  resource_group_name      = azurerm_resource_group.platform.name
  location                 = azurerm_resource_group.platform.location
  account_kind             = "StorageV2"
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = true
  https_traffic_only_enabled      = true
  tags                            = azurerm_resource_group.platform.tags
}

resource "azurerm_storage_share" "kursliste" {
  name               = "kursliste"
  storage_account_id = azurerm_storage_account.reference_data.id
  quota              = 5
  access_tier        = "TransactionOptimized"
  enabled_protocol   = "SMB"
}

resource "azurerm_container_app_environment_storage" "kursliste" {
  name                         = "kursliste"
  container_app_environment_id = azurerm_container_app_environment.platform.id
  account_name                 = azurerm_storage_account.reference_data.name
  share_name                   = azurerm_storage_share.kursliste.name
  access_key                   = azurerm_storage_account.reference_data.primary_access_key
  access_mode                  = "ReadOnly"
}
