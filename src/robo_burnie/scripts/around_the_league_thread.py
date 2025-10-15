from __future__ import annotations

import logging
import sys
from datetime import datetime

import praw

from robo_burnie import _helpers
from robo_burnie._settings import SUBREDDIT, TEAM
from robo_burnie.private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)

# Today's date is eastern time minus 4 hours just to ensure we stay within the same "day" after midnight on the east coast
TODAYS_DATE_STR = _helpers.get_todays_date_str(hours_offset=3)


def _main(action: str) -> None:
    """Creates or updates the Around the League thread on the subreddit"""
    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET_KEY,
        password=BOT_PASSWORD,
        user_agent="Game Bot for r/heat",
        username="RoboBurnie",
    )
    subreddit = reddit.subreddit(SUBREDDIT)

    team_game_today = _helpers.get_todays_game_v2(team=TEAM)
    if team_game_today:
        logging.info(f"{TEAM} Game Today.  Skipping Around the League Thread")
        _unsticky_old_around_the_league_thread(subreddit)
        return

    todays_games = _helpers.get_todays_games()
    if not todays_games:
        logging.info("No Games Today. Skipping Around the League Thread")
        _unsticky_old_around_the_league_thread(subreddit)
        return
    else:
        body = _generate_post_body(todays_games)
        if action == "create":
            _create_around_the_league_thread(subreddit, body)
        elif action == "update":
            _update_around_the_league_thread(subreddit, body)


def _generate_post_body(todays_games: dict) -> str:
    body = (
        "| **Away** | **Home** | **Score** | **TV** |\n"
        "| :---: | :---: | :---: | :---: |\n"
    )
    for game_id, game in todays_games.items():
        score = (
            f"{game['visitor_pts']} - {game['home_pts']}"
            if game["home_pts"] and game["visitor_pts"]
            else None
        )
        status = (
            f"({game['game_status_text'].strip()})"
            if score
            else game["game_status_text"].strip()
        )
        game_details = f"| {game['visitor_name']} | {game['home_name']} | {score or ''} {status} | {game['natl_tv_broadcaster_abbreviation'] or ''} |\n"
        body += game_details

    return body


def _unsticky_old_around_the_league_thread(subreddit: praw.models.Subreddit) -> None:
    """Unstickies the any Around the League thread that was not made today"""
    for post in subreddit.hot(limit=10):
        if post.stickied and "[Around the League]" in post.title:
            post_date = datetime.fromtimestamp(post.created_utc).strftime("%Y%m%d")
            if post_date != TODAYS_DATE_STR:
                post.mod.sticky(False)


def _create_around_the_league_thread(
    subreddit: praw.models.Subreddit, body: str
) -> None:
    """Creates the Around the League thread"""
    # Unsticky old Around the League Thread (if applicable)
    _unsticky_old_around_the_league_thread(subreddit)

    title = "[Around the League] Discuss today's NBA news and games"
    submission = subreddit.submit(
        title,
        selftext=body,
        send_replies=False,
        flair_id="29f18426-a10b-11e6-af2b-0ea571864a50",
    )
    submission.mod.sticky()
    submission.mod.suggested_sort(sort="new")
    logging.info("Around the League thread posted")


def _update_around_the_league_thread(
    subreddit: praw.models.Subreddit, body: str
) -> None:
    """Updates the Around the League thread"""
    for post in subreddit.new(limit=35):
        if "[Around the League]" in post.title:
            post.edit(body)
            post.save()
            break
    logging.info("Around the League thread updated")


if __name__ == "__main__":
    _main(sys.argv[1])
