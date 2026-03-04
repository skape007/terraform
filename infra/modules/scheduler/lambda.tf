resource "aws_lambda_function" "scheduler" {
  function_name = local.scheduler_lambda_name
  runtime       = var.lambda_runtime
  handler       = "lambda_handler.lambda_handler"
  role          = aws_iam_role.lambda.arn

  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size

  s3_bucket = var.code_s3_bucket
  s3_key    = var.scheduler_code_s3_key

  layers = [aws_lambda_layer_version.shared.arn]

  environment {
    variables = {
      SCHEDULE_TABLE  = aws_dynamodb_table.schedule.name
      GSI1_INDEX_NAME = var.schedule_table_gsi_name
      GSI1_HASH_KEY   = var.schedule_table_gsi_hash_key

      SCHEDULE_BUCKET = aws_s3_bucket.job_bucket.bucket
      ACTIVE_PREFIX   = var.active_prefix
      DELETED_PREFIX  = var.deleted_prefix
      CATALOG_KEY     = var.catalog_key

      SES_SENDER    = var.ses_sender
      AZURE_PAT     = var.azure_pat_encrypted
      AZURE_ORG     = var.azure_org
      AZURE_PROJECT = var.default_azure_project

      NOTIFY_FALLBACK_RECIPIENT = var.notify_fallback_recipient
      NOTIFY_ONLY_ENABLED       = tostring(var.notify_only_enabled)
      REQUIRE_DELETE_CONFIRM    = tostring(var.require_delete_confirm)
      ENFORCE_VERSION_STEP      = tostring(var.enforce_version_step)
    }
  }
}

resource "aws_lambda_function" "sync" {
  function_name = local.sync_lambda_name
  runtime       = var.lambda_runtime
  handler       = "lambda_handler.lambda_handler"
  role          = aws_iam_role.lambda.arn

  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size

  s3_bucket = var.code_s3_bucket
  s3_key    = var.sync_code_s3_key

  layers = [aws_lambda_layer_version.shared.arn]

  environment {
    variables = {
      SES_SENDER    = var.ses_sender
      AZURE_PAT     = var.azure_pat_encrypted
      AZURE_ORG     = var.azure_org
      AZURE_PROJECT = var.default_azure_project

      LOG_LEVEL      = var.log_level
      TARGET_PROJECT = var.target_project
    }
  }
}

resource "aws_lambda_function_url" "sync" {
  function_name      = aws_lambda_function.sync.function_name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "sync_url" {
  statement_id           = "FunctionUrlAllowPublicAccess"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.sync.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}
