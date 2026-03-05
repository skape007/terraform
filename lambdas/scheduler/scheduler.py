from datetime import datetime
from config import table, config
from boto3.dynamodb.conditions import Key
from utils import should_run
from models import JobItem, EmailConfig
from email_service import send_job_email
from functions.logger import appLogger


def run_slot() -> dict:
    now = datetime.utcnow()
    weekday = now.strftime("%a").upper()
    hour = f"{now.hour:02d}"
    slot = f"{weekday}#{hour}"
    today_iso = now.date().isoformat()
    resp = table.query(
        IndexName=config.gsi_index_name,
        KeyConditionExpression=Key(config.gsi_hash_key).eq(slot),
    )
    items = resp.get("Items", [])
    executed = []
    skipped = []
    for it in items:
        if it.get("enabled") and should_run(it["interval_days"], it.get("last_run"), it.get("anchor_date"), today_iso):
            try:
                ec = EmailConfig.from_dict(it["email_config"])
                ji = JobItem(
                    id=it["id"], group_id=it["group_id"], day_of_week=it["day_of_week"],
                    hour=it["hour"], interval_days=it["interval_days"], anchor_date=it.get("anchor_date"),
                    enabled=it["enabled"], email_config=ec, description=it.get("description"),
                    version=it.get("version"), time_slot=it["time_slot"],
                    original_weekdays=it["original_weekdays"], last_run=it.get("last_run")
                )
                send_job_email(ji)
                table.update_item(Key={"id": it["id"]},
                                  UpdateExpression="SET last_run=:d",
                                  ExpressionAttributeValues={":d": today_iso})
                executed.append(it["id"])
            except Exception as e:
                appLogger.error(f"[EXEC_FAIL] {it['id']}: {e}")
                skipped.append(it["id"])
        else:
            skipped.append(it["id"])
    return {"time_slot": slot, "executed": executed, "skipped": skipped, "queried": len(items)}
