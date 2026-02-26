from config import ses_client, config
from utils import fallback_recipients
from models import JobItem
from html_builder import build_email_html


def send_job_email(item: JobItem, mode_prefix: str | None = None, demo: bool = False):
    html = build_email_html(item, mode_prefix)
    recipients = fallback_recipients(item.email_config.recipient, config.notify_fallback)
    if demo and recipients:
        recipients = [recipients[0]]
    subject = item.email_config.email_title
    if mode_prefix:
        subject = f"{mode_prefix} {subject}"
    ses_client.send_email(
        Source=config.ses_sender,
        Destination={'ToAddresses': recipients},
        Message={'Subject': {'Data': subject},
                 'Body': {'Html': {'Data': html}}}
    )
    return {"subject": subject, "recipients": recipients, "demo": demo}
