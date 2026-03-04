resource "aws_lambda_layer_version" "shared" {
  layer_name = local.layer_name

  compatible_runtimes = [
    "python3.11",
    "python3.12",
    "python3.13",
  ]

  s3_bucket = var.s3_template_bucket_name
  s3_key    = local.layer_s3_key

  description = "AzureDevOps layer shared tools"
}

