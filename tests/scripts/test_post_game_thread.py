from __future__ import annotations

import random
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from robo_burnie.scripts.post_game_thread import (
    GameStatus,
    _generate_post_details,
    _generate_post_title,
    _get_stats_leader_text,
    _is_game_over,
    _main,
    _post_game_thread_exists,
    _sleep_for_awhile,
    _submit_post,
    _unsticky_game_thread,
    _unsticky_old_post_game_thread,
    _wait_for_game_to_end,
    _wait_for_game_to_start,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_player(name: str, pts: int, reb: int, ast: int) -> dict:
    return {
        "name": name,
        "statistics": {
            "points": pts,
            "reboundsTotal": reb,
            "assists": ast,
        },
    }


@pytest.fixture()
def boxscore():
    return {
        "gameId": "0022400100",
        "gameStatus": GameStatus.POST_GAME.value,
        "gameClock": "PT00M00.00S",
        "period": 4,
        "gameTimeLocal": "2025-01-15T19:30:00-05:00",
        "homeTeam": {
            "teamTricode": "MIA",
            "teamName": "Heat",
            "score": 110,
            "players": [
                _make_player("Bam Adebayo", 28, 12, 5),
                _make_player("Tyler Herro", 22, 4, 6),
            ],
        },
        "awayTeam": {
            "teamTricode": "BOS",
            "teamName": "Celtics",
            "score": 100,
            "players": [
                _make_player("Jayson Tatum", 30, 8, 4),
                _make_player("Jaylen Brown", 20, 5, 3),
            ],
        },
    }


# ---------------------------------------------------------------------------
# GameStatus enum
# ---------------------------------------------------------------------------


def test_game_status_values():
    assert GameStatus.NOT_STARTED.value == 1
    assert GameStatus.IN_PROGRESS.value == 2
    assert GameStatus.POST_GAME.value == 3


# ---------------------------------------------------------------------------
# _is_game_over
# ---------------------------------------------------------------------------


def test_is_game_over_true(boxscore):
    assert _is_game_over(boxscore) is True


def test_is_game_over_false_still_in_progress(boxscore):
    boxscore["gameStatus"] = GameStatus.IN_PROGRESS.value
    assert _is_game_over(boxscore) is False


def test_is_game_over_false_tied(boxscore):
    boxscore["homeTeam"]["score"] = 100
    boxscore["awayTeam"]["score"] = 100
    assert _is_game_over(boxscore) is False


# ---------------------------------------------------------------------------
# _get_stats_leader_text
# ---------------------------------------------------------------------------


def test_get_stats_leader_text_points(boxscore):
    result = _get_stats_leader_text("points", boxscore["homeTeam"]["players"])
    assert "Bam Adebayo" in result
    assert "28" in result
    assert "PTS" in result


def test_get_stats_leader_text_rebounds(boxscore):
    result = _get_stats_leader_text("reboundsTotal", boxscore["homeTeam"]["players"])
    assert "Bam Adebayo" in result
    assert "12" in result
    assert "REBS" in result


def test_get_stats_leader_text_assists(boxscore):
    result = _get_stats_leader_text("assists", boxscore["homeTeam"]["players"])
    assert "Tyler Herro" in result
    assert "6" in result
    assert "ASTS" in result


# ---------------------------------------------------------------------------
# _generate_post_title
# ---------------------------------------------------------------------------


def test_generate_post_title_blowout_win(boxscore):
    boxscore["homeTeam"]["score"] = 120
    boxscore["awayTeam"]["score"] = 95
    random.seed(0)
    title = _generate_post_title(boxscore, "homeTeam", "awayTeam")
    assert "[Post Game]" in title
    assert "120 - 95" in title


def test_generate_post_title_close_win(boxscore):
    boxscore["homeTeam"]["score"] = 105
    boxscore["awayTeam"]["score"] = 102
    random.seed(0)
    title = _generate_post_title(boxscore, "homeTeam", "awayTeam")
    assert "[Post Game]" in title
    assert "105 - 102" in title


def test_generate_post_title_moderate_loss(boxscore):
    boxscore["homeTeam"]["score"] = 95
    boxscore["awayTeam"]["score"] = 108
    random.seed(0)
    title = _generate_post_title(boxscore, "homeTeam", "awayTeam")
    assert "[Post Game]" in title
    assert "95 - 108" in title


def test_generate_post_title_blowout_loss(boxscore):
    boxscore["homeTeam"]["score"] = 80
    boxscore["awayTeam"]["score"] = 110
    random.seed(0)
    title = _generate_post_title(boxscore, "homeTeam", "awayTeam")
    assert "[Post Game]" in title
    assert "80 - 110" in title


def test_generate_post_title_close_loss(boxscore):
    boxscore["homeTeam"]["score"] = 100
    boxscore["awayTeam"]["score"] = 103
    random.seed(0)
    title = _generate_post_title(boxscore, "homeTeam", "awayTeam")
    assert "[Post Game]" in title
    assert "100 - 103" in title


# ---------------------------------------------------------------------------
# _generate_post_details
# ---------------------------------------------------------------------------


@patch(
    "robo_burnie.scripts.post_game_thread._helpers.get_boxscore_link",
    return_value="https://espn.com/boxscore",
)
def test_generate_post_details(mock_boxscore_link, boxscore):
    random.seed(0)
    title, selftext = _generate_post_details(boxscore)

    assert "[Post Game]" in title
    assert "110 - 100" in title
    assert "https://espn.com/boxscore" in selftext
    assert "PTS" in selftext
    assert "REBS" in selftext
    assert "ASTS" in selftext


@patch(
    "robo_burnie.scripts.post_game_thread._helpers.get_boxscore_link",
    return_value="https://espn.com/boxscore",
)
def test_generate_post_details_away_team(mock_boxscore_link, boxscore):
    boxscore["awayTeam"]["teamTricode"] = "MIA"
    boxscore["homeTeam"]["teamTricode"] = "BOS"
    random.seed(0)
    title, selftext = _generate_post_details(boxscore)

    assert "Celtics" in title
    assert "Heat" in title


# ---------------------------------------------------------------------------
# _wait_for_game_to_start
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.post_game_thread._helpers.get_boxscore")
def test_wait_for_game_to_start_already_in_progress(mock_get_boxscore):
    mock_get_boxscore.return_value = {"gameStatus": GameStatus.IN_PROGRESS.value}
    _wait_for_game_to_start("001")
    mock_get_boxscore.assert_called_once_with("001")


@patch("robo_burnie.scripts.post_game_thread.time.sleep")
@patch("robo_burnie.scripts.post_game_thread._helpers.get_boxscore")
def test_wait_for_game_to_start_waits_then_starts(mock_get_boxscore, mock_sleep):
    mock_get_boxscore.side_effect = [
        {"gameStatus": GameStatus.NOT_STARTED.value},
        {"gameStatus": GameStatus.IN_PROGRESS.value},
    ]
    _wait_for_game_to_start("001")
    assert mock_get_boxscore.call_count == 2
    mock_sleep.assert_called_once_with(7200)


# ---------------------------------------------------------------------------
# _wait_for_game_to_end
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.post_game_thread._sleep_for_awhile")
@patch("robo_burnie.scripts.post_game_thread._helpers.get_boxscore")
def test_wait_for_game_to_end_already_over(mock_get_boxscore, mock_sleep):
    mock_get_boxscore.return_value = {
        "gameStatus": GameStatus.POST_GAME.value,
        "awayTeam": {"score": 100},
        "homeTeam": {"score": 110},
    }
    _wait_for_game_to_end("001")
    mock_sleep.assert_not_called()


@patch("robo_burnie.scripts.post_game_thread._sleep_for_awhile")
@patch("robo_burnie.scripts.post_game_thread._helpers.get_boxscore")
def test_wait_for_game_to_end_loops_until_over(mock_get_boxscore, mock_sleep):
    mock_get_boxscore.side_effect = [
        {
            "gameStatus": GameStatus.IN_PROGRESS.value,
            "awayTeam": {"score": 50},
            "homeTeam": {"score": 55},
        },
        {
            "gameStatus": GameStatus.POST_GAME.value,
            "awayTeam": {"score": 100},
            "homeTeam": {"score": 110},
        },
    ]
    _wait_for_game_to_end("001")
    assert mock_sleep.call_count == 1


# ---------------------------------------------------------------------------
# _sleep_for_awhile
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.post_game_thread.time.sleep")
def test_sleep_for_awhile_4th_quarter_under_24_seconds(mock_sleep):
    box = {"period": 4, "gameClock": "PT00M20.00S"}
    _sleep_for_awhile(box)
    mock_sleep.assert_called_once_with(5)


@patch("robo_burnie.scripts.post_game_thread.time.sleep")
def test_sleep_for_awhile_4th_quarter_under_40_seconds(mock_sleep):
    box = {"period": 4, "gameClock": "PT00M35.00S"}
    _sleep_for_awhile(box)
    mock_sleep.assert_called_once_with(10)


@patch("robo_burnie.scripts.post_game_thread.time.sleep")
def test_sleep_for_awhile_4th_quarter(mock_sleep):
    box = {"period": 4, "gameClock": "PT05M00.00S"}
    _sleep_for_awhile(box)
    mock_sleep.assert_called_once_with(40)


@patch("robo_burnie.scripts.post_game_thread.time.sleep")
def test_sleep_for_awhile_before_4th_quarter(mock_sleep):
    box = {"period": 2, "gameClock": "PT05M00.00S"}
    _sleep_for_awhile(box)
    mock_sleep.assert_called_once_with(720)


# ---------------------------------------------------------------------------
# _post_game_thread_exists
# ---------------------------------------------------------------------------


def test_post_game_thread_exists_true():
    mock_reddit = MagicMock()
    today_post = MagicMock()
    today_post.title = "[Post Game] Heat beat Celtics"
    today_post.created_utc = datetime.now(tz=timezone.utc).timestamp()
    mock_reddit.subreddit.return_value.new.return_value = [today_post]

    assert _post_game_thread_exists(mock_reddit) is True


def test_post_game_thread_exists_false_no_matching_title():
    mock_reddit = MagicMock()
    post = MagicMock()
    post.title = "Daily Discussion"
    post.created_utc = datetime.now(tz=timezone.utc).timestamp()
    mock_reddit.subreddit.return_value.new.return_value = [post]

    assert _post_game_thread_exists(mock_reddit) is False


def test_post_game_thread_exists_false_old_post():
    mock_reddit = MagicMock()
    old_post = MagicMock()
    old_post.title = "[Post Game] Heat beat Celtics"
    old_post.created_utc = 0  # epoch = 1970
    mock_reddit.subreddit.return_value.new.return_value = [old_post]

    assert _post_game_thread_exists(mock_reddit) is False


# ---------------------------------------------------------------------------
# _unsticky helpers
# ---------------------------------------------------------------------------


def test_unsticky_old_post_game_thread():
    mock_reddit = MagicMock()
    stickied_post = MagicMock(stickied=True, title="[Post Game] Heat lose")
    mock_reddit.subreddit.return_value.hot.return_value = [stickied_post]

    _unsticky_old_post_game_thread(mock_reddit)
    stickied_post.mod.sticky.assert_called_once_with(False)


def test_unsticky_old_post_game_thread_none_found():
    mock_reddit = MagicMock()
    other_post = MagicMock(stickied=True, title="Daily Discussion")
    mock_reddit.subreddit.return_value.hot.return_value = [other_post]

    _unsticky_old_post_game_thread(mock_reddit)
    other_post.mod.sticky.assert_not_called()


def test_unsticky_game_thread():
    mock_reddit = MagicMock()
    game_post = MagicMock(stickied=True, title="[Game Thread] MIA vs BOS")
    mock_reddit.subreddit.return_value.hot.return_value = [game_post]

    _unsticky_game_thread(mock_reddit)
    game_post.mod.sticky.assert_called_once_with(False)


# ---------------------------------------------------------------------------
# _submit_post
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.post_game_thread._unsticky_game_thread")
@patch("robo_burnie.scripts.post_game_thread._submit_post_game_thread")
@patch("robo_burnie.scripts.post_game_thread._unsticky_old_post_game_thread")
@patch("robo_burnie.scripts.post_game_thread._generate_post_details")
@patch("robo_burnie.scripts.post_game_thread._helpers.get_boxscore")
def test_submit_post(
    mock_boxscore,
    mock_gen_details,
    mock_unsticky_old,
    mock_submit_thread,
    mock_unsticky_game,
    boxscore,
):
    mock_boxscore.return_value = boxscore
    mock_gen_details.return_value = ("Title", "Body")

    _submit_post(MagicMock(), "001")

    mock_unsticky_old.assert_called_once()
    mock_submit_thread.assert_called_once()
    mock_unsticky_game.assert_called_once()


# ---------------------------------------------------------------------------
# _main
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.post_game_thread._helpers.get_todays_game_v2")
def test_main_no_game(mock_get_game):
    mock_get_game.return_value = {}
    _main()
    mock_get_game.assert_called_once()


@patch("robo_burnie.scripts.post_game_thread._helpers.set_script_enabled")
@patch("robo_burnie.scripts.post_game_thread._submit_post")
@patch("robo_burnie.scripts.post_game_thread._post_game_thread_exists")
@patch("robo_burnie.scripts.post_game_thread.praw.Reddit")
@patch("robo_burnie.scripts.post_game_thread._wait_for_game_to_end")
@patch("robo_burnie.scripts.post_game_thread._wait_for_game_to_start")
@patch("robo_burnie.scripts.post_game_thread._helpers.get_todays_game_v2")
def test_main_posts_thread(
    mock_get_game,
    mock_wait_start,
    mock_wait_end,
    mock_reddit_cls,
    mock_exists,
    mock_submit,
    mock_set_enabled,
):
    mock_get_game.return_value = {"game_id": "001"}
    mock_exists.return_value = False

    _main()

    mock_wait_start.assert_called_once_with("001")
    mock_wait_end.assert_called_once_with("001")
    mock_submit.assert_called_once()
    mock_set_enabled.assert_called_once_with("post_game_thread", False)


@patch("robo_burnie.scripts.post_game_thread._submit_post")
@patch("robo_burnie.scripts.post_game_thread._post_game_thread_exists")
@patch("robo_burnie.scripts.post_game_thread.praw.Reddit")
@patch("robo_burnie.scripts.post_game_thread._wait_for_game_to_end")
@patch("robo_burnie.scripts.post_game_thread._wait_for_game_to_start")
@patch("robo_burnie.scripts.post_game_thread._helpers.get_todays_game_v2")
def test_main_skips_when_thread_exists(
    mock_get_game,
    mock_wait_start,
    mock_wait_end,
    mock_reddit_cls,
    mock_exists,
    mock_submit,
):
    mock_get_game.return_value = {"game_id": "001"}
    mock_exists.return_value = True

    _main()

    mock_submit.assert_not_called()
