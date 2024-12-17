from __future__ import annotations

import logging
import random
import time
from typing import Tuple

import praw

from .. import _helpers
from .._settings import TEAM, TEAM_INFO
from ..private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY


def generate_post_details(todays_game: dict) -> Tuple[str, str]:
    team_stats_key = "hTeam"
    opponent_stats_key = "vTeamm"
    if todays_game["vTeam"]["triCode"] == TEAM:
        team_stats_key = "vTeam"
        opponent_stats_key = "hTeam"
    boxscore = _helpers.get_boxscore(todays_game["gameId"])

    # Grab general score information
    team_score = todays_game[team_stats_key]["score"]
    opponents_score = todays_game[opponent_stats_key]["score"]
    opponents_name = todays_game[opponent_stats_key]["triCode"]

    # Grab points leader information
    points_statline = "\n\n"
    points_leader_value = boxscore["stats"][team_stats_key]["leaders"]["points"][
        "value"
    ]
    for index, player in enumerate(
        boxscore["stats"][team_stats_key]["leaders"]["points"]["players"]
    ):
        if index > 0:
            points_statline += " /"
        points_statline += " **{} {}**".format(player["firstName"], player["lastName"])
    points_statline += ": {} PTS".format(points_leader_value)

    # Grab reboundss leader information
    rebounds_statline = "\n\n"
    rebounds_leader_value = boxscore["stats"][team_stats_key]["leaders"]["rebounds"][
        "value"
    ]
    for index, player in enumerate(
        boxscore["stats"][team_stats_key]["leaders"]["rebounds"]["players"]
    ):
        if index > 0:
            rebounds_statline += " /"
        rebounds_statline += " **{} {}**".format(
            player["firstName"], player["lastName"]
        )
    rebounds_statline += ": {} REBS".format(rebounds_leader_value)

    # Grab assists leader information
    assists_statline = "\n\n"
    assists_leader_value = boxscore["stats"][team_stats_key]["leaders"]["assists"][
        "value"
    ]
    for index, player in enumerate(
        boxscore["stats"][team_stats_key]["leaders"]["assists"]["players"]
    ):
        if index > 0:
            assists_statline += " /"
        assists_statline += " **{} {}**".format(player["firstName"], player["lastName"])
    assists_statline += ": {} ASTS".format(assists_leader_value)

    if team_score < opponents_score:
        result = random.choice(["lose to", "fall to"])
    else:
        result = random.choice(["defeat", "win against"])

    title = "[Post Game Thread] {} {} {} {} - {}".format(
        TEAM_INFO[TEAM]["full_name"],
        result,
        TEAM_INFO[opponents_name]["full_name"],
        team_score,
        opponents_score,
    )
    selftext = "* [Box Score](https://www.nba.com/games/{}#/boxscore)".format(
        todays_game["gameUrlCode"]
    )
    selftext += "\n\nStat Leaders"
    selftext += points_statline
    selftext += rebounds_statline
    selftext += assists_statline

    return title, selftext


if __name__ == "__main__":
    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET_KEY,
        password=BOT_PASSWORD,
        user_agent="Game Bot for r/heat",
        username="RoboBurnie",
    )

    while True:
        todays_game = _helpers.get_todays_game(hours_offset=5)
        if todays_game == {}:
            logging.info("No Game Today")
            break
        elif todays_game["statusNum"] == 3:
            logging.info("Post Game Thread already Posted")
            break

        if todays_game["statusNum"] == 1:
            logging.info("Game hasn't started yet")
            time.sleep(5400)  # checks again in an hour and a half
            continue

        while todays_game["statusNum"] in [2, 3]:
            todays_game = _helpers.get_todays_game(hours_offset=5)
            # Check if game is over
            if todays_game["statusNum"] == 3 or (
                todays_game["period"]["current"] >= 4
                and todays_game["statusNum"] == 2
                and todays_game["period"]["isEndOfPeriod"]
                and todays_game["vTeam"]["score"] != todays_game["hTeam"]["score"]
            ):
                title, selftext = generate_post_details(todays_game)

                # Submit Post
                submission = reddit.subreddit("heatcss").submit(
                    title,
                    selftext=selftext,
                    send_replies=False,
                    flair_id="aa3be42a-c182-11e3-b8ca-12313b0e88c2",
                )
                submission.mod.sticky()

                # Unsticky Game Thread
                subreddit = reddit.subreddit("heatcss")
                for post in subreddit.hot(limit=5):
                    if post.stickied and "[Game Thread]" in post.title:
                        post.mod.sticky(False)
                        break

                logging.info("Game ended thread posted")
                quit()
                break

            elif (
                todays_game["period"]["current"] >= 4
                and todays_game["statusNum"] == 2
                and not todays_game["clock"]
            ):
                logging.info("Game might have ended")
                time.sleep(3)
            elif (
                todays_game["period"]["current"] >= 4
                and todays_game["clock"]
                and int(todays_game["clock"].replace(":", "").split(".")[0]) < 40
            ):
                logging.info("Game is almost over")
                time.sleep(10)
            else:
                logging.info("Game not over yet")
                time.sleep(90)
