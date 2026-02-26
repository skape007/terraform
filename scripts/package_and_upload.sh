#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/package_and_upload.sh [options]

Options:
  --scheduler-src PATH     Source directory to zip for scheduler Lambda (default: lambdas/scheduler)
  --sync-src PATH          Source directory to zip for sync Lambda (default: lambdas/sync)
  --layer-src PATH         Source directory to zip for Lambda layer (default: layers/python)
  --scheduler-zip PATH     Output zip for scheduler Lambda (default: dist/scheduler.zip)
  --sync-zip PATH          Output zip for sync Lambda (default: dist/sync.zip)
  --layer-zip PATH         Output zip for Lambda layer (default: dist/python_layer.zip)
  --s3-bucket NAME         S3 bucket to upload to (required for upload)
  --scheduler-key KEY      S3 key for scheduler zip (default: lambdas/scheduler.zip)
  --sync-key KEY           S3 key for sync zip (default: lambdas/sync.zip)
  --layer-key KEY          S3 key for Layer zip (default: layers/python_layer.zip)
  --html-src PATH          Optional HTML directory to upload (e.g., html)
  --html-prefix PREFIX     S3 prefix for HTML upload (default: html/)
  --region REGION          AWS region (optional)
  --profile PROFILE        AWS CLI profile (optional)
  --skip-zip               Skip zipping; only upload existing zip files
  --skip-upload            Only create zip files, do not upload
  --only-upload            Upload only; implies --skip-zip
  --dry-run                Show actions without uploading
  -h, --help               Show this help

Examples:
  # Zip and upload Lambdas + Layer
  scripts/package_and_upload.sh --s3-bucket my-bucket

  # Only zip (no upload)
  scripts/package_and_upload.sh --skip-upload

  # Only upload existing zips
  scripts/package_and_upload.sh --only-upload --s3-bucket my-bucket

  # Upload HTML to S3
  scripts/package_and_upload.sh --s3-bucket my-bucket --html-src html --html-prefix ui/
USAGE
}

# Defaults
SCHEDULER_SRC="lambdas/scheduler"
SYNC_SRC="lambdas/sync"
LAYER_SRC="layers/python"
SCHEDULER_ZIP="dist/scheduler.zip"
SYNC_ZIP="dist/sync.zip"
LAYER_ZIP="dist/python_layer.zip"
S3_BUCKET=""
SCHEDULER_KEY="lambdas/scheduler.zip"
SYNC_KEY="lambdas/sync.zip"
LAYER_KEY="layers/python_layer.zip"
HTML_SRC=""
HTML_PREFIX="html/"
REGION=""
PROFILE=""
SKIP_ZIP=false
SKIP_UPLOAD=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scheduler-src) SCHEDULER_SRC="$2"; shift 2 ;;
    --sync-src) SYNC_SRC="$2"; shift 2 ;;
    --layer-src) LAYER_SRC="$2"; shift 2 ;;
    --scheduler-zip) SCHEDULER_ZIP="$2"; shift 2 ;;
    --sync-zip) SYNC_ZIP="$2"; shift 2 ;;
    --layer-zip) LAYER_ZIP="$2"; shift 2 ;;
    --s3-bucket) S3_BUCKET="$2"; shift 2 ;;
    --scheduler-key) SCHEDULER_KEY="$2"; shift 2 ;;
    --sync-key) SYNC_KEY="$2"; shift 2 ;;
    --layer-key) LAYER_KEY="$2"; shift 2 ;;
    --html-src) HTML_SRC="$2"; shift 2 ;;
    --html-prefix) HTML_PREFIX="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --skip-zip) SKIP_ZIP=true; shift ;;
    --skip-upload) SKIP_UPLOAD=true; shift ;;
    --only-upload) SKIP_ZIP=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "[ERROR] Unknown argument: $1"; usage; exit 1 ;;
  esac
 done

if [[ "$SKIP_UPLOAD" == false && -z "$S3_BUCKET" ]]; then
  echo "[ERROR] --s3-bucket is required unless --skip-upload is set"
  exit 1
fi

AWS_OPTS=()
if [[ -n "$REGION" ]]; then AWS_OPTS+=(--region "$REGION"); fi
if [[ -n "$PROFILE" ]]; then AWS_OPTS+=(--profile "$PROFILE"); fi

if [[ "$SKIP_ZIP" == false ]]; then
  mkdir -p "$(dirname "$SCHEDULER_ZIP")" "$(dirname "$SYNC_ZIP")" "$(dirname "$LAYER_ZIP")"

  if [[ -d "$SCHEDULER_SRC" ]]; then
    echo "[INFO] Zipping scheduler Lambda: $SCHEDULER_SRC -> $SCHEDULER_ZIP"
    (cd "$SCHEDULER_SRC" && zip -r "../../${SCHEDULER_ZIP}" . -x "*/__pycache__/*" "*.pyc" "*.pyo")
  else
    echo "[ERROR] Scheduler source not found: $SCHEDULER_SRC"
    exit 1
  fi

  if [[ -d "$SYNC_SRC" ]]; then
    echo "[INFO] Zipping sync Lambda: $SYNC_SRC -> $SYNC_ZIP"
    (cd "$SYNC_SRC" && zip -r "../../${SYNC_ZIP}" . -x "*/__pycache__/*" "*.pyc" "*.pyo")
  else
    echo "[ERROR] Sync source not found: $SYNC_SRC"
    exit 1
  fi

  if [[ -d "$LAYER_SRC" ]]; then
    echo "[INFO] Zipping Layer source: $LAYER_SRC -> $LAYER_ZIP"
    (cd "$LAYER_SRC" && zip -r "../../${LAYER_ZIP}" . -x "*/__pycache__/*" "*.pyc" "*.pyo")
  else
    echo "[ERROR] Layer source not found: $LAYER_SRC"
    exit 1
  fi
fi

if [[ "$SKIP_UPLOAD" == false ]]; then
  if [[ "$DRY_RUN" == true ]]; then
    echo "[DRY-RUN] aws s3 cp $SCHEDULER_ZIP s3://$S3_BUCKET/$SCHEDULER_KEY"
    echo "[DRY-RUN] aws s3 cp $SYNC_ZIP s3://$S3_BUCKET/$SYNC_KEY"
    echo "[DRY-RUN] aws s3 cp $LAYER_ZIP s3://$S3_BUCKET/$LAYER_KEY"
  else
    echo "[INFO] Uploading scheduler zip to s3://$S3_BUCKET/$SCHEDULER_KEY"
    aws s3 cp "$SCHEDULER_ZIP" "s3://$S3_BUCKET/$SCHEDULER_KEY" "${AWS_OPTS[@]}"
    echo "[INFO] Uploading sync zip to s3://$S3_BUCKET/$SYNC_KEY"
    aws s3 cp "$SYNC_ZIP" "s3://$S3_BUCKET/$SYNC_KEY" "${AWS_OPTS[@]}"
    echo "[INFO] Uploading layer zip to s3://$S3_BUCKET/$LAYER_KEY"
    aws s3 cp "$LAYER_ZIP" "s3://$S3_BUCKET/$LAYER_KEY" "${AWS_OPTS[@]}"
  fi

  if [[ -n "$HTML_SRC" ]]; then
    if [[ ! -d "$HTML_SRC" ]]; then
      echo "[ERROR] HTML source not found: $HTML_SRC"
      exit 1
    fi
    if [[ "$DRY_RUN" == true ]]; then
      echo "[DRY-RUN] aws s3 sync $HTML_SRC s3://$S3_BUCKET/$HTML_PREFIX"
    else
      echo "[INFO] Uploading HTML to s3://$S3_BUCKET/$HTML_PREFIX"
      aws s3 sync "$HTML_SRC" "s3://$S3_BUCKET/$HTML_PREFIX" "${AWS_OPTS[@]}"
    fi
  fi
fi

echo "[DONE]"
