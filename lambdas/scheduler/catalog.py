from config import config, table, s3_client
from utils import to_plain
import datetime, json


def build_and_write():
    groups = {}
    scan_kwargs = {}
    while True:
        resp = table.scan(**scan_kwargs)
        for it in resp.get("Items", []):
            g = it["group_id"]
            entry = groups.setdefault(g, {
                "group_id": g,
                "weekdays": set(),
                "hours": set(),
                "interval_days": it["interval_days"],
                "anchor_date": it.get("anchor_date"),
                "description": it.get("description"),
                "enabled_any": False
            })
            entry["weekdays"].add(it["day_of_week"])
            entry["hours"].add(it["hour"])
            if it.get("enabled"):
                entry["enabled_any"] = True
        if "LastEvaluatedKey" in resp:
            scan_kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
        else:
            break

    catalog = {
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "job_groups": []
    }
    for g, v in groups.items():
        catalog["job_groups"].append({
            "group_id": g,
            "weekdays": sorted(v["weekdays"]),
            "hours": sorted(v["hours"]),
            "interval_days": v["interval_days"],
            "anchor_date": v["anchor_date"],
            "description": v["description"],
            "enabled_any": v["enabled_any"]
        })
    plain = to_plain(catalog)
    s3_client.put_object(
        Bucket=config.bucket,
        Key=config.catalog_key,
        Body=json.dumps(plain, indent=2),
        ContentType="application/json"
    )
