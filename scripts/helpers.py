from datetime import datetime, timedelta

import requests

from settings import TEAM
from nba_api.live.nba.endpoints import scoreboard


def get_todays_standings():
    standings = requests.get(
        "https://data.nba.net/data/10s/prod/v2/current/standings_conference.json"
    ).json()
    return standings["league"]["standard"]["conference"]["east"]


def get_full_schedule(year):
    schedule = requests.get(
        f"https://data.nba.net/data/10s/prod/v1/{year}/teams/heat/schedule.json"
    ).json()
    return schedule["league"]["standard"]


def get_todays_date_str(hours_offset=0):
    return (datetime.now() - timedelta(hours=hours_offset)).strftime("%Y%m%d")


def get_todays_games(hours_offset=0):
    """Get all games for the day"""
    scoreboard = requests.get(
        f"https://data.nba.net/data/10s/prod/v1/{get_todays_date_str(hours_offset)}/scoreboard.json"
    ).json()
    return scoreboard["games"]

def get_todays_game_v2(team=TEAM):

    # Today's Score Board
    games = scoreboard.ScoreBoard().get_dict()['scoreboard']['games']
    for game in games:
        if game["homeTeam"]["teamTricode"] == team or game["awayTeam"]["teamTricode"] == team:
            todays_game = game
    return todays_game

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
    return f"https://www.nba.com/game/{game['awayTeam']['teamTricode']}-vs-{game['homeTeam']['teamTricode']}-{game['gameId']}/box-score#box-score"
