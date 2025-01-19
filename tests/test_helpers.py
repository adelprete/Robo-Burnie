import json
from unittest.mock import MagicMock, patch

import pytest

from robo_burnie._helpers import get_todays_standings


@pytest.fixture(scope="session")
def league_standings_response():
    with open("tests/nba_api_responses/leaguestandings.json") as f:
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
