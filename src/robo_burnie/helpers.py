from datetime import datetime, timedelta
from typing import List, NamedTuple

import requests
from nba_api.stats.endpoints import (boxscoresummaryv2, leaguestandings,
                                     scoreboardv2)
from nba_api.stats.library.parameters import GameDate

from .constants import TEAM_ID_TO_INFO
from .settings import TEAM

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


def get_full_team_schedule(team_name: str) -> List[dict]:
    schedule = requests.get(
        f"https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"
    ).json()

    teams_games = []
    for game_date in schedule["leagueSchedule"]["gameDates"]:
        for game in game_date["games"]:
            if game["homeTeam"]["teamSlug"] == team_name or game["awayTeam"]["teamSlug"] == team_name:
                teams_games.append(game)

    return teams_games

def get_game_from_cdn_endpoint(game_id: str) -> dict:
    schedule = requests.get(
        f"https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"
    ).json()

    for game_date in schedule["leagueSchedule"]["gameDates"]:
        for game in game_date["games"]:
            if game["gameId"] == game_id:
                return game

    return {}

def get_current_datetime() -> datetime:
    """Returns"""
    return datetime.now() - timedelta(hours=4)

def get_todays_date_str(hours_offset=0):
    return (datetime.now() - timedelta(hours=hours_offset)).strftime("%Y%m%d")

def get_todays_games() -> list[dict]:
    """Get all games for the day"""
    games = {}
    game_date = GameDate().get_date_format(get_current_datetime())
    scoreboard = scoreboardv2.ScoreboardV2(game_date=game_date).get_dict()["resultSets"]

    # Walkthrough each scoreboard section and build out the data for each game
    game_headers = create_dictionary_list(scoreboard[0]["headers"], scoreboard[0]["rowSet"])
    for game in game_headers:
        games[game["GAME_ID"]] = {
            "game_status_text": game["GAME_STATUS_TEXT"],
            "game_status_id": game["GAME_STATUS_ID"],
            "live_period": game["LIVE_PERIOD"],
            "live_period_time_bcast": game["LIVE_PERIOD_TIME_BCAST"],
            "home_team_id": game["HOME_TEAM_ID"],
            "visitor_team_id": game["VISITOR_TEAM_ID"],
            "natl_tv_broadcaster_abbreviation": game["NATL_TV_BROADCASTER_ABBREVIATION"],
        }

    line_scores = create_dictionary_list(scoreboard[1]["headers"], scoreboard[1]["rowSet"])
    for line_score in line_scores:
        team_prefix = "home"
        if line_score["TEAM_ID"] == games[line_score["GAME_ID"]]["visitor_team_id"]:
            team_prefix = "visitor"

        games[line_score["GAME_ID"]].update({
            f"{team_prefix}_name": line_score["TEAM_NAME"],
            f"{team_prefix}_abbreviation": line_score["TEAM_ABBREVIATION"],
            f"{team_prefix}_city_name": line_score["TEAM_CITY_NAME"],
            f"{team_prefix}_wins_losses": line_score["TEAM_WINS_LOSSES"],
            f"{team_prefix}_pts": line_score["PTS"],
        })

    return games


def get_todays_game_v2(team=TEAM):

    # Use scoreboardv2.ScoreboardV2 to check if we have a game today and get its game_id
    # And then use boxscoresummaryv2.BoxScoreSummaryV2(game_id) to get details about that game

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


def get_boxscore(gameid):
    """Get boxscore for specific game"""
    today = datetime.utcnow() - timedelta(hours=5)
    boxscore = requests.get(
        "https://data.nba.net/data/10s/prod/v1/{}{}{}/{}_boxscore.json".format(
            today.strftime("%Y"), today.strftime("%m"), today.strftime("%d"), gameid
        )
    ).json()
    return boxscore


def get_game_link(game):
    """Create box score link for specific game"""
    return f"https://www.nba.com/game/{TEAM_ID_TO_INFO[game['away_team_id']]['tricode']}-vs-{TEAM_ID_TO_INFO[game['home_team_id']]['tricode']}-{game['game_id']}/box-score#box-score"
