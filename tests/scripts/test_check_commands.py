from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from robo_burnie.scripts.check_commands import (
    _collect_new_commands,
    _find_game_thread,
    _get_last_checked_utc,
    _main,
    _set_last_checked_utc,
)

# ---------------------------------------------------------------------------
# _find_game_thread
# ---------------------------------------------------------------------------


def test_find_game_thread_found():
    subreddit = MagicMock()
    game_post = MagicMock(stickied=True, title="[Game Thread] MIA vs BOS")
    other_post = MagicMock(stickied=True, title="Daily Discussion")
    subreddit.hot.return_value = [other_post, game_post]

    result = _find_game_thread(subreddit)
    assert result is game_post


def test_find_game_thread_not_found():
    subreddit = MagicMock()
    other_post = MagicMock(stickied=True, title="Daily Discussion")
    subreddit.hot.return_value = [other_post]

    result = _find_game_thread(subreddit)
    assert result is None


def test_find_game_thread_not_stickied():
    subreddit = MagicMock()
    unstickied = MagicMock(stickied=False, title="[Game Thread] MIA vs BOS")
    subreddit.hot.return_value = [unstickied]

    result = _find_game_thread(subreddit)
    assert result is None


# ---------------------------------------------------------------------------
# _collect_new_commands
# ---------------------------------------------------------------------------


def _mock_comments(comment_list):
    """Build a MagicMock that behaves like PRAW's CommentForest."""
    comments = MagicMock()
    comments.__iter__ = MagicMock(return_value=iter(comment_list))
    return comments


def test_collect_new_commands_postgame_on():
    submission = MagicMock()
    subreddit = MagicMock()

    mod = MagicMock()
    mod.name = "mod_user"
    subreddit.moderator.return_value = [mod]

    comment = MagicMock()
    comment.body = "!postgame on"
    comment.created_utc = 1000.0
    comment.author.name = "mod_user"
    submission.comments = _mock_comments([comment])

    result = _collect_new_commands(submission, subreddit, last_checked_utc=0)

    assert len(result) == 1
    assert result[0] == (comment, True)


def test_collect_new_commands_postgame_off():
    submission = MagicMock()
    subreddit = MagicMock()

    mod = MagicMock()
    mod.name = "mod_user"
    subreddit.moderator.return_value = [mod]

    comment = MagicMock()
    comment.body = "!postgame off"
    comment.created_utc = 1000.0
    comment.author.name = "mod_user"
    submission.comments = _mock_comments([comment])

    result = _collect_new_commands(submission, subreddit, last_checked_utc=0)

    assert len(result) == 1
    assert result[0] == (comment, False)


def test_collect_new_commands_ignores_non_mods():
    submission = MagicMock()
    subreddit = MagicMock()

    mod = MagicMock()
    mod.name = "mod_user"
    subreddit.moderator.return_value = [mod]

    comment = MagicMock()
    comment.body = "!postgame on"
    comment.created_utc = 1000.0
    comment.author.name = "random_user"
    submission.comments = _mock_comments([comment])

    result = _collect_new_commands(submission, subreddit, last_checked_utc=0)
    assert len(result) == 0


def test_collect_new_commands_ignores_old_comments():
    submission = MagicMock()
    subreddit = MagicMock()

    mod = MagicMock()
    mod.name = "mod_user"
    subreddit.moderator.return_value = [mod]

    comment = MagicMock()
    comment.body = "!postgame on"
    comment.created_utc = 500.0
    comment.author.name = "mod_user"
    submission.comments = _mock_comments([comment])

    result = _collect_new_commands(submission, subreddit, last_checked_utc=1000.0)
    assert len(result) == 0


def test_collect_new_commands_ignores_irrelevant_text():
    submission = MagicMock()
    subreddit = MagicMock()

    mod = MagicMock()
    mod.name = "mod_user"
    subreddit.moderator.return_value = [mod]

    comment = MagicMock()
    comment.body = "great game tonight!"
    comment.created_utc = 1000.0
    comment.author.name = "mod_user"
    submission.comments = _mock_comments([comment])

    result = _collect_new_commands(submission, subreddit, last_checked_utc=0)
    assert len(result) == 0


def test_collect_new_commands_oldest_first():
    submission = MagicMock()
    subreddit = MagicMock()

    mod = MagicMock()
    mod.name = "mod_user"
    subreddit.moderator.return_value = [mod]

    comment_on = MagicMock()
    comment_on.body = "!postgame on"
    comment_on.created_utc = 2000.0
    comment_on.author.name = "mod_user"

    comment_off = MagicMock()
    comment_off.body = "!postgame off"
    comment_off.created_utc = 1500.0
    comment_off.author.name = "mod_user"

    submission.comments = _mock_comments([comment_on, comment_off])

    result = _collect_new_commands(submission, subreddit, last_checked_utc=0)

    assert len(result) == 2
    assert result[0] == (comment_off, False)  # older first
    assert result[1] == (comment_on, True)  # newer second


# ---------------------------------------------------------------------------
# _get_last_checked_utc / _set_last_checked_utc
# ---------------------------------------------------------------------------


def test_get_last_checked_utc_from_config(tmp_path):
    config = {
        "scripts": {"check_commands": {"last_checked_utc": 12345.0, "enabled": True}}
    }
    config_file = tmp_path / ".config.json"
    config_file.write_text(json.dumps(config))

    with patch("robo_burnie.scripts.check_commands.CONFIG_PATH", str(config_file)):
        result = _get_last_checked_utc()
    assert result == 12345.0


def test_get_last_checked_utc_missing_key(tmp_path):
    config = {"scripts": {}}
    config_file = tmp_path / ".config.json"
    config_file.write_text(json.dumps(config))

    with patch("robo_burnie.scripts.check_commands.CONFIG_PATH", str(config_file)):
        result = _get_last_checked_utc()
    assert result == 0


def test_get_last_checked_utc_file_not_found():
    with patch(
        "robo_burnie.scripts.check_commands.CONFIG_PATH", "/nonexistent/path.json"
    ):
        result = _get_last_checked_utc()
    assert result == 0


def test_set_last_checked_utc(tmp_path):
    config = {"scripts": {"check_commands": {"enabled": True, "last_checked_utc": 0}}}
    config_file = tmp_path / ".config.json"
    config_file.write_text(json.dumps(config))

    with patch("robo_burnie.scripts.check_commands.CONFIG_PATH", str(config_file)):
        _set_last_checked_utc(99999.0)

    result = json.loads(config_file.read_text())
    assert result["scripts"]["check_commands"]["last_checked_utc"] == 99999.0


def test_set_last_checked_utc_creates_from_default(tmp_path):
    config_file = tmp_path / ".config.json"

    with patch("robo_burnie.scripts.check_commands.CONFIG_PATH", str(config_file)):
        _set_last_checked_utc(99999.0)

    result = json.loads(config_file.read_text())
    assert result["scripts"]["check_commands"]["last_checked_utc"] == 99999.0


# ---------------------------------------------------------------------------
# _main
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.check_commands._set_last_checked_utc")
@patch("robo_burnie.scripts.check_commands._collect_new_commands")
@patch("robo_burnie.scripts.check_commands._get_last_checked_utc", return_value=0)
@patch("robo_burnie.scripts.check_commands._find_game_thread")
@patch("robo_burnie.scripts.check_commands.praw.Reddit")
def test_main_no_game_thread(
    mock_reddit_cls, mock_find, mock_last_checked, mock_collect, mock_set
):
    mock_reddit = MagicMock()
    mock_reddit_cls.return_value = mock_reddit
    mock_find.return_value = None

    _main()

    mock_collect.assert_not_called()
    mock_set.assert_not_called()


@patch("robo_burnie.scripts.check_commands._set_last_checked_utc")
@patch("robo_burnie.scripts.check_commands._collect_new_commands")
@patch("robo_burnie.scripts.check_commands._get_last_checked_utc", return_value=0)
@patch("robo_burnie.scripts.check_commands._find_game_thread")
@patch("robo_burnie.scripts.check_commands.praw.Reddit")
def test_main_with_commands(
    mock_reddit_cls, mock_find, mock_last_checked, mock_collect, mock_set
):
    mock_reddit = MagicMock()
    mock_reddit_cls.return_value = mock_reddit
    mock_find.return_value = MagicMock()

    comment = MagicMock()
    comment.author.name = "mod_user"
    mock_collect.return_value = [(comment, True)]

    with patch(
        "robo_burnie.scripts.check_commands._helpers.set_script_enabled"
    ) as mock_enable:
        _main()

    mock_enable.assert_called_once_with("post_game_thread", True)
    comment.reply.assert_called_once()
    mock_set.assert_called_once()


@patch("robo_burnie.scripts.check_commands._set_last_checked_utc")
@patch("robo_burnie.scripts.check_commands._collect_new_commands", return_value=[])
@patch("robo_burnie.scripts.check_commands._get_last_checked_utc", return_value=0)
@patch("robo_burnie.scripts.check_commands._find_game_thread")
@patch("robo_burnie.scripts.check_commands.praw.Reddit")
def test_main_no_commands(
    mock_reddit_cls, mock_find, mock_last_checked, mock_collect, mock_set
):
    mock_reddit = MagicMock()
    mock_reddit_cls.return_value = mock_reddit
    mock_find.return_value = MagicMock()

    _main()

    mock_set.assert_called_once()  # still updates last_checked_utc
