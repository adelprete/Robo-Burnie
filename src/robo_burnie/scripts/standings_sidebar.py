from __future__ import annotations

import logging
import sys

import praw

from robo_burnie import _helpers
from robo_burnie.constants import TEAM_ID_TO_INFO
from robo_burnie.private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY
from robo_burnie.settings import TEAM

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)


# The css on the custom widget gets saved as a giant string
_css_str = """
p {
font-family: Arial, Helvetica, sans-serif;
padding: 14px;
color: white;
font-size: 12px;
letter-spacing: .5px;
background: #850129;
border-radius: 5px 5px 0px 0px;
margin-bottom: 12px;
}

th {
font-family: Arial, Helvetica, sans-serif;
font-size:11px;
}

td{
padding: 3px 18px;
font-family: Arial, Helvetica, sans-serif;
font-size:12px;
}

table tr:nth-child(1)>th{
background: #dcdcdc
}

table tr:nth-child(1)>td,table tr:nth-child(2), table tr:nth-child(3), table tr:nth-child(4), table tr:nth-child(5), table tr:nth-child(6), table tr:nth-child(7), table tr:nth-child(8) {
background: #ffb000;
}

table {
border-collapse: collapse;
}

table td{
border: .5px solid black;
}
table tr:first-child th {
border-top: 0;
}
table tr td:first-child, table tr th:first-child{
border-left: 0;
}
table tr:last-child td,table tr:last-child th {
border-bottom: 0;
}
table tr td:last-child, table tr th:last-child{
border-right: 0;
}
"""


def _main() -> None:
    """
    This script will update the standings on the sidbear on New Reddit.
    """

    # Connect to Reddit
    reddit_client = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET_KEY,
        password=BOT_PASSWORD,
        user_agent="Game Bot for r/heat",
        username="RoboBurnie",
    )

    # Find standings widget on subreddit
    standings_widget = _get_standings_widget(reddit_client)

    if standings_widget:
        standings_markdown = _build_standings_markdown()
        standings_widget.mod.update(text=standings_markdown, css=_css_str)
        logging.info("standings updated")


def _get_standings_widget(reddit_client: praw.Reddit) -> praw.models.Widget | None:
    """Finds the standings widget and returns it"""
    widgets = reddit_client.subreddit("heat").widgets
    for widget in widgets.sidebar:
        if widget.shortName.lower() == "standings":
            return widget


def _build_standings_markdown() -> str:
    """Grabs the latest nba standings and builds the markdown of those standings"""
    standings = _helpers.get_todays_standings()
    standings_markdown = "| | Team | W | L | Pct |\n|--|--|--|--|--|"

    for position, team in enumerate(standings, start=1):
        if team["Conference"] == "West":
            continue

        team_name = "{}".format(team["TeamName"])
        if TEAM_ID_TO_INFO[str(team["TeamID"])]["tricode"] == TEAM:
            team_name = "**{}**".format(team["TeamName"])
        team_standing_markdown = "\n| {} |  {} | {} | {} | {}".format(
            position,
            team_name,
            team["WINS"],
            team["LOSSES"],
            team["WinPCT"],
        )
        standings_markdown += team_standing_markdown

    return standings_markdown


if __name__ == "__main__":
    _main()
