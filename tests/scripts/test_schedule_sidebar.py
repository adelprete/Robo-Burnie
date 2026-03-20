from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from robo_burnie.scripts.schedule_sidebar import (
    _build_events_map,
    _generate_event_data,
    _generate_event_start_end_times,
    _generate_event_summary,
    _main,
    _sync_schedule_widget,
    _update_google_calendar,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MIAMI_ID = "1610612748"
BOSTON_ID = "1610612738"


@pytest.fixture()
def home_game():
    return {
        "gameId": "0022400100",
        "homeTeam": {"teamSlug": "heat", "teamId": int(MIAMI_ID)},
        "awayTeam": {"teamSlug": "celtics", "teamId": int(BOSTON_ID)},
        "gameDateTimeUTC": "2025-01-20T00:30:00.000Z",
        "gameDateEst": "2025-01-19T19:30:00",
        "gameLabel": "",
    }


@pytest.fixture()
def away_game():
    return {
        "gameId": "0022400200",
        "homeTeam": {"teamSlug": "celtics", "teamId": int(BOSTON_ID)},
        "awayTeam": {"teamSlug": "heat", "teamId": int(MIAMI_ID)},
        "gameDateTimeUTC": "2025-01-22T00:00:00.000Z",
        "gameDateEst": "2025-01-21T19:00:00",
        "gameLabel": "",
    }


# ---------------------------------------------------------------------------
# _generate_event_summary
# ---------------------------------------------------------------------------


def test_generate_event_summary_home_game(home_game):
    result = _generate_event_summary(home_game)
    assert result == "Celtics"


def test_generate_event_summary_away_game(away_game):
    result = _generate_event_summary(away_game)
    assert result == "@Celtics"


def test_generate_event_summary_with_game_label(home_game):
    home_game["gameLabel"] = "Emirates NBA Cup"
    result = _generate_event_summary(home_game)
    assert result == "Celtics (NBA Cup)"


def test_generate_event_summary_with_playoff_label(home_game):
    home_game["gameLabel"] = "Round 1, Game 1"
    result = _generate_event_summary(home_game)
    assert result == "Celtics (Round 1, Game 1)"


# ---------------------------------------------------------------------------
# _generate_event_start_end_times
# ---------------------------------------------------------------------------


def test_generate_event_start_end_times(home_game):
    start, end = _generate_event_start_end_times(home_game)
    assert start is not None
    assert end is not None
    # End should be 2h30m after start
    from dateutil.parser import parse

    start_dt = parse(start)
    end_dt = parse(end)
    assert (end_dt - start_dt) == timedelta(hours=2, minutes=30)


# ---------------------------------------------------------------------------
# _generate_event_data
# ---------------------------------------------------------------------------


def test_generate_event_data(home_game):
    result = _generate_event_data(home_game)

    assert result["id"] == "0022400100"
    assert result["summary"] == "Celtics"
    assert result["start"]["timeZone"] == "America/New_York"
    assert result["end"]["timeZone"] == "America/New_York"


# ---------------------------------------------------------------------------
# _build_events_map
# ---------------------------------------------------------------------------


def test_build_events_map():
    mock_service = MagicMock()
    mock_service.events.return_value.list.return_value.execute.return_value = {
        "items": [
            {"id": "event1", "summary": "Celtics"},
            {"id": "event2", "summary": "@Lakers"},
        ]
    }

    result = _build_events_map(mock_service, "2025-01-20T00:00:00Z")

    assert "event1" in result
    assert "event2" in result
    assert result["event1"]["summary"] == "Celtics"


# ---------------------------------------------------------------------------
# _update_google_calendar
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.schedule_sidebar.time.sleep")
@patch("robo_burnie.scripts.schedule_sidebar._helpers.get_full_team_schedule")
def test_update_google_calendar_inserts_new(mock_schedule, mock_sleep):
    mock_service = MagicMock()
    mock_schedule.return_value = [
        {
            "gameId": "game1",
            "gameDateTimeUTC": "2025-02-01T00:00:00Z",
            "homeTeam": {"teamSlug": "heat", "teamId": int(MIAMI_ID)},
            "awayTeam": {"teamSlug": "celtics", "teamId": int(BOSTON_ID)},
            "gameDateEst": "2025-01-31T19:00:00",
            "gameLabel": "",
        },
    ]

    _update_google_calendar(mock_service, "2025-01-01T00:00:00Z", {})

    mock_service.events.return_value.insert.return_value.execute.assert_called_once()


@patch("robo_burnie.scripts.schedule_sidebar.time.sleep")
@patch("robo_burnie.scripts.schedule_sidebar._helpers.get_full_team_schedule")
def test_update_google_calendar_updates_existing(mock_schedule, mock_sleep):
    mock_service = MagicMock()
    mock_schedule.return_value = [
        {
            "gameId": "game1",
            "gameDateTimeUTC": "2025-02-01T00:00:00Z",
            "homeTeam": {"teamSlug": "heat", "teamId": int(MIAMI_ID)},
            "awayTeam": {"teamSlug": "celtics", "teamId": int(BOSTON_ID)},
            "gameDateEst": "2025-01-31T19:00:00",
            "gameLabel": "",
        },
    ]
    events_map = {"game1": {"id": "game1", "summary": "Celtics"}}

    _update_google_calendar(mock_service, "2025-01-01T00:00:00Z", events_map)

    mock_service.events.return_value.update.return_value.execute.assert_called_once()


@patch("robo_burnie.scripts.schedule_sidebar.time.sleep")
@patch("robo_burnie.scripts.schedule_sidebar._helpers.get_full_team_schedule")
def test_update_google_calendar_skips_past_games(mock_schedule, mock_sleep):
    mock_service = MagicMock()
    mock_schedule.return_value = [
        {
            "gameId": "game1",
            "gameDateTimeUTC": "2024-12-01T00:00:00Z",
            "homeTeam": {"teamSlug": "heat", "teamId": int(MIAMI_ID)},
            "awayTeam": {"teamSlug": "celtics", "teamId": int(BOSTON_ID)},
            "gameDateEst": "2024-11-30T19:00:00",
            "gameLabel": "",
        },
    ]

    _update_google_calendar(mock_service, "2025-01-01T00:00:00Z", {})

    mock_service.events.return_value.insert.return_value.execute.assert_not_called()
    mock_service.events.return_value.update.return_value.execute.assert_not_called()


# ---------------------------------------------------------------------------
# _sync_schedule_widget
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.schedule_sidebar.praw.Reddit")
def test_sync_schedule_widget(mock_reddit_cls):
    mock_reddit = MagicMock()
    mock_reddit_cls.return_value = mock_reddit
    schedule_widget = MagicMock()
    schedule_widget.shortName = "Schedule"
    other_widget = MagicMock()
    other_widget.shortName = "Standings"
    mock_reddit.subreddit.return_value.widgets.sidebar = [other_widget, schedule_widget]

    _sync_schedule_widget()

    schedule_widget.mod.update.assert_called_once_with(requiresSync=True)


# ---------------------------------------------------------------------------
# _main
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.schedule_sidebar._sync_schedule_widget")
@patch("robo_burnie.scripts.schedule_sidebar._update_google_calendar")
@patch("robo_burnie.scripts.schedule_sidebar._build_events_map")
@patch("robo_burnie.scripts.schedule_sidebar._get_google_calendar_service")
def test_main(mock_service, mock_events_map, mock_update_cal, mock_sync):
    mock_service.return_value = MagicMock()
    mock_events_map.return_value = {}

    _main()

    mock_service.assert_called_once()
    mock_events_map.assert_called_once()
    mock_update_cal.assert_called_once()
    mock_sync.assert_called_once()
