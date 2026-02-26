import re
from decimal import Decimal
from typing import Any, Dict, List
import boto3.dynamodb.types

VALID_GROUP_ID = re.compile(r'^[a-z0-9][a-z0-9_\-]{2,80}$')

def validate_group_id(group_id: str) -> bool:
    return bool(VALID_GROUP_ID.match(group_id))

def to_plain(value: Any):
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    if isinstance(value, dict):
        return {k: to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_plain(v) for v in value]
    if isinstance(value, tuple):
        return tuple(to_plain(v) for v in value)
    return value


def fallback_recipients(recipient, fallback):
    if isinstance(recipient, list):
        return recipient if recipient else ([fallback] if fallback else [])
    if recipient:
        return [recipient]
    return [fallback] if fallback else []


def should_run(interval_days: int, last_run: str | None, anchor_date: str | None, today_iso: str) -> bool:
    from datetime import date
    today = date.fromisoformat(today_iso)
    if interval_days in (1, 7):
        return last_run != today_iso
    if anchor_date:
        anchor_dt = date.fromisoformat(anchor_date)
        diff = (today - anchor_dt).days
        if diff < 0 or diff % interval_days != 0:
            return False
        return last_run != today_iso
    # fallback spacing
    if not last_run:
        return True
    return (today - date.fromisoformat(last_run)).days >= interval_days

def dynamodb_to_plain(item):
    """
    Recursively converts DynamoDB attribute format to plain Python types.
    - If item is a DynamoDB attribute dict (contains keys like 'S', 'N', 'M', etc), convert it.
    - If item is a dict of attribute dicts (full DynamoDB item), convert each field.
    - If item is already a simple type (bool, str, int, float, None), return as-is.
    """
    deserializer = boto3.dynamodb.types.TypeDeserializer()
    dynamodb_keys = {"S", "N", "BOOL", "NULL", "L", "M", "B", "SS", "NS", "BS"}
    if isinstance(item, dict):
        # If the dict looks like a DynamoDB attribute-value, deserialize it.
        if set(item.keys()) & dynamodb_keys:
            return deserializer.deserialize(item)
        # Otherwise, recursively convert each value.
        return {k: dynamodb_to_plain(v) for k, v in item.items()}
    elif isinstance(item, list):
        return [dynamodb_to_plain(v) for v in item]
    else:
        # Already plain (bool, str, int, float, None)
        return item

