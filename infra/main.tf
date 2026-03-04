module "automations" {
  source = "./modules/automations"

  stack_name = var.stack_name

  code_s3_bucket        = var.code_s3_bucket
  scheduler_code_s3_key = var.scheduler_code_s3_key
  sync_code_s3_key      = var.sync_code_s3_key
  layer_s3_key          = var.layer_s3_key

  azure_pat_encrypted   = var.azure_pat_encrypted
  ses_sender            = var.ses_sender
  azure_org             = var.azure_org
  default_azure_project = var.default_azure_project

  notify_fallback_recipient = var.notify_fallback_recipient
  notify_only_enabled       = var.notify_only_enabled
  require_delete_confirm    = var.require_delete_confirm
  enforce_version_step      = var.enforce_version_step

  target_project = var.target_project

  s3_template_bucket_name   = var.s3_template_bucket_name
  s3_template_bucket_prefix = var.s3_template_bucket_prefix

  active_prefix  = var.active_prefix
  deleted_prefix = var.deleted_prefix
  catalog_key    = var.catalog_key

  html_prefix = var.html_prefix

  lambda_runtime     = var.lambda_runtime
  lambda_memory_size = var.lambda_memory_size
  lambda_timeout     = var.lambda_timeout
  log_level          = var.log_level

  schedule_table_billing_mode = var.schedule_table_billing_mode
  schedule_table_hash_key     = var.schedule_table_hash_key
  schedule_table_gsi_hash_key = var.schedule_table_gsi_hash_key
  schedule_table_gsi_name     = var.schedule_table_gsi_name
}
