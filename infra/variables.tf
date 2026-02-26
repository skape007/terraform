variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "stack_name" {
  description = "Name prefix used for resources (equivalent to StackName)"
  type        = string
}

variable "code_s3_bucket" {
  description = "Bucket containing the Lambda deployment package zip"
  type        = string
}

variable "scheduler_code_s3_key" {
  description = "S3 key to the scheduler Lambda deployment package zip"
  type        = string
}

variable "sync_code_s3_key" {
  description = "S3 key to the sync Lambda deployment package zip"
  type        = string
}

variable "azure_pat" {
  description = "Azure DevOps PAT"
  type        = string
  sensitive   = true
}

variable "ses_sender" {
  description = "Verified SES sender email"
  type        = string
}

variable "azure_org" {
  description = "Azure DevOps org"
  type        = string
  default     = "onenetcloud"
}

variable "default_azure_project" {
  description = "Default Azure DevOps project"
  type        = string
  default     = "DEP"
}

variable "notify_fallback_recipient" {
  description = "Fallback recipient for notifications"
  type        = string
  default     = "ops-team@example.com"
}

variable "notify_only_enabled" {
  description = "Whether to notify only enabled jobs"
  type        = bool
  default     = false
}

variable "require_delete_confirm" {
  description = "Require delete confirm"
  type        = bool
  default     = false
}

variable "enforce_version_step" {
  description = "Enforce version step"
  type        = bool
  default     = false
}

variable "target_project" {
  description = "Target Azure DevOps project for sync operations"
  type        = string
  default     = "Demand-testing"
}

variable "s3_template_bucket_name" {
  description = "Bucket containing the Lambda layer zip"
  type        = string
}

variable "s3_template_bucket_prefix" {
  description = "Prefix for the Lambda layer zip"
  type        = string
  default     = "layers"
}

variable "active_prefix" {
  description = "S3 prefix for active job files"
  type        = string
  default     = "jobs/active/"
}

variable "deleted_prefix" {
  description = "S3 prefix for deleted job files"
  type        = string
  default     = "jobs/deleted/"
}

variable "catalog_key" {
  description = "S3 key for job catalog file"
  type        = string
  default     = "jobs/catalog.json"
}

variable "html_prefix" {
  description = "S3 prefix for static HTML assets"
  type        = string
  default     = "html"
}

variable "lambda_runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.12"
}

variable "lambda_memory_size" {
  description = "Lambda memory size"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Lambda timeout"
  type        = number
  default     = 900
}

variable "log_level" {
  description = "Log level"
  type        = string
  default     = "DEBUG"
}

variable "schedule_table_billing_mode" {
  description = "DynamoDB billing mode"
  type        = string
  default     = "PAY_PER_REQUEST"
}

variable "schedule_table_hash_key" {
  description = "DynamoDB hash key attribute name"
  type        = string
  default     = "id"
}

variable "schedule_table_gsi_hash_key" {
  description = "DynamoDB GSI hash key attribute name"
  type        = string
  default     = "time_slot"
}

variable "schedule_table_gsi_name" {
  description = "DynamoDB GSI name"
  type        = string
  default     = "GSI1"
}
