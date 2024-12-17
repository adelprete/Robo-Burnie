from __future__ import annotations

import logging
import sys
from datetime import datetime
from typing import Tuple

import praw

from robo_burnie import _helpers
from robo_burnie.constants import TEAM_ID_TO_INFO, TEAM_TRI_TO_INFO
from robo_burnie.private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY
from robo_burnie.settings import SUBREDDIT, TEAM

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)


def _main(action: str) -> None:
    todays_game = _helpers.get_todays_game_v2(team=TEAM)

    if todays_game == {}:
        logging.info("No Game Today")
    elif todays_game.get("status_id") == 1:
        logging.info("Game hasn't started yet")

        title, self_text = _generate_post_details(todays_game, TEAM)

        reddit = praw.Reddit(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET_KEY,
            password=BOT_PASSWORD,
            user_agent="Game Bot for r/heat",
            username="RoboBurnie",
        )
        subreddit = reddit.subreddit(SUBREDDIT)

        if action == "create":
            _create_game_thread(subreddit, title, self_text)


def _generate_post_details(todays_game: dict, team: str) -> Tuple[str, str]:

    cdn_game_data = _helpers.get_game_from_cdn_endpoint(todays_game["game_id"])
    tv_channels = _get_tv_broadcasters(cdn_game_data, team)
    radio_channels = _get_radio_broadcasters(cdn_game_data, team)

    home_team = TEAM_ID_TO_INFO[todays_game["home_team_id"]]
    away_team = TEAM_ID_TO_INFO[todays_game["away_team_id"]]

    # Grab general game information
    visitor_team_name = away_team["fullName"]
    visitor_reddit = TEAM_TRI_TO_INFO[away_team["tricode"]]["reddit"]
    visitor_win = todays_game["away_team_wins"]
    visitor_loss = todays_game["away_team_losses"]

    home_team_name = home_team["fullName"]
    home_reddit = TEAM_TRI_TO_INFO[home_team["tricode"]]["reddit"]
    home_win = todays_game["home_team_wins"]
    home_loss = todays_game["home_team_losses"]

    # Get Date information
    today = datetime.utcnow()
    month = today.strftime("%m")
    day = today.strftime("%d")
    start_time = todays_game["status_text"]

    title = "[Game Thread] {} ({}-{}) @ {} ({}-{}) - {}/{} {}".format(
        visitor_team_name,
        visitor_win,
        visitor_loss,
        home_team_name,
        home_win,
        home_loss,
        month,
        day,
        start_time,
    )

    self_text = "**[{}]({}) ({}-{}) @ [{}]({}) ({}-{})**\n\n".format(
        visitor_team_name,
        "http://www.reddit.com" + visitor_reddit,
        visitor_win,
        visitor_loss,
        home_team_name,
        "http://www.reddit.com" + home_reddit,
        home_win,
        home_loss,
    )

    table = (
        "| Game Details |  |\n"
        "|--|--|\n"
        "| **Tip-Off Time** | {} |\n"
        "| **TV Broadcasts** | {} |\n"
        "| **Radio Broadcasts** | {} |\n"
        "| **Game Info & Stats** | [nba.com]({}) |"
    )

    table = table.format(
        start_time,
        ", ".join(tv_channels),
        ", ".join(radio_channels),
        _helpers.get_game_link(todays_game),
    )

    self_text = self_text + table

    return title, self_text


def _create_game_thread(subreddit: str, title: str, self_text: str) -> None:
    game_thread_exists = False
    for post in subreddit.hot(limit=10):
        if post.stickied and "[Game Thread]" in post.title:
            game_thread_exists = True
            break

    if game_thread_exists is False:
        # Unsticky Post Game Thread (if any)
        for post in subreddit.hot(limit=5):
            if post.stickied and "[Post Game]" in post.title:
                post.mod.sticky(False)
                break

        submission = subreddit.submit(
            title,
            selftext=self_text,
            send_replies=False,
            flair_id="92815388-3a88-11e2-a4e1-12313d14a568",
        )
        submission.mod.sticky()
        submission.mod.suggested_sort("new")

        # Unsticky Post Game Thread (if any)
        for post in subreddit.hot(limit=5):
            if post.stickied and "[Post Game]" in post.title:
                post.mod.sticky(False)
                break

        logging.info("Game thread posted")
    else:
        logging.info("Game thread already posted")


def _get_tv_broadcasters(game_data: dict, team: str):
    national_tv_broadcasters = []
    for broadcaster in game_data["broadcasters"]["nationalTvBroadcasters"]:
        national_tv_broadcasters.append(broadcaster["broadcasterAbbreviation"])

    team_key = (
        "homeTvBroadcasters"
        if game_data["homeTeam"]["teamTricode"] == team
        else "awayTvBroadcasters"
    )
    team_tv_broadcasters = []
    for broadcaster in game_data["broadcasters"][team_key]:
        team_tv_broadcasters.append(broadcaster["broadcasterAbbreviation"])

    return team_tv_broadcasters + national_tv_broadcasters


def _get_radio_broadcasters(game_data: dict, team: str):
    national_radio_broadcasters = []
    for broadcaster in game_data["broadcasters"]["nationalRadioBroadcasters"]:
        national_radio_broadcasters.append(broadcaster["broadcasterAbbreviation"])

    team_key = (
        "homeRadioBroadcasters"
        if game_data["homeTeam"]["teamTricode"] == team
        else "awayRadioBroadcasters"
    )
    team_radio_broadcasters = []
    for broadcaster in game_data["broadcasters"][team_key]:
        team_radio_broadcasters.append(broadcaster["broadcasterAbbreviation"])

    return team_radio_broadcasters + national_radio_broadcasters


if __name__ == "__main__":
    _main(sys.argv[1])
