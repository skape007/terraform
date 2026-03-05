import os
import json
from dataclasses import dataclass


@dataclass
class Config:
    azure_org: str
    azure_pat: str

    def validate(self) -> None:
        missing = [field for field in self.__dataclass_fields__ if not getattr(self, field, None)]
        if missing:
            raise ValueError(f"Missing configuration variables: {', '.join(missing)}")

    def get_base_url(self, project: str) -> str:
        return f"https://dev.azure.com/{self.azure_org}/{project}/"


def load_config() -> Config:
    return Config(
        azure_org=os.environ.get("AZURE_ORG", "onenetcloud"),
        azure_pat=os.environ["AZURE_PAT"],
    )


def load_sync_fields(path: str = "sync_fields.json") -> dict:
    with open(path, "r") as f:
        return json.load(f)


def get_sync_target_field(project: str, source_field: str) -> dict | None:
    src = SYNC_FIELDS_BY_PROJECT.get(project, {}).get(source_field)
    if src is None:
        return None

    new_config = dict(src)

    title_regex = src.get("title_regex") or SYNC_FIELDS_BY_PROJECT.get(project, {}).get("default_title_regex")
    new_config["title_regex"] = title_regex

    title_prefix = src.get("title_prefix") or SYNC_FIELDS_BY_PROJECT.get(project, {}).get("title_prefix", "")
    new_config["title_prefix"] = title_prefix

    return new_config


SYNC_FIELDS_BY_PROJECT = load_sync_fields()
config = load_config()
