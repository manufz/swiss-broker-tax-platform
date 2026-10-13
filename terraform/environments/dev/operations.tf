resource "azurerm_consumption_budget_resource_group" "platform" {
  name              = "budget-swiss-tax-statement-dev"
  resource_group_id = azurerm_resource_group.platform.id
  amount            = var.monthly_budget
  time_grain        = "Monthly"

  time_period {
    start_date = var.budget_start_date
  }

  dynamic "notification" {
    for_each = toset([80, 100])
    content {
      enabled        = true
      threshold      = notification.value
      operator       = "GreaterThanOrEqualTo"
      threshold_type = "Actual"
      contact_roles  = ["Owner"]
      contact_emails = var.notification_email == null ? [] : [var.notification_email]
    }
  }
}

resource "azurerm_monitor_action_group" "operations" {
  name                = "ag-swiss-tax-statement-dev"
  resource_group_name = azurerm_resource_group.platform.name
  short_name          = "swisstaxdev"
  dynamic "email_receiver" {
    for_each = var.notification_email == null ? [] : [var.notification_email]
    content {
      name          = "developer"
      email_address = email_receiver.value
    }
  }
  dynamic "arm_role_receiver" {
    for_each = var.notification_email == null ? [1] : []
    content {
      name                    = "subscription-owner"
      role_id                 = "8e3af657-a8ff-443c-a75c-2fe8c4bcb635"
      use_common_alert_schema = true
    }
  }
}

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "processing_failures" {
  name                    = "alert-swiss-tax-processing-dev"
  resource_group_name     = azurerm_resource_group.platform.name
  location                = azurerm_resource_group.platform.location
  scopes                  = [azurerm_log_analytics_workspace.platform.id]
  evaluation_frequency    = "PT5M"
  window_duration         = "PT15M"
  severity                = 2
  description             = "At least three engine/server failures in fifteen minutes; inspect status-only logs and reference-data readiness."
  auto_mitigation_enabled = true

  criteria {
    query                   = <<-KQL
      ContainerAppConsoleLogs_CL
      | where ContainerAppName_s == "${local.api_app_name}"
      | where Log_s matches regex @"statement_processing status=5[0-9]{2} duration_ms="
      | project TimeGenerated
    KQL
    time_aggregation_method = "Count"
    operator                = "GreaterThanOrEqual"
    threshold               = 3
    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.operations.id]
  }
}
