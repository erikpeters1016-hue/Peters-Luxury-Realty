import os
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

LA = ZoneInfo("America/Los_Angeles")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar",
]


def get_calendar_service():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file("google-credentials.json", scopes=SCOPES)
    return build("calendar", "v3", credentials=creds)


def check_availability(date_str):
    """Return available 1-hour slots on date_str (YYYY-MM-DD), 9 AM–5 PM PT."""
    calendar_id = os.environ.get("CALENDAR_ID", "primary")
    service = get_calendar_service()

    date = datetime.strptime(date_str, "%Y-%m-%d")
    day_start = datetime(date.year, date.month, date.day, 9, 0, tzinfo=LA)
    day_end = datetime(date.year, date.month, date.day, 17, 0, tzinfo=LA)

    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=day_start.isoformat(),
        timeMax=(day_end + timedelta(hours=1)).isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    booked = []
    for event in events_result.get("items", []):
        start = event["start"].get("dateTime")
        end = event["end"].get("dateTime")
        if start and end:
            booked.append((
                datetime.fromisoformat(start).astimezone(LA),
                datetime.fromisoformat(end).astimezone(LA),
            ))

    available = []
    slot = day_start
    while slot <= day_end:
        slot_end = slot + timedelta(hours=1)
        conflict = any(slot < e and slot_end > s for s, e in booked)
        if not conflict:
            available.append(slot.strftime("%I:%M %p").lstrip("0"))
        slot += timedelta(hours=1)

    return available


def book_showing(date_str, time_str, property_address, buyer_name, buyer_contact):
    """Create a 1-hour showing event and return the calendar event link."""
    calendar_id = os.environ.get("CALENDAR_ID", "primary")
    service = get_calendar_service()

    start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %I:%M %p").replace(tzinfo=LA)
    end_dt = start_dt + timedelta(hours=1)

    event = {
        "summary": f"Showing: {property_address}",
        "description": (
            f"Buyer: {buyer_name}\n"
            f"Contact: {buyer_contact}\n"
            f"Booked via Riley (AI Concierge)"
        ),
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "America/Los_Angeles"},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": "America/Los_Angeles"},
    }

    created = service.events().insert(calendarId=calendar_id, body=event).execute()
    return created.get("htmlLink", "")
