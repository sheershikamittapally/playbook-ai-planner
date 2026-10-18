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
USER_ID = "dev_user"

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
    
    print(len(open_tasks))
    print(prompt)
    return prompt

if __name__ == "__main__":
    lambda_handler({}, None)