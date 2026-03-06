# Azure Automations

> Automated Azure DevOps reporting platform — schedules recurring email reports, syncs work item field changes, and serves a live HTML dashboard, all running serverless on AWS.

---

## Table of Contents

1. [Scope](#1-scope)
2. [Pre-Requisites](#2-pre-requisites)
3. [Deploying the Pre-Req Stack](#3-deploying-the-pre-req-stack)
4. [Prerequisites Before Running the Pipeline](#4-prerequisites-before-running-the-pipeline)
5. [Terraform Structure and Configuration](#5-terraform-structure-and-configuration)

---

## 1. Scope

This project bridges **Azure DevOps** and **AWS** to automate team reporting and field synchronisation.

### What it does

| Components           | Description |
|----------------------|---|
| **Scheduler Lambda** | Triggered hourly by EventBridge and on S3 object events. Reads job configs from S3, checks DynamoDB for due jobs, fetches work items from Azure DevOps via WIQL, renders HTML tables and delivers them via SES. |
| **Sync Lambda**      | Exposed via a public Lambda Function URL. Receives Azure DevOps service hook webhooks (work item created/updated) and syncs configured fields back to a target Azure DevOps project. |
| **HTML Dashboard**   | Single-page app served over HTTPS via CloudFront. Displays a live catalogue of all active report jobs fetched from `jobs/catalog.json`. |
| **Shared Layer**     | `azure_client.py` and `logger.py` shared between both Lambdas, deployed as a Lambda Layer at `/opt/python/functions/`. |

### Scheduler Lambda

- Triggered **hourly** by EventBridge and on **S3 object create/delete** events
- Reads job configs from `s3://{job-bucket}/jobs/active/`
- Checks DynamoDB to determine which jobs are due based on `interval_days` and `anchor_date`
- Fetches work items from Azure DevOps via saved WIQL queries
- Renders formatted HTML tables and sends emails via **SES**
- Writes a `catalog.json` summary to S3 after each ingest or delete

### Sync Lambda

- Exposed via a public **Lambda Function URL** — configure this as an Azure DevOps service hook target
- Receives `workitem.created` and `workitem.updated` webhook payloads
- Uses `sync_fields.json` to map source project fields to target project fields
- Writes field changes back to Azure DevOps and adds a comment to the source work item
- Supports `Custom.ExternalUpdate`, `Custom.TargetDate1`, and `System.State` field sync

### Repository layout

```
azure-automations-code/
├── buildspec-plan.yaml          # CodeBuild: package lambdas + terraform plan
├── buildspec-apply.yaml         # CodeBuild: terraform apply + S3 content upload
├── buildspec-destroy.yaml       # CodeBuild: terraform destroy
├── infra/                       # Terraform root module
│   ├── environments/
│   │   └── <environment>.tfvars          # Environment-specific variable values
│   └── modules/automations/     # All AWS resources
├── lambdas/
│   ├── scheduler/               # Report scheduling Lambda
│   └── sync/                    # Azure DevOps sync Lambda
├── layers/python/functions/     # Shared Lambda Layer code
├── html/                        # Static dashboard (index.html, catalog.js, styles.css)
├── reports_configuration/       # Example job config JSON files
└── pre-req-stack/
    └── template.yaml            # CloudFormation bootstrap stack
```

---

## 2. Pre-Requisites

The following must exist **before** deploying the pre-req stack.

### 2.1 AWS

| Requirements    | Notes |
|-----------------|---|
| AWS account     | `eu-west-1` region recommended |
| AWS CLI         | Configured with credentials that have `AdministratorAccess` or equivalent |
| IAM permissions | Ability to create IAM roles, S3 buckets, KMS keys, CodePipeline, CodeBuild, SNS |

### 2.2 GitHub

| Requirement | Notes |
|---|---|
| GitHub repository | The repo this code lives in |
| GitHub CodeStar Connection | Must be in **Available** status — AWS Console → Developer Tools → Connections. Created once per AWS account. |

To create a CodeStar Connection:

```
AWS Console → Developer Tools → Connections → Create connection → GitHub
```

Copy the Connection ARN — it is required as a CloudFormation parameter.

### 2.3 Azure DevOps

| Requirement | Notes |
|---|---|
| Azure DevOps organisation | e.g. `onenetcloud` |
| Personal Access Token (PAT) | Requires `Work Items (Read & Write)` scope |
| Saved WIQL queries | Query IDs are referenced inside job config JSON files |
| Service hook | Configure after first deploy — point to the `sync_lambda_url` Terraform output |

### 2.4 AWS SES

| Requirement | Notes |
|---|---|
| Verified sender email | The address in `ses_sender` must be SES-verified before emails can be sent |
| SES out of sandbox | In production, request SES production access to send to unverified recipients |

---

## 3. Deploying the Pre-Req Stack

`pre-req-stack/template.yaml` is a CloudFormation template that bootstraps the entire CI/CD pipeline infrastructure. It creates:

- **KMS key** — encrypts S3 artifacts, Terraform state, and SSM parameters
- **S3 buckets** — artifact store and Terraform remote state bucket
- **CodePipeline** — Source → Plan → Approve → Deploy → Destroy stages
- **CodeBuild projects** — Plan, Apply, Destroy (each referencing its own buildspec file)
- **IAM roles** — CodePipeline and CodeBuild execution roles
- **SNS topic** — approval notification emails

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `StackName` | `azure` | Name prefix for all created resources |
| `Environment` | `<environment>` | Target environment (`dev`, `test`, `prod`) |
| `TerraformDir` | `infra` | Path to the Terraform root module inside the repo |
| `TerraformVersion` | `1.14.6` | Terraform version installed in CodeBuild |
| `RepoBranch` | `develop` | Git branch that triggers the pipeline |
| `GitHubTeam` | — | GitHub organisation or user name |
| `GitHubRepo` | — | GitHub repository name |
| `GitHubCloudConnectionArn` | — | ARN of the CodeStar Connection to GitHub |
| `RootAccount` | — | 12-digit AWS account ID |
| `AZUREPATSSMParameterSufix` | `pat` | SSM parameter suffix — full name: `{StackName}-{Environment}-{Suffix}` |
| `CodePipelineType` | `V2` | CodePipeline type (`V1` or `V2`) |

### Deploy command

```bash
aws cloudformation deploy \
  --stack-name azure-<environment> \
  --template-file pre-req-stack/template.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    StackName=azure \
    Environment=<environment> \
    RepoBranch=develop \
    GitHubTeam=<your-github-org> \
    GitHubRepo=<your-repo-name> \
    GitHubCloudConnectionArn=<codestar-connection-arn> \
    RootAccount=<aws-account-id> \
  --region eu-west-1
```

### Update command

```bash
aws cloudformation deploy \
  --stack-name azure-<environment> \
  --template-file pre-req-stack/template.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region eu-west-1
```

> **Warning:** Deleting the CloudFormation stack removes the pipeline, S3 buckets, and KMS key but does **not** remove the Terraform-managed application resources. Run the Destroy pipeline stage first.

---

## 4. Prerequisites Before Running the Pipeline

After the pre-req stack is deployed, complete the following before the first pipeline run.

### 4.1 Create the Azure PAT SSM Parameter

The pipeline reads the Azure DevOps PAT from SSM Parameter Store. This parameter is **not** created by CloudFormation and must be created manually.

Parameter name pattern: `{StackName}-{Environment}-{AZUREPATSSMParameterSufix}`

For the default values this is: `azure-<environment>-pat`

```bash
aws ssm put-parameter \
  --name "azure-<environment>-pat" \
  --value "<your-azure-devops-pat>" \
  --type SecureString \
  --key-id alias/azure-<environment>-kms \
  --region eu-west-1
```

> The KMS key alias `azure-<environment>-kms` is created by the pre-req stack. Adjust the alias to match your `{StackName}-{Environment}`.

### 4.2 Update the tfvars file

Edit `infra/environments/<environment>.tfvars`:

```hcl
stack_name = "azure-<environment>"
aws_region = "eu-west-1"

# Must match the ArtifactS3Bucket created by the pre-req stack
# Pattern: {StackName}-{Environment}-pipeline-artifacts-{AccountId}
code_s3_bucket          = "azure-<environment>-pipeline-artifacts-<account-id>"
s3_template_bucket_name = "azure-<environment>-pipeline-artifacts-<account-id>"

# SES verified sender email
ses_sender = "your-verified-email@company.com"

# Azure DevOps configuration
azure_org             = "your-azure-org"
default_azure_project = "your-default-project"
target_project        = "your-sync-target-project"
```

> `scheduler_code_s3_key`, `sync_code_s3_key`, and `layer_s3_key` are placeholder defaults — they are overridden at plan time by the buildspec with an epoch timestamp: `lambdas/{epoch}/scheduler.zip`.

### 4.3 Verify SES sender email

```bash
aws ses verify-email-identity \
  --email-address your-verified-email@company.com \
  --region eu-west-1
```

### 4.4 Trigger the pipeline

```bash
git push origin develop
```

### 4.5 Configure the Azure DevOps Webhook (Sync Lambda)

This step is required after every first-time deploy or if the Sync Lambda URL changes.

**Step 1 — Get the Sync Lambda URL from Terraform output:**

```bash
terraform -chdir=infra output sync_lambda_url
```

The URL will look like:
```
https://<id>.lambda-url.eu-west-1.on.aws/
```

**Step 2 — Open Azure DevOps Service Hooks:**

```
Azure DevOps → Project Settings (bottom-left) → Service hooks → + Create subscription
```

**Step 3 — Create the "Work item updated" subscription:**

| Field | Value |
|---|---|
| Service | `Web Hooks` |
| Trigger | `Work item updated` |
| Filters | Leave as default (all work item types, all fields) |
| URL | Paste the `sync_lambda_url` value |
| HTTP headers | Leave empty |
| Resource version | `2.0` |
| Messages to send | `All` |

Click **Test** to verify the connection returns HTTP 200, then click **Finish**.

**Step 4 — Create the "Work item created" subscription:**

Repeat Step 3 with:

| Field | Value |
|---|---|
| Trigger | `Work item created` |
| URL | Same `sync_lambda_url` value |

> Both subscriptions must point to the **same URL**. The Sync Lambda reads the `eventType` field from the webhook payload (`workitem.updated` or `workitem.created`) and routes accordingly.

**Step 5 — Verify in CloudWatch:**

After saving, trigger a work item update in Azure DevOps and check the Sync Lambda logs:

```
AWS Console → Lambda → {stack_name}-sync → Monitor → View CloudWatch logs
```

You should see a log entry starting with `[INFO] Event Type: workitem.updated`.

---

## 5. Terraform Structure and Configuration

### 5.1 State backend

`backend.tf` declares only the backend type. All values are injected by the pipeline at runtime via `-backend-config` flags:

```hcl
terraform {
  backend "s3" {}
}
```

| Backend config | Value |
|---|---|
| `bucket` | `{StackName}-{Environment}-tf-state-{AccountId}` (created by pre-req stack) |
| `key` | `{StackName}/{Environment}/terraform.tfstate` |
| `encrypt` | `true` |
| `use_lockfile` | `true` |

### 5.2 Module structure

```
infra/
├── main.tf                      # Calls the automations module
├── variables.tf                 # Root input variables
├── outputs.tf                   # Exposes module outputs
├── backend.tf                   # S3 backend type declaration
├── provider.tf                  # AWS provider configuration
├── versions.tf                  # Terraform >= 1.14.0, AWS provider ~> 6.34
├── environments/
│   └── <environment>.tfvars              # Environment variable values
└── modules/
    └── automations/
        ├── locals.tf            # Computed resource names
        ├── lambda.tf            # Scheduler + Sync Lambda functions
        ├── layer.tf             # Lambda Layer version
        ├── dynamodb.tf          # Job schedule DynamoDB table
        ├── s3.tf                # Job S3 bucket + versioning
        ├── s3_notifications.tf  # S3 to Lambda event triggers
        ├── cloudfront.tf        # CloudFront distribution + OAC
        ├── events.tf            # EventBridge hourly rule
        ├── iam.tf               # Lambda execution role + policies
        ├── variables.tf         # Module input variables
        └── outputs.tf           # Module outputs
```

### 5.3 Key variables

| Variable | Default | Description |
|---|---|---|
| `stack_name` | — | **Required.** Name prefix for all resources e.g. `azure-<environment>` |
| `code_s3_bucket` | — | **Required.** Artifact S3 bucket holding Lambda zip files |
| `ses_sender` | — | **Required.** SES verified sender email address |
| `azure_org` | `onenetcloud` | Azure DevOps organisation name |
| `default_azure_project` | `DEP` | Default Azure DevOps project for the Scheduler Lambda |
| `target_project` | `Demand-testing` | Target project for the Sync Lambda write-back |
| `lambda_runtime` | `python3.12` | Lambda runtime |
| `lambda_memory_size` | `512` | Lambda memory in MB |
| `lambda_timeout` | `900` | Lambda timeout in seconds |
| `azure_pat_encrypted` | `""` | Injected at plan time from SSM — do not set in tfvars |

### 5.4 Resource naming

All names are derived from `stack_name` in `modules/automations/locals.tf`:

| Resource | Name |
|---|---|
| S3 job bucket | `{stack_name}-schedule` |
| DynamoDB table | `{stack_name}-schedule-jobs` |
| Scheduler Lambda | `{stack_name}-scheduler` |
| Sync Lambda | `{stack_name}-sync` |
| Lambda Layer | `{stack_name}` |
| IAM Role | `{stack_name}-lambda` |
| CloudFront OAC | `{stack_name}-html-oac` |
| EventBridge Rule | `per-job-hourly` |

### 5.5 Outputs

| Output | Description |
|---|---|
| `job_bucket_name` | S3 bucket for job configs and dashboard assets |
| `schedule_table_name` | DynamoDB table name |
| `scheduler_lambda_name` | Scheduler Lambda function name |
| `sync_lambda_name` | Sync Lambda function name |
| `sync_lambda_url` | Public HTTPS URL — use as Azure DevOps service hook target |
| `html_cloudfront_domain` | CloudFront distribution domain name |
| `html_url` | Full HTTPS dashboard URL |

### 5.6 Pipeline flow

```
git push
    |
    v
Source
    Triggered by push to the configured branch
    Produces: SourceOutput artifact
    |
    v
Plan  (buildspec-plan.yaml)
    - Packages Scheduler Lambda  ->  s3://{artifact-bucket}/lambdas/{epoch}/scheduler.zip
    - Packages Sync Lambda       ->  s3://{artifact-bucket}/lambdas/{epoch}/sync.zip
    - Packages Lambda Layer      ->  s3://{artifact-bucket}/layers/{epoch}/python_layer.zip
    - terraform init + validate + plan (S3 keys baked into tfplan binary)
    - Uploads plan.txt + plan-summary.txt to S3
    - Logs pre-signed download URLs to CloudWatch
    Produces: TfPlanOutput artifact (tfplan, plan.txt, plan-summary.txt)
    |
    v
Approve  (Manual gate)
    - SNS notification sent to subscribers
    - Reviewer opens S3 console link or pre-signed URL to read plan.txt
    - Approve to continue / Reject to abort
    |
    v
Deploy  (buildspec-apply.yaml)
    - terraform apply using the approved tfplan binary
    - Creates jobs/active/ and jobs/deleted/ folders in S3 (first deploy only)
    - Uploads index.html, catalog.js, styles.css to S3
    |
    v
Destroy  (manual approval required)
    - Empties the job S3 bucket (all object versions and delete markers)
    - terraform destroy
```

> **Note:** The Destroy stage is **commented out by default** in `pre-req-stack/template.yaml`.
> To enable it, uncomment the Destroy stage section in the template and update the stack:
>
> ```bash
> aws cloudformation deploy \
>   --stack-name azure-mgmt \
>   --template-file pre-req-stack/template.yaml \
>   --capabilities CAPABILITY_NAMED_IAM \
>   --region eu-west-1
> ```
>
> Alternatively, to destroy all Terraform-managed resources manually without the pipeline:
>
> ```bash
> cd infra
> terraform init \
>   -backend-config="bucket=azure-mgmt-tf-state-<account-id>" \
>   -backend-config="key=azure/<environment>/terraform.tfstate" \
>   -backend-config="encrypt=true"
>
> terraform destroy \
>   -var-file="environments/<environment>.tfvars" \
>   -var="azure_pat_encrypted=<your-pat>"
> ```
>
> Before running destroy, manually empty the S3 job bucket or it will fail:
>
> ```bash
> # Delete all object versions and delete markers
> BUCKET="azure-<environment>-schedule"
> aws s3api list-object-versions --bucket "$BUCKET" \
>   --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' \
>   --output json | aws s3api delete-objects --bucket "$BUCKET" --delete file:///dev/stdin || true
> aws s3api list-object-versions --bucket "$BUCKET" \
>   --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' \
>   --output json | aws s3api delete-objects --bucket "$BUCKET" --delete file:///dev/stdin || true
> ```

