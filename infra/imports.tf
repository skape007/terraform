# =============================================================================
# ONE-TIME IMPORTS: Resources that already exist in AWS from previous runs
# but may not be in the current Terraform state.
# REMOVE THIS FILE after the first successful apply.
# =============================================================================

# CloudFront OAC (409 AlreadyExists)
import {
  to = module.scheduler.aws_cloudfront_origin_access_control.html_oac
  id = "E3N5PDPAASDAFI"
}

# IAM Role (409 AlreadyExists)
import {
  to = module.scheduler.aws_iam_role.lambda
  id = "rest-reports-dev-lambda"
}
