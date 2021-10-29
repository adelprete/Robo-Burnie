import requests
import praw
import sys
from datetime import datetime
import constants import teams_map
from private import BOT_PASSWORD, CLIENT_SECRET_KEY, CLIENT_ID

SUBREDDIT = 'heatcss'

def get_todays_games():
    today_json = requests.get(f'https://data.nba.net/data/10s/prod/v1/today.json').json()
    todays_date = today_json['links']['currentDate']

    scoreboard = requests.get(f'https://data.nba.net/data/10s/prod/v1/{todays_date}/scoreboard.json').json()
    return scoreboard['games']

def main(action):

    todays_games = get_todays_games()
    if not todays_games:
        print('[{}]: No Games Today'.format(datetime.now().strftime("%a, %b %d, %Y %I:%M %p")))
        return
    else:
        title = "[Around The League] Discuss today's NBA news and games"

        body = ""

        for game in todays_games:

            # Determine the status of the game
            game_time = game['startTimeEastern']
            if game['statusNum'] == 2:
                game_time = f"Q{game['period']} {game['clock']}"
            elif game['statusNum'] == 3:
                game_time = 'Final'

            game_details = (
                f">{teams_map[game['vTeam']['teamId']]['fullName']:<25} {game['vTeam']['score']:>3}\n"
                f">{teams_map[game['hTeam']['teamId']]['fullName']:<25} {game['hTeam']['score']:>3}\n"
                f">{game_time}/n"
                f"[Box-Score](https://www.nba.com/games/{game['gameUrlCode']}#/boxscore)\n\n"
            )

            body += game_details

    
        # Connect to reddit
        reddit = praw.Reddit(client_id=CLIENT_ID,
                            client_secret=CLIENT_SECRET_KEY,
                            password=BOT_PASSWORD,
                            user_agent='Game Bot by BobbaGanush87',
                            username='RoboBurnie')
                            
        subreddit = reddit.subreddit('heatcss')

        if action == 'create':
            submission = reddit.subreddit(SUBREDDIT).submit(title, selftext=body, send_replies=False)
            submission.mod.sticky()
            submission.mod.suggested_sort('new')

            # Unsticky Around the League Thread (if any)
            for post in subreddit.hot(limit=10):
                if post.stickied and "[Around the League]" in post.title:
                    post.mod.sticky(False)
                    break

            print('[{}]: Around the League thread posted'.format(datetime.now().strftime("%a, %b %d, %Y %I:%M %p")))
        elif action == 'update':
            for post in subreddit.hot(limit=10):
                if post.stickied and "[Around the League]" in post.title:
                    post.edit(body)
                    break
            print('[{}]: Around the League thread updated'.format(datetime.now().strftime("%a, %b %d, %Y %I:%M %p")))

        


if __name__ == '__main__':

    main(sys.argv[1])