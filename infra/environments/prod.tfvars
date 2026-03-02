stack_name = "rest-reports-prod"

aws_region = "eu-west-1"

# S3 Buckets (from CloudFormation ArtifactS3Bucket)
# Pattern: {StackName}-{Environment}-pipeline-artifacts-{AccountId}
code_s3_bucket        = "debug-azure-prod-pipeline-artifacts-977206434297"
scheduler_code_s3_key = "lambdas/scheduler.zip"
sync_code_s3_key      = "lambdas/sync.zip"

# Layer bucket (same as code_s3_bucket)
s3_template_bucket_name   = "debug-azure-prod-pipeline-artifacts-977206434297"
s3_template_bucket_prefix = "layers"

azure_pat  = "REPLACE_ME"
ses_sender = "REPLACE_ME"

azure_org             = "onenetcloud"
default_azure_project = "DEP"

target_project = "Demand-testing"
