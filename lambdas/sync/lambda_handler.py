import json
from config import config
from lambdas.sync.sync_wi_created import handle_work_item_created
from lambdas.sync.sync_wi_updated import handle_work_item_updated
from functions.logger import appLogger

def lambda_handler(event: dict, context) -> dict:

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

