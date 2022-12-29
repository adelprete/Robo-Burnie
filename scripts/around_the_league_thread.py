import logging
import sys
from datetime import datetime, timedelta
from typing import Tuple

import praw

from constants import TEAM_ID_TO_INFO
from private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY
from scripts import helpers

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)


# its eastern time minus 4 hours just to ensure we stay within the same day after midnight on the east coast
TODAYS_DATE_STR = helpers.get_todays_date_str(hours_offset=3)

SUBREDDIT = "heat"


def main(action: str) -> None:

    todays_games = helpers.get_todays_games(hours_offset=3)
    if not todays_games:
        logging.info("No Games Today")
        return
    else:

        title, body = generate_post_details(todays_games)

        # Connect to reddit
        reddit = praw.Reddit(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET_KEY,
            password=BOT_PASSWORD,
            user_agent="Game Bot by BobbaGanush87",
            username="RoboBurnie",
        )

        subreddit = reddit.subreddit(SUBREDDIT)

        if action == "create":
            # Unsticky old Around the League Thread (if any)
            for post in subreddit.hot(limit=10):
                if post.stickied and "[Around the League]" in post.title:
                    post_date = datetime.fromtimestamp(post.created_utc).strftime(
                        "%Y%m%d"
                    )
                    if post_date != TODAYS_DATE_STR:
                        post.mod.sticky(False)
                    break

            # Submit the post if one doesnt already exist for the day
            submission = subreddit.submit(
                title,
                selftext=body,
                send_replies=False,
                flair_id="29f18426-a10b-11e6-af2b-0ea571864a50",
            )
            submission.mod.sticky()
            submission.mod.suggested_sort("new")
            logging.info("Around the League thread posted")

        elif action == "update":
            for post in subreddit.new(limit=35):
                if "[Around the League]" in post.title:
                    post.edit(body)
                    post.save()
                    break
            logging.info("Around the League thread updated")


def generate_post_details(todays_games: list) -> Tuple[str, str]:
    title = "[Around the League] Discuss today's NBA news and games"

    body = (
        f"| **Visitors** | **Home** | **Score** | **Time** |\n"
        f"| :---: | :---: | :---: | :---: |\n"
    )
    for game in todays_games:

        # Determine the status of the game
        game_time = game["startTimeEastern"]
        if game["statusNum"] == 2:
            if game["period"]["isHalftime"]:
                game_time = "Halftime"
            else:
                game_time = f"Q{game['period']['current']} {game['clock']}"
        elif game["statusNum"] == 3:
            game_time = "Final"

        score = f"{game['vTeam']['score']:>3} - {game['hTeam']['score']:<3}"
        # box_score = f"[Link]({helpers.get_game_link(game)})"

        game_details = f"| {TEAM_ID_TO_INFO[game['vTeam']['teamId']]['nickname']} | {TEAM_ID_TO_INFO[game['hTeam']['teamId']]['nickname']} | {score} | {game_time} |\n"
        """
        game_details = (
            f"| Teams | Score |\n"
            f"| --- | --- |\n"
            f"| {TEAM_ID_TO_INFO[game['vTeam']['teamId']]['fullName']} |  {game['vTeam']['score']:>3} |\n"
            f"| {TEAM_ID_TO_INFO[game['hTeam']['teamId']]['fullName']} |  {game['hTeam']['score']:>3} |\n"
            f"| [Box-Score]({get_game_link(game)}) | {game_time} |\n"
            f"\n--\n\n" 
        )"""

        body += game_details

    return title, body


if __name__ == "__main__":

    main(sys.argv[1])
