from __future__ import annotations

import logging
import random
import time
from datetime import datetime
from enum import Enum
from json import JSONDecodeError
from typing import Tuple

import praw

from robo_burnie import _helpers
from robo_burnie._file_lock import file_lock
from robo_burnie._settings import SUBREDDIT, TEAM
from robo_burnie.private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
)

SUBREDDIT = "heatcss"
_POST_GAME_FLAIR_ID = "aa3be42a-c182-11e3-b8ca-12313b0e88c2"


class GameStatus(Enum):
    NOT_STARTED = 1
    IN_PROGRESS = 2
    POST_GAME = 3


def _main():
    todays_game = _helpers.get_todays_game_v2(team=TEAM)
    if todays_game == {}:
        logger.debug("No Game Today")
        return

    try:
        _wait_for_game_to_start(todays_game["game_id"])
    except JSONDecodeError as e:
        logger.error(f"Game hasnt started yet: {e}")
        return

    _wait_for_game_to_end(todays_game["game_id"])

    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET_KEY,
        password=BOT_PASSWORD,
        user_agent="Game Bot for r/heat",
        username="RoboBurnie",
    )
    if not _post_game_thread_exists(reddit):
        _submit_post(reddit, todays_game["game_id"])
    else:
        logger.debug("Post Game Thread already exists")


def _wait_for_game_to_start(game_id: str) -> None:
    while True:
        boxscore = _helpers.get_boxscore(game_id)
        if boxscore["gameStatus"] in [
            GameStatus.IN_PROGRESS.value,
            GameStatus.POST_GAME.value,
        ]:
            return
        logger.info("Game hasn't started yet. Sleeping...")
        # TODO: dynamically adjust sleep time based on time until game starts
        time.sleep(7200)  # 2 hours


def _wait_for_game_to_end(game_id: str) -> None:
    double_check_close_game = True
    while True:
        boxscore = _helpers.get_boxscore(game_id)
        if _is_game_over(boxscore):
            if (
                double_check_close_game
                and abs(boxscore["awayTeam"]["score"] - boxscore["homeTeam"]["score"])
                <= 3
            ):
                # Sometimes close games can be misreported as over when the final play is still being reviewed
                logger.info(
                    "Game was close. Double checking that the game actually ended."
                )
                double_check_close_game = False
                time.sleep(15)
            else:
                break
        else:
            _sleep_for_awhile(boxscore)


def _is_game_over(boxscore: dict) -> bool:
    return (
        boxscore["gameStatus"] == GameStatus.POST_GAME.value
        and boxscore["awayTeam"]["score"] != boxscore["homeTeam"]["score"]
    ) or (
        boxscore["period"] >= 4
        and boxscore["gameStatus"] == GameStatus.IN_PROGRESS.value
        and boxscore["awayTeam"]["score"] != boxscore["homeTeam"]["score"]
        and _helpers.gameclock_to_seconds(boxscore["gameClock"]) == 0
    )


def _sleep_for_awhile(boxscore: dict) -> None:
    time_left = _helpers.gameclock_to_seconds(boxscore["gameClock"])
    if boxscore["period"] >= 4 and boxscore["gameStatus"] == 2 and not time_left:
        """if the game is in the 4th quarter and the clock has no value, the game might be over"""
        logger.debug(f"Game might have ended: {time_left}")
        time.sleep(3)
    elif boxscore["period"] >= 4 and time_left < 40:
        """if the game is in the 4th quarter and the clock is less than 40 seconds, the game is almost over"""
        logger.debug(f"Game is almost over: {time_left}")
        time.sleep(10)
    elif boxscore["period"] >= 4:
        """if the game is in the 4th quarter and its not almost over"""
        logger.debug(f"Game is in the 4th quarter: {time_left}")
        time.sleep(40)
    elif boxscore["period"] < 4:
        """if the game is not in the 4th quarter, wait for a longer period"""
        logger.debug("Game is not in the 4th quarter yet")
        time.sleep(720)  # 12 mins
    else:
        logger.debug(f"Game is not over yet: {time_left}")
        time.sleep(90)


def _post_game_thread_exists(reddit: praw.Reddit) -> bool:
    subreddit = reddit.subreddit(SUBREDDIT)
    for post in subreddit.hot(limit=15):
        if post.stickied and "[Post Game]" in post.title:
            return True
    return False


def _submit_post(reddit: praw.Reddit, game_id: str) -> None:
    boxscore = _helpers.get_boxscore(game_id)
    title, selftext = _generate_post_details(boxscore)
    _submit_post_game_thread(reddit, title, selftext)
    logger.info("Post Game Thread posted")
    _unsticky_game_thread(reddit)
    logger.info("Unstickied Game Thread")


def _generate_post_details(boxscore: dict) -> Tuple[str, str]:
    # Determine if our team is home or away
    team_stats_key = "homeTeam"
    opponent_stats_key = "awayTeam"
    if boxscore["awayTeam"]["teamTricode"] == TEAM:
        team_stats_key = "awayTeam"
        opponent_stats_key = "homeTeam"

    # Get Stat leaders
    points_leader_text = _get_stats_leader_text(
        "points", boxscore[team_stats_key]["players"]
    )
    rebounds_leader_text = _get_stats_leader_text(
        "reboundsTotal", boxscore[team_stats_key]["players"]
    )
    assists_leader_text = _get_stats_leader_text(
        "assists", boxscore[team_stats_key]["players"]
    )

    title = _generate_post_title(boxscore, team_stats_key, opponent_stats_key)

    box_score_link = _helpers._get_boxscore_link(
        away_tricode=boxscore["awayTeam"]["teamTricode"],
        home_tricode=boxscore["homeTeam"]["teamTricode"],
        game_id=boxscore["gameId"],
        game_time=datetime.strptime(boxscore["gameTimeLocal"], "%Y-%m-%dT%H:%M:%S%z"),
    )

    selftext = f"Box Score: {box_score_link}"
    selftext += "\n\n"
    selftext += points_leader_text
    selftext += "\n\n"
    selftext += rebounds_leader_text
    selftext += "\n\n"
    selftext += assists_leader_text

    return title, selftext


def _get_stats_leader_text(stat: str, players: list[dict]) -> str:
    sorted_players = sorted(players, key=lambda p: p["statistics"][stat], reverse=True)
    stat_leader = sorted_players[0]

    abbreviated_stat_map = {
        "points": "PTS",
        "reboundsTotal": "REBS",
        "assists": "ASTS",
    }
    statline_text = f"**{stat_leader['name']}**: {stat_leader['statistics'][stat]} {abbreviated_stat_map[stat]}"
    return statline_text


def _generate_post_title(
    boxscore: dict, team_stats_key: str, opponent_stats_key: str
) -> str:
    team_score = boxscore[team_stats_key]["score"]
    opponent_score = boxscore[opponent_stats_key]["score"]
    if team_score < opponent_score:
        result = random.choice(["lose to the", "fall to the"])
    else:
        result = random.choice(["defeat the", "win against the"])

    return "[Post Game] {} {} {}: {} - {}".format(
        boxscore[team_stats_key]["teamName"],
        result,
        boxscore[opponent_stats_key]["teamName"],
        team_score,
        opponent_score,
    )


def _submit_post_game_thread(reddit: praw.Reddit, title: str, selftext: str) -> None:
    submission = reddit.subreddit(SUBREDDIT).submit(
        title,
        selftext=selftext,
        send_replies=False,
        flair_id=_POST_GAME_FLAIR_ID,
    )
    submission.mod.sticky()


def _unsticky_game_thread(reddit: praw.Reddit) -> None:
    subreddit = reddit.subreddit(SUBREDDIT)
    for post in subreddit.hot(limit=5):
        if post.stickied and "[Game Thread]" in post.title:
            post.mod.sticky(False)
            break


if __name__ == "__main__":

    if _helpers.is_script_enabled("post_game_thread"):
        try:
            with file_lock("post_game_thread"):
                _main()
        except IOError:
            logger.debug("Another instance of post_game_thread is already running")
    else:
        logger.debug("post_game_thread is disabled")
