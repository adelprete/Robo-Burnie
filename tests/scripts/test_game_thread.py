from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from robo_burnie.scripts.game_thread import (
    _build_standings_table,
    _generate_post_details,
    _get_radio_broadcasters,
    _get_tv_broadcasters,
    _main,
    _ordinal,
    _submit_post,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MIAMI_TEAM_ID = "1610612748"
BOSTON_TEAM_ID = "1610612738"


@pytest.fixture()
def todays_game():
    return {
        "game_id": "0022400100",
        "game_label": "",
        "status_id": 1,
        "status_text": "7:30 PM ET",
        "home_team_id": int(MIAMI_TEAM_ID),
        "home_team_wins": 20,
        "home_team_losses": 10,
        "away_team_id": int(BOSTON_TEAM_ID),
        "away_team_wins": 25,
        "away_team_losses": 5,
    }


@pytest.fixture()
def cdn_game_data():
    return {
        "homeTeam": {"teamTricode": "MIA"},
        "awayTeam": {"teamTricode": "BOS"},
        "broadcasters": {
            "nationalTvBroadcasters": [
                {"broadcasterAbbreviation": "ESPN"},
            ],
            "homeTvBroadcasters": [
                {"broadcasterAbbreviation": "BSSUN"},
            ],
            "awayTvBroadcasters": [
                {"broadcasterAbbreviation": "NBCSB"},
            ],
            "nationalRadioBroadcasters": [],
            "homeRadioBroadcasters": [
                {"broadcasterAbbreviation": "WAXY"},
            ],
            "awayRadioBroadcasters": [
                {"broadcasterAbbreviation": "WBZ"},
            ],
        },
    }


@pytest.fixture()
def standings_entry():
    return {
        "PlayoffRank": 4,
        "Conference": "East",
        "strCurrentStreak": "W 3",
        "L10": "7-3",
        "PointsPG": 112.5,
        "OppPointsPG": 108.3,
    }


# ---------------------------------------------------------------------------
# _ordinal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "n, expected",
    [
        (1, "1st"),
        (2, "2nd"),
        (3, "3rd"),
        (4, "4th"),
        (11, "11th"),
        (12, "12th"),
        (13, "13th"),
        (21, "21st"),
        (22, "22nd"),
        (23, "23rd"),
        (100, "100th"),
    ],
)
def test_ordinal(n, expected):
    assert _ordinal(n) == expected


# ---------------------------------------------------------------------------
# _get_tv_broadcasters / _get_radio_broadcasters
# ---------------------------------------------------------------------------


def test_get_tv_broadcasters_home_team(cdn_game_data):
    result = _get_tv_broadcasters(cdn_game_data, "MIA")
    assert result == ["BSSUN", "ESPN"]


def test_get_tv_broadcasters_away_team(cdn_game_data):
    result = _get_tv_broadcasters(cdn_game_data, "BOS")
    assert result == ["NBCSB", "ESPN"]


def test_get_radio_broadcasters_home_team(cdn_game_data):
    result = _get_radio_broadcasters(cdn_game_data, "MIA")
    assert result == ["WAXY"]


def test_get_radio_broadcasters_away_team(cdn_game_data):
    result = _get_radio_broadcasters(cdn_game_data, "BOS")
    assert result == ["WBZ"]


# ---------------------------------------------------------------------------
# _build_standings_table
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.game_thread._helpers.get_team_standings")
@patch("robo_burnie.scripts.game_thread._helpers.get_todays_standings")
def test_build_standings_table(mock_standings, mock_team_standings, standings_entry):
    mock_standings.return_value = []
    mock_team_standings.return_value = standings_entry

    result = _build_standings_table(
        int(BOSTON_TEAM_ID), int(MIAMI_TEAM_ID), "BOS", "MIA"
    )

    assert "**BOS**" in result
    assert "**MIA**" in result
    assert "4th East" in result
    assert "W 3" in result


@patch("robo_burnie.scripts.game_thread._helpers.get_team_standings")
@patch("robo_burnie.scripts.game_thread._helpers.get_todays_standings")
def test_build_standings_table_missing_team(mock_standings, mock_team_standings):
    mock_standings.return_value = []
    mock_team_standings.return_value = {}

    result = _build_standings_table(
        int(BOSTON_TEAM_ID), int(MIAMI_TEAM_ID), "BOS", "MIA"
    )
    assert result == ""


@patch(
    "robo_burnie.scripts.game_thread._helpers.get_todays_standings",
    side_effect=Exception("API down"),
)
def test_build_standings_table_exception(mock_standings):
    result = _build_standings_table(
        int(BOSTON_TEAM_ID), int(MIAMI_TEAM_ID), "BOS", "MIA"
    )
    assert result == ""


# ---------------------------------------------------------------------------
# _generate_post_details
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.game_thread._build_standings_table", return_value="")
@patch(
    "robo_burnie.scripts.game_thread._helpers.get_boxscore_link",
    return_value="https://espn.com/boxscore",
)
@patch("robo_burnie.scripts.game_thread._helpers.get_game_from_cdn_endpoint")
def test_generate_post_details(
    mock_cdn, mock_boxscore_link, mock_standings_table, todays_game, cdn_game_data
):
    mock_cdn.return_value = cdn_game_data

    title, body = _generate_post_details(todays_game, "MIA")

    assert "[Game Thread]" in title
    assert "Boston Celtics" in title
    assert "Miami Heat" in title
    assert "25-5" in title
    assert "20-10" in title
    assert "7:30 PM ET" in title
    assert "BSSUN" in body
    assert "ESPN" in body
    assert "WAXY" in body
    assert "https://espn.com/boxscore" in body


@patch("robo_burnie.scripts.game_thread._build_standings_table", return_value="")
@patch(
    "robo_burnie.scripts.game_thread._helpers.get_boxscore_link",
    return_value="https://espn.com/boxscore",
)
@patch("robo_burnie.scripts.game_thread._helpers.get_game_from_cdn_endpoint")
def test_generate_post_details_with_game_label(
    mock_cdn, mock_boxscore_link, mock_standings_table, todays_game, cdn_game_data
):
    todays_game["game_label"] = "NBA Cup"
    mock_cdn.return_value = cdn_game_data

    title, _ = _generate_post_details(todays_game, "MIA")
    assert "[NBA Cup]" in title


@patch(
    "robo_burnie.scripts.game_thread._build_standings_table",
    return_value="| standings |",
)
@patch(
    "robo_burnie.scripts.game_thread._helpers.get_boxscore_link",
    return_value="https://espn.com/boxscore",
)
@patch("robo_burnie.scripts.game_thread._helpers.get_game_from_cdn_endpoint")
def test_generate_post_details_includes_standings(
    mock_cdn, mock_boxscore_link, mock_standings_table, todays_game, cdn_game_data
):
    mock_cdn.return_value = cdn_game_data

    _, body = _generate_post_details(todays_game, "MIA")
    assert "| standings |" in body


# ---------------------------------------------------------------------------
# _submit_post
# ---------------------------------------------------------------------------


def test_submit_post_creates_thread_when_none_exists():
    mock_subreddit = MagicMock()
    mock_submission = MagicMock()
    mock_subreddit.submit.return_value = mock_submission

    post1 = MagicMock(stickied=False, title="Some other post")
    post2 = MagicMock(stickied=True, title="Daily Discussion")
    mock_subreddit.hot.return_value = [post1, post2]

    _submit_post(mock_subreddit, "Test Title", "Test Body")

    mock_subreddit.submit.assert_called_once()
    mock_submission.mod.sticky.assert_called_once()
    mock_submission.mod.suggested_sort.assert_called_once_with("new")


def test_submit_post_skips_when_game_thread_exists():
    mock_subreddit = MagicMock()
    stickied_post = MagicMock(stickied=True, title="[Game Thread] MIA vs BOS")
    mock_subreddit.hot.return_value = [stickied_post]

    _submit_post(mock_subreddit, "Test Title", "Test Body")

    mock_subreddit.submit.assert_not_called()


def test_submit_post_unstickies_post_game_thread():
    mock_subreddit = MagicMock()
    mock_submission = MagicMock()
    mock_subreddit.submit.return_value = mock_submission

    non_game_post = MagicMock(stickied=True, title="Daily Discussion")
    post_game = MagicMock(stickied=True, title="[Post Game] Heat beat Celtics")
    mock_subreddit.hot.return_value = [non_game_post, post_game]

    _submit_post(mock_subreddit, "Test Title", "Test Body")

    post_game.mod.sticky.assert_called_with(False)


# ---------------------------------------------------------------------------
# _main
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.game_thread._helpers.get_todays_game_v3")
def test_main_no_game_today(mock_get_game):
    mock_get_game.return_value = {}
    _main("create")
    mock_get_game.assert_called_once()


@patch("robo_burnie.scripts.game_thread._submit_post")
@patch("robo_burnie.scripts.game_thread.praw.Reddit")
@patch("robo_burnie.scripts.game_thread._generate_post_details")
@patch("robo_burnie.scripts.game_thread._helpers.get_todays_game_v3")
def test_main_game_not_started(
    mock_get_game, mock_gen_details, mock_reddit_cls, mock_submit
):
    mock_get_game.return_value = {
        "game_id": "001",
        "game_label": "",
        "status_id": 1,
        "status_text": "7:30 PM ET",
        "home_team_id": int(MIAMI_TEAM_ID),
        "home_team_wins": 20,
        "home_team_losses": 10,
        "away_team_id": int(BOSTON_TEAM_ID),
        "away_team_wins": 25,
        "away_team_losses": 5,
    }
    mock_gen_details.return_value = ("Title", "Body")
    mock_reddit = MagicMock()
    mock_reddit_cls.return_value = mock_reddit

    _main("create")

    mock_submit.assert_called_once()


@patch("robo_burnie.scripts.game_thread._submit_post")
@patch("robo_burnie.scripts.game_thread.praw.Reddit")
@patch("robo_burnie.scripts.game_thread._generate_post_details")
@patch("robo_burnie.scripts.game_thread._helpers.get_todays_game_v3")
def test_main_game_already_started(
    mock_get_game, mock_gen_details, mock_reddit_cls, mock_submit
):
    mock_get_game.return_value = {
        "status_id": 2,
    }

    _main("create")

    mock_gen_details.assert_not_called()
    mock_submit.assert_not_called()
