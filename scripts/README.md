# Scripts

## package_and_upload.sh

Generic helper to zip the scheduler and sync Lambdas plus the Lambda layer, then upload to S3. It can also upload static HTML to S3.

### Usage

```bash
scripts/package_and_upload.sh --help
```

### Examples

```bash
# Zip and upload scheduler + sync + layer
scripts/package_and_upload.sh \
  --s3-bucket my-artifacts-bucket
```

```bash
# Only zip (no upload)
scripts/package_and_upload.sh --skip-upload
```

```bash
# Only upload existing zips
scripts/package_and_upload.sh --only-upload --s3-bucket my-artifacts-bucket
```

```bash
# Upload HTML files to S3
scripts/package_and_upload.sh \
  --s3-bucket my-artifacts-bucket \
  --html-src html \
  --html-prefix ui/
```

### Notes

- Defaults are aligned with Terraform defaults:
  - Scheduler key: `lambdas/scheduler.zip`
  - Sync key: `lambdas/sync.zip`
  - Layer key: `layers/python_layer.zip`
- Use `--region` and `--profile` to target a specific AWS account.
- The script expects `zip` and `aws` CLI to be available in PATH.

