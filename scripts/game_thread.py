from datetime import datetime
import sys

import praw
from private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY

from constants import TEAM_TRI_TO_INFO
from scripts import helpers


def main(action):

    todays_game = helpers.get_todays_game(team='DET')

    if todays_game == {}:
        print(
            "[{}]: No Game Today".format(
                datetime.now().strftime("%a, %b %d, %Y %I:%M %p")
            )
        )
    elif todays_game.get("statusNum") == 1:
        print(
            "[{}]: Game hasn't started yet".format(
                datetime.now().strftime("%a, %b %d, %Y %I:%M %p")
            )
        )

        # Grab general game information
        visitor_team_name = TEAM_TRI_TO_INFO[todays_game["vTeam"]["triCode"]][
            "full_name"
        ]
        visitor_reddit = TEAM_TRI_TO_INFO[todays_game["vTeam"]["triCode"]]["reddit"]
        visitor_win = todays_game["vTeam"]["win"]
        visitor_loss = todays_game["vTeam"]["loss"]

        home_team_name = TEAM_TRI_TO_INFO[todays_game["hTeam"]["triCode"]]["full_name"]
        home_reddit = TEAM_TRI_TO_INFO[todays_game["hTeam"]["triCode"]]["reddit"]
        home_win = todays_game["hTeam"]["win"]
        home_loss = todays_game["hTeam"]["loss"]

        # Get Date information
        today = datetime.utcnow()
        month = today.strftime("%m")
        day = today.strftime("%d")
        start_time = todays_game["startTimeEastern"]

        # Grab Broadcast information and build its string while we're at it
        broadcast_info = todays_game["watch"]["broadcast"]["broadcasters"]
        broadcast_str = ""
        if broadcast_info["national"]:
            broadcast_str += "{} / ".format(broadcast_info["national"][0]["longName"])
        if broadcast_info["vTeam"]:
            broadcast_str += "{} / ".format(broadcast_info["vTeam"][0]["longName"])
        if broadcast_info["hTeam"]:
            broadcast_str += "{}".format(broadcast_info["hTeam"][0]["longName"])

        title = "[Game Thread] {} ({}-{}) @ {} ({}-{}) - {}/{} {}".format(
            visitor_team_name,
            visitor_win,
            visitor_loss,
            home_team_name,
            home_win,
            home_loss,
            month,
            day,
            start_time,
        )

        self_text = "**[{}]({}) ({}-{}) @ [{}]({}) ({}-{})**\n\n".format(
            visitor_team_name,
            "http://www.reddit.com" + visitor_reddit,
            visitor_win,
            visitor_loss,
            home_team_name,
            "http://www.reddit.com" + home_reddit,
            home_win,
            home_loss,
        )

        table = (
            "| Game Details |  |\n"
            "|--|--|\n"
            "| **Location** | {}, {}, {} |\n"
            "| **Tip-Off Time** | {} |\n"
            "| **TV/Radio** | {} |\n"
            "| **Game Info & Stats** | [nba.com]({}) |"
        )

        table = table.format(
            todays_game["arena"]["name"],
            todays_game["arena"]["city"],
            todays_game["arena"]["stateAbbr"],
            start_time,
            broadcast_str,
            helpers.get_game_link(todays_game),
        )

        self_text = self_text + table

        reddit = praw.Reddit(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET_KEY,
            password=BOT_PASSWORD,
            user_agent="Game Bot by BobbaGanush87",
            username="RoboBurnie",
        )

        subreddit = reddit.subreddit("heatCSS")

        if action == "create":
            game_thread_exists = False
            for post in subreddit.hot(limit=10):
                if post.stickied and "[Game Thread]" in post.title:
                    game_thread_exists = True
                    break
            
            if game_thread_exists == False:
                submission = subreddit.submit(
                    title,
                    selftext=self_text,
                    send_replies=False,
                    flair_id="8a22ad40-c182-11e3-877e-12313b0d38eb",
                )
                submission.mod.sticky()
                submission.mod.suggested_sort("new")

                # Unsticky Post Game Thread (if any)
                for post in subreddit.hot(limit=5):
                    if post.stickied and "[Post Game]" in post.title:
                        post.mod.sticky(False)
                        break

                print(
                    "[{}]: Game thread posted".format(
                        datetime.now().strftime("%a, %b %d, %Y %I:%M %p")
                    )
                )
            else:
                print(
                    "[{}]: Game thread already posted".format(
                        datetime.now().strftime("%a, %b %d, %Y %I:%M %p")
                    )
                )

if __name__ == "__main__":

    main(sys.argv[1])
