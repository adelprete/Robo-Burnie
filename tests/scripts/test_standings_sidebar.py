from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from robo_burnie.scripts.standings_sidebar import (
    _build_standings_markdown,
    _get_standings_widget,
    _main,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def east_standings():
    """Minimal standings for two East teams including Miami."""
    return [
        {
            "Conference": "East",
            "TeamID": 1610612738,
            "TeamName": "Celtics",
            "WINS": 30,
            "LOSSES": 10,
            "WinPCT": 0.750,
        },
        {
            "Conference": "East",
            "TeamID": 1610612748,
            "TeamName": "Heat",
            "WINS": 25,
            "LOSSES": 15,
            "WinPCT": 0.625,
        },
        {
            "Conference": "West",
            "TeamID": 1610612747,
            "TeamName": "Lakers",
            "WINS": 28,
            "LOSSES": 12,
            "WinPCT": 0.700,
        },
    ]


# ---------------------------------------------------------------------------
# _build_standings_markdown
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.standings_sidebar._helpers.get_todays_standings")
def test_build_standings_markdown(mock_standings, east_standings):
    mock_standings.return_value = east_standings

    result = _build_standings_markdown()

    assert "Team" in result
    assert "Celtics" in result
    assert "**Heat**" in result  # Heat row should be bolded
    assert "Lakers" not in result  # West teams excluded
    assert "30" in result
    assert "10" in result


@patch("robo_burnie.scripts.standings_sidebar._helpers.get_todays_standings")
def test_build_standings_markdown_positions(mock_standings, east_standings):
    mock_standings.return_value = east_standings

    result = _build_standings_markdown()

    lines = result.strip().split("\n")
    header_line = lines[0]
    assert "| | Team | W | L | Pct |" == header_line

    celtics_line = lines[2]
    assert "| 1 |" in celtics_line

    heat_line = lines[3]
    assert "| 2 |" in heat_line


# ---------------------------------------------------------------------------
# _get_standings_widget
# ---------------------------------------------------------------------------


def test_get_standings_widget_found():
    mock_reddit = MagicMock()
    standings_widget = MagicMock()
    standings_widget.shortName = "Standings"
    other_widget = MagicMock()
    other_widget.shortName = "Schedule"
    mock_reddit.subreddit.return_value.widgets.sidebar = [
        other_widget,
        standings_widget,
    ]

    result = _get_standings_widget(mock_reddit)
    assert result is standings_widget


def test_get_standings_widget_not_found():
    mock_reddit = MagicMock()
    other_widget = MagicMock()
    other_widget.shortName = "Schedule"
    mock_reddit.subreddit.return_value.widgets.sidebar = [other_widget]

    result = _get_standings_widget(mock_reddit)
    assert result is None


# ---------------------------------------------------------------------------
# _main
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.standings_sidebar._build_standings_markdown")
@patch("robo_burnie.scripts.standings_sidebar._get_standings_widget")
@patch("robo_burnie.scripts.standings_sidebar.praw.Reddit")
def test_main_updates_widget(mock_reddit_cls, mock_get_widget, mock_build_md):
    mock_widget = MagicMock()
    mock_get_widget.return_value = mock_widget
    mock_build_md.return_value = "| standings markdown |"

    _main()

    mock_widget.mod.update.assert_called_once()
    call_kwargs = mock_widget.mod.update.call_args
    assert "| standings markdown |" in str(call_kwargs)


@patch("robo_burnie.scripts.standings_sidebar._build_standings_markdown")
@patch("robo_burnie.scripts.standings_sidebar._get_standings_widget")
@patch("robo_burnie.scripts.standings_sidebar.praw.Reddit")
def test_main_no_widget(mock_reddit_cls, mock_get_widget, mock_build_md):
    mock_get_widget.return_value = None

    _main()

    mock_build_md.assert_not_called()
