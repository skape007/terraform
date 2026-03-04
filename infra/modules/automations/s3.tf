resource "aws_s3_bucket" "job_bucket" {
  bucket = local.job_bucket_name
}

resource "aws_s3_bucket_versioning" "job_bucket" {
  bucket = aws_s3_bucket.job_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "job_bucket" {
  bucket = aws_s3_bucket.job_bucket.id

  block_public_acls       = true
  block_public_policy     = false
  ignore_public_acls      = true
  restrict_public_buckets = false
}

