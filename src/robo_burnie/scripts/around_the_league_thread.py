import logging
import sys
from datetime import datetime, timedelta
from typing import Tuple

import praw

from ..private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY
from .. import helpers

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)


# Today's date is eastern time minus 4 hours just to ensure we stay within the same "day" after midnight on the east coast
TODAYS_DATE_STR = helpers.get_todays_date_str(hours_offset=3)

SUBREDDIT = "heatcss"

def main(action: str) -> None:
    """Creates or updates the Around the League thread on the subreddit"""
    todays_games = helpers.get_todays_games()

    if not todays_games:
        logging.info("No Games Today")
        return
    else:
        reddit = praw.Reddit(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET_KEY,
            password=BOT_PASSWORD,
            user_agent="Game Bot by BobbaGanush87",
            username="RoboBurnie",
        )

        title = "[Around the League] Discuss today's NBA news and games"
        body = _generate_post_body(todays_games)

        subreddit = reddit.subreddit(SUBREDDIT)

        if action == "create":
            # Unsticky old Around the League Thread (if applicable)
            for post in subreddit.hot(limit=10):
                if post.stickied and "[Around the League]" in post.title:
                    post_date = datetime.fromtimestamp(post.created_utc).strftime(
                        "%Y%m%d"
                    )
                    if post_date != TODAYS_DATE_STR:
                        post.mod.sticky(False)
                    break

            submission = subreddit.submit(
                title,
                selftext=body,
                send_replies=False,

                # flair_id="29f18426-a10b-11e6-af2b-0ea571864a50",
            )
            submission.mod.sticky()
            submission.mod.suggested_sort(sort="new")
            logging.info("Around the League thread posted")

        elif action == "update":
            for post in subreddit.new(limit=35):
                if "[Around the League]" in post.title:
                    post.edit(body)
                    post.save()
                    break
            logging.info("Around the League thread updated")


def _generate_post_body(todays_games: dict) -> str:
    body = (

        f"| **Away** | **Score** | **Home** | **TV** |\n"
        f"| :---: | :---: | :---: | :---: |\n"
    )
    for game_id, game in todays_games.items():
        score = f"{game['visitor_pts']} - {game['home_pts']}" if game['home_pts'] and game['visitor_pts'] else None
        status = f"({game['game_status_text'].strip()})" if score else game['game_status_text'].strip()
        game_details = f"| {game['visitor_name']} | {score or ''} {status} | {game['home_name']} | {game['natl_tv_broadcaster_abbreviation'] or ''} |\n"
        body += game_details

    return body


if __name__ == "__main__":
    main(sys.argv[1])
