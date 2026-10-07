resource "azurerm_resource_group" "platform" {
  name     = "rg-swiss-tax-statement-dev"
  location = var.location

  tags = {
    project     = "swiss-broker-tax-platform"
    environment = "dev"
    managed_by  = "terraform"
  }
}
