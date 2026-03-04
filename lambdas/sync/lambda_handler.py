import json
import re
from config import config, get_sync_target_field

from functions.azure_client import add_external_update_comment, \
    clear_external_update_field, search_work_item_by_title, get_work_item_details, update_work_item
from functions.logger import appLogger


def lambda_handler(event, context):

    appLogger.debug("Received event: " + json.dumps(event, indent=2))

    try:
        config.validate()

        body = json.loads(event.get("body", "{}"))
        event_type = body.get("eventType")
        resource = body.get("resource", {})

        appLogger.info(f"Event Type: {event_type}")

        if event_type == "workitem.updated":
            return handle_work_item_updated(resource)
        elif event_type == "workitem.created":
            return handle_work_item_created(resource)
        else:
            appLogger.error(f"Unhandled event type: {event_type}")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": f"Event type {event_type} not processed"})
            }

    except Exception as e:
        appLogger.debug(f"Exception: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


"""
Handle work item created events
"""
def handle_work_item_created(resource):

    work_item_id = resource.get("id")
    work_item_type = resource.get("fields", {}).get("System.WorkItemType")
    title = resource.get("fields", {}).get("System.Title")

    appLogger.info(f"New {work_item_type} created: {title} (ID: {work_item_id})")
    appLogger.info(f"No actions defined for Work Item Creation events yet.")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Processed creation of {work_item_type} {work_item_id}"
        })
    }


"""
Handle work item updated events with enhanced logic
"""
def handle_work_item_updated(resource):

    work_item_id = resource.get("workItemId")
    revision = resource.get("revision", {})
    fields_changed = resource.get("fields", {})
    source_project = revision.get("fields", {}).get("System.TeamProject")

    log_work_item_details(fields_changed, revision)

    # Check if update should be ignored
    if should_ignore_update(fields_changed, source_project):
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Update ignored based on filtering rules"})
        }

    # Get user information
    revised_by = resource.get("revisedBy", {})
    user_display_name = revised_by.get("displayName", "Unknown User")

    # Get work item title for target work item lookup
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


def process_status_update(new_value, work_item_title, sync_config):
    target_project = sync_config.get("target_project")
    target_field = sync_config.get("target_field")
    if new_value == "In Progress":
        target_work_item_id = find_target_work_item(work_item_title, target_project, sync_config)
        if target_work_item_id:
            update_work_item(target_project, target_work_item_id, new_value, target_field)
    else:
        appLogger.error(f"Skip state update: {new_value}")


def process_external_target_date_update(new_value, work_item_title, sync_config):
    target_project = sync_config.get("target_project")
    target_field = sync_config.get("target_field")
    target_work_item_id = find_target_work_item(work_item_title, target_project, sync_config)
    if target_work_item_id:
        update_work_item(target_project, target_work_item_id, new_value, target_field)


def process_external_update(new_value, source_project, sync_config, work_item_id, work_item_title, field):
    add_external_update_comment(work_item_id, new_value, source_project)
    clear_external_update_field(work_item_id, source_project, field)
    target_project = sync_config.get("target_project")
    target_work_item_id = find_target_work_item(work_item_title, target_project, sync_config)
    if target_work_item_id:
        add_external_update_comment(target_work_item_id, new_value, target_project)


def log_work_item_details(fields_changed, revision):
    appLogger.info(f"Source project: {revision.get('fields', {}).get('System.TeamProject')}")
    appLogger.info(f"Work Item Type: {revision.get('fields', {}).get('System.WorkItemType')}")
    appLogger.info(f"Work Item ID: {revision.get('id')}")
    appLogger.info(f"Work Item Title: {revision.get('fields', {}).get('System.Title')}")
    appLogger.info(f"Work Item Status: {revision.get('fields', {}).get('System.State')}")
    appLogger.debug(f"Changed fields: {list(fields_changed.keys())}")


"""
Check if update should be ignored based on field changes
"""
def should_ignore_update(fields_changed, source_project):

    for field in fields_changed.keys():
        sync_config = get_sync_target_field(source_project, field)
        if sync_config:
            return False
    appLogger.debug("Ignore update - no sync-configured fields changed")
    return True


"""
Find target work item based on source title pattern
Example: "DD002 | Support for Operator Connect" -> "DEP | DD002 | Support for Operator Connect"
if 
"""
def find_target_work_item(source_title, target_project, sync_config):
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

    # Search for work item by title in target project
    work_item_id = search_work_item_by_title(target_title, target_project)

    if work_item_id:
        appLogger.info(f"Found target work item ID: {work_item_id}")
        # Get and print target work item details
        get_work_item_details(work_item_id, target_project)
    else:
        appLogger.info(f"Target work item not found with title: {target_title}")

    return work_item_id
