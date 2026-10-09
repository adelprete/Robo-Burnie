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
    _update_score,
    _with_score_row,
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
        "home_tricode": "MIA",
        "away_tricode": "BOS",
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


def test_get_tv_broadcasters_home_team(todays_game):
    result = _get_tv_broadcasters(todays_game, "MIA")
    assert result == ["BSSUN", "ESPN"]


def test_get_tv_broadcasters_away_team(todays_game):
    result = _get_tv_broadcasters(todays_game, "BOS")
    assert result == ["NBCSB", "ESPN"]


def test_get_radio_broadcasters_home_team(todays_game):
    result = _get_radio_broadcasters(todays_game, "MIA")
    assert result == ["WAXY"]


def test_get_radio_broadcasters_away_team(todays_game):
    result = _get_radio_broadcasters(todays_game, "BOS")
    assert result == ["WBZ"]


def test_get_tv_broadcasters_missing_cdn_data():
    result = _get_tv_broadcasters({}, "MIA")
    assert result == []


def test_get_tv_broadcasters_summer_league_schedule_format():
    game_data = {
        "home_tricode": "SAS",
        "broadcasters": {
            "nationalBroadcasters": [
                {
                    "broadcasterMedia": "tv",
                    "broadcasterAbbreviation": "ESPN",
                },
                {
                    "broadcasterMedia": "tv",
                    "broadcasterAbbreviation": "NBA TV",
                },
                {
                    "broadcasterMedia": "tv",
                    "broadcasterAbbreviation": "LeaguePass",
                },
                {
                    "broadcasterMedia": "tv",
                    "broadcasterAbbreviation": "Amazon",
                },
            ],
            "homeTvBroadcasters": [],
            "awayTvBroadcasters": [],
        },
    }

    result = _get_tv_broadcasters(game_data, "MIA")

    assert result == ["ESPN", "NBA TV"]


def test_get_tv_broadcasters_keeps_amazon_when_only_channel():
    game_data = {
        "home_tricode": "SAS",
        "broadcasters": {
            "nationalBroadcasters": [
                {
                    "broadcasterMedia": "tv",
                    "broadcasterAbbreviation": "Amazon",
                },
            ],
            "homeTvBroadcasters": [],
            "awayTvBroadcasters": [],
        },
    }

    result = _get_tv_broadcasters(game_data, "MIA")

    assert result == ["Amazon"]


def test_get_tv_broadcasters_hides_amazon_when_regional_tv_exists():
    game_data = {
        "home_tricode": "MIA",
        "broadcasters": {
            "nationalBroadcasters": [
                {
                    "broadcasterMedia": "tv",
                    "broadcasterAbbreviation": "Amazon",
                },
            ],
            "homeTvBroadcasters": [{"broadcasterAbbreviation": "BSSUN"}],
            "awayTvBroadcasters": [],
        },
    }

    result = _get_tv_broadcasters(game_data, "MIA")

    assert result == ["BSSUN"]


def test_get_radio_broadcasters_missing_cdn_data():
    result = _get_radio_broadcasters({}, "MIA")
    assert result == []


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
def test_generate_post_details(mock_boxscore_link, mock_standings_table, todays_game):

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
def test_generate_post_details_with_game_label(
    mock_boxscore_link, mock_standings_table, todays_game
):
    todays_game["game_label"] = "NBA Cup"

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
def test_generate_post_details_includes_standings(
    mock_boxscore_link, mock_standings_table, todays_game
):

    _, body = _generate_post_details(todays_game, "MIA")
    assert "| standings |" in body


@patch(
    "robo_burnie.scripts.game_thread._build_standings_table",
    return_value="| standings |",
)
@patch(
    "robo_burnie.scripts.game_thread._helpers.get_boxscore_link",
    return_value="https://espn.com/summer-league/boxscore",
)
def test_generate_post_details_summer_league_skips_standings(
    mock_boxscore_link, mock_standings_table, todays_game
):
    todays_game["game_label"] = "Summer League"
    todays_game["game_id"] = "1322600001"
    todays_game["home_tricode"] = "SAS"
    todays_game["away_tricode"] = "MIA"
    todays_game["broadcasters"] = {
        "nationalBroadcasters": [
            {"broadcasterMedia": "tv", "broadcasterAbbreviation": "ESPN"},
            {"broadcasterMedia": "tv", "broadcasterAbbreviation": "NBA TV"},
        ],
        "homeTvBroadcasters": [],
        "awayTvBroadcasters": [],
        "nationalRadioBroadcasters": [],
        "homeRadioBroadcasters": [],
        "awayRadioBroadcasters": [],
    }

    title, body = _generate_post_details(todays_game, "MIA")

    assert "[Game Thread] [Summer League]" in title
    assert "ESPN" in body
    assert "NBA TV" in body
    assert "| standings |" not in body
    mock_standings_table.assert_not_called()


@patch(
    "robo_burnie.scripts.game_thread._helpers.get_boxscore_link",
    return_value="https://espn.com/summer-league/boxscore",
)
def test_generate_post_details_summer_league_alternate_team_ids(
    mock_boxscore_link, todays_game
):
    """Summer league schedule API returns 1710612xxx IDs, not regular 1610612xxx."""
    todays_game["game_label"] = "Summer League"
    todays_game["game_id"] = "1322600002"
    todays_game["home_team_id"] = 1710612744  # GSW summer league ID
    todays_game["home_tricode"] = "GSW"
    todays_game["home_team_wins"] = 1
    todays_game["home_team_losses"] = 0
    todays_game["away_team_id"] = 1710612748  # MIA summer league ID
    todays_game["away_tricode"] = "MIA"
    todays_game["away_team_wins"] = 0
    todays_game["away_team_losses"] = 1
    todays_game["broadcasters"] = {}

    title, body = _generate_post_details(todays_game, "MIA")

    assert "Golden State Warriors" in title
    assert "Miami Heat" in title
    assert "/r/warriors" in body
    assert "/r/heat" in body


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
    mock_submission.mod.suggested_sort.assert_called_once_with(sort="new")


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

    post_game.mod.sticky.assert_called_with(state=False)


# ---------------------------------------------------------------------------
# _main
# ---------------------------------------------------------------------------


@patch("robo_burnie.scripts.game_thread._helpers.get_todays_game_auto")
def test_main_no_game_today(mock_get_game):
    mock_get_game.return_value = {}
    _main("create")
    mock_get_game.assert_called_once()


@patch("robo_burnie.scripts.game_thread._submit_post")
@patch("robo_burnie.scripts.game_thread.praw.Reddit")
@patch("robo_burnie.scripts.game_thread._generate_post_details")
@patch("robo_burnie.scripts.game_thread._helpers.get_todays_game_auto")
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
@patch("robo_burnie.scripts.game_thread._helpers.get_todays_game_auto")
def test_main_game_already_started(
    mock_get_game, mock_gen_details, mock_reddit_cls, mock_submit
):
    mock_get_game.return_value = {
        "status_id": 2,
    }

    _main("create")

    mock_gen_details.assert_not_called()
    mock_submit.assert_not_called()


# ---------------------------------------------------------------------------
# Live score updates
# ---------------------------------------------------------------------------

LIVE_GAME = {
    "home_abbreviation": "MIA",
    "visitor_abbreviation": "NOP",
    "home_pts": 54,
    "visitor_pts": 50,
    "game_status_text": "Q3 5:42 ",
}
GAME_BODY = (
    "| Game Details | . |\n"
    "|--|--|\n"
    "| **Tip-Off Time** | 7:30 pm ET |\n"
    "| **TV Broadcasts** | NBC & Peacock |"
)


def test_with_score_row_inserts_then_replaces():
    body = _with_score_row(GAME_BODY, LIVE_GAME)
    assert "|--|--|\n| **Score** | **NOP 50 - MIA 54** (Q3 5:42) |\n| **Tip-Off" in body

    final_game = {**LIVE_GAME, "home_pts": 101, "game_status_text": "Final"}
    final = _with_score_row(body, final_game)
    assert final.count("**Score**") == 1
    assert "| **Score** | **NOP 50 - MIA 101** (Final) |" in final
    assert _with_score_row(final, final_game) == final


NOW = 1_000_000


def _game_thread_post(selftext: str, created_utc: float = NOW - 3600) -> MagicMock:
    return MagicMock(
        title="[Game Thread] New Orleans Pelicans @ Miami Heat",
        selftext=selftext.replace("&", "&amp;"),
        created_utc=created_utc,
    )


@pytest.fixture()
def bot_posts():
    """Patch the bot's recent submissions; returns the list to fill."""
    posts = []
    with patch("robo_burnie.scripts.game_thread._get_reddit") as mock_reddit, patch(
        "robo_burnie.scripts.game_thread.time.time", return_value=NOW
    ):
        mock_reddit.return_value.user.me.return_value.submissions.new.return_value = (
            posts
        )
        yield posts


@patch("robo_burnie.scripts.game_thread._helpers.get_todays_games")
def test_update_score_edits_unstickied_thread(mock_games, bot_posts):
    mock_games.return_value = {"1": LIVE_GAME}
    post = _game_thread_post(GAME_BODY)
    post.stickied = False  # post game thread already unstickied it
    bot_posts.append(post)

    _update_score()

    mock_games.assert_called_once_with(("00",))
    edited = post.edit.call_args[0][0]
    assert "**NOP 50 - MIA 54** (Q3 5:42)" in edited
    assert "NBC & Peacock" in edited


@patch("robo_burnie.scripts.game_thread._helpers.get_todays_games")
def test_update_score_ignores_yesterdays_thread(mock_games, bot_posts):
    post = _game_thread_post(GAME_BODY, created_utc=NOW - 25 * 3600)
    bot_posts.append(post)

    _update_score()

    mock_games.assert_not_called()
    post.edit.assert_not_called()


@pytest.mark.parametrize("final_status", ["Final", "Final/OT", "Final/2OT"])
@patch("robo_burnie.scripts.game_thread._helpers.get_todays_games")
def test_update_score_skips_nba_once_final(mock_games, bot_posts, final_status):
    final_body = _with_score_row(
        GAME_BODY, {**LIVE_GAME, "game_status_text": final_status}
    )
    post = _game_thread_post(final_body)
    bot_posts.append(post)

    _update_score()

    mock_games.assert_not_called()
    post.edit.assert_not_called()


@patch("robo_burnie.scripts.game_thread._helpers.get_todays_games")
def test_update_score_skips_before_tip_off(mock_games, bot_posts):
    mock_games.return_value = {"1": {**LIVE_GAME, "home_pts": None}}
    post = _game_thread_post(GAME_BODY)
    bot_posts.append(post)

    _update_score()

    post.edit.assert_not_called()
