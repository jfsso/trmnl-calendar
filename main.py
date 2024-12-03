from dotenv import load_dotenv
import datetime
import icalendar
import json
import locale
import os
import pytz
import recurring_ical_events
import requests

load_dotenv()

DEBUG = os.getenv('DEBUG', default=False)
trmnl_title = os.getenv('TRMNL_TITLE', default='Calendar')
trmnl_webhook_url = os.getenv('TRMNL_WEBHOOK_URL')
trmnl_ics_urls = os.getenv('TRMNL_ICS_URL', default='').split(',')
trmnl_days = int(os.getenv('TRMNL_DAYS', default='30'))
trmnl_tz = os.getenv('TRMNL_TZ')
trmnl_date_format = os.getenv('TRMNL_DATE_FORMAT', default='%x (%a)')
trmnl_time_format = os.getenv('TRMNL_TIME_FORMAT', default='%H:%M')
trmnl_updated_at_format = os.getenv('TRMNL_UPDATED_AT_FORMAT', default='%x %X')
trmnl_locale = os.getenv('TRMNL_LOCALE')
trmnl_number_columns = int(os.getenv('TRMNL_NUMBER_COLUMNS', default='5'))

if trmnl_locale:
    locale.setlocale(locale.LC_ALL, trmnl_locale)

now = datetime.datetime.now(pytz.timezone(trmnl_tz))
start_date = now.date()

merged_calendar = icalendar.Calendar()
for ics_url in trmnl_ics_urls:
    ics_url = ics_url.strip()
    if not ics_url:
        continue
    response = requests.get(ics_url)
    response.raise_for_status()
    calendar = icalendar.Calendar.from_ical(response.text)

    # this will keep the calendar timezone
    for name, value in calendar.property_items(recursive=False):
        merged_calendar.add(name, value)

    for component in calendar.walk('VEVENT'):
        merged_calendar.add_component(component)

#merged_calendar.add_missing_timezones()
query = recurring_ical_events.of(merged_calendar)

results = []

for i in range(trmnl_days):
    date = start_date + datetime.timedelta(days=i)
    events = query.at(date)
    if len(events) == 0:
        continue

    json_events = []

    def sort_date(e):
        return e["DTSTART"].dt.strftime("%H:%M")
    events.sort(key=sort_date)

    if DEBUG:
        print(f"--- {date.strftime(trmnl_date_format)} ---")
    for event in events:
        start = event["DTSTART"].dt.strftime(trmnl_time_format) if "DTSTART" in event else "00:00"
        end = event["DTEND"].dt.strftime(trmnl_time_format) if "DTEND" in event else "23:59"
        summary = event.get("SUMMARY", "No Title")
        all_day = isinstance(event["DTSTART"].dt, datetime.date) and not isinstance(event["DTSTART"].dt, datetime.datetime)
        if all_day:
            if DEBUG:
                print(f"{summary}")
            json_events.append({"summary": summary})
        else:
            if DEBUG:
                print(f"{start}-{end} {summary}")
            json_events.append({"summary": summary, "start": start, "end": end})

    results.append({"date": date.strftime(trmnl_date_format), "events": json_events})

webhook_body = {
    "merge_variables": {
        "updated_at": now.strftime(trmnl_updated_at_format),
        "title": trmnl_title,
        "calendar": results,
        "columns": trmnl_number_columns
    }
}
json_string = json.dumps(webhook_body)
if DEBUG:
    print(json_string)

r = requests.post(trmnl_webhook_url, json=webhook_body)
if DEBUG:
    print(r.status_code)
    print(r.text)
