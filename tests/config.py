import json

import pytest


@pytest.fixture(scope="session")
def league_standings_response():
    with open("tests/nba_api_responses/leaguestandings.json") as f:
        return json.load(f)
