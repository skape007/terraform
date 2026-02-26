stack_name = "rest-reports-dev"

aws_region = "eu-west-1"

# S3 Buckets (from CloudFormation ArtifactS3Bucket)
# Pattern: {StackName}-pipeline-artifacts-{AccountId}
# Example: debug-azure-pipeline-artifacts-977206434297
code_s3_bucket        = "debug-azure-pipeline-artifacts-977206434297 "  # CloudFormation ArtifactS3Bucket output
scheduler_code_s3_key = "lambdas/scheduler.zip"
sync_code_s3_key      = "lambdas/sync.zip"

# Layer bucket (recommend same as code_s3_bucket)
s3_template_bucket_name   = "debug-azure-pipeline-artifacts-977206434297 "  # Same as code_s3_bucket
s3_template_bucket_prefix = "layers"

azure_pat  = "111111111"
ses_sender = "noemail@noemail.com"

azure_org             = "onenetcloud"
default_azure_project = "DEP"

target_project = "Demand-testing"
