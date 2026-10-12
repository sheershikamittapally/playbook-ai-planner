from icalendar import Calendar
from datetime import (
    datetime,
    date
)
from zoneinfo import ZoneInfo
import hashlib
import boto3
import os
import urllib.request

table = boto3.resource("dynamodb", region_name="us-east-1").Table(os.environ["TABLE_NAME"])
ssm = boto3.client("ssm", region_name="us-east-1")
cutoff = date(2026, 8, 1)
USER_ID = "dev_user"

def lambda_handler(event, context):
    response = ssm.get_parameter(Name="/playbook/schoology-feed-url", WithDecryption=True)
    link = response["Parameter"]["Value"]
    data = urllib.request.urlopen(link, timeout=10).read()
    cal = Calendar.from_ical(data)

    new_count = 0
    changed_count = 0
    unchanged_count = 0

    for vevent in cal.walk("VEVENT"):
        due = vevent.get("DTSTART").dt
        if isinstance(due, datetime):
            due = due.astimezone(ZoneInfo("America/New_York")).date()
        if due >= cutoff:
            title = " ".join(str(vevent.get("SUMMARY")).split())
            description = str(vevent.get("DESCRIPTION", ""))
            fingerprint_source = title + "|" + due.isoformat() + "|" + description
            feed_hash = hashlib.sha256(fingerprint_source.encode()).hexdigest()
            task = {
                "user_id": USER_ID,
                "task_id": "sch#"+str(vevent.get("UID")),
                "title": title,
                "due_date": due.isoformat(),
                "source": "schoology",
                "feed_hash": feed_hash
            }
            existing = table.get_item(Key={"user_id": USER_ID, "task_id": task["task_id"]}).get("Item")
            if existing is None:
                task["status"] = "open"
                task["created_at"] = datetime.now(ZoneInfo("UTC")).isoformat()
                table.put_item(Item=task)
                new_count += 1
            elif existing["feed_hash"] != feed_hash:
                table.update_item(
                    Key={"user_id": USER_ID, "task_id": task["task_id"]},
                    UpdateExpression="SET #t = :t, #d = :d, #h = :h, #u = :u",
                    ExpressionAttributeNames={"#t": "title", "#d": "due_date", "#h": "feed_hash", "#u": "updated_at"},
                    ExpressionAttributeValues={":t": title, ":d": due.isoformat(), ":h": feed_hash, ":u": datetime.now(ZoneInfo("UTC")).isoformat()}
                )
                changed_count += 1
            else:
                unchanged_count += 1

    print("new:", new_count, "changed:", changed_count, "unchanged:", unchanged_count)
    return {"new": new_count, "changed": changed_count, "unchanged": unchanged_count}

if __name__ == "__main__":
    lambda_handler({}, None)