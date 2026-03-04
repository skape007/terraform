# Azure Automations

> Automated Azure DevOps reporting platform — schedules recurring email reports, syncs work item changes, and serves a live HTML dashboard, all running serverless on AWS.

---

## Overview

This project bridges **Azure DevOps** and **AWS** to automate team reporting. It reads work items from Azure DevOps boards using saved WIQL queries, formats them into HTML email reports, and delivers them on a configurable schedule. A live dashboard hosted on CloudFront provides a catalogue view of all active report jobs.

Each report job is defined as a JSON file stored in S3 — no code changes required to add, modify, or remove reports.

---

## Architecture

```
Azure DevOps Boards
        │
        │  WIQL queries (REST API)
        ▼
┌─────────────────────────────────────────────────────────────┐
│                        AWS (eu-west-1)                      │
│                                                             │
│  EventBridge (hourly) ──► Scheduler Lambda                  │
│  S3 events (job upload) ──► Scheduler Lambda                │
│                               │                             │
│                               ├── DynamoDB (job store)      │
│                               ├── S3 (job configs)          │
│                               └── SES (email delivery)      │
│                                                             │
│  Azure DevOps webhook ──► Sync Lambda (Function URL)        │
│                               └── Azure DevOps (write back) │
│                                                             │
│  CloudFront ──► S3 (index.html + ui/ + jobs/catalog.json)  │
└─────────────────────────────────────────────────────────────┘
```

---

## Components

### Scheduler Lambda (`lambdas/scheduler/`)
- Triggered **hourly** by EventBridge and on **S3 object events** (job file created/deleted)
- Reads active job configs from `s3://…/jobs/active/`
- Checks DynamoDB to determine which jobs are due to run
- Fetches work items from Azure DevOps via WIQL
- Renders formatted HTML tables and sends email via **SES**
- Writes a `catalog.json` summary to S3 after each run

### Sync Lambda (`lambdas/sync/`)
- Exposed via a public **Lambda Function URL**
- Receives **Azure DevOps service hook webhooks** (work item updated events)
- Maps incoming field changes to configured target fields using `sync_fields.json`
- Writes changes back to Azure DevOps and adds a comment to the work item

### Shared Lambda Layer (`layers/python/functions/`)
- `azure_client.py` — HTTP client for the Azure DevOps REST API (auth, WIQL, work item reads/writes, comments)
- `logger.py` — structured logger shared across both Lambdas

### HTML Dashboard (`html/`)
- Single-page app served via **CloudFront** over HTTPS
- `index.html` — dashboard entry point (served from S3 bucket root)
- `catalog.js` — fetches `jobs/catalog.json` and renders the active job list
- `styles.css` — dashboard styles

---

## Repository Structure

```
azure-automations-code/
├── buildspec-plan.yml          # CodeBuild: package lambdas + terraform plan
├── buildspec-apply.yml         # CodeBuild: terraform apply + S3 upload
│
├── infra/
│   ├── main.tf                 # Root module
│   ├── variables.tf            # Input variables
│   ├── outputs.tf              # URLs, bucket names, lambda names
│   ├── backend.tf              # S3 remote state (configured at runtime)
│   ├── versions.tf             # Terraform + provider version pins
│   ├── environments/
│   │   ├── dev.tfvars
│   │   ├── test.tfvars
│   │   └── prod.tfvars
│   └── modules/scheduler/      # All infrastructure resources
│       ├── lambda.tf           # Scheduler + Sync Lambda functions
│       ├── layer.tf            # Lambda layer version
│       ├── dynamodb.tf         # Job schedule table
│       ├── s3.tf               # Job bucket + versioning + public access block
│       ├── s3_notifications.tf # S3 → Lambda triggers
│       ├── cloudfront.tf       # Distribution + OAC + bucket policy
│       ├── events.tf           # EventBridge hourly rule
│       └── iam.tf              # Lambda execution role + policies
│
├── lambdas/
│   ├── scheduler/              # Report scheduling logic
│   │   ├── lambda_handler.py   # Entry point — routes S3 and EventBridge events
│   │   ├── scheduler.py        # Slot evaluation and job dispatch
│   │   ├── ingestion.py        # Parse and store job configs from S3
│   │   ├── deletion.py         # Remove jobs and notify recipients
│   │   ├── catalog.py          # Build and write catalog.json
│   │   ├── email_service.py    # SES HTML email composition and sending
│   │   ├── html_builder.py     # Work item HTML table rendering
│   │   ├── wiql_builder.py     # Azure DevOps WIQL query construction
│   │   ├── models.py           # Job config data classes
│   │   ├── config.py           # Environment variable loading
│   │   └── utils.py            # Shared helpers
│   └── sync/
│       ├── lambda_handler.py   # Entry point — handles webhook payload
│       ├── config.py           # Environment variable loading
│       └── sync_fields.json    # Field mapping configuration
│
├── layers/
│   └── python/functions/       # Shared layer (deployed to /opt/python/functions/)
│       ├── azure_client.py
│       └── logger.py
│
├── html/
│   ├── index.html
│   ├── catalog.js
│   └── styles.css
│
├── reports_configuration/      # Example job config JSON files
│   ├── sprint_review_overview.json
│   ├── sprint_planning_overview.json
│   ├── demand_week_review.json
│   └── …
│
├── scripts/
│   └── package_and_upload.sh   # Local helper: zip and upload lambdas/layer/HTML to S3
│
└── pre-req-stack/
    └── template.yaml           # CloudFormation bootstrap (pipeline + state bucket + IAM)
```

---

## Job Configuration

Reports are defined as JSON files. Drop one into `s3://{job-bucket}/jobs/active/` to schedule it — no deployment required.

```json
{
  "description": "Biweekly Sprint Review Overview email",
  "schedule": {
    "day_of_week": ["TUE"],
    "hour": 8,
    "interval_days": 14,
    "anchor_date": "2025-10-28"
  },
  "email_config": {
    "recipient": ["user@company.com"],
    "email_title": "DEP - Sprint Review Overview",
    "intro_title": "Hi Product Owners",
    "intro_body": "Summary of the latest sprint review...",
    "team": "Dev Team",
    "comments": true,
    "queries": [
      {
        "id": "619f4099-3009-4975-8f75-10817fc9c72a",
        "title": "Sprint Review",
        "description": "Completed work from the last sprint",
        "track_sprint_changes": true
      }
    ]
  },
  "enabled": true
}
```

Sample configurations for different report types are in [`reports_configuration/`](reports_configuration/).

---

## Infrastructure

Deployed with **Terraform** (application resources) bootstrapped by **CloudFormation** (pipeline + state bucket).

| Resource | Name | Purpose |
|---|---|---|
| S3 Bucket | `rest-reports-{env}-schedule` | Job configs + HTML dashboard |
| DynamoDB | `rest-reports-{env}-schedule-jobs` | Job state and scheduling |
| Lambda | `rest-reports-{env}-scheduler` | Report scheduling and email |
| Lambda | `rest-reports-{env}-sync` | Azure DevOps field sync |
| Lambda Layer | `rest-reports-{env}` | Shared azure_client + logger |
| CloudFront | — | HTTPS dashboard |
| EventBridge | `per-job-hourly` | Hourly scheduler trigger |
| IAM Role | `rest-reports-{env}-lambda` | Lambda execution permissions |

---

## Deployment Pipeline

Each environment (`dev` / `test` / `prod`) has its own independent CodePipeline:

```
git push  →  Source  →  Plan + Manual Approval  →  Deploy
```

| Stage | What happens |
|---|---|
| **Source** | Triggered by push to `develop` / `test` / `main` |
| **Plan** | Packages Lambdas with epoch-timestamped S3 keys, runs `terraform plan`, uploads `plan.txt` to S3 for review |
| **Approval** | Reviewer downloads plan via S3 console link or pre-signed URL, approves or rejects |
| **Deploy** | Runs `terraform apply`, uploads HTML to S3, creates `jobs/active/` and `jobs/deleted/` folders |

| Branch | Environment |
|---|---|
| `develop` | dev |
| `test` | test |
| `main` | prod |

---

## Prerequisites

- AWS CLI configured for account `977206434297` (eu-west-1)
- GitHub CodeStar Connection in **Available** status
- Azure DevOps PAT with board read access
- SES verified sender email

---

## Quick Start

```bash
# 1. Bootstrap the pipeline (once per environment)
aws cloudformation deploy \
  --stack-name azure-dev \
  --template-file pre-req-stack/template.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides StackName=azure Environment=dev RepoBranch=develop \
  --region eu-west-1

# 2. Set real values in infra/environments/mgmt.tfvars
#    azure_pat  = "YOUR_PAT"
#    ses_sender = "your-email@company.com"

# 3. Push — the pipeline triggers automatically
git push origin develop
```

For full deployment instructions, environment variables reference, and troubleshooting see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Local Utilities

The [`scripts/package_and_upload.sh`](scripts/README.md) helper can zip and upload Lambdas, the layer, and HTML files directly to S3 without running the pipeline — useful for manual testing.

```bash
# Zip and upload everything
scripts/package_and_upload.sh --s3-bucket my-artifacts-bucket

# Upload HTML only
scripts/package_and_upload.sh \
  --s3-bucket my-job-bucket \
  --html-src html \
  --html-prefix ui/
```

