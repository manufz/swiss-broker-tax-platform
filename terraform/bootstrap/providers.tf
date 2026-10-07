provider "azurerm" {
  resource_provider_registrations = "none"
  storage_use_azuread             = true
  features {
    storage {
      # Bootstrap uses Resource Manager APIs; no queue or static website reads.
      data_plane_available = false
    }
  }
}
