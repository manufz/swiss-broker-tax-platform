variable "location" {
  description = "Azure region for the development resource group."
  type        = string
  default     = "switzerlandnorth"
}

variable "api_image_digest" {
  description = "Verified registry digest of the API image to deploy."
  type        = string
  default     = "sha256:1185602b5e73048c2ef42396900feeee34a03ec7f81cd1b146e061219d11afc1"

  validation {
    condition     = can(regex("^sha256:[0-9a-f]{64}$", var.api_image_digest))
    error_message = "Use a sha256 digest with 64 lowercase hexadecimal characters."
  }
}

variable "allowed_user_object_ids" {
  description = "Microsoft Entra user object IDs allowed to access the development API."
  type        = set(string)

  validation {
    condition = length(var.allowed_user_object_ids) > 0 && alltrue([
      for id in var.allowed_user_object_ids : can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", id))
    ])
    error_message = "Provide at least one valid Entra user object ID."
  }
}
