from config import config
from ingestion import ingest_object
from deletion import delete_object
from catalog import build_and_write
from scheduler import run_slot
from functions.logger import appLogger


def lambda_handler(event, context):
    # S3 events
    appLogger.info(f"Lambda triggered: event={event}")
    if "Records" in event:
        for rec in event["Records"]:
            if rec.get("eventSource") == "aws:s3":
                key = rec["s3"]["object"]["key"]
                if key.startswith(config.active_prefix):
                    ingest_object(key)
                    build_and_write()
                elif key.startswith(config.deleted_prefix):
                    delete_object(key)
                    build_and_write()
        return {"status": "s3_processed"}

    # Scheduled events
    if event.get("detail-type") == "Scheduled Event":
        return run_slot()

    # Manual triggers removed deliberately
    return {"status": "noop", "reason": "Unsupported event"}
