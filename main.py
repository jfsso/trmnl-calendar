from dotenv import load_dotenv
import datetime
import icalendar
import json
import os
import pytz
import recurring_ical_events
import requests

load_dotenv()

DEBUG = os.getenv('DEBUG', default=False)
trmnl_title = os.getenv('TRMNL_TITLE', default='Calendar')
trmnl_webhook_url  = os.getenv('TRMNL_WEBHOOK_URL')
trmnl_ics_url = os.getenv('TRMNL_ICS_URL')
trmnl_days = int(os.getenv('TRMNL_DAYS', default='30'))
trmnl_tz = os.getenv('TRMNL_TZ')

calendar = icalendar.Calendar.from_ical(requests.get(trmnl_ics_url).text)

now = datetime.datetime.now(pytz.timezone(trmnl_tz))
now_date = now.date()

query = recurring_ical_events.of(calendar)

results = []

for i in range(0, trmnl_days):
  date= now_date + datetime.timedelta(days=i)
  events = query.at(date)
  if len(events) == 0:
    continue

  json_events = []

  def sortDate(e):
    return e["DTSTART"].dt.strftime("%H:%M")
  events.sort(key=sortDate)

  if DEBUG: print(f"--- {date} ---")
  for event in events:
    start = event["DTSTART"].dt.strftime("%H:%M")
    end = event["DTEND"].dt.strftime("%H:%M")
    summary = event["SUMMARY"]
    all_day = type(event["DTSTART"].dt) is datetime.date
    if all_day:
      if DEBUG: print(f"{summary}")
      json_events.append({"summary": summary})
    else:
      if DEBUG: print(f"{start}-{end} {summary}")
      json_events.append({"summary": summary, "start": start, "end": end})

  results.append({"date": date.strftime("%Y-%m-%d (%a)"), "events":json_events})

webhook_body = {"merge_variables": {"updated_at": now.strftime("%Y-%m-%d %H:%M"), "title": trmnl_title, "calendar": results}}
json_string = json.dumps(webhook_body)
if DEBUG: print(json_string)

r = requests.post(trmnl_webhook_url, json=webhook_body)
if DEBUG: print(r.status_code) 
if DEBUG: print(r.text)

