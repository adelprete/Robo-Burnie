import logging
import sys

import praw
from private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY

from constants import TEAM_ID_TO_INFO
from scripts import helpers
from settings import TEAM

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)


# The css on the custom widget gets saved as a giant string
css_str = """
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


if __name__ == "__main__":
    """
    This script will update the standings on the Miami Heat 'new' reddit.
    """

    # Connect to Reddit
    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET_KEY,
        password=BOT_PASSWORD,
        user_agent="Game Bot by BobbaGanush87",
        username="RoboBurnie",
    )

    # Find standings widget
    widgets = reddit.subreddit("heat").widgets
    standings_widget = None
    for widget in widgets.sidebar:
        if widget.shortName.lower() == "standings":
            standings_widget = widget
            break

    # Get latest standings from NBA api and build Markdown
    if standings_widget:
        standings = helpers.get_todays_standings()
        standings_markdown = "STANDINGS\n\n| | Team | W | L | Pct |\n|--|--|--|--|--|"

        for position, team in enumerate(standings, start=1):
            team_name = "{}".format(team["TeamName"])
            if TEAM_ID_TO_INFO[str(team["TeamID"])]["tricode"] == TEAM:
                team_name = "**{}**".format(team["TeamName"])
            standing_markdown = "\n| {} |  {} | {} | {} | {}".format(
                position,
                team_name,
                team["WINS"],
                team["LOSSES"],
                team["WinPCT"],
            )
            standings_markdown += standing_markdown

        standings_widget.mod.update(text=standings_markdown, css=css_str)
        logging.info("standings updated")
