from __future__ import annotations

import json
from collections import defaultdict

__all__ = [
    "get_todays_standings",
    "get_team_standings",
    "get_boxscore",
    "get_full_team_schedule",
    "get_game_from_cdn_endpoint",
    "get_todays_date_str",
    "get_todays_games_from_schedule",
    "get_todays_game_v2",
    "get_todays_game_v3",
    "get_todays_game_auto",
    "get_boxscore_link",
    "gameclock_to_seconds",
    "get_espn_boxscore_link",
    "get_espn_summer_league_boxscore_link",
    "is_summer_league_game",
    "is_amazon_prime_channel",
    "filter_tv_broadcasters",
    "is_script_enabled",
    "set_script_enabled",
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

from robo_burnie._settings import TEAM

SUMMER_LEAGUE_IDS = ("13", "15", "16")
SCOREBOARD_LEAGUE_IDS = ("00", *SUMMER_LEAGUE_IDS)
ESPN_SUMMER_LEAGUE_PATHS = (
    "nba-summer-california",
    "nba-summer-las-vegas",
    "nba-summer-utah",
)
SCHEDULE_LEAGUE_V2_CDN_URL = (
    "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"
)
HTTP_REQUEST_TIMEOUT = 60
_STREAM_TITLE_TO_CHANNEL = (
    ("nba tv", "NBA TV"),
    ("espnu", "ESPNU"),
    ("espn", "ESPN"),
    ("tnt", "TNT"),
    ("abc", "ABC"),
    ("nbc", "NBC"),
    ("peacock", "Peacock"),
    ("telemundo", "Telemundo"),
    ("amazon", "Amazon Prime Video"),
    ("prime", "Amazon Prime Video"),
)


def is_amazon_prime_channel(label: str) -> bool:
    n = label.strip().lower()
    if not n:
        return False
    if n in ("amazon", "amazon prime video", "prime video"):
        return True
    if "amazon" in n and "prime" in n:
        return True
    return False


def filter_tv_broadcasters(channels: list[str]) -> list[str]:
    """Drop Amazon/Prime from the list when any other TV broadcaster is also listed."""
    non_amazon = [c for c in channels if not is_amazon_prime_channel(c)]
    if non_amazon:
        return non_amazon
    return channels


def _broadcaster_label(broadcaster: dict) -> str:
    return (
        broadcaster.get("broadcasterDisplay")
        or broadcaster.get("broadcasterAbbreviation")
        or ""
    ).strip()


def _collect_schedule_tv_broadcasters(
    broadcasters: dict,
) -> tuple[list[str], list[str]]:
    national: list[str] = []
    for broadcaster in broadcasters.get("nationalTvBroadcasters", []):
        label = _broadcaster_label(broadcaster)
        if label:
            national.append(label)

    for broadcaster in broadcasters.get("nationalBroadcasters", []):
        if broadcaster.get("broadcasterMedia") != "tv":
            continue
        label = _broadcaster_label(broadcaster)
        if label and label != "LeaguePass":
            national.append(label)

    regional: list[str] = []
    for key in ("homeTvBroadcasters", "awayTvBroadcasters"):
        for broadcaster in broadcasters.get(key, []):
            label = _broadcaster_label(broadcaster)
            if label:
                regional.append(label)

    return national, regional


def format_game_tv_broadcasters(broadcasters: dict) -> str:
    """Build a TV display string, hiding Amazon unless it's the only broadcaster."""
    national, regional = _collect_schedule_tv_broadcasters(broadcasters)
    filtered = filter_tv_broadcasters(national + regional)

    national_kept = [channel for channel in national if channel in filtered]
    if national_kept:
        return ", ".join(national_kept)

    regional_kept = [channel for channel in regional if channel in filtered]
    if regional_kept:
        return ", ".join(regional_kept)

    return ", ".join(filtered)


def get_todays_standings():
    result = leaguestandings.LeagueStandings().get_dict()["resultSets"][0]

    header = result["headers"]
    standings = [dict(zip(header, sublist)) for sublist in result["rowSet"]]
    return standings


def get_team_standings(team_id: int, standings: list[dict] | None = None) -> dict:
    """Look up a single team's standings entry by team ID.

    If standings are not provided, they will be fetched via get_todays_standings().
    """
    if standings is None:
        standings = get_todays_standings()

    for team in standings:
        if team["TeamID"] == team_id:
            return team
    return {}


def get_boxscore(game_id: str) -> dict:
    box_score = boxscore.BoxScore(game_id).get_dict()["game"]
    return box_score


def _fetch_season_schedule_cdn() -> dict:
    return requests.get(SCHEDULE_LEAGUE_V2_CDN_URL, timeout=HTTP_REQUEST_TIMEOUT).json()


def get_full_team_schedule(team_name: str) -> List[dict]:
    schedule = _fetch_season_schedule_cdn()

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
    schedule = _fetch_season_schedule_cdn()

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


def _channel_from_stream_title(title: str) -> str | None:
    lowered = title.lower()
    for keyword, channel in _STREAM_TITLE_TO_CHANNEL:
        if keyword in lowered:
            return channel
    return None


def _channels_cdn_url(league_id: str) -> str:
    return f"https://cdn.nba.com/static/json/liveData/channels/v2/channels_{league_id}.json"


def _scoreboard_cdn_url(league_id: str) -> str:
    return f"https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_{league_id}.json"


def _parse_scoreboard_game(game: dict, game_id_to_channels_map: dict) -> dict:
    return {
        "game_status_text": game["gameStatusText"],
        "game_status_id": game["gameStatus"],
        "live_period": game["period"],
        "natl_tv_broadcaster_abbreviation": ", ".join(
            filter_tv_broadcasters(
                list(game_id_to_channels_map.get(game["gameId"], []))
            )
        ),
        "home_team_id": game["homeTeam"]["teamId"],
        "visitor_team_id": game["awayTeam"]["teamId"],
        "home_name": game["homeTeam"]["teamName"],
        "visitor_name": game["awayTeam"]["teamName"],
        "home_abbreviation": game["homeTeam"]["teamTricode"],
        "visitor_abbreviation": game["awayTeam"]["teamTricode"],
        "home_city_name": game["homeTeam"]["teamCity"],
        "visitor_city_name": game["awayTeam"]["teamCity"],
        "home_pts": game["homeTeam"].get("score"),
        "visitor_pts": game["awayTeam"].get("score"),
    }


def get_game_id_to_channels_map(
    league_ids: tuple[str, ...] = SCOREBOARD_LEAGUE_IDS,
) -> dict:
    game_id_to_channels = defaultdict(set)
    for league_id in league_ids:
        response = requests.get(
            _channels_cdn_url(league_id), timeout=HTTP_REQUEST_TIMEOUT
        )
        if response.status_code != 200:
            continue
        data = response.json()
        for game in data.get("channels", {}).get("games", []):
            for stream in game.get("streams", []):
                title = stream.get("title")
                if not title:
                    continue
                channel = _channel_from_stream_title(title)
                if channel:
                    game_id_to_channels[game["gameId"]].add(channel)
    return game_id_to_channels


def get_todays_games_cdn(
    league_ids: tuple[str, ...] = SCOREBOARD_LEAGUE_IDS,
) -> dict:
    game_id_to_channels_map: dict = get_game_id_to_channels_map(league_ids)

    games = {}
    for league_id in league_ids:
        response = requests.get(
            _scoreboard_cdn_url(league_id), timeout=HTTP_REQUEST_TIMEOUT
        )
        if response.status_code != 200:
            continue
        data = response.json()
        for game in data.get("scoreboard", {}).get("games", []):
            games[game["gameId"]] = _parse_scoreboard_game(
                game, game_id_to_channels_map
            )
    for game_id, game in _get_todays_summer_league_games_espn().items():
        games.setdefault(game_id, game)
    return games


def _espn_home_away_competitors(
    competition: dict,
) -> tuple[dict, dict] | None:
    competitors = competition.get("competitors", [])
    if len(competitors) < 2:
        return None

    home = None
    away = None
    for competitor in competitors:
        if competitor.get("homeAway") == "home":
            home = competitor
        elif competitor.get("homeAway") == "away":
            away = competitor

    if home is None or away is None:
        home = competitors[0]
        away = competitors[1]

    return home, away


def _espn_competitor_score(competitor: dict, game_state: str) -> int | None:
    score = competitor.get("score")
    if score in (None, ""):
        return None
    if game_state == "pre" and score in ("0", 0):
        return None
    return int(score)


def _espn_national_broadcasters(competition: dict) -> str:
    names: list[str] = []
    for broadcast in competition.get("broadcasts", []):
        if broadcast.get("market") == "national":
            names.extend(broadcast.get("names", []))
    return ", ".join(filter_tv_broadcasters(names))


def _parse_espn_scoreboard_event(event: dict) -> dict | None:
    competition = event["competitions"][0]
    home_away = _espn_home_away_competitors(competition)
    if home_away is None:
        return None
    home, away = home_away
    status = competition["status"]["type"]
    state = status.get("state", "pre")
    game_status_id = {"pre": 1, "in": 2, "post": 3}.get(state, 1)

    return {
        "game_status_text": status.get("shortDetail", status.get("description", "")),
        "game_status_id": game_status_id,
        "live_period": competition["status"].get("period", 0),
        "natl_tv_broadcaster_abbreviation": _espn_national_broadcasters(competition),
        "home_team_id": home["team"]["id"],
        "visitor_team_id": away["team"]["id"],
        "home_name": home["team"].get("shortDisplayName", home["team"]["displayName"]),
        "visitor_name": away["team"].get(
            "shortDisplayName", away["team"]["displayName"]
        ),
        "home_abbreviation": home["team"]["abbreviation"],
        "visitor_abbreviation": away["team"]["abbreviation"],
        "home_city_name": home["team"].get("location", ""),
        "visitor_city_name": away["team"].get("location", ""),
        "home_pts": _espn_competitor_score(home, state),
        "visitor_pts": _espn_competitor_score(away, state),
    }


def _get_todays_summer_league_games_espn() -> dict:
    """Summer league scoreboard CDN endpoints are often blocked; ESPN is the fallback."""
    games: dict = {}
    date_str = get_todays_date_str(format="%Y%m%d")

    for league_path in ESPN_SUMMER_LEAGUE_PATHS:
        scoreboard_url = (
            "https://site.api.espn.com/apis/site/v2/sports/basketball/"
            f"{league_path}/scoreboard?dates={date_str}"
        )
        response = requests.get(scoreboard_url, timeout=HTTP_REQUEST_TIMEOUT)
        if response.status_code != 200:
            continue

        for event in response.json().get("events", []):
            parsed = _parse_espn_scoreboard_event(event)
            if parsed is not None:
                games[event["id"]] = parsed

    return games


def get_todays_games_from_schedule() -> dict:
    """Get today's games from the season schedule CDN."""
    games_data = _fetch_season_schedule_cdn()["leagueSchedule"]
    todays_date = get_todays_date_str(format="%m/%d/%Y")

    games = {}
    for game_date in games_data["gameDates"]:
        if todays_date in game_date["gameDate"]:
            for game in game_date["games"]:
                games[game["gameId"]] = {
                    "game_status_text": game["gameStatusText"],
                    "game_status_id": game["gameStatus"],
                    "live_period": 0,
                    "natl_tv_broadcaster_abbreviation": format_game_tv_broadcasters(
                        game.get("broadcasters", {})
                    ),
                    "home_team_id": game["homeTeam"]["teamId"],
                    "visitor_team_id": game["awayTeam"]["teamId"],
                    "home_name": game["homeTeam"]["teamName"],
                    "visitor_name": game["awayTeam"]["teamName"],
                    "home_abbreviation": game["homeTeam"]["teamTricode"],
                    "visitor_abbreviation": game["awayTeam"]["teamTricode"],
                    "home_city_name": game["homeTeam"]["teamCity"],
                    "visitor_city_name": game["awayTeam"]["teamCity"],
                    "home_pts": None,
                    "visitor_pts": None,
                }
            break
    return games


def _summer_league_season(dt: datetime | None = None) -> str:
    dt = dt or get_current_datetime()
    return f"{dt.year}-{(dt.year + 1) % 100:02d}"


def _normalize_game_label(game_label: str) -> str:
    if "Emirates NBA Cup" in game_label:
        return "NBA Cup"
    if "Summer League" in game_label:
        return "Summer League"
    return game_label


def is_summer_league_game(game_id: str) -> bool:
    return game_id.startswith(SUMMER_LEAGUE_IDS)


def get_todays_game_v3(
    team=TEAM, league_id: str = "00", season: str | None = None
) -> dict:
    """Get today's game for specific team using scheduleleaguev2 endpoint
    ScheduleLeagueV2 provides a gameLabel that other endpoints do not provide.
    """
    schedule_kwargs: dict[str, str] = {"league_id": league_id}
    if season:
        schedule_kwargs["season"] = season
    elif league_id in SUMMER_LEAGUE_IDS:
        schedule_kwargs["season"] = _summer_league_season()

    games = scheduleleaguev2.ScheduleLeagueV2(**schedule_kwargs).get_dict()[
        "leagueSchedule"
    ]
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
                        "game_label": _normalize_game_label(game["gameLabel"]),
                        "status_id": game["gameStatus"],
                        "status_text": game["gameStatusText"],
                        "home_team_id": game["homeTeam"]["teamId"],
                        "home_team_wins": game["homeTeam"]["wins"],
                        "home_team_losses": game["homeTeam"]["losses"],
                        "away_team_id": game["awayTeam"]["teamId"],
                        "away_team_wins": game["awayTeam"]["wins"],
                        "away_team_losses": game["awayTeam"]["losses"],
                        "broadcasters": game.get("broadcasters", {}),
                        "home_tricode": game["homeTeam"]["teamTricode"],
                        "away_tricode": game["awayTeam"]["teamTricode"],
                    }
                    break

    return todays_game


def get_todays_game_auto(team=TEAM) -> dict:
    """Check Summer League schedules first, then fall back to regular season."""
    for league_id in SUMMER_LEAGUE_IDS:
        game = get_todays_game_v3(team=team, league_id=league_id)
        if game:
            return game
    return get_todays_game_v3(team=team, league_id="00")


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


def get_boxscore_link(
    away_tricode: str, home_tricode: str, game_id: str, game_time: datetime = None
):
    """Create box score link for specific game"""
    if is_summer_league_game(game_id) and game_time:
        espn_box_score_link = get_espn_summer_league_boxscore_link(
            away_tricode=away_tricode,
            home_tricode=home_tricode,
            date=game_time,
        )
    else:
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


def _espn_tricode(tricode: str) -> str:
    # account for weird tricodes in ESPNs api.
    # TODO: Move this check to a proper method. There will probably be more weirdness like this to handle.
    if tricode == "SAS":
        return "SA"
    return tricode


def _match_espn_event(event: dict, away_tricode: str, home_tricode: str) -> str | None:
    competitors = event["competitions"][0]["competitors"]
    home_abbr = None
    away_abbr = None
    for competitor in competitors:
        abbreviation = competitor["team"]["abbreviation"]
        if competitor.get("homeAway") == "home":
            home_abbr = abbreviation
        elif competitor.get("homeAway") == "away":
            away_abbr = abbreviation

    if home_abbr is None or away_abbr is None:
        home_abbr = competitors[0]["team"]["abbreviation"]
        away_abbr = competitors[1]["team"]["abbreviation"]

    if away_abbr == away_tricode and home_abbr == home_tricode:
        return event["links"][0]["href"]
    return None


def get_espn_boxscore_link(
    away_tricode: str, home_tricode: str, date: datetime
) -> str | None:
    away_tricode = _espn_tricode(away_tricode)
    home_tricode = _espn_tricode(home_tricode)

    scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date.strftime('%Y%m%d')}"
    scoreboard = requests.get(scoreboard_url, timeout=HTTP_REQUEST_TIMEOUT).json()
    for event in scoreboard["events"]:
        link = _match_espn_event(event, away_tricode, home_tricode)
        if link:
            return link


def get_espn_summer_league_boxscore_link(
    away_tricode: str, home_tricode: str, date: datetime
) -> str | None:
    away_tricode = _espn_tricode(away_tricode)
    home_tricode = _espn_tricode(home_tricode)
    date_str = date.strftime("%Y%m%d")

    for league_path in ESPN_SUMMER_LEAGUE_PATHS:
        scoreboard_url = (
            "https://site.api.espn.com/apis/site/v2/sports/basketball/"
            f"{league_path}/scoreboard?dates={date_str}"
        )
        response = requests.get(scoreboard_url, timeout=HTTP_REQUEST_TIMEOUT)
        if response.status_code != 200:
            continue

        for event in response.json().get("events", []):
            link = _match_espn_event(event, away_tricode, home_tricode)
            if link:
                return link


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


def set_script_enabled(script_name: str, enabled: bool) -> None:
    """Toggle a script's enabled flag in .config.json."""
    config_path = "src/robo_burnie/.config.json"
    default_config_path = "src/robo_burnie/default_config.json"

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        # First run on a new machine: initialize runtime config from defaults.
        with open(default_config_path, "r") as f:
            config = json.load(f)

    config["scripts"][script_name]["enabled"] = enabled
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
