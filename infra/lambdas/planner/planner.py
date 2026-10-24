import boto3, os
from boto3.dynamodb.conditions import Key
from datetime import (
    datetime,
    date,
    timedelta
)
from zoneinfo import ZoneInfo
import json

table = boto3.resource("dynamodb", region_name="us-east-1").Table(os.environ["TABLE_NAME"])
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
USER_ID = "dev_user"

def build_schedule(open_tasks, judgements, today):
    work = []
    for t in open_tasks:
        j = judgements.get(t["task_id"], {})
        if t["remaining_minutes"] is not None:
            minutes = t["remaining_minutes"]
            estimated = False
        else:
            minutes = j.get("est_minutes")
            estimated = True
            if minutes is None:
                minutes = 30
                estimated = True
        target = date.fromisoformat(t["due_by"])
        if j.get("start_early") is True:
            target = target - timedelta(days=1)
        
        work.append({
            "task_id": t["task_id"],
            "minutes": minutes,
            "estimated": estimated,
            "target": target,
            "note": j.get("note", ""),
        })

    work.sort(key=lambda w: w["target"])

    days = []
    for i in range(7):
        d = today + timedelta(days=i)
        limit = 150 if d.weekday() < 5 else 180
        days.append({
            "date": d.isoformat(),
            "left": limit,
            "blocks": []
        })

    overflow = []
    for w in work:
        left = w["minutes"]
        last = (w["target"] - today).days
        if last < 0:
            last = 0
        if last > 6:
            last = 6
        placed = []
        for day in days[0 : last + 1]:
            if left == 0:
                break
            chunk = min(60, left, day["left"])
            if chunk > 0:
                block = {
                    "task_id": w["task_id"],
                    "minutes_today": chunk,
                    "estimated": w["estimated"],
                    "note": w["note"],
                }
                day["blocks"].append(block)
                placed.append(block)
                left -= chunk
                day["left"] -= chunk
    
        overflow.append((w, last, left, placed))
    
    for w, last, left, placed in overflow:
        if left > 0:
            block = {
                "task_id": w["task_id"],
                "minutes_today": left,
                "estimated": w["estimated"],
                "note": "Over limit",
            }
            days[last]["blocks"].append(block)
            placed.append(block)
            days[last]["left"] -= left
        if len(placed) > 1:
            for i, b in enumerate(placed, start=1):
                if b["note"] != "Over limit":
                    b["note"] = f"Part {i} of {len(placed)}"

    print(days)
    return days

def lambda_handler(event, context):
    date_today = datetime.now(ZoneInfo("America/New_York")).date()
    overdue_cutoff = date_today - timedelta(days=7)
    items = table.query(KeyConditionExpression=Key("user_id").eq(USER_ID)).get("Items", [])

    open_tasks = []
    ai_tasks = []
    for x in items:
        if x.get("status") != "open":
            continue
        if date.fromisoformat(x["due_date"]) < overdue_cutoff:
            continue

        if x.get("est_minutes") is None:
            remaining_minutes = None
        else:
            remaining_minutes = int(x["est_minutes"]) - int(x.get("minutes_done", 0))

        open_tasks.append({
            "task_id": x["task_id"],
            "title": x["title"],
            "subject": x.get("subject", ""),
            "due_by": x["due_date"],
            "remaining_minutes": remaining_minutes
        })
        ai_tasks.append({
            "task_id": x["task_id"],
            "title": x["title"],
            "subject": x.get("subject", ""),
            "remaining_minutes": remaining_minutes
        })

    tasks_json = json.dumps(ai_tasks)
    
    prompt_path = os.path.join(os.path.dirname(__file__), "prompt.txt")
    with open(prompt_path, "r") as f:
        template = f.read()
        
    prompt = (template
              .replace("{today}", date_today.isoformat())
              .replace("{tasks}", tasks_json)
              .replace("{late_history}", "[]"))

    response = bedrock.converse(
        modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"temperature": 0, "maxTokens": 2000}
    )

    reply_text = response["output"]["message"]["content"][0]["text"]
    
    start = reply_text.find("[")
    end = reply_text.rfind("]") + 1
    clean = reply_text[start:end]

    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        print("invalid JSON:", reply_text)
        return {}

    if not isinstance(parsed, list):
        print("expected a list, got:", type(parsed))
        return {}

    valid_ids = {t["task_id"] for t in open_tasks}
    judgements = {}
    for item in parsed:
            if item.get("task_id") not in valid_ids:
                continue
            if not isinstance(item.get("start_early"), bool):
                continue
            if "est_minutes" in item and not isinstance(item["est_minutes"], (int, float)):
                continue
            judgements[item["task_id"]] = item
    
    print(len(judgements), "of", len(open_tasks), "tasks passed validation")

    work = build_schedule(open_tasks, judgements, date_today)
    return work

if __name__ == "__main__":
    lambda_handler({}, None)