import json
from config import config, table, s3_client, ses_client
from utils import fallback_recipients
from functions.logger import appLogger


def delete_object(key: str):
    group_id = key.split("/")[-1].removesuffix(".json")
    obj = s3_client.get_object(Bucket=config.bucket, Key=key)
    try:
        data = json.loads(obj["Body"].read().decode())
    except Exception:
        data = {}
    if config.require_delete_confirm and not data.get("confirm_delete", False):
        appLogger.error(f"[DELETE] Delete confirm missing for {group_id}, aborting deletion.")
        _send_delete_email(group_id, [], failure=True)
        return
    items = []
    scan_kwargs = {}
    while True:
        resp = table.scan(**scan_kwargs)
        for it in resp.get("Items", []):
            if it.get("group_id") == group_id:
                appLogger.info(f"[DELETE] DynamoDB item: {json.dumps(it, default=str)}")
                items.append(it)
        if "LastEvaluatedKey" in resp:
            scan_kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
        else:
            break
    deleted = []
    recipients = set()
    for it in items:
        table.delete_item(Key={"id": it["id"]})
        deleted.append(it["id"])
        appLogger.info(f"[DELETE] email_config for {it['id']}: {it.get('email_config')}")
        rcpt = it.get("email_config", {}).get("recipient")
        appLogger.info(f"[DELETE] recipient extracted for {it['id']}: {rcpt}")
        if rcpt:
            recipients.add(rcpt)

    appLogger.info(f"[DELETE] All recipients collected: {recipients}")
    _send_delete_email(group_id, deleted, recipients=recipients)

def _send_delete_email(group_id: str, deleted_ids, recipients=None, failure=False):
    subject = f"Job {group_id} {'DELETE FAILED' if failure else ('DELETED' if deleted_ids else 'NOOP_DELETE')}"
    if failure:
        body = "<h3>DELETE FAILED</h3><p>Missing confirm_delete flag.</p>"
    elif deleted_ids:
        body = ("<h3>DELETED</h3>"
                f"<p>Items removed: {len(deleted_ids)}</p>"
                "<ul>" + "".join(f"<li>{d}</li>" for d in deleted_ids) + "</ul>")
    else:
        body = "<h3>NOOP DELETE</h3><p>No items found.</p>"
    to = list(recipients) if recipients else []
    to = fallback_recipients(to[0] if len(to) == 1 else None, config.notify_fallback) if not to else to
    appLogger.info(f"[DELETE] Final recipient list for SES: {to}")
    if not to or not to[0]:
        appLogger.error(f"[DELETE] No valid recipients found for job {group_id}. Skipping email send.")
        return
    ses_client.send_email(
        Source=config.ses_sender,
        Destination={'ToAddresses': to},
        Message={'Subject': {'Data': subject}, 'Body': {'Html': {'Data': body}}}
    )