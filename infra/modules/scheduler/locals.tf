locals {
  job_bucket_name       = "${var.stack_name}-schedule"
  schedule_table_name   = "${var.stack_name}-schedule-jobs"
  lambda_role_name      = "${var.stack_name}-lambda"
  scheduler_lambda_name = "${var.stack_name}-scheduler"
  sync_lambda_name      = "${var.stack_name}-sync"

  layer_name   = var.stack_name
  layer_s3_key = "${var.s3_template_bucket_prefix}/python_layer.zip"
}

