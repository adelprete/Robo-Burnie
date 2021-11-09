import requests
import praw
import sys
from datetime import datetime, timedelta
from constants import teams_map
from private import BOT_PASSWORD, CLIENT_SECRET_KEY, CLIENT_ID

# its eastern time minus 4 hours just to ensure we stay within the same day after midnight on the east coast
TODAYS_DATE_STR = (datetime.now() - timedelta(hours=3)).strftime("%Y%m%d")

SUBREDDIT = 'heat'


def get_todays_games():
    scoreboard = requests.get(f'https://data.nba.net/data/10s/prod/v1/{TODAYS_DATE_STR}/scoreboard.json').json()
    return scoreboard['games']

def main(action):

    todays_games = get_todays_games()
    if not todays_games:
        print('[{}]: No Games Today'.format(datetime.now().strftime("%a, %b %d, %Y %I:%M %p")))
        return
    else:
        title = "[Around the League] Discuss today's NBA news and games"

        body = (
            f"| **Visitors** | **Home** | **Score** | **Time** | **Box Score** |\n"
            f"| :---: | :---: | :---: | :---: | :---: |\n"
        )
        for game in todays_games:

            # Determine the status of the game
            game_time = game['startTimeEastern']
            if game['statusNum'] == 2:
                if game['period']['isHalftime']:
                    game_time = 'Halftime'
                else:
                    game_time = f"Q{game['period']['current']} {game['clock']}"
            elif game['statusNum'] == 3:
                game_time = 'Final'
            
            score = f"{game['vTeam']['score']:>3} - {game['hTeam']['score']:<3}"
            box_score = f"[Link](https://www.nba.com/games/{game['gameUrlCode']}#/boxscore)"
            
            game_details = (
                f"| {teams_map[game['vTeam']['teamId']]['nickname']} | {teams_map[game['hTeam']['teamId']]['nickname']} | {score} | {game_time} | {box_score} |\n"
            )
            """
            game_details = (
                f"| Teams | Score |\n"
                f"| --- | --- |\n"
                f"| {teams_map[game['vTeam']['teamId']]['fullName']} |  {game['vTeam']['score']:>3} |\n"
                f"| {teams_map[game['hTeam']['teamId']]['fullName']} |  {game['hTeam']['score']:>3} |\n"
                f"| [Box-Score](https://www.nba.com/games/{game['gameUrlCode']}#/boxscore) | {game_time} |\n"
                f"\n--\n\n" 
            )"""

            body += game_details

    
        # Connect to reddit
        reddit = praw.Reddit(client_id=CLIENT_ID,
                            client_secret=CLIENT_SECRET_KEY,
                            password=BOT_PASSWORD,
                            user_agent='Game Bot by BobbaGanush87',
                            username='RoboBurnie')
                            
        subreddit = reddit.subreddit(SUBREDDIT)

        if action == 'create':
            # Make it True for now, just always create it. Normally this is False initally
            need_to_create = True
            # Unsticky old Around the League Thread (if any)
            for post in subreddit.hot(limit=10):
                if post.stickied and "[Around the League]" in post.title:
                    post_date = datetime.fromtimestamp(post.created_utc).strftime("%Y%m%d")
                    if post_date != TODAYS_DATE_STR:
                        need_to_create = True
                        post.mod.sticky(False)
                    break
            else:
                need_to_create = True
            
            # Submit the post if one doesnt already exist for the day
            if need_to_create:
                submission = reddit.subreddit(SUBREDDIT).submit(title, selftext=body, send_replies=False, flair_id='29f18426-a10b-11e6-af2b-0ea571864a50')
                submission.mod.sticky()
                submission.mod.suggested_sort('new')
                print('[{}]: Around the League thread posted'.format(datetime.now().strftime("%a, %b %d, %Y %I:%M %p")))
            else:
                print('[{}]: Around the League thread already created'.format(datetime.now().strftime("%a, %b %d, %Y %I:%M %p")))

        elif action == 'update':
            for post in subreddit.hot(limit=5):
                if post.stickied and "[Around the League]" in post.title:
                    post.edit(body)
                    post.save()
                    break
            print('[{}]: Around the League thread updated'.format(datetime.now().strftime("%a, %b %d, %Y %I:%M %p"))) 


if __name__ == '__main__':

    main(sys.argv[1])
