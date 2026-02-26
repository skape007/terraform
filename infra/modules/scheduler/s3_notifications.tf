resource "aws_lambda_permission" "s3_invoke" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scheduler.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.job_bucket.arn
}

resource "aws_s3_bucket_notification" "job_bucket" {
  bucket = aws_s3_bucket.job_bucket.id

  depends_on = [aws_lambda_permission.s3_invoke]

  lambda_function {
    lambda_function_arn = aws_lambda_function.scheduler.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = var.active_prefix
  }

  lambda_function {
    lambda_function_arn = aws_lambda_function.scheduler.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = var.deleted_prefix
  }
}

