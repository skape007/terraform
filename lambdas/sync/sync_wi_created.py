import json
from functions.logger import appLogger


def handle_work_item_created(resource: dict) -> dict:

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
