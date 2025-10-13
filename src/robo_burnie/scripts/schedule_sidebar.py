from __future__ import annotations

import logging
import os.path
import sys
import time
from datetime import datetime, timedelta
from typing import Any

import praw
import pytz
from dateutil.parser import parse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

from robo_burnie import _helpers
from robo_burnie._constants import TEAM_ID_TO_INFO
from robo_burnie.private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)


SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_ID = "heat.sub.mods@gmail.com"


def _main() -> None:
    """Updates the Google Calendar with the Heat's schedule and resyncs the schedule widget on Reddit"""
    current_time = datetime.now(tz=pytz.utc).isoformat()
    service = _get_google_calendar_service()
    events_map = _build_events_map(service, current_time)
    _update_google_calendar(service, current_time, events_map)
    _sync_schedule_widget()


def _get_google_calendar_service() -> Resource:
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "google_credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("calendar", "v3", credentials=creds)

    return service


def _build_events_map(service: Resource, current_time: str) -> dict:
    """Build a map of events in the calendar"""
    events_list = (
        service.events().list(calendarId=CALENDAR_ID, timeMin=current_time).execute()
    )
    events_map = {}
    for event in events_list["items"]:
        events_map[event["id"]] = event

    return events_map


def _update_google_calendar(service: Any, current_time: str, events_map: dict[Any]):
    """Update the Google Calendar with the Heat's schedule"""
    all_games = _helpers.get_full_team_schedule("heat")
    for game in all_games:
        # skip games in the past
        if game["gameDateTimeUTC"] < current_time:
            continue

        event_data = _generate_event_data(game)
        if game["gameId"] not in events_map:
            service.events().insert(calendarId=CALENDAR_ID, body=event_data).execute()
        else:
            service.events().update(
                calendarId=CALENDAR_ID, eventId=game["gameId"], body=event_data
            ).execute()

        # Brief pause to avoid rate limits
        time.sleep(0.5)

    logging.info("Calender Updated")


def _generate_event_data(game: dict) -> dict:
    """Generate the event data for the game"""
    event_summary = _generate_event_summary(game)
    start, end = _generate_event_start_end_times(game)
    event_data = {
        "id": game["gameId"],
        "summary": event_summary,
        "start": {"dateTime": start, "timeZone": "America/New_York"},
        "end": {"dateTime": end, "timeZone": "America/New_York"},
    }
    return event_data


def _generate_event_summary(game: dict) -> str:
    """Generate the summary for the event"""
    if game["homeTeam"]["teamSlug"] == "heat":
        summary = TEAM_ID_TO_INFO[str(game["awayTeam"]["teamId"])]["nickname"]
    else:
        summary = "@" + TEAM_ID_TO_INFO[str(game["homeTeam"]["teamId"])]["nickname"]

    if game["gameLabel"].lower():
        summary += f" ({game['gameLabel']})"

    return summary


def _generate_event_start_end_times(game: dict) -> tuple[str, str]:
    """Generate the start and end times for the event"""
    utc_datetime = parse(game["gameDateTimeUTC"])
    eastern_datetime = utc_datetime.replace(tzinfo=pytz.utc).astimezone(
        pytz.timezone("US/Eastern")
    )
    eastern_start_str = eastern_datetime.isoformat()
    eastern_end_str = (
        eastern_datetime + timedelta(hours=2) + timedelta(minutes=30)
    ).isoformat()

    return eastern_start_str, eastern_end_str


def _sync_schedule_widget() -> None:
    # Connect to Reddit
    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET_KEY,
        password=BOT_PASSWORD,
        user_agent="Game Bot for r/heat",
        username="RoboBurnie",
    )

    # Find schedule widget
    widgets = reddit.subreddit("heat").widgets
    schedule_widget = None
    for widget in widgets.sidebar:
        if widget.shortName.lower() == "schedule":
            schedule_widget = widget
            break

    schedule_widget.mod.update(requiresSync=True)
    logging.info("Schedule widget synced")


if __name__ == "__main__":
    _main()
