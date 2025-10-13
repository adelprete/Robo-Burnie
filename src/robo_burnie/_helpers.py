from __future__ import annotations

import json

__all__ = [
    "get_todays_standings",
    "get_boxscore",
    "get_full_team_schedule",
    "get_game_from_cdn_endpoint",
    "get_current_datetime",
    "get_todays_date_str",
    "get_todays_games",
    "get_todays_game_v2",
    "get_todays_game",
    "get_boxscore",
    "get_boxscore_link",
    "gameclock_to_seconds",
    "get_espn_boxscore_link",
    "is_script_enabled",
]
from datetime import datetime, timedelta
from typing import List

import requests
from nba_api.live.nba.endpoints import boxscore
from nba_api.stats.endpoints import (
    boxscoresummaryv2,
    leaguestandings,
    scheduleleaguev2,
    scoreboardv2,
)
from nba_api.stats.library.parameters import GameDate

from robo_burnie._settings import TEAM


def create_dictionary_list(headers, rows):
    result = []
    for row in rows:
        result.append(dict(zip(headers, row)))
    return result


def get_todays_standings():
    result = leaguestandings.LeagueStandings().get_dict()["resultSets"][0]

    header = result["headers"]
    standings = [dict(zip(header, sublist)) for sublist in result["rowSet"]]
    return standings


def get_boxscore(game_id: str) -> dict:
    box_score = boxscore.BoxScore(game_id).get_dict()["game"]
    return box_score


def get_full_team_schedule(team_name: str) -> List[dict]:
    schedule = requests.get(
        "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"
    ).json()

    teams_games = []
    for game_date in schedule["leagueSchedule"]["gameDates"]:
        for game in game_date["games"]:
            if (
                game["homeTeam"]["teamSlug"] == team_name
                or game["awayTeam"]["teamSlug"] == team_name
            ):
                teams_games.append(game)

    return teams_games


def get_game_from_cdn_endpoint(game_id: str) -> dict:
    schedule = requests.get(
        "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"
    ).json()

    for game_date in schedule["leagueSchedule"]["gameDates"]:
        for game in game_date["games"]:
            if game["gameId"] == game_id:
                return game

    return {}


def get_current_datetime() -> datetime:
    """Returns"""
    return datetime.now() - timedelta(hours=4)


def get_todays_date_str(hours_offset=0, format: str = "%Y%m%d") -> str:
    return (datetime.now() - timedelta(hours=hours_offset)).strftime(format)


def get_todays_games() -> list[dict]:
    """Get all games for the day"""
    games = {}
    game_date = GameDate().get_date_format(get_current_datetime())
    scoreboard = scoreboardv2.ScoreboardV2(game_date=game_date).get_dict()["resultSets"]

    # Walkthrough each scoreboard section and build out the data for each game
    game_headers = create_dictionary_list(
        scoreboard[0]["headers"], scoreboard[0]["rowSet"]
    )
    for game in game_headers:
        games[game["GAME_ID"]] = {
            "game_status_text": game["GAME_STATUS_TEXT"],
            "game_status_id": game["GAME_STATUS_ID"],
            "live_period": game["LIVE_PERIOD"],
            "live_period_time_bcast": game["LIVE_PERIOD_TIME_BCAST"],
            "home_team_id": game["HOME_TEAM_ID"],
            "visitor_team_id": game["VISITOR_TEAM_ID"],
            "natl_tv_broadcaster_abbreviation": game[
                "NATL_TV_BROADCASTER_ABBREVIATION"
            ],
        }

    line_scores = create_dictionary_list(
        scoreboard[1]["headers"], scoreboard[1]["rowSet"]
    )
    for line_score in line_scores:
        team_prefix = "home"
        if line_score["TEAM_ID"] == games[line_score["GAME_ID"]]["visitor_team_id"]:
            team_prefix = "visitor"

        games[line_score["GAME_ID"]].update(
            {
                f"{team_prefix}_name": line_score["TEAM_NAME"],
                f"{team_prefix}_abbreviation": line_score["TEAM_ABBREVIATION"],
                f"{team_prefix}_city_name": line_score["TEAM_CITY_NAME"],
                f"{team_prefix}_wins_losses": line_score["TEAM_WINS_LOSSES"],
                f"{team_prefix}_pts": line_score["PTS"],
            }
        )

    return games


def get_todays_game_v3(team=TEAM) -> dict:
    """Get today's game for specific team using scheduleleaguev2 endpoint
    ScheduleLeagueV2 provides a gameLabel that other endpoints do not provide.
    """
    games = scheduleleaguev2.ScheduleLeagueV2().get_dict()["leagueSchedule"]
    todays_date: str = get_todays_date_str(format="%m/%d/%Y")  # 10/02/2025

    todays_game = {}
    for game_date in games["gameDates"]:
        if todays_date in game_date["gameDate"]:
            for game in game_date["games"]:
                if team in (
                    game["homeTeam"]["teamTricode"],
                    game["awayTeam"]["teamTricode"],
                ):
                    todays_game = {
                        "game_id": game["gameId"],
                        "game_label": game["gameLabel"],
                        "status_id": game["gameStatus"],
                        "status_text": game["gameStatusText"],
                        "home_team_id": game["homeTeam"]["teamId"],
                        "home_team_wins": game["homeTeam"]["wins"],
                        "home_team_losses": game["homeTeam"]["losses"],
                        "away_team_id": game["awayTeam"]["teamId"],
                        "away_team_wins": game["awayTeam"]["wins"],
                        "away_team_losses": game["awayTeam"]["losses"],
                    }
                    break

    return todays_game


def get_todays_game_v2(team=TEAM):
    """Get today's game for specific team using scoreboardv2 and boxscoresummaryv2 endpoints

    Faster than get_todays_game_v3 but does not provide gameLabel
    """

    # Today's ScoreBoard
    games = scoreboardv2.ScoreboardV2().get_dict()["resultSets"][0]["rowSet"]

    todays_game = {}
    for game in games:
        if team in game[5]:
            todays_game = game
            break

    if not todays_game:
        return {}

    box_score = boxscoresummaryv2.BoxScoreSummaryV2(todays_game[2]).get_dict()[
        "resultSets"
    ]

    game_status_id = box_score[0]["rowSet"][0][3]
    status_text = box_score[0]["rowSet"][0][4]
    home_team_id = str(box_score[0]["rowSet"][0][6])
    home_wins = 0
    home_losses = 0
    away_team_id = str(box_score[0]["rowSet"][0][7])
    away_wins = 0
    away_losses = 0

    # Grab the team wins and losses from another source
    if todays_game:
        standings = get_todays_standings()
        for team in standings:
            if home_team_id == str(team["TeamID"]):
                home_wins = team["WINS"]
                home_losses = team["LOSSES"]
            elif away_team_id == str(team["TeamID"]):
                away_wins = team["WINS"]
                away_losses = team["LOSSES"]

    game_data = {
        "game_id": todays_game[2],
        "status_id": game_status_id,
        "status_text": status_text,
        "home_team_id": home_team_id,
        "home_team_wins": home_wins,
        "home_team_losses": home_losses,
        "away_team_id": away_team_id,
        "away_team_wins": away_wins,
        "away_team_losses": away_losses,
    }

    return game_data


def get_todays_game(team=TEAM):
    """Get today's game for specific team"""
    today = datetime.utcnow() - timedelta(hours=5)
    games = requests.get(
        "https://data.nba.net/prod/v2/{}{}{}/scoreboard.json".format(
            today.strftime("%Y"), today.strftime("%m"), today.strftime("%d")
        )
    ).json()

    todays_game = {}
    for game in games["games"]:
        if game["vTeam"]["triCode"] == team or game["hTeam"]["triCode"] == team:
            todays_game = game

    # Grab the team wins and losses from another source because our
    # orignal source stopped providing them for some reason.
    if todays_game:
        standings = get_todays_standings()
        for team in standings:
            if todays_game["vTeam"]["teamId"] == str(team["TeamID"]):
                todays_game["vTeam"]["win"] = team["WINS"]
                todays_game["vTeam"]["loss"] = team["LOSSES"]
            if todays_game["hTeam"]["teamId"] == str(team["TeamID"]):
                todays_game["hTeam"]["win"] = team["WINS"]
                todays_game["hTeam"]["loss"] = team["LOSSES"]

    return todays_game


def get_boxscore_link(
    away_tricode: str, home_tricode: str, game_id: str, game_time: datetime = None
):
    """Create box score link for specific game"""
    espn_box_score_link = get_espn_boxscore_link(
        away_tricode=away_tricode,
        home_tricode=home_tricode,
        date=game_time,
    )
    if espn_box_score_link:
        return espn_box_score_link
    else:
        return f"https://www.nba.com/game/{away_tricode}-vs-{home_tricode}-{game_id}/boxscore#boxscore"


def gameclock_to_seconds(game_clock: str) -> float:
    """Converts game clock string 'PT00M00.00S' to seconds"""
    minutes, seconds = game_clock[2:].split("M")
    seconds = seconds[:-1]
    time_left = int(minutes) * 60 + float(seconds)
    return time_left


def get_espn_boxscore_link(
    away_tricode: str, home_tricode: str, date: datetime
) -> str | None:

    # account for weird tricodes in ESPNs api.
    # TODO: Move this check to a proper method. There will probably be more weirdness like this to handle.
    if away_tricode == "SAS":
        away_tricode = "SA"
    elif home_tricode == "SAS":
        home_tricode = "SA"

    scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date.strftime('%Y%m%d')}"
    scoreboard = requests.get(scoreboard_url).json()
    for event in scoreboard["events"]:
        if (
            event["competitions"][0]["competitors"][1]["team"]["abbreviation"]
            == away_tricode
            and event["competitions"][0]["competitors"][0]["team"]["abbreviation"]
            == home_tricode
        ):
            return event["links"][0]["href"]


def is_script_enabled(script_name: str) -> bool:
    """Check if a script is enabled in .config.json if it exists"""
    try:
        with open("src/robo_burnie/.config.json", "r") as file:
            config = json.load(file)
            return config["scripts"].get(script_name, {}).get("enabled", False)
    except FileNotFoundError:
        with open("src/robo_burnie/default_config.json", "r") as file:
            config = json.load(file)
            return config["scripts"].get(script_name, {}).get("enabled", False)
    return False
