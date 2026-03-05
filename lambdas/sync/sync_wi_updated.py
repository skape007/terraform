import json
from lambdas.sync.config import get_sync_target_field
from lambdas.sync.utils import log_work_item_details, should_ignore_update, find_target_work_item
from functions.logger import appLogger
from functions.azure_client import add_external_update_comment, \
    clear_external_update_field, search_work_item_by_title, get_work_item_details, update_work_item


def handle_work_item_updated(resource: dict) -> dict:

    work_item_id = resource.get("workItemId")
    revision = resource.get("revision", {})
    fields_changed = resource.get("fields", {})
    source_project = revision.get("fields", {}).get("System.TeamProject")

    log_work_item_details(fields_changed, revision)

    if should_ignore_update(fields_changed, source_project):
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Update ignored based on filtering rules"})
        }

    work_item_title = revision.get("fields", {}).get("System.Title", "")

    for field, change in fields_changed.items():
        sync_config = get_sync_target_field(source_project, field)
        new_value = change.get("newValue")
        if not sync_config or not new_value:
            continue

        appLogger.debug(f"Sync value update: {field} -> {new_value}")

        match field:
            case "Custom.ExternalUpdate":
                process_external_update(new_value,
                                        source_project,
                                        sync_config,
                                        work_item_id,
                                        work_item_title,
                                        field)
            case "Custom.TargetDate1":
                process_external_target_date_update(new_value, work_item_title, sync_config)
            case "System.State":
                process_status_update(new_value, work_item_title, sync_config)

            case _:
                appLogger.error(f"Unknown field {field}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Processed update for work item {work_item_id}",
            "fieldsChanged": list(fields_changed.keys())
        })
    }


def process_status_update(new_value: str,
                          work_item_title: str,
                          sync_config: dict) -> None:
    target_project = sync_config.get("target_project")
    target_field = sync_config.get("target_field")
    if new_value == "In Progress":
        target_work_item_id = find_target_work_item(work_item_title, target_project, sync_config)
        if target_work_item_id:
            update_work_item(target_project, target_work_item_id, new_value, target_field)
    else:
        appLogger.error(f"Skip state update: {new_value}")


def process_external_target_date_update(new_value: str,
                                        work_item_title: str,
                                        sync_config: dict) -> None:
    target_project = sync_config.get("target_project")
    target_field = sync_config.get("target_field")
    target_work_item_id = find_target_work_item(work_item_title, target_project, sync_config)
    if target_work_item_id:
        update_work_item(target_project, target_work_item_id, new_value, target_field)


def process_external_update(new_value: str,
                            source_project: str,
                            sync_config: dict,
                            work_item_id: int,
                            work_item_title: str,
                            field: str) -> None:
    add_external_update_comment(work_item_id, new_value, source_project)
    clear_external_update_field(work_item_id, source_project, field)
    target_project = sync_config.get("target_project")
    target_work_item_id = find_target_work_item(work_item_title, target_project, sync_config)
    if target_work_item_id:
        add_external_update_comment(target_work_item_id, new_value, target_project)
