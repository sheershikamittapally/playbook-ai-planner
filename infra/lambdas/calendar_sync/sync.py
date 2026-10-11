from icalendar import Calendar
from datetime import (
    datetime,
    date
)
from zoneinfo import ZoneInfo

with open("/Users/sheershikamittapally/Downloads/ical.ics", "rb") as f:
    data=f.read()
    cal=Calendar.from_ical(data)

cutoff=date(2026, 8, 1)

for event in cal.walk("VEVENT"):
    due=event.get("DTSTART").dt
    if isinstance(due, datetime):
        due=due.astimezone(ZoneInfo("America/New_York")).date()
    if due>=cutoff:
        print(event.get("SUMMARY"), due, type(due), event.get("UID"))