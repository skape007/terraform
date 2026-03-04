resource "aws_cloudfront_origin_access_control" "html_oac" {
  name                              = "${var.stack_name}-html-oac"
  description                       = "OAC for S3 HTML origin"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "html_cdn" {
  enabled             = true
  default_root_object = "index.html"

  origin {
    domain_name              = aws_s3_bucket.job_bucket.bucket_regional_domain_name
    origin_id                = "${var.stack_name}-html-origin"
    origin_access_control_id = aws_cloudfront_origin_access_control.html_oac.id
    # No origin_path - serve from bucket root so index.html is accessible
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
    target_origin_id       = "${var.stack_name}-html-origin"
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

data "aws_iam_policy_document" "html_bucket_policy" {
  # Allow public read for UI assets and catalog
  statement {
    sid     = "PublicReadSite"
    effect  = "Allow"
    actions = ["s3:GetObject"]
    resources = [
      "${aws_s3_bucket.job_bucket.arn}/index.html",
      "${aws_s3_bucket.job_bucket.arn}/${var.html_prefix}/*",
      "${aws_s3_bucket.job_bucket.arn}/jobs/catalog.json",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
  }

  # Allow CloudFront OAC to read all objects
  statement {
    sid     = "AllowCloudFrontServicePrincipal"
    effect  = "Allow"
    actions = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.job_bucket.arn}/*"]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.html_cdn.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "html_bucket_policy" {
  bucket     = aws_s3_bucket.job_bucket.id
  policy     = data.aws_iam_policy_document.html_bucket_policy.json
  depends_on = [aws_s3_bucket_public_access_block.job_bucket]
}

