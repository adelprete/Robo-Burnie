import logging
from datetime import datetime

import praw
from nba_api.stats.endpoints import boxscoresummaryv2
from nba_api.stats.library.parameters import Season

from constants import TEAM_ID_TO_INFO
from private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY
from scripts import helpers


def main() -> None:

    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET_KEY,
        password=BOT_PASSWORD,
        user_agent="Game Bot by BobbaGanush87",
        username="RoboBurnie",
    )
    subreddit = reddit.subreddit("heat")
    sidebar = subreddit.wiki["config/sidebar"]

    updated_sidebar_text = update_standings(sidebar, "MIA")
    updated_sidebar_text = update_schedule(updated_sidebar_text, "heat")

    sidebar.edit(content=updated_sidebar_text)
    logging.info("Old sidebar updated")


def update_standings(sidebar, team_to_highlight):
    """
    ||Team|W|L|PCT|
    |:--:|:--|:--:|:--:|:--:|
    |1|[Brooklyn](/r/gonets)|33|15|.688|
    |2|[Philadelphia](/r/Sixers)|32|15|.681|
    |3|[Milwaukee](/r/MkeBucks)|30|17|.638|
    |4|[Charlotte](/r/CharlotteHornets)|24|22|.522|
    |**5**|**[Miami](/r/Heat)**|**24**|**24**|**.500**|
    |6|[New York](/r/nyknicks)|24|24|.500|
    |7|[Atlanta](/r/AtlantaHawks)|23|24|.489|
    |8|[Boston](/r/BostonCeltics)|23|25|.479|
    |9|[Indiana](/r/Pacers)|21|25|.457|
    |10|[Chicago](/r/ChicagoBulls)|19|27|.413|
    |11|[Toronto](/r/TorontoRaptors)|18|30|.375|
    |12|[Washington](/r/WashingtonWizards)|17|29|.370|
    |13|[Cleveland](/r/ClevelandCavs)|17|30|.362|
    |14|[Orlando](/r/OrlandoMagic)|16|31|.340|
    |15|[Detroit](/r/DetroitPistons)|13|34|.277|
    """

    sidebar_txt_before_standings = sidebar.content_md.split(
        "##[Standings](http://espn.go.com/nba/standings/_/group/3)", 1
    )[0]
    sidebar_txt_after_standings = (
        "###Roster" + sidebar.content_md.split("###Roster", 1)[1]
    )

    standings = helpers.get_todays_standings()
    standings_markdown = "##[Standings](http://espn.go.com/nba/standings/_/group/3)\n\n||Team|W|L|PCT|\n|:--:|:--|:--:|:--:|:--:|\n"

    count = 1
    for team in standings:
        if team["Conference"] == "West":
            continue
        position = count
        team_city = team["TeamCity"]
        team_reddit = TEAM_ID_TO_INFO[str(team["TeamID"])]["reddit"]
        team_name = f"[{team_city}]({team_reddit})"
        team_wins = team["WINS"]
        team_losses = team["LOSSES"]
        team_win_pct = team["WinPCT"]
        if TEAM_ID_TO_INFO[str(team["TeamID"])]["tricode"] == team_to_highlight:
            position = f"**{position}**"
            team_name = f"**{team_name}**"
            team_wins = f"**{team_wins}**"
            team_losses = f"**{team_losses}**"
            team_win_pct = f"**{team_win_pct}**"

        standing_markdown = "|{}|{}|{}|{}|{}|\n".format(
            position,
            team_name,
            team_wins,
            team_losses,
            team_win_pct,
        )
        standings_markdown += standing_markdown

        count += 1

    standings_markdown += "\n"

    updated_sidebar_txt = (
        sidebar_txt_before_standings + standings_markdown + sidebar_txt_after_standings
    )

    return updated_sidebar_txt


def update_schedule(sidebar_text: str, team_name: str) -> str:
    """
    |Date|Matchup|Score|
    |:--:|:--:|:--:|
    |Wed, Nov 16 *7:30 PM*|[@ TOR](/r/TorontoRaptors)|104 - 112 L|
    |Fri, Nov 18 *7:00 PM*|[@ WAS](/r/WashingtonWizards)|106 - 107 L|
    |Sun, Nov 20 *7:00 PM*|[@ CLE](/r/ClevelandCavs)|87 - 113 L|
    |Mon, Nov 21 *8:00 PM*|[@ MIN](/r/Timberwolves)|101 - 105 L|
    |Wed, Nov 23 *7:30 PM*|[WAS](/r/WashingtonWizards)|**105 - 113 W**|
    |Fri, Nov 25 *8:00 PM*|[WAS](/r/WashingtonWizards)||
    |Sun, Nov 27 *5:00 PM*|[@ ATL](/r/AtlantaHawks)||
    |Wed, Nov 30 *7:30 PM*|[@ BOS](/r/BostonCeltics)||
    |Fri, Dec  2 *7:30 PM*|[@ BOS](/r/BostonCeltics)||
    |Mon, Dec  5 *8:00 PM*|[@ MEM](/r/MemphisGrizzlies)||
    """

    sidebar_txt_before_schedule = sidebar_text.split(
        "##[Schedule](https://www.nba.com/heat/schedule/)", 1
    )[0]
    sidebar_txt_after_schedule = (
        "##[Standings]" + sidebar_text.split("##[Standings]", 1)[1]
    )

    today = datetime.today()
    seasons_games = helpers.get_full_schedule(Season.default[:4], team_name)

    # Find where we are in the schedule
    for index, game in enumerate(seasons_games):
        if datetime.strptime(game["startDateEastern"], "%Y%m%d") >= today:
            break
    nearby_games = seasons_games[max(0, index - 5) : index + 5]

    schedule_markdown = "##[Schedule](https://www.nba.com/heat/schedule/)\n\n|Date|Matchup|Score|\n|:--:|:--:|:--:|\n"
    for game in nearby_games:
        date_display_text = (
            datetime.strptime(game["startDateEastern"], "%Y%m%d").strftime("%a, %b %d")
            + f" *{game['startTimeEastern']}*"
        )
        opponent_display_str = get_opponent_display_str(game)
        score_display_str = get_score_display_str(game)

        game_markdown = "|{}|{}|{}|".format(
            date_display_text, opponent_display_str, score_display_str
        )
        schedule_markdown += f"{game_markdown}\n"

    schedule_markdown += "\n"

    updated_sidebar_txt = (
        sidebar_txt_before_schedule + schedule_markdown + sidebar_txt_after_schedule
    )

    return updated_sidebar_txt


def get_opponent_display_str(game: dict) -> str:
    if game["isHomeTeam"]:
        opponent_tricode = f'{TEAM_ID_TO_INFO[game["vTeam"]["teamId"]]["tricode"]}'
        opponent_reddit = TEAM_ID_TO_INFO[game["vTeam"]["teamId"]]["reddit"]
    else:
        opponent_tricode = f'@ {TEAM_ID_TO_INFO[game["hTeam"]["teamId"]]["tricode"]}'
        opponent_reddit = TEAM_ID_TO_INFO[game["hTeam"]["teamId"]]["reddit"]
    return f"[{opponent_tricode}]({opponent_reddit})"


def get_score_display_str(game: dict) -> str:
    line_scores = boxscoresummaryv2.BoxScoreSummaryV2(game["gameId"]).get_dict()[
        "resultSets"
    ][5]["rowSet"]
    if str(line_scores[0][3]) == game["vTeam"]["teamId"]:
        away_score = line_scores[0][-1]
        home_score = line_scores[1][-1]
    else:
        away_score = line_scores[1][-1]
        home_score = line_scores[0][-1]

    score = ""
    if home_score is not None:
        score = f"{away_score} - {home_score}"
        if (game["isHomeTeam"] and home_score > away_score) or (
            not game["isHomeTeam"] and away_score > home_score
        ):
            score = f"**{score}**"

    return score


if __name__ == "__main__":
    main()
