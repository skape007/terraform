stack_name = "rest-reports-dev"

aws_region = "eu-west-1"

# S3 Buckets (from CloudFormation ArtifactS3Bucket)
# Pattern: {StackName}-{Environment}-pipeline-artifacts-{AccountId}
code_s3_bucket        = "azure-dev-pipeline-artifacts-977206434297"
scheduler_code_s3_key = "lambdas/scheduler.zip"
sync_code_s3_key      = "lambdas/sync.zip"

# Layer bucket (same as code_s3_bucket)
s3_template_bucket_name   = "azure-dev-pipeline-artifacts-977206434297"
s3_template_bucket_prefix = "layers"
layer_s3_key              = "layers/python_layer.zip"

azure_pat  = "111111111"
ses_sender = "noemail@noemail.com"

azure_org             = "onenetcloud"
default_azure_project = "DEP"

target_project = "Demand-testing"
