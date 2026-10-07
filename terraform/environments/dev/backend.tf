terraform {
  backend "azurerm" {
    storage_account_name = "stswisstfdev6f89f856"
    container_name       = "tfstate"
    key                  = "dev.terraform.tfstate"
    use_azuread_auth     = true
    use_cli              = true
  }
}
