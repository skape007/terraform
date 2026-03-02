resource "aws_s3_bucket" "job_bucket" {
  bucket = local.job_bucket_name
}

resource "aws_s3_bucket_versioning" "job_bucket" {
  bucket = aws_s3_bucket.job_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

