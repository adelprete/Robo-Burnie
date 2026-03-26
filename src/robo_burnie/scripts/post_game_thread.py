from __future__ import annotations

import logging
import random
import re
import time
from datetime import datetime, timezone
from enum import Enum
from json import JSONDecodeError
from typing import Tuple

import praw

from robo_burnie import _helpers
from robo_burnie._file_lock import file_lock
from robo_burnie._settings import TEAM, get_flair_id
from robo_burnie.private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
)

SUBREDDIT = "heatcss"


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
        _helpers.set_script_enabled("post_game_thread", False)
        logger.info("post_game_thread disabled until next !postgame on")
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
    while True:
        boxscore = _helpers.get_boxscore(game_id)
        if _is_game_over(boxscore):
            break
        _sleep_for_awhile(boxscore)


def _is_game_over(boxscore: dict) -> bool:
    return (
        boxscore["gameStatus"] == GameStatus.POST_GAME.value
        and boxscore["awayTeam"]["score"] != boxscore["homeTeam"]["score"]
    )


def _sleep_for_awhile(boxscore: dict) -> None:
    time_left = _helpers.gameclock_to_seconds(boxscore["gameClock"])
    if boxscore["period"] >= 4 and time_left < 24:
        logger.debug(f"Game is almost over: {time_left}")
        time.sleep(5)
    elif boxscore["period"] >= 4 and time_left < 40:
        logger.debug(f"Game is almost over: {time_left}")
        time.sleep(10)
    elif boxscore["period"] >= 4:
        logger.debug(f"Game is in the 4th quarter: {time_left}")
        time.sleep(40)
    elif boxscore["period"] < 4:
        logger.debug("Game is not in the 4th quarter yet")
        time.sleep(720)  # 12 mins
    else:
        logger.debug(f"Game is not over yet: {time_left}")
        time.sleep(90)


def _post_game_thread_exists(reddit: praw.Reddit) -> bool:
    """True if a [Post Game] thread from today (UTC) exists."""
    today_utc = datetime.now(tz=timezone.utc).date()
    subreddit = reddit.subreddit(SUBREDDIT)
    for post in subreddit.new(limit=25):
        if "[Post Game]" not in post.title:
            continue
        post_date = datetime.fromtimestamp(post.created_utc, tz=timezone.utc).date()
        if post_date == today_utc:
            return True
    return False


def _submit_post(reddit: praw.Reddit, game_id: str) -> None:
    boxscore = _helpers.get_boxscore(game_id)
    title, selftext = _generate_post_details(boxscore)
    _unsticky_old_post_game_thread(reddit)
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

    title = _generate_post_title(boxscore, team_stats_key, opponent_stats_key)

    box_score_link = _helpers.get_boxscore_link(
        away_tricode=boxscore["awayTeam"]["teamTricode"],
        home_tricode=boxscore["homeTeam"]["teamTricode"],
        game_id=boxscore["gameId"],
        game_time=datetime.strptime(boxscore["gameTimeLocal"], "%Y-%m-%dT%H:%M:%S%z"),
    )

    our_team = boxscore[team_stats_key]
    opponent_team = boxscore[opponent_stats_key]
    top_scorer_line = _get_top_scorer_lead_line(
        our_team.get("players", []),
        our_team.get("teamCity", ""),
        our_team["teamName"],
    )
    heat_table = _team_boxscore_markdown(our_team)
    opponent_table = _team_boxscore_markdown(opponent_team)

    selftext = f"Box Score: {box_score_link}\n\n{top_scorer_line}\n\n{heat_table}\n\n{opponent_table}"

    return title, selftext


def _minutes_display(minutes_iso: str) -> str:
    if not minutes_iso:
        return "-"
    match = re.match(r"PT(\d+)M(?:(\d+(?:\.\d+)?)S)?", minutes_iso)
    if not match:
        return "-"
    mins = int(match.group(1))
    secs = float(match.group(2)) if match.group(2) else 0.0
    return f"{mins}:{int(round(secs)):02d}"


def _fg_split(stats: dict, made_key: str, att_key: str) -> str:
    return f"{stats.get(made_key, 0)}-{stats.get(att_key, 0)}"


def _sort_players_for_boxscore(players: list[dict]) -> list[dict]:
    played = [p for p in players if p.get("played", "1") == "1"]
    return sorted(
        played,
        key=lambda p: (0 if p.get("starter") == "1" else 1, int(p.get("order", 999))),
    )


def _player_display_name(player: dict) -> str:
    return player.get("nameI") or player.get("name", "Unknown")


def _get_top_scorer_lead_line(
    players: list[dict], team_city: str, team_name: str
) -> str:
    played = [p for p in players if p.get("played", "1") == "1"]
    if not played:
        return ""
    leader = max(played, key=lambda p: p.get("statistics", {}).get("points", 0))
    stats = leader.get("statistics") or {}
    pts = stats.get("points", 0)
    name = leader.get("name") or _player_display_name(leader)
    label = f"{team_city} {team_name}".strip() if team_city else team_name
    return f"**{name}** led the {label} with **{pts}** PTS."


def _team_boxscore_markdown(team: dict) -> str:
    city = team.get("teamCity", "")
    name = team.get("teamName", "Team")
    header_title = f"{city} {name}".strip() if city else name
    score = team.get("score", 0)
    players = _sort_players_for_boxscore(team.get("players", []))

    lines = [
        f"### {header_title} ({score})",
        "",
        "| Player | MIN | PTS | REB | AST | STL | BLK | FG | 3PT | FT |",
        "|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|",
    ]

    for p in players:
        stats = p.get("statistics") or {}
        min_src = stats.get("minutes") or stats.get("minutesCalculated") or ""
        row = [
            _player_display_name(p),
            _minutes_display(min_src),
            str(stats.get("points", 0)),
            str(stats.get("reboundsTotal", 0)),
            str(stats.get("assists", 0)),
            str(stats.get("steals", 0)),
            str(stats.get("blocks", 0)),
            _fg_split(stats, "fieldGoalsMade", "fieldGoalsAttempted"),
            _fg_split(stats, "threePointersMade", "threePointersAttempted"),
            _fg_split(stats, "freeThrowsMade", "freeThrowsAttempted"),
        ]
        lines.append("| " + " | ".join(row) + " |")

    team_stats = team.get("statistics")
    if isinstance(team_stats, dict):
        totals = [
            str(team_stats.get("points", score)),
            str(team_stats.get("reboundsTotal", 0)),
            str(team_stats.get("assists", 0)),
            str(team_stats.get("steals", 0)),
            str(team_stats.get("blocks", 0)),
            _fg_split(team_stats, "fieldGoalsMade", "fieldGoalsAttempted"),
            _fg_split(team_stats, "threePointersMade", "threePointersAttempted"),
            _fg_split(team_stats, "freeThrowsMade", "freeThrowsAttempted"),
        ]
        lines.append("| **TEAM** | | " + " | ".join(totals) + " |")

    return "\n".join(lines)


def _generate_post_title(
    boxscore: dict, team_stats_key: str, opponent_stats_key: str
) -> str:
    team_name = boxscore[team_stats_key]["teamName"]
    opponent_name = boxscore[opponent_stats_key]["teamName"]
    team_score = boxscore[team_stats_key]["score"]
    opponent_score = boxscore[opponent_stats_key]["score"]
    margin = abs(team_score - opponent_score)

    if team_score > opponent_score:
        if margin >= 20:
            templates = [
                f"{team_name} blow out the {opponent_name}",
                f"{team_name} dominate the {opponent_name}",
                f"{team_name} cruise past the {opponent_name}",
            ]
        elif margin >= 10:
            templates = [
                f"{team_name} take down the {opponent_name}",
                f"{team_name} defeat the {opponent_name}",
                f"{team_name} handle the {opponent_name}",
            ]
        else:
            templates = [
                f"{team_name} hold off the {opponent_name}",
                f"{team_name} edge out the {opponent_name}",
                f"{team_name} squeak by the {opponent_name}",
                f"{team_name} outlast the {opponent_name}",
            ]
    else:
        if margin >= 20:
            templates = [
                f"{team_name} get blown out by the {opponent_name}",
                f"{team_name} get routed by the {opponent_name}",
            ]
        elif margin >= 10:
            templates = [
                f"{team_name} fall to the {opponent_name}",
                f"{team_name} lose to the {opponent_name}",
                f"{team_name} drop one to the {opponent_name}",
            ]
        else:
            templates = [
                f"{team_name} fall short against the {opponent_name}",
                f"{team_name} come up short against the {opponent_name}",
                f"{team_name} lose a close one to the {opponent_name}",
            ]

    return f"[Post Game] {random.choice(templates)}, {team_score} - {opponent_score}"


def _submit_post_game_thread(reddit: praw.Reddit, title: str, selftext: str) -> None:
    submission = reddit.subreddit(SUBREDDIT).submit(
        title,
        selftext=selftext,
        send_replies=False,
        flair_id=get_flair_id("post_game_thread", SUBREDDIT),
    )
    submission.mod.sticky()


def _unsticky_old_post_game_thread(reddit: praw.Reddit) -> None:
    subreddit = reddit.subreddit(SUBREDDIT)
    for post in subreddit.hot(limit=5):
        if post.stickied and "[Post Game]" in post.title:
            post.mod.sticky(False)
            logger.info("Unstickied old Post Game Thread")
            break


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
