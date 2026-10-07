resource "azurerm_log_analytics_workspace" "platform" {
  name                = "log-swiss-tax-statement-dev"
  resource_group_name = azurerm_resource_group.platform.name
  location            = azurerm_resource_group.platform.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = azurerm_resource_group.platform.tags
}

resource "azurerm_container_app_environment" "platform" {
  name                       = "cae-swiss-tax-statement-dev"
  resource_group_name        = azurerm_resource_group.platform.name
  location                   = azurerm_resource_group.platform.location
  logs_destination           = "log-analytics"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.platform.id
  tags                       = azurerm_resource_group.platform.tags

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
}

resource "azurerm_container_app" "api" {
  name                         = "ca-swiss-tax-statement-api-dev"
  resource_group_name          = azurerm_resource_group.platform.name
  container_app_environment_id = azurerm_container_app_environment.platform.id
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = azurerm_resource_group.platform.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.registry_pull.id]
  }

  registry {
    server   = azurerm_container_registry.api.login_server
    identity = azurerm_user_assigned_identity.registry_pull.id
  }

  ingress {
    external_enabled           = false
    allow_insecure_connections = false
    target_port                = 8000
    transport                  = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    # Keep one replica available for the first runtime checks via Azure CLI.
    min_replicas = 1
    max_replicas = 1

    volume {
      name         = "kursliste"
      storage_name = azurerm_container_app_environment_storage.kursliste.name
      storage_type = "AzureFile"
    }

    container {
      name   = "api"
      image  = "${azurerm_container_registry.api.login_server}/swiss-tax-statement-api@${var.api_image_digest}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "KURSLISTE_DIR"
        value = "/data/kursliste"
      }

      volume_mounts {
        name = "kursliste"
        path = "/data/kursliste"
      }

      startup_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/health"
        interval_seconds        = 5
        failure_count_threshold = 30
        timeout                 = 2
      }

      liveness_probe {
        transport        = "HTTP"
        port             = 8000
        path             = "/health"
        interval_seconds = 30
        timeout          = 2
      }

      readiness_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/health"
        interval_seconds        = 10
        success_count_threshold = 1
        timeout                 = 2
      }
    }
  }

  depends_on = [azurerm_role_assignment.registry_pull]
}
