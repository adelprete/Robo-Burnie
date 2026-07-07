from __future__ import annotations

import logging
import re
import sys
from datetime import datetime

import praw

from robo_burnie import _helpers
from robo_burnie._settings import SUBREDDIT, TEAM, get_flair_id
from robo_burnie.private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)

# Today's date is eastern time minus 4 hours just to ensure we stay within the same "day" after midnight on the east coast
TODAYS_DATE_STR = _helpers.get_todays_date_str(hours_offset=3)

# ESPN shortDetail prefixes scheduled games with the date (e.g. "7/4 - 3:00 PM EDT").
_ESPN_DATE_PREFIX_RE = re.compile(r"^\d{1,2}/\d{1,2}\s*-\s*")


def _format_game_status(status_text: str) -> str:
    return _ESPN_DATE_PREFIX_RE.sub("", status_text.strip()).strip()


def _team_plays_today(todays_games: dict, team: str) -> bool:
    return any(
        team in (game["home_abbreviation"], game["visitor_abbreviation"])
        for game in todays_games.values()
    )


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

    todays_games = _helpers.get_todays_games_cdn()
    if _team_plays_today(todays_games, TEAM):
        logging.info(f"{TEAM} Game Today. Skipping Around the League Thread")
        _unsticky_old_around_the_league_thread(subreddit)
        return

    if not todays_games:
        logging.info("No Games Today. Skipping Around the League Thread")
        _unsticky_old_around_the_league_thread(subreddit)
        return

    body = _generate_post_body(todays_games)
    if action == "create":
        _create_around_the_league_thread(subreddit, body)
    elif action == "update":
        _update_around_the_league_thread(subreddit, body)


def _generate_post_body(todays_games: dict) -> str:
    body = (
        "[nba.com](https://www.nba.com/schedule)\n\n"
        "| **Away** | **Home** | **Score** | **TV** |\n"
        "| :---: | :---: | :---: | :---: |\n"
    )
    for game_id, game in todays_games.items():
        score = (
            f"{game['visitor_pts']} - {game['home_pts']}"
            if game.get("home_pts") is not None and game.get("visitor_pts") is not None
            else None
        )
        status_text = _format_game_status(game["game_status_text"])
        status = f"({status_text})" if score else status_text
        raw_tv = game["natl_tv_broadcaster_abbreviation"]
        natl_tv_broadcaster = "" if not raw_tv or raw_tv == "TBD" else raw_tv
        # Timberwolves name is too long and wraps on mobile
        visitor_name = (
            game["visitor_name"]
            if "Timberwolves" != game["visitor_name"]
            else "T-Wolves"
        )
        home_name = (
            game["home_name"] if "Timberwolves" != game["home_name"] else "T-Wolves"
        )
        game_details = f"| {visitor_name} | {home_name} | {score or ''} {status} | {natl_tv_broadcaster} |\n"
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
        flair_id=get_flair_id("around_the_league", SUBREDDIT),
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
