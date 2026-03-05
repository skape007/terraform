import os
import boto3
from dataclasses import dataclass


@dataclass
class Config:
    table_name: str
    gsi_index_name: str
    gsi_hash_key: str
    bucket: str
    active_prefix: str
    deleted_prefix: str
    catalog_key: str
    ses_sender: str
    azure_org: str
    azure_project: str
    azure_pat: str
    notify_fallback: str | None
    require_delete_confirm: bool
    enforce_version_step: bool
    allowed_intervals: set

    def get_base_url(self, project: str) -> str:
        return f"https://dev.azure.com/{self.azure_org}/{project}/"


def load_config() -> Config:
    return Config(
        table_name=os.environ["SCHEDULE_TABLE"],
        gsi_index_name=os.environ.get("GSI1_INDEX_NAME", "GSI1"),
        gsi_hash_key=os.environ.get("GSI1_HASH_KEY", "time_slot"),
        bucket=os.environ["SCHEDULE_BUCKET"].strip(),
        active_prefix=os.environ.get("ACTIVE_PREFIX", "jobs/active/"),
        deleted_prefix=os.environ.get("DELETED_PREFIX", "jobs/deleted/"),
        catalog_key=os.environ.get("CATALOG_KEY", "jobs/catalog.json"),
        ses_sender=os.environ["SES_SENDER"],
        azure_org=os.environ.get("AZURE_ORG", "onenetcloud"),
        azure_project=os.environ.get("AZURE_PROJECT", "DEP"),
        azure_pat=os.environ["AZURE_PAT"],
        notify_fallback=os.environ.get("NOTIFY_FALLBACK_RECIPIENT"),
        require_delete_confirm=os.environ.get("REQUIRE_DELETE_CONFIRM", "false").lower() == "true",
        enforce_version_step=os.environ.get("ENFORCE_VERSION_STEP", "false").lower() == "true",
        allowed_intervals={1, 7, 14, 30},
    )


# Shared AWS clients
config = load_config()
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(config.table_name)
s3_client = boto3.client("s3")
ses_client = boto3.client("ses")
