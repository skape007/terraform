variable "stack_name" { type = string }

variable "schedule_table_gsi_name" { type = string }
variable "schedule_table_gsi_hash_key" { type = string }
variable "schedule_table_hash_key" { type = string }
variable "schedule_table_billing_mode" { type = string }

variable "log_level" { type = string }
variable "lambda_timeout" { type = number }
variable "lambda_memory_size" { type = number }
variable "lambda_runtime" { type = string }

variable "catalog_key" { type = string }
variable "deleted_prefix" { type = string }
variable "active_prefix" { type = string }
variable "html_prefix" {
  type    = string
  default = "html"
}

variable "s3_template_bucket_prefix" { type = string }
variable "s3_template_bucket_name" { type = string }

variable "target_project" { type = string }

variable "enforce_version_step" { type = bool }
variable "require_delete_confirm" { type = bool }
variable "notify_only_enabled" { type = bool }
variable "notify_fallback_recipient" { type = string }

variable "default_azure_project" { type = string }
variable "azure_org" { type = string }
variable "azure_pat_encrypted" {
  type        = string
  description = "Azure DevOps PAT — read from SSM at plan time and injected via -var in buildspec. Do not set in tfvars."
  default     = ""
  sensitive   = true
}
variable "ses_sender" { type = string }

variable "code_s3_bucket" { type = string }

variable "scheduler_code_s3_key" { type = string }
variable "sync_code_s3_key" { type = string }
variable "layer_s3_key" { type = string }
