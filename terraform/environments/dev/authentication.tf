data "azuread_client_config" "current" {}

locals {
  api_app_name   = "ca-swiss-tax-statement-api-dev"
  api_public_url = "https://${local.api_app_name}.${azurerm_container_app_environment.platform.default_domain}"
}

resource "azuread_application" "api_login" {
  display_name            = "swiss-tax-statement-api-dev"
  sign_in_audience        = "AzureADMyOrg"
  owners                  = [data.azuread_client_config.current.object_id]
  prevent_duplicate_names = true

  web {
    homepage_url  = "${local.api_public_url}/docs"
    redirect_uris = ["${local.api_public_url}/.auth/login/aad/callback"]

    # Container Apps uses a hybrid OpenID Connect flow with a client secret.
    implicit_grant {
      id_token_issuance_enabled     = true
      access_token_issuance_enabled = false
    }
  }
}

resource "azuread_service_principal" "api_login" {
  client_id = azuread_application.api_login.client_id
  owners    = [data.azuread_client_config.current.object_id]
}

resource "time_rotating" "auth_secret" {
  rotation_days = 150
}

resource "azuread_application_password" "api_login" {
  application_id = azuread_application.api_login.id
  display_name   = "container-app-authentication"
  end_date       = timeadd(time_rotating.auth_secret.id, "4320h")

  lifecycle {
    create_before_destroy = true
  }
}

resource "azapi_resource" "api_auth" {
  type      = "Microsoft.App/containerApps/authConfigs@2025-07-01"
  name      = "current"
  parent_id = azurerm_container_app.api.id

  body = {
    properties = {
      platform = { enabled = true }
      globalValidation = {
        unauthenticatedClientAction = "Return401"
      }
      httpSettings = { requireHttps = true }
      identityProviders = {
        azureActiveDirectory = {
          enabled = true
          registration = {
            clientId                = azuread_application.api_login.client_id
            clientSecretSettingName = "entra-client-secret"
            openIdIssuer            = "https://login.microsoftonline.com/${data.azuread_client_config.current.tenant_id}/v2.0"
          }
          login = { loginParameters = ["scope=openid profile email"] }
          validation = {
            allowedAudiences = [azuread_application.api_login.client_id]
            defaultAuthorizationPolicy = {
              allowedPrincipals = {
                identities = sort(tolist(var.allowed_user_object_ids))
              }
            }
          }
        }
      }
      login = {
        tokenStore = { enabled = false }
      }
    }
  }

  response_export_values = []
  depends_on             = [azuread_service_principal.api_login]
}
