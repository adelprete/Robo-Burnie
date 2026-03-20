from __future__ import annotations

import json
import logging
import sys
import time

import praw

from robo_burnie import _helpers
from robo_burnie._settings import SUBREDDIT
from robo_burnie.private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)

CONFIG_PATH = "src/robo_burnie/.config.json"
BOT_USERNAME = "RoboBurnie"


def _main() -> None:
    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET_KEY,
        password=BOT_PASSWORD,
        user_agent="Game Bot for r/heat",
        username=BOT_USERNAME,
    )
    subreddit = reddit.subreddit(SUBREDDIT)

    game_thread = _find_game_thread(subreddit)
    if game_thread is None:
        logging.info("No game thread found")
        return

    last_checked_utc = _get_last_checked_utc()
    commands = _collect_new_commands(game_thread, subreddit, last_checked_utc)

    for comment, enabled in commands:
        _helpers.set_script_enabled("post_game_thread", enabled)
        state = "enabled" if enabled else "disabled"
        comment.reply(f"Post game thread has been {state}.")
        logging.info(f"Post game thread {state} by u/{comment.author.name}")

    _set_last_checked_utc(time.time())


def _find_game_thread(
    subreddit: praw.models.Subreddit,
) -> praw.models.Submission | None:
    for post in subreddit.hot(limit=15):
        if post.stickied and "[Game Thread]" in post.title:
            return post
    return None


def _collect_new_commands(
    submission: praw.models.Submission,
    subreddit: praw.models.Subreddit,
    last_checked_utc: float,
) -> list[tuple[praw.models.Comment, bool]]:
    """Return command comments newer than last_checked_utc, oldest-first."""
    submission.comment_sort = "new"
    submission.comments.replace_more(limit=0)

    moderators = {mod.name for mod in subreddit.moderator()}
    commands: list[tuple[praw.models.Comment, bool]] = []

    for comment in submission.comments:
        if comment.created_utc <= last_checked_utc:
            break

        if not comment.author or comment.author.name not in moderators:
            continue

        body = comment.body.strip().lower()
        if body == "!postgame on":
            commands.append((comment, True))
        elif body == "!postgame off":
            commands.append((comment, False))

    commands.reverse()
    return commands


def _get_last_checked_utc() -> float:
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        return config["scripts"].get("check_commands", {}).get("last_checked_utc", 0)
    except FileNotFoundError:
        return 0


def _set_last_checked_utc(utc_timestamp: float) -> None:
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        with open("src/robo_burnie/default_config.json", "r") as f:
            config = json.load(f)
    config["scripts"].setdefault("check_commands", {})[
        "last_checked_utc"
    ] = utc_timestamp
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)


if __name__ == "__main__":
    if _helpers.is_script_enabled("check_commands"):
        _main()
    else:
        logging.debug("check_commands is disabled")
