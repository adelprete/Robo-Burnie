import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from robo_burnie._helpers import (
    filter_tv_broadcasters,
    format_game_tv_broadcasters,
    get_boxscore_link,
    get_espn_boxscore_link,
    get_espn_summer_league_boxscore_link,
    get_game_id_to_channels_map,
    get_todays_game_auto,
    get_todays_game_v3,
    get_todays_standings,
    is_amazon_prime_channel,
    is_summer_league_game,
)


@pytest.fixture(scope="module")
def league_standings_response():
    with open("tests/test_data/nba_api_responses/leaguestandings.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def espn_scoreboard_response():
    with open("tests/test_data/espn_api/scoreboard.json") as f:
        return json.load(f)


@patch("robo_burnie._helpers.requests.get")
def test_get_game_id_to_channels_map_espnu(mock_requests_get):
    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = {
        "channels": {
            "games": [
                {
                    "gameId": "0022500001",
                    "streams": [
                        {"title": "Watch on ESPNU"},
                        {"title": "Watch on ESPN"},
                    ],
                }
            ]
        }
    }

    result = get_game_id_to_channels_map()

    assert result["0022500001"] == {"ESPNU", "ESPN"}


@pytest.mark.parametrize(
    "label, expected",
    [
        ("Amazon", True),
        ("Amazon Prime Video", True),
        ("Prime Video", True),
        ("ESPN", False),
        ("BSSUN", False),
    ],
)
def test_is_amazon_prime_channel(label, expected):
    assert is_amazon_prime_channel(label) is expected


@pytest.mark.parametrize(
    "channels, expected",
    [
        (["ESPN", "Amazon Prime Video"], ["ESPN"]),
        (["Amazon Prime Video", "TNT"], ["TNT"]),
        (["Amazon Prime Video"], ["Amazon Prime Video"]),
        (["Amazon"], ["Amazon"]),
        (["BSSUN", "Amazon"], ["BSSUN"]),
    ],
)
def test_filter_tv_broadcasters(channels, expected):
    assert filter_tv_broadcasters(channels) == expected


def test_format_game_tv_broadcasters_omits_amazon_with_national_linear():
    broadcasters = {
        "nationalBroadcasters": [
            {"broadcasterMedia": "tv", "broadcasterDisplay": "ESPN"},
            {"broadcasterMedia": "tv", "broadcasterDisplay": "Amazon Prime Video"},
        ],
    }
    assert format_game_tv_broadcasters(broadcasters) == "ESPN"


def test_format_game_tv_broadcasters_shows_regional_when_national_is_amazon_only():
    broadcasters = {
        "nationalBroadcasters": [
            {"broadcasterMedia": "tv", "broadcasterDisplay": "Amazon Prime Video"},
        ],
        "homeTvBroadcasters": [{"broadcasterAbbreviation": "BSSUN"}],
    }
    assert format_game_tv_broadcasters(broadcasters) == "BSSUN"


def test_format_game_tv_broadcasters_keeps_amazon_when_only_option():
    broadcasters = {
        "nationalBroadcasters": [
            {"broadcasterMedia": "tv", "broadcasterDisplay": "Amazon Prime Video"},
        ],
    }
    assert format_game_tv_broadcasters(broadcasters) == "Amazon Prime Video"


def test_get_todays_standings(league_standings_response):
    mock_league_standings = MagicMock()
    mock_league_standings.get_dict.return_value = league_standings_response
    with patch(
        "robo_burnie._helpers.leaguestandings.LeagueStandings",
        return_value=mock_league_standings,
    ):
        result = get_todays_standings()
        assert len(result) == 30
        assert "Conference" in result[0]
        assert "TeamName" in result[0]
        assert "WINS" in result[0]
        assert "LOSSES" in result[0]
        assert "WinPCT" in result[0]


@pytest.mark.parametrize(
    "away_tricode, home_tricode, game_id, espn_response, expected_link",
    [
        (
            "BOS",
            "LAL",
            "401307570",
            "https://www.espn.com/nba/boxscore/_/gameId/401307570",
            "https://www.espn.com/nba/boxscore/_/gameId/401307570",
        ),
        (
            "LAL",
            "BOS",
            "401307571",
            None,
            "https://www.nba.com/game/LAL-vs-BOS-401307571/boxscore#boxscore",
        ),
    ],
)
@pytest.mark.parametrize(
    "game_time",
    [
        datetime.now(timezone.utc),
        None,
    ],
)
def test_get_boxscore_link(
    away_tricode, home_tricode, game_id, espn_response, expected_link, game_time
):
    mock_scoreboard = MagicMock()
    mock_scoreboard.get_dict.return_value = espn_scoreboard_response
    with patch(
        "robo_burnie._helpers.get_espn_boxscore_link", return_value=espn_response
    ) as mock_espn_boxscore_link:
        result = get_boxscore_link(away_tricode, home_tricode, game_id, game_time)
        mock_espn_boxscore_link.assert_called_once_with(
            away_tricode=away_tricode, home_tricode=home_tricode, date=game_time
        )
        assert result == expected_link


@pytest.mark.parametrize(
    "game_id, expected",
    [
        ("1322600001", True),
        ("1522400010", True),
        ("1622600001", True),
        ("0022400100", False),
    ],
)
def test_is_summer_league_game(game_id, expected):
    assert is_summer_league_game(game_id) is expected


@patch("robo_burnie._helpers.get_todays_game_v3")
def test_get_todays_game_auto_prefers_summer_league(mock_get_game_v3):
    summer_game = {"game_id": "1322600001", "game_label": "Summer League"}
    mock_get_game_v3.side_effect = [summer_game]

    result = get_todays_game_auto(team="MIA")

    assert result == summer_game
    mock_get_game_v3.assert_called_once_with(team="MIA", league_id="13")


@patch("robo_burnie._helpers.get_todays_game_v3")
def test_get_todays_game_auto_falls_back_to_regular_season(mock_get_game_v3):
    regular_game = {"game_id": "0022400100", "game_label": ""}
    mock_get_game_v3.side_effect = [{}, {}, {}, regular_game]

    result = get_todays_game_auto(team="MIA")

    assert result == regular_game
    assert mock_get_game_v3.call_count == 4
    mock_get_game_v3.assert_any_call(team="MIA", league_id="00")


@patch("robo_burnie._helpers.scheduleleaguev2.ScheduleLeagueV2")
def test_get_todays_game_v3_normalizes_summer_league_label(mock_schedule):
    mock_schedule.return_value.get_dict.return_value = {
        "leagueSchedule": {
            "gameDates": [
                {
                    "gameDate": "07/03/2026 00:00:00",
                    "games": [
                        {
                            "gameId": "1322600001",
                            "gameLabel": "California Classic Summer League",
                            "gameStatus": 1,
                            "gameStatusText": "4:00 PM ET",
                            "homeTeam": {
                                "teamId": 1610612759,
                                "teamTricode": "SAS",
                                "wins": 0,
                                "losses": 1,
                            },
                            "awayTeam": {
                                "teamId": 1610612748,
                                "teamTricode": "MIA",
                                "wins": 1,
                                "losses": 0,
                            },
                        }
                    ],
                }
            ]
        }
    }

    with patch("robo_burnie._helpers.get_todays_date_str", return_value="07/03/2026"):
        result = get_todays_game_v3(team="MIA", league_id="13")

    assert result["game_label"] == "Summer League"
    mock_schedule.assert_called_once_with(league_id="13", season="2026-27")


@pytest.mark.parametrize(
    "away_tricode, home_tricode, game_id, espn_response, expected_link",
    [
        (
            "MIA",
            "SAS",
            "1322600001",
            "https://www.espn.com/nba-summer-league/game/_/gameId/401881933",
            "https://www.espn.com/nba-summer-league/game/_/gameId/401881933",
        ),
    ],
)
def test_get_boxscore_link_summer_league(
    away_tricode, home_tricode, game_id, espn_response, expected_link
):
    game_time = datetime.now(timezone.utc)
    with patch(
        "robo_burnie._helpers.get_espn_summer_league_boxscore_link",
        return_value=espn_response,
    ) as mock_espn_summer_link:
        result = get_boxscore_link(away_tricode, home_tricode, game_id, game_time)
        mock_espn_summer_link.assert_called_once_with(
            away_tricode=away_tricode, home_tricode=home_tricode, date=game_time
        )
        assert result == expected_link


def test_get_espn_summer_league_boxscore_link():
    game_time = datetime(2026, 7, 3, tzinfo=timezone.utc)
    scoreboard_response = {
        "events": [
            {
                "links": [
                    {
                        "href": "https://www.espn.com/nba-summer-league/game/_/gameId/401881933"
                    }
                ],
                "competitions": [
                    {
                        "competitors": [
                            {
                                "homeAway": "home",
                                "team": {"abbreviation": "SA"},
                            },
                            {
                                "homeAway": "away",
                                "team": {"abbreviation": "MIA"},
                            },
                        ]
                    }
                ],
            }
        ]
    }

    with patch("robo_burnie._helpers.requests.get") as mock_requests_get:
        mock_requests_get.return_value.status_code = 200
        mock_requests_get.return_value.json.return_value = scoreboard_response
        result = get_espn_summer_league_boxscore_link("MIA", "SAS", game_time)

    mock_requests_get.assert_called_once_with(
        "https://site.api.espn.com/apis/site/v2/sports/basketball/"
        "nba-summer-california/scoreboard?dates=20260703"
    )
    assert result == "https://www.espn.com/nba-summer-league/game/_/gameId/401881933"


@pytest.mark.parametrize(
    "away_tricode, home_tricode, game_time, expected_link",
    [
        (
            "PHX",
            "WSH",
            datetime.now(timezone.utc),
            "https://www.espn.com/nba/game?gameId=401705139",
        ),
        ("WSH", "PHX", datetime.now(timezone.utc), None),
    ],
)
def test_get_espn_boxscore_link(
    away_tricode, home_tricode, game_time, expected_link, espn_scoreboard_response
):
    with patch("robo_burnie._helpers.requests.get") as mock_requests_get:
        mock_requests_get.return_value.json.return_value = espn_scoreboard_response
        result = get_espn_boxscore_link(away_tricode, home_tricode, game_time)
        mock_requests_get.assert_called_once_with(
            f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={game_time.strftime('%Y%m%d')}"
        )
        assert result == expected_link
