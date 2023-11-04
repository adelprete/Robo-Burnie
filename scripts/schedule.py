import logging
import os.path
import sys
import time
from datetime import datetime, timedelta

import praw
import pytz
from dateutil.parser import parse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

from constants import TEAM_ID_TO_INFO
from private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY
from scripts import helpers

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)


SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_ID = "heat.sub.mods@gmail.com"
YEAR = 2021


def build_games_map() -> dict:
    all_games = helpers.get_full_team_schedule()

    games_map = {}
    for game in all_games:
        games_map[game["gameId"]] = game

    return games_map


def get_google_calendar_service() -> Resource:
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
            flow = InstalledAppFlow.from_client_secrets_file("creds.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("calendar", "v3", credentials=creds)

    return service


def build_events_map(service: Resource, current_time: str) -> dict:
    events_list = (
        service.events().list(calendarId=CALENDAR_ID, timeMin=current_time).execute()
    )
    events_map = {}
    for event in events_list["items"]:
        events_map[event["id"]] = event

    return events_map


def main() -> None:
    # game_map = build_games_map()
    all_games = helpers.get_full_team_schedule(YEAR)

    service = get_google_calendar_service()
    current_time = datetime.now(tz=pytz.utc).isoformat()
    events_map = build_events_map(service, current_time)

    for game in all_games:
        # skip games in the past
        if game["startTimeUTC"] < current_time:
            continue

        # Make our summary
        if game["isHomeTeam"]:
            summary = TEAM_ID_TO_INFO[game["vTeam"]["teamId"]]["nickname"]
        else:
            summary = "@" + TEAM_ID_TO_INFO[game["hTeam"]["teamId"]]["nickname"]

        if game["seasonStageId"] == 1:
            summary += " (preseason)"

        # convert time to eastern
        utc_datetime = parse(game["startTimeUTC"])
        eastern_datetime = utc_datetime.replace(tzinfo=pytz.utc).astimezone(
            pytz.timezone("US/Eastern")
        )
        eastern_start_str = eastern_datetime.isoformat()
        eastern_end_str = (
            eastern_datetime + timedelta(hours=2) + timedelta(minutes=30)
        ).isoformat()

        event_data = {
            "id": game["gameId"],
            "summary": summary,
            "start": {"dateTime": eastern_start_str, "timeZone": "America/New_York"},
            "end": {"dateTime": eastern_end_str, "timeZone": "America/New_York"},
        }
        if game["gameId"] not in events_map:
            service.events().insert(calendarId=CALENDAR_ID, body=event_data).execute()
        else:
            service.events().update(
                calendarId=CALENDAR_ID, eventId=game["gameId"], body=event_data
            ).execute()

        # cause of quotas
        time.sleep(0.5)

    logging.info("Calender Updated")
    # Connect to Reddit
    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET_KEY,
        password=BOT_PASSWORD,
        user_agent="Game Bot by BobbaGanush87",
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
    logging.info("Calendar widget synced")


if __name__ == "__main__":
    main()
