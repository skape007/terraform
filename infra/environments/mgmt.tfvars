stack_name = "azure-mgmt"

aws_region = "eu-west-1"

# S3 Buckets (from CloudFormation ArtifactS3Bucket)
# Pattern: {StackName}-{Environment}-pipeline-artifacts-{AccountId}
code_s3_bucket        = "azure-mgmt-pipeline-artifacts-977206434297"

# S3 keys below are placeholder defaults - overridden at plan time by buildspec-plan.yaml
# via -var flags using the BUILD_TS timestamp: lambdas/{epoch}/scheduler.zip
scheduler_code_s3_key = "lambdas/scheduler.zip"
sync_code_s3_key      = "lambdas/sync.zip"

# Layer bucket (same as code_s3_bucket)
s3_template_bucket_name   = "azure-mgmt-pipeline-artifacts-977206434297"
s3_template_bucket_prefix = "layers"
# Overridden at plan time by buildspec-plan.yaml: layers/{epoch}/python_layer.zip
layer_s3_key              = "layers/python_layer.zip"

# AZURE_PAT is injected at plan/apply time by buildspec-plan.yaml via:
#   aws ssm get-parameter --name "${AZURE_PAT_SSM_NAME}" --with-decryption
# SSM parameter created by pre-req-stack/template.yaml: ${StackName}-${Environment}-${AZUREPATSSMParameterSufix}
ses_sender = "noemail@noemail.com"

azure_org             = "onenetcloud"
default_azure_project = "DEP"

target_project = "Demand-testing"
