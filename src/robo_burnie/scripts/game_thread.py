from __future__ import annotations

import html
import logging
import re
import sys
import time
from typing import Tuple

import praw

from robo_burnie import _helpers
from robo_burnie._constants import TEAM_ID_TO_INFO, TEAM_TRI_TO_INFO
from robo_burnie._settings import SUBREDDIT, TEAM, get_flair_id
from robo_burnie.private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)

TIP_OFF_ROW = "| **Tip-Off Time** |"
SCORE_ROW_RE = re.compile(r"^\| \*\*Score\*\* \|.*\n", re.MULTILINE)


def _main(action: str) -> None:
    if action == "update":
        _update_score()
        return

    todays_game = _helpers.get_todays_game_auto(team=TEAM)

    if todays_game == {}:
        logging.info("No Game Today")
    elif todays_game.get("status_id") == 1:
        logging.info("Game hasn't started yet")

        title, self_text = _generate_post_details(todays_game, TEAM)

        if action == "create":
            _submit_post(_get_reddit().subreddit(SUBREDDIT), title, self_text)


def _get_reddit() -> praw.Reddit:
    return praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET_KEY,
        password=BOT_PASSWORD,
        user_agent="Game Bot for r/heat",
        username="RoboBurnie",
    )


def _update_score() -> None:
    """Keeps a live Score row in today's game thread, above the tip-off time"""
    # The bot's own posts, not stickies: the post game thread may already have
    # unstickied it. Within the last day so yesterday's thread is never edited.
    post = next(
        (
            post
            for post in _get_reddit().user.me().submissions.new(limit=10)
            if "[Game Thread]" in post.title
            and time.time() - post.created_utc < 24 * 60 * 60
        ),
        None,
    )
    if post is None:
        logging.info("No game thread to update")
        return

    # Reddit returns selftext HTML-escaped (&amp;); unescape so edits don't double it
    body = html.unescape(post.selftext)
    score_row = SCORE_ROW_RE.search(body)
    # "(Final", not "(Final)": overtime games end as Final/OT, Final/2OT, ...
    if score_row and "(Final" in score_row.group():
        logging.info("Game already final")
        return

    league_ids = (
        _helpers.SUMMER_LEAGUE_IDS if "[Summer League]" in post.title else ("00",)
    )
    game = _helpers.find_team_game(_helpers.get_todays_games(league_ids), TEAM)
    if game is None or game["home_pts"] is None:
        logging.info("No live game to update")
        return

    new_body = _with_score_row(body, game)
    if new_body == body:
        logging.info("Score unchanged")
        return

    post.edit(new_body)
    logging.info("Game thread score updated")


def _with_score_row(body: str, game: dict) -> str:
    score_row = "| **Score** | **{} {} - {} {}** ({}) |\n".format(
        game["visitor_abbreviation"],
        game["visitor_pts"],
        game["home_abbreviation"],
        game["home_pts"],
        _helpers.format_game_status(game["game_status_text"]),
    )
    body = SCORE_ROW_RE.sub("", body)
    return body.replace(TIP_OFF_ROW, score_row + TIP_OFF_ROW, 1)


def _generate_post_details(todays_game: dict, team: str) -> Tuple[str, str]:
    tv_channels = _get_tv_broadcasters(todays_game, team)
    radio_channels = _get_radio_broadcasters(todays_game, team)

    home_team = _resolve_team_info(todays_game, "home")
    away_team = _resolve_team_info(todays_game, "away")

    # Grab general game information
    visitor_team_name = away_team["fullName"]
    visitor_reddit = _team_reddit(away_team)
    visitor_win = todays_game["away_team_wins"]
    visitor_loss = todays_game["away_team_losses"]

    home_team_name = home_team["fullName"]
    home_reddit = _team_reddit(home_team)
    home_win = todays_game["home_team_wins"]
    home_loss = todays_game["home_team_losses"]

    # Get Date information
    today_datetime = _helpers.get_current_datetime()
    month = today_datetime.strftime("%m")
    day = today_datetime.strftime("%d")
    start_time = todays_game["status_text"]
    game_label = f" [{todays_game['game_label']}]" if todays_game["game_label"] else ""

    title = "[Game Thread]{} {} ({}-{}) @ {} ({}-{}) - {}/{} {}".format(
        game_label,
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
        "| Game Details | . |\n"
        "|--|--|\n"
        f"{TIP_OFF_ROW} {{}} |\n"
        "| **TV Broadcasts** | {} |\n"
        "| **Radio Broadcasts** | {} |\n"
        "| **Game Info & Stats** | [Box Score]({}) |"
    )

    table = table.format(
        start_time,
        ", ".join(tv_channels),
        ", ".join(radio_channels),
        _helpers.get_boxscore_link(
            away_team["tricode"],
            home_team["tricode"],
            todays_game["game_id"],
            today_datetime,
        ),
    )

    self_text = self_text + table

    if not _is_summer_league_game(todays_game):
        standings_table = _build_standings_table(
            todays_game["away_team_id"],
            todays_game["home_team_id"],
            away_team["tricode"],
            home_team["tricode"],
        )
        if standings_table:
            self_text = self_text + "\n\n" + standings_table

    return title, self_text


def _is_summer_league_game(todays_game: dict) -> bool:
    return todays_game.get("game_label") == "Summer League"


def _resolve_team_info(todays_game: dict, side: str) -> dict:
    """Resolve team metadata; exhibition games may use non-standard team IDs."""
    prefix = "home" if side == "home" else "away"
    team_id = str(todays_game[f"{prefix}_team_id"])

    if team_id in TEAM_ID_TO_INFO:
        return TEAM_ID_TO_INFO[team_id]

    tricode = todays_game.get(f"{prefix}_tricode")
    if tricode:
        for info in TEAM_ID_TO_INFO.values():
            if info["tricode"] == tricode:
                return info
        tri_info = TEAM_TRI_TO_INFO.get(tricode)
        if tri_info:
            return {"fullName": tri_info["full_name"], "tricode": tricode}

    raise KeyError(team_id)


def _team_reddit(team_info: dict) -> str:
    tricode = team_info["tricode"]
    if "reddit" in team_info:
        return team_info["reddit"]
    return TEAM_TRI_TO_INFO.get(tricode, {}).get("reddit", "")


def _build_standings_table(
    away_team_id: int, home_team_id: int, away_tricode: str, home_tricode: str
) -> str:
    """Build a Reddit markdown table comparing both teams' standings context."""
    try:
        standings = _helpers.get_todays_standings()
        away = _helpers.get_team_standings(away_team_id, standings)
        home = _helpers.get_team_standings(home_team_id, standings)

        if not away or not home:
            return ""

        rows = [
            f"| | **{away_tricode}** | **{home_tricode}** |",
            "|--|--|--|",
            f"| **Seed** | {_ordinal(away['PlayoffRank'])} {away['Conference']} | {_ordinal(home['PlayoffRank'])} {home['Conference']} |",
            f"| **Streak** | {away['strCurrentStreak']} | {home['strCurrentStreak']} |",
            f"| **Last 10** | {away['L10']} | {home['L10']} |",
            f"| **PPG** | {away['PointsPG']} | {home['PointsPG']} |",
            f"| **Opp PPG** | {away['OppPointsPG']} | {home['OppPointsPG']} |",
        ]
        return "\n".join(rows)
    except Exception:
        logging.exception("Failed to build standings table")
        return ""


def _ordinal(n: int) -> str:
    """Convert an integer to its ordinal string (1st, 2nd, 3rd, etc.)."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _submit_post(subreddit: str, title: str, self_text: str) -> None:
    if _helpers.find_game_thread(subreddit) is None:
        # Unsticky Post Game Thread (if any)
        for post in subreddit.hot(limit=5):
            if post.stickied and "[Post Game]" in post.title:
                post.mod.sticky(False)
                break

        submission = subreddit.submit(
            title,
            selftext=self_text,
            send_replies=False,
            flair_id=get_flair_id("game_thread"),
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


def _get_tv_broadcasters(todays_game: dict, team: str):
    broadcasters = todays_game.get("broadcasters")
    if not broadcasters:
        return []

    national_tv_broadcasters = []
    for broadcaster in broadcasters.get("nationalTvBroadcasters", []):
        national_tv_broadcasters.append(broadcaster["broadcasterAbbreviation"])

    if not national_tv_broadcasters:
        for broadcaster in broadcasters.get("nationalBroadcasters", []):
            if broadcaster.get("broadcasterMedia") != "tv":
                continue
            abbreviation = broadcaster.get("broadcasterAbbreviation", "")
            if abbreviation == "LeaguePass":
                continue
            national_tv_broadcasters.append(abbreviation)

    team_key = (
        "homeTvBroadcasters"
        if todays_game.get("home_tricode") == team
        else "awayTvBroadcasters"
    )
    team_tv_broadcasters = []
    for broadcaster in broadcasters.get(team_key, []):
        team_tv_broadcasters.append(broadcaster["broadcasterAbbreviation"])

    return _helpers.filter_tv_broadcasters(
        team_tv_broadcasters + national_tv_broadcasters
    )


def _get_radio_broadcasters(todays_game: dict, team: str):
    broadcasters = todays_game.get("broadcasters")
    if not broadcasters:
        return []

    national_radio_broadcasters = []
    for broadcaster in broadcasters.get("nationalRadioBroadcasters", []):
        national_radio_broadcasters.append(broadcaster["broadcasterAbbreviation"])

    team_key = (
        "homeRadioBroadcasters"
        if todays_game.get("home_tricode") == team
        else "awayRadioBroadcasters"
    )
    team_radio_broadcasters = []
    for broadcaster in broadcasters.get(team_key, []):
        team_radio_broadcasters.append(broadcaster["broadcasterAbbreviation"])

    return team_radio_broadcasters + national_radio_broadcasters


if __name__ == "__main__":
    _main(sys.argv[1])
