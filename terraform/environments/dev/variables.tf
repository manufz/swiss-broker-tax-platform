variable "location" {
  description = "Azure region for the development resource group."
  type        = string
  default     = "switzerlandnorth"
}

variable "min_replicas" {
  description = "Keep zero replicas when idle; set one temporarily for CLI diagnostics."
  type        = number
  default     = 0
  validation {
    condition     = contains([0, 1], var.min_replicas)
    error_message = "Use zero for the portfolio deployment or one for diagnostics."
  }
}

variable "readiness_probe_path" {
  description = "Use /ready for current images; /health only for older images during rollback."
  type        = string
  default     = "/ready"
  validation {
    condition     = contains(["/ready", "/health"], var.readiness_probe_path)
    error_message = "Use a supported application readiness endpoint."
  }
}

variable "kursliste_directory" {
  description = "Read-only mounted data directory; use /data/kursliste/releases/<release-id> for immutable releases."
  type        = string
  default     = "/data/kursliste/releases/2025-77a29260f56c"
  validation {
    condition     = startswith(var.kursliste_directory, "/data/kursliste") && !strcontains(var.kursliste_directory, "..")
    error_message = "Select a directory inside the Kursliste mount."
  }
}

variable "notification_email" {
  description = "Optional operations email address; configure privately using TF_VAR_notification_email."
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
  validation {
    condition     = var.notification_email == null ? true : can(regex("^[^@ ]+@[^@ ]+\\.[^@ ]+$", var.notification_email))
    error_message = "Use a valid email address or null."
  }
}

variable "monthly_budget" {
  description = "Monthly resource-group notification budget in Azure billing currency; not a spending cap."
  type        = number
  default     = 25
  validation {
    condition     = var.monthly_budget > 0
    error_message = "Provide a positive budget amount."
  }
}

variable "budget_start_date" {
  description = "Stable first day of a billing month; change only when creating a new budget."
  type        = string
  default     = "2026-10-01T00:00:00Z"
}

variable "github_oidc_subject" {
  description = "Exact GitHub OIDC sub for the azure-dev environment; null until the repository exists."
  type        = string
  default     = null
  validation {
    condition     = var.github_oidc_subject == null ? true : can(regex("^repo:[^:]+:environment:azure-dev$", var.github_oidc_subject))
    error_message = "Copy the repository's exact azure-dev environment subject; do not allow pull requests."
  }
}

variable "api_image_digest" {
  description = "Verified registry digest of the API image to deploy."
  type        = string
  default     = "sha256:0d1548239d65cbe4fdd785f1365a7213c9abca3086fa038dd0d15f3a44e2d1f9"

  validation {
    condition     = can(regex("^sha256:[0-9a-f]{64}$", var.api_image_digest))
    error_message = "Use a sha256 digest with 64 lowercase hexadecimal characters."
  }
}

variable "allowed_user_object_ids" {
  description = "Microsoft Entra user object IDs allowed to access the development API."
  type        = set(string)
  nullable    = false

  validation {
    condition = length(var.allowed_user_object_ids) > 0 && alltrue([
      for id in var.allowed_user_object_ids : can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", id))
    ])
    error_message = "Provide at least one valid Entra user object ID."
  }
}
