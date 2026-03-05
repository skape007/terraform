from config import config
from ingestion import ingest_object
from deletion import delete_object
from catalog import build_and_write
from scheduler import run_slot
from functions.logger import appLogger


def lambda_handler(event, context):
    appLogger.info(f"Lambda triggered: event={event}")

    if "Records" in event:
        for rec in event["Records"]:
            if rec.get("eventSource") == "aws:s3":
                key = rec["s3"]["object"]["key"]
                if key.startswith(config.active_prefix):
                    ingest_object(key)
                    build_and_write()
                    appLogger.info(f"[S3] Ingested: {key}")
                elif key.startswith(config.deleted_prefix):
                    delete_object(key)
                    build_and_write()
                    appLogger.info(f"[S3] Deleted: {key}")
        return

    if event.get("detail-type") == "Scheduled Event":
        result = run_slot()
        appLogger.info(f"[SCHEDULED] {result}")
        return

    appLogger.warning(f"[NOOP] Unsupported event: {event}")
