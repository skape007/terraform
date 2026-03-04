output "job_bucket_name" {
  value       = module.automations.job_bucket_name
  description = "S3 bucket where job configs are stored"
}

output "schedule_table_name" {
  value       = module.automations.schedule_table_name
  description = "DynamoDB table for scheduled jobs"
}

output "schedule_table_arn" {
  value       = module.automations.schedule_table_arn
  description = "ARN of the DynamoDB table"
}

output "scheduler_lambda_name" {
  value       = module.automations.scheduler_lambda_name
  description = "Scheduler Lambda function name"
}

output "sync_lambda_name" {
  value       = module.automations.sync_lambda_name
  description = "Sync Lambda function name"
}

output "sync_lambda_url" {
  value       = module.automations.sync_lambda_url
  description = "Function URL for sync Lambda"
}

output "html_cloudfront_domain" {
  value       = module.automations.html_cloudfront_domain
  description = "CloudFront domain for the static HTML site"
}

output "html_url" {
  value       = module.automations.html_url
  description = "HTTPS URL for the static HTML site"
}
