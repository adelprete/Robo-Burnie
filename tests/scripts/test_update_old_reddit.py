from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from robo_burnie.scripts.update_old_reddit import (
    _get_opponent_display_str,
    _get_score_display_str,
    _main,
    _update_schedule,
    _update_standings,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MIAMI_ID = "1610612748"
BOSTON_ID = "1610612738"


@pytest.fixture()
def east_standings():
    return [
        {
            "Conference": "East",
            "TeamID": 1610612738,
            "TeamCity": "Boston",
            "TeamName": "Celtics",
            "WINS": 30,
            "LOSSES": 10,
            "WinPCT": 0.750,
        },
        {
            "Conference": "East",
            "TeamID": 1610612748,
            "TeamCity": "Miami",
            "TeamName": "Heat",
            "WINS": 25,
            "LOSSES": 15,
            "WinPCT": 0.625,
        },
        {
            "Conference": "West",
            "TeamID": 1610612747,
            "TeamCity": "Los Angeles",
            "TeamName": "Lakers",
            "WINS": 28,
            "LOSSES": 12,
            "WinPCT": 0.700,
        },
    ]


@pytest.fixture()
def sidebar_wiki():
    mock_sidebar = MagicMock()
    mock_sidebar.content_md = (
        "Welcome to r/heat\n\n"
        "##[Schedule](https://www.nba.com/heat/schedule/)\n\n"
        "|Date|Matchup|Score|\n|:--:|:--:|:--:|\n"
        "|old schedule data|\n\n"
        "##[Standings](http://espn.go.com/nba/standings/_/group/3)\n\n"
        "||Team|W|L|PCT|\n|:--:|:--|:--:|:--:|:--:|\n"
        "|old standings data|\n\n"
        "###Roster\nPlayer data here"
    )
    return mock_sidebar


@pytest.fixture()
def sample_schedule_games():
    """A list of 12 games — tests need at least 10 to exercise the windowing logic."""
    games = []
    for i in range(12):
        game_date = datetime(2025, 1, 10 + i)
        games.append(
            {
                "gameDateEst": f"{game_date.strftime('%Y-%m-%d')}T19:00:00",
                "gameStatusText": "7:00 PM ET",
                "homeTeam": {
                    "teamSlug": "heat" if i % 2 == 0 else "celtics",
                    "teamId": int(MIAMI_ID) if i % 2 == 0 else int(BOSTON_ID),
                    "teamTricode": "MIA" if i % 2 == 0 else "BOS",
                    "score": 110 if i < 6 else None,
                },
                "awayTeam": {
                    "teamSlug": "celtics" if i % 2 == 0 else "heat",
                    "teamId": int(BOSTON_ID) if i % 2 == 0 else int(MIAMI_ID),
                    "teamTricode": "BOS" if i % 2 == 0 else "MIA",
                    "score": 100 if i < 6 else None,
                },
            }
        )
    return games


# ---------------------------------------------------------------------------
# _get_opponent_display_str
# ---------------------------------------------------------------------------


def test_get_opponent_display_str_home():
    game = {
        "homeTeam": {"teamSlug": "heat", "teamId": int(MIAMI_ID)},
        "awayTeam": {
            "teamSlug": "celtics",
            "teamId": int(BOSTON_ID),
            "teamTricode": "BOS",
        },
    }
    result = _get_opponent_display_str(game, "heat")
    assert "BOS" in result
    assert "@" not in result


def test_get_opponent_display_str_away():
    game = {
        "homeTeam": {
            "teamSlug": "celtics",
            "teamId": int(BOSTON_ID),
            "teamTricode": "BOS",
        },
        "awayTeam": {"teamSlug": "heat", "teamId": int(MIAMI_ID)},
    }
    result = _get_opponent_display_str(game, "heat")
    assert "@ BOS" in result


# ---------------------------------------------------------------------------
# _get_score_display_str
# ---------------------------------------------------------------------------


def test_get_score_display_str_no_score():
    game = {
        "homeTeam": {"teamSlug": "heat", "score": None},
        "awayTeam": {"teamSlug": "celtics", "score": None},
    }
    assert _get_score_display_str(game, "heat") == ""


def test_get_score_display_str_home_win():
    game = {
        "homeTeam": {"teamSlug": "heat", "score": 110},
        "awayTeam": {"teamSlug": "celtics", "score": 100},
    }
    result = _get_score_display_str(game, "heat")
    assert "100 - 110" in result
    assert "**" in result  # bolded for a win


def test_get_score_display_str_home_loss():
    game = {
        "homeTeam": {"teamSlug": "heat", "score": 95},
        "awayTeam": {"teamSlug": "celtics", "score": 105},
    }
    result = _get_score_display_str(game, "heat")
    assert "105 - 95" in result
    assert "**" not in result  # not bolded for a loss


def test_get_score_display_str_away_win():
    game = {
        "homeTeam": {"teamSlug": "celtics", "score": 95},
        "awayTeam": {"teamSlug": "heat", "score": 105},
    }
    result = _get_score_display_str(game, "heat")
    assert "105 - 95" in result
    assert "**" in result


# ---------------------------------------------------------------------------
# _update_standings
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.update_old_reddit._helpers.get_todays_standings")
def test_update_standings(mock_standings, east_standings, sidebar_wiki):
    mock_standings.return_value = east_standings

    result = _update_standings(sidebar_wiki, "MIA")

    assert "Boston" in result
    assert "**[Miami]" in result  # Miami should be bolded
    assert "Los Angeles" not in result  # West teams excluded
    assert "###Roster" in result  # text after standings preserved


# ---------------------------------------------------------------------------
# _update_schedule
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.update_old_reddit._helpers.get_full_team_schedule")
def test_update_schedule(mock_schedule, sidebar_wiki, sample_schedule_games):
    mock_schedule.return_value = sample_schedule_games

    sidebar_text = sidebar_wiki.content_md
    with patch(
        "robo_burnie.scripts.update_old_reddit.datetime",
        wraps=datetime,
    ) as mock_dt:
        mock_dt.today.return_value = datetime(2025, 1, 16)
        mock_dt.strptime = datetime.strptime
        result = _update_schedule(sidebar_text, "heat")

    assert "##[Schedule]" in result
    assert "##[Standings]" in result
    assert "|" in result


# ---------------------------------------------------------------------------
# _main
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.update_old_reddit._update_schedule")
@patch("robo_burnie.scripts.update_old_reddit._update_standings")
@patch("robo_burnie.scripts.update_old_reddit.praw.Reddit")
def test_main(mock_reddit_cls, mock_update_standings, mock_update_schedule):
    mock_reddit = MagicMock()
    mock_reddit_cls.return_value = mock_reddit
    mock_subreddit = MagicMock()
    mock_reddit.subreddit.return_value = mock_subreddit
    mock_wiki = MagicMock()
    mock_subreddit.wiki.__getitem__.return_value = mock_wiki

    mock_update_standings.return_value = "standings text"
    mock_update_schedule.return_value = "final text"

    _main()

    mock_update_standings.assert_called_once_with(mock_wiki, "MIA")
    mock_update_schedule.assert_called_once_with("standings text", "heat")
    mock_wiki.edit.assert_called_once_with(content="final text")
