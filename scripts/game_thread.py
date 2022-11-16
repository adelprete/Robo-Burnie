import logging
import sys
from datetime import datetime
from typing import Tuple

import praw
from private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY

from constants import TEAM_TRI_TO_INFO
from scripts import helpers

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)


def main(action: str) -> None:

    todays_game = helpers.get_todays_game(team="MIA")
    if todays_game == {}:
        logging.info("No Game Today")
    elif todays_game.get("statusNum") == 1:
        logging.info("Game hasn't started yet")

        # Generate the details of our post
        title, self_text = generate_post_details(todays_game)

        reddit = praw.Reddit(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET_KEY,
            password=BOT_PASSWORD,
            user_agent="Game Bot by BobbaGanush87",
            username="RoboBurnie",
        )
        subreddit = reddit.subreddit("heat")

        if action == "create":
            create_game_thread(subreddit, title, self_text)


def generate_post_details(todays_game: dict) -> Tuple[str, str]:
    # Grab general game information
    visitor_team_name = TEAM_TRI_TO_INFO[todays_game["vTeam"]["triCode"]]["full_name"]
    visitor_reddit = TEAM_TRI_TO_INFO[todays_game["vTeam"]["triCode"]]["reddit"]
    visitor_win = todays_game["vTeam"]["win"]
    visitor_loss = todays_game["vTeam"]["loss"]

    home_team_name = TEAM_TRI_TO_INFO[todays_game["hTeam"]["triCode"]]["full_name"]
    home_reddit = TEAM_TRI_TO_INFO[todays_game["hTeam"]["triCode"]]["reddit"]
    home_win = todays_game["hTeam"]["win"]
    home_loss = todays_game["hTeam"]["loss"]

    # Grab Broadcast information and build its string while we're at it
    broadcast_info = todays_game["watch"]["broadcast"]["broadcasters"]
    broadcast_str = ""
    if broadcast_info["national"]:
        broadcast_str += f"{broadcast_info['national'][0]['longName']} / "
    if broadcast_info["vTeam"]:
        broadcast_str += f"{broadcast_info['vTeam'][0]['longName']} / "
    if broadcast_info["hTeam"]:
        broadcast_str += f"{broadcast_info['hTeam'][0]['longName']}"

    # Get Date information
    today = datetime.utcnow()
    month = today.strftime("%m")
    day = today.strftime("%d")
    start_time = todays_game["startTimeEastern"]

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
        "| **Location** | {}, {}, {} |\n"
        "| **Tip-Off Time** | {} |\n"
        "| **TV/Radio** | {} |\n"
        "| **Game Info & Stats** | [nba.com]({}) |"
    )

    table = table.format(
        todays_game["arena"]["name"],
        todays_game["arena"]["city"],
        todays_game["arena"]["stateAbbr"],
        start_time,
        broadcast_str,
        helpers.get_game_link(todays_game),
    )

    self_text = self_text + table

    return title, self_text


def create_game_thread(subreddit: str, title: str, self_text: str) -> None:
    game_thread_exists = False
    for post in subreddit.hot(limit=10):
        if post.stickied and "[Game Thread]" in post.title:
            game_thread_exists = True
            break

    if game_thread_exists == False:
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


if __name__ == "__main__":

    main(sys.argv[1])
