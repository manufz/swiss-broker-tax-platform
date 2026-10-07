variable "location" {
  description = "Azure region for the development resource group."
  type        = string
  default     = "switzerlandnorth"
}

variable "api_image_digest" {
  description = "Verified registry digest of the API image to deploy."
  type        = string
  default     = "sha256:dd43bea8b6f9a71fc77a901e14cdaab32d0651d3ec615b3834103e5a7778dc67"

  validation {
    condition     = can(regex("^sha256:[0-9a-f]{64}$", var.api_image_digest))
    error_message = "Use a sha256 digest with 64 lowercase hexadecimal characters."
  }
}
