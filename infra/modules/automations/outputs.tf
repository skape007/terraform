output "job_bucket_name" {
  value = aws_s3_bucket.job_bucket.bucket
}

output "schedule_table_name" {
  value = aws_dynamodb_table.schedule.name
}

output "schedule_table_arn" {
  value = aws_dynamodb_table.schedule.arn
}

output "scheduler_lambda_name" {
  value = aws_lambda_function.scheduler.function_name
}

output "sync_lambda_name" {
  value = aws_lambda_function.sync.function_name
}

output "sync_lambda_url" {
  value = aws_lambda_function_url.sync.function_url
}

output "html_cloudfront_domain" {
  value = aws_cloudfront_distribution.html_cdn.domain_name
}

output "html_url" {
  value = "https://${aws_cloudfront_distribution.html_cdn.domain_name}/"
}
