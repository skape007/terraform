import json
import traceback
from config import ses_client
from config import config, table, s3_client
from models import JobFile, ScheduleDef, EmailConfig, QueryDef, JobItem
from utils import validate_group_id, fallback_recipients, dynamodb_to_plain
from email_service import send_job_email
from functions.logger import appLogger


def parse_job_json(group_id: str, raw: dict) -> JobFile:
    if not validate_group_id(group_id):
        raise ValueError("Invalid group_id / filename pattern.")
    if raw.get("id") and raw["id"] != group_id:
        raise ValueError("JSON id differs from filename.")
    schedule = raw.get("schedule")
    email_cfg = raw.get("email_config")
    if not schedule or not email_cfg:
        raise ValueError("Missing 'schedule' or 'email_config'")
    interval = schedule["interval_days"]
    if interval in (14, 30) and not schedule.get("anchor_date"):
        raise ValueError("anchor_date required for interval_days > 7")
    if interval not in config.allowed_intervals:
        raise ValueError("interval_days not allowed")
    queries = []
    for q in email_cfg.get("queries", []):
        if "title" not in q or "id" not in q:
            raise ValueError("query requires 'title' and 'id'")
        queries.append(QueryDef.from_dict(q))
    job = JobFile(
        group_id=group_id,
        description=raw.get("description"),
        schedule=ScheduleDef(
            day_of_week=[d.upper() for d in schedule["day_of_week"]],
            hour=int(schedule["hour"]),
            interval_days=int(interval),
            anchor_date=schedule.get("anchor_date")
        ),
        email_config=EmailConfig(
            recipient=email_cfg["recipient"],
            email_title=email_cfg["email_title"],
            intro_title=email_cfg.get("intro_title"),
            intro_body=email_cfg.get("intro_body"),
            comments=bool(email_cfg.get("comments", False)),
            feedback=bool(email_cfg.get("feedback", False)),
            team=email_cfg.get("team"),
            queries=queries
        ),
        enabled=bool(raw.get("enabled", True)),
        version=raw.get("version"),
        demo_on_ingest=bool(raw.get("demo_on_ingest", False))
    )
    return job

def ingest_object(key: str):
    group_id = key.split("/")[-1].removesuffix(".json")
    obj = s3_client.get_object(Bucket=config.bucket, Key=key)
    appLogger.info(f"[INGEST] Successfully fetched job file {key}")
    data = json.loads(obj["Body"].read().decode())
    appLogger.debug(f"[INGEST] Loaded job file content: {json.dumps(data, indent=2)}")
    try:
        job = parse_job_json(group_id, data)
    except Exception as e:
        appLogger.error(f"[INGEST] Error parsing job file {key}: {e}")
        _send_failure(group_id, str(e), data.get("email_config", {}).get("recipient"))
        return

    upserted = []
    for dow in job.schedule.day_of_week:
        item_id = f"{job.group_id}__{dow}"
        time_slot = f"{dow}#{job.schedule.hour:02d}"
        existing = table.get_item(Key={"id": item_id}).get("Item")
        last_run = existing.get("last_run") if existing else None
        table.put_item(Item={
            "id": item_id,
            "group_id": job.group_id,
            "description": job.description,
            "day_of_week": dow,
            "hour": job.schedule.hour,
            "interval_days": job.schedule.interval_days,
            "anchor_date": job.schedule.anchor_date,
            "enabled": job.enabled,
            "email_config": {
                "recipient": job.email_config.recipient,
                "email_title": job.email_config.email_title,
                "intro_title": job.email_config.intro_title,
                "intro_body": job.email_config.intro_body,
                "comments": job.email_config.comments,
                "feedback": job.email_config.feedback,
                "team": job.email_config.team,
                "queries": [vars(q) for q in job.email_config.queries]
            },
            "version": job.version,
            "time_slot": time_slot,
            "original_weekdays": job.schedule.day_of_week,
            "last_run": last_run
        })
        upserted.append(item_id)

    _send_success(job.group_id, upserted, job.email_config.recipient, job.demo_on_ingest)

def _send_failure(group_id: str, reason: str, recipient: str | None):
    body = f"<h3>FAILURE</h3><p>{reason}</p>"
    ses_client.send_email(
        Source=config.ses_sender,
        Destination={'ToAddresses': fallback_recipients(recipient, config.notify_fallback)},
        Message={'Subject': {'Data': f"Job {group_id} FAILURE"},
                 'Body': {'Html': {'Data': body}}}
    )

def _send_success(group_id: str, ids, recipient: str, demo: bool):
    body = "<h3>SUCCESS</h3><p>Items upserted:</p><ul>" + "".join(f"<li>{i}</li>" for i in ids) + "</ul>"
    body += f"<p>Demo on ingest: {'ENABLED' if demo else 'DISABLED'}</p>"

    email = ""
    if isinstance (recipient, list) and recipient:
        email = recipient[0]
    elif isinstance(recipient, str):
        email = recipient

    ses_client.send_email(
        Source=config.ses_sender,
        Destination={'ToAddresses': fallback_recipients(email, config.notify_fallback)},
        Message={'Subject': {'Data': f"Job {group_id} SUCCESS"},
                 'Body': {'Html': {'Data': body}}}
    )
    if demo:
        try:
            item_id = ids[0]
            saved = table.get_item(Key={"id": item_id}).get("Item")
            plain_saved = dynamodb_to_plain(saved)
            ec = EmailConfig.from_dict(plain_saved["email_config"])
            if isinstance(ec.recipient, list) and ec.recipient:
                ec.recipient = [ec.recipient[0]]
            elif isinstance(ec.recipient, str):
                ec.recipient = [ec.recipient]
            ji = JobItem(
                id=plain_saved["id"], group_id=plain_saved["group_id"], day_of_week=plain_saved["day_of_week"],
                hour=plain_saved["hour"], interval_days=plain_saved["interval_days"], anchor_date=plain_saved.get("anchor_date"),
                enabled=plain_saved["enabled"], email_config=ec, description=plain_saved.get("description"),
                version=plain_saved.get("version"), time_slot=plain_saved["time_slot"],
                original_weekdays=plain_saved["original_weekdays"], last_run=plain_saved.get("last_run")
            )
            send_job_email(ji, mode_prefix="[DEMO AFTER INGEST]", demo=True)
            appLogger.info(f"[INGEST] Sending demo email for group_id {group_id} to {ec.recipient}")
        except Exception as e:
            appLogger.error(f"[DEMO] Failed: {e}\n{traceback.format_exc()}")