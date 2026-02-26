resource "aws_s3_bucket" "job_bucket" {
  bucket = local.job_bucket_name

  versioning {
    enabled = true
  }
}

