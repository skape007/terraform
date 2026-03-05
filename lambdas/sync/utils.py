
import re
from lambdas.sync.config import get_sync_target_field
from functions.azure_client import add_external_update_comment, \
    clear_external_update_field, search_work_item_by_title, get_work_item_details, update_work_item
from functions.logger import appLogger


def log_work_item_details(fields_changed: dict,
                          revision: dict) -> None:
    appLogger.info(f"Source project: {revision.get('fields', {}).get('System.TeamProject')}")
    appLogger.info(f"Work Item Type: {revision.get('fields', {}).get('System.WorkItemType')}")
    appLogger.info(f"Work Item ID: {revision.get('id')}")
    appLogger.info(f"Work Item Title: {revision.get('fields', {}).get('System.Title')}")
    appLogger.info(f"Work Item Status: {revision.get('fields', {}).get('System.State')}")
    appLogger.debug(f"Changed fields: {list(fields_changed.keys())}")


def should_ignore_update(fields_changed: dict,
                         source_project: str) -> bool:

    for field in fields_changed.keys():
        sync_config = get_sync_target_field(source_project, field)
        if sync_config:
            return False
    appLogger.debug("Ignore update - no sync-configured fields changed")
    return True


def find_target_work_item(source_title: str,
                          target_project: str,
                          sync_config: dict) -> int | None:
    appLogger.debug(f"Searching for target work item based on source title: {source_title}")
    appLogger.debug(f"Target project: {target_project}")
    appLogger.debug(f"Sync config: {sync_config}")

    if not source_title:
        appLogger.info("No source title provided for target work item lookup")
        return None

    title_regex = sync_config.get("title_regex")
    title_prefix = sync_config.get("title_prefix")
    appLogger.debug(f"Title prefix: {title_prefix}")

    if title_regex:
        match = re.match(title_regex, source_title)
        if match:
            code = match.group(1).strip()
            name = match.group(2).strip()
            target_title = f"{title_prefix} {code} | {name}".strip()
        else:
            target_title = source_title
    else:
        target_title = source_title

    appLogger.info(f"Searching for target work item with title: {target_title}")

    work_item_id = search_work_item_by_title(target_title, target_project)

    if work_item_id:
        appLogger.info(f"Found target work item ID: {work_item_id}")
        get_work_item_details(work_item_id, target_project)
    else:
        appLogger.info(f"Target work item not found with title: {target_title}")

    return work_item_id