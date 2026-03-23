from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from robo_burnie.scripts.around_the_league_thread import (
    _create_around_the_league_thread,
    _format_around_the_league_tv_channels,
    _generate_post_body,
    _main,
    _unsticky_old_around_the_league_thread,
    _update_around_the_league_thread,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def todays_games():
    return {
        "001": {
            "visitor_name": "Celtics",
            "home_name": "Lakers",
            "visitor_pts": 105,
            "home_pts": 110,
            "game_status_text": " Final ",
            "natl_tv_broadcaster_abbreviation": "ESPN",
        },
        "002": {
            "visitor_name": "Knicks",
            "home_name": "Bulls",
            "visitor_pts": None,
            "home_pts": None,
            "game_status_text": " 7:00 PM ET ",
            "natl_tv_broadcaster_abbreviation": None,
        },
    }


# ---------------------------------------------------------------------------
# _format_around_the_league_tv_channels
# ---------------------------------------------------------------------------


def test_format_tv_omits_amazon_when_other_channels():
    assert _format_around_the_league_tv_channels("ESPN, Amazon Prime Video") == "ESPN"
    assert _format_around_the_league_tv_channels("Amazon Prime Video, TNT") == "TNT"


def test_format_tv_keeps_amazon_when_only_channel():
    assert (
        _format_around_the_league_tv_channels("Amazon Prime Video")
        == "Amazon Prime Video"
    )


def test_format_tv_prime_video_display_name():
    assert _format_around_the_league_tv_channels("Prime Video") == "Prime Video"
    assert _format_around_the_league_tv_channels("ESPN, Prime Video") == "ESPN"


# ---------------------------------------------------------------------------
# _generate_post_body
# ---------------------------------------------------------------------------


def test_generate_post_body(todays_games):
    body = _generate_post_body(todays_games)

    assert "nba.com" in body
    assert "Celtics" in body
    assert "Lakers" in body
    assert "105 - 110" in body
    assert "(Final)" in body
    assert "ESPN" in body
    assert "Knicks" in body
    assert "Bulls" in body
    assert "7:00 PM ET" in body


def test_generate_post_body_timberwolves_abbreviated():
    games = {
        "001": {
            "visitor_name": "Timberwolves",
            "home_name": "Heat",
            "visitor_pts": None,
            "home_pts": None,
            "game_status_text": " 8:00 PM ET ",
            "natl_tv_broadcaster_abbreviation": "TBD",
        },
    }
    body = _generate_post_body(games)
    assert "T-Wolves" in body
    assert "Timberwolves" not in body
    # TBD broadcasters should be empty
    assert "TBD" not in body


def test_generate_post_body_tbd_broadcaster():
    games = {
        "001": {
            "visitor_name": "Heat",
            "home_name": "Celtics",
            "visitor_pts": None,
            "home_pts": None,
            "game_status_text": " 7:30 PM ET ",
            "natl_tv_broadcaster_abbreviation": "TBD",
        },
    }
    body = _generate_post_body(games)
    assert "TBD" not in body


def test_generate_post_body_amazon_prime_with_linear_tv():
    games = {
        "001": {
            "visitor_name": "Heat",
            "home_name": "Celtics",
            "visitor_pts": None,
            "home_pts": None,
            "game_status_text": " 7:30 PM ET ",
            "natl_tv_broadcaster_abbreviation": "ESPN, Amazon Prime Video",
        },
    }
    body = _generate_post_body(games)
    assert "ESPN" in body
    assert "Amazon" not in body


def test_generate_post_body_amazon_prime_only():
    games = {
        "001": {
            "visitor_name": "Heat",
            "home_name": "Celtics",
            "visitor_pts": None,
            "home_pts": None,
            "game_status_text": " 7:30 PM ET ",
            "natl_tv_broadcaster_abbreviation": "Amazon Prime Video",
        },
    }
    body = _generate_post_body(games)
    assert "Amazon Prime Video" in body


# ---------------------------------------------------------------------------
# _unsticky_old_around_the_league_thread
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.around_the_league_thread.TODAYS_DATE_STR", "20250120")
def test_unsticky_old_thread():
    old_post = MagicMock(stickied=True, title="[Around the League] Discuss")
    old_post.created_utc = datetime(2025, 1, 19, 12, 0, 0).timestamp()
    subreddit = MagicMock()
    subreddit.hot.return_value = [old_post]

    _unsticky_old_around_the_league_thread(subreddit)
    old_post.mod.sticky.assert_called_once_with(False)


@patch("robo_burnie.scripts.around_the_league_thread.TODAYS_DATE_STR", "20250120")
def test_unsticky_keeps_todays_thread():
    today_post = MagicMock(stickied=True, title="[Around the League] Discuss")
    today_post.created_utc = datetime(2025, 1, 20, 12, 0, 0).timestamp()
    subreddit = MagicMock()
    subreddit.hot.return_value = [today_post]

    _unsticky_old_around_the_league_thread(subreddit)
    today_post.mod.sticky.assert_not_called()


# ---------------------------------------------------------------------------
# _create_around_the_league_thread
# ---------------------------------------------------------------------------


@patch(
    "robo_burnie.scripts.around_the_league_thread._unsticky_old_around_the_league_thread"
)
def test_create_thread(mock_unsticky):
    subreddit = MagicMock()
    submission = MagicMock()
    subreddit.submit.return_value = submission

    _create_around_the_league_thread(subreddit, "test body")

    subreddit.submit.assert_called_once()
    submission.mod.sticky.assert_called_once()
    submission.mod.suggested_sort.assert_called_once_with(sort="new")
    mock_unsticky.assert_called_once()


# ---------------------------------------------------------------------------
# _update_around_the_league_thread
# ---------------------------------------------------------------------------


def test_update_thread():
    subreddit = MagicMock()
    matching_post = MagicMock(title="[Around the League] Discuss today's NBA news")
    other_post = MagicMock(title="Daily Discussion")
    subreddit.new.return_value = [other_post, matching_post]

    _update_around_the_league_thread(subreddit, "updated body")

    matching_post.edit.assert_called_once_with("updated body")
    matching_post.save.assert_called_once()
    other_post.edit.assert_not_called()


# ---------------------------------------------------------------------------
# _main
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.around_the_league_thread.praw.Reddit")
@patch("robo_burnie.scripts.around_the_league_thread._helpers.get_todays_game_v3")
def test_main_team_plays_today(mock_get_game, mock_reddit_cls):
    mock_get_game.return_value = {"game_id": "001"}
    mock_reddit = MagicMock()
    mock_reddit_cls.return_value = mock_reddit
    mock_subreddit = MagicMock()
    mock_reddit.subreddit.return_value = mock_subreddit
    mock_subreddit.hot.return_value = []

    _main("create")

    mock_get_game.assert_called_once()


@patch(
    "robo_burnie.scripts.around_the_league_thread._helpers.get_todays_games_from_schedule"
)
@patch("robo_burnie.scripts.around_the_league_thread.praw.Reddit")
@patch("robo_burnie.scripts.around_the_league_thread._helpers.get_todays_game_v3")
def test_main_no_games_today(mock_get_game, mock_reddit_cls, mock_games_schedule):
    mock_get_game.return_value = {}
    mock_games_schedule.return_value = {}
    mock_reddit = MagicMock()
    mock_reddit_cls.return_value = mock_reddit
    mock_subreddit = MagicMock()
    mock_reddit.subreddit.return_value = mock_subreddit
    mock_subreddit.hot.return_value = []

    _main("create")

    mock_games_schedule.assert_called_once()


@patch("robo_burnie.scripts.around_the_league_thread._create_around_the_league_thread")
@patch("robo_burnie.scripts.around_the_league_thread._generate_post_body")
@patch(
    "robo_burnie.scripts.around_the_league_thread._helpers.get_todays_games_from_schedule"
)
@patch("robo_burnie.scripts.around_the_league_thread.praw.Reddit")
@patch("robo_burnie.scripts.around_the_league_thread._helpers.get_todays_game_v3")
def test_main_create_action(
    mock_get_game, mock_reddit_cls, mock_games_schedule, mock_gen_body, mock_create
):
    mock_get_game.return_value = {}
    mock_games_schedule.return_value = {"001": {"some": "game"}}
    mock_gen_body.return_value = "body"
    mock_reddit = MagicMock()
    mock_reddit_cls.return_value = mock_reddit

    _main("create")

    mock_create.assert_called_once()


@patch("robo_burnie.scripts.around_the_league_thread._update_around_the_league_thread")
@patch("robo_burnie.scripts.around_the_league_thread._generate_post_body")
@patch("robo_burnie.scripts.around_the_league_thread._helpers.get_todays_games_cdn")
@patch("robo_burnie.scripts.around_the_league_thread.praw.Reddit")
@patch("robo_burnie.scripts.around_the_league_thread._helpers.get_todays_game_v3")
def test_main_update_action(
    mock_get_game, mock_reddit_cls, mock_games_cdn, mock_gen_body, mock_update
):
    mock_get_game.return_value = {}
    mock_games_cdn.return_value = {"001": {"some": "game"}}
    mock_gen_body.return_value = "body"
    mock_reddit = MagicMock()
    mock_reddit_cls.return_value = mock_reddit

    _main("update")

    mock_update.assert_called_once()
