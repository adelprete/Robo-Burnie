import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from robo_burnie._helpers import (
    get_boxscore_link,
    get_espn_boxscore_link,
    get_todays_standings,
)


@pytest.fixture(scope="module")
def league_standings_response():
    with open("tests/test_data/nba_api_responses/leaguestandings.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def espn_scoreboard_response():
    with open("tests/test_data/espn_api/scoreboard.json") as f:
        return json.load(f)


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
