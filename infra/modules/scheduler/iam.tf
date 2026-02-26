data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "lambda" {
  name               = local.lambda_role_name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json

  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
  ]
}

data "aws_iam_policy_document" "lambda_inline" {
  statement {
    sid    = "DBAccess"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:GetItem",
      "dynamodb:Scan",
      "dynamodb:Query",
    ]
    resources = [
      aws_dynamodb_table.schedule.arn,
      "${aws_dynamodb_table.schedule.arn}/index/*",
    ]
  }

  statement {
    sid     = "S3Access"
    effect  = "Allow"
    actions = ["s3:GetObject"]
    resources = [
      "${aws_s3_bucket.job_bucket.arn}/${var.active_prefix}*",
      "${aws_s3_bucket.job_bucket.arn}/${var.deleted_prefix}*",
    ]
  }

  statement {
    sid       = "SESAccess"
    effect    = "Allow"
    actions   = ["ses:SendEmail"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "lambda" {
  name   = "${var.stack_name}-lambda"
  policy = data.aws_iam_policy_document.lambda_inline.json
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.lambda.arn
}

