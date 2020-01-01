import requests
import praw
import time
from datetime import datetime, timedelta
from settings import TEAM, TEAM_NAMES
from private import BOT_PASSWORD, CLIENT_SECRET_KEY, CLIENT_ID

def get_todays_game():
    today = datetime.utcnow() - timedelta(hours=5)
    games = requests.get(f'https://data.nba.net/prod/v2/{today.strftime("%Y")}{today.strftime("%m")}{today.strftime("%d")}/scoreboard.json').json()
    
    todays_game = {}
    for game in games['games']:
        if game['vTeam']['triCode'] == TEAM or game['hTeam']['triCode'] == TEAM:
            todays_game = game
    
    return todays_game

def get_boxscore(gameid):
    today = datetime.utcnow() - timedelta(hours=5)
    boxscore = requests.get(f'https://data.nba.net/data/10s/prod/v1/{today.strftime("%Y")}{today.strftime("%m")}{today.strftime("%d")}/{gameid}_boxscore.json').json()
    return boxscore

if __name__ == '__main__':
    while True:
        todays_game = get_todays_game()
        
        if todays_game == {} or todays_game.get('statusNum') == 3:
            print(f'[{datetime.now().strftime("%a, %b %d, %Y %I:%M %p")}]: Game ended waiting 15 hrs to check for next game')
            time.sleep(54000)
            continue 
        print(f'[{datetime.now().strftime("%a, %b %d, %Y %I:%M %p")}]: Checked if game started')
        while todays_game['statusNum'] in [2,3]:
            todays_game = get_todays_game()
            if todays_game['statusNum'] == 3 or (todays_game['period']['current'] >= 4 and todays_game['statusNum'] == 2 and todays_game['period']['isEndOfPeriod'] and todays_game['vTeam']['score'] != todays_game['hTeam']['score']):
                team_stats_key = 'hTeam'
                opponent_stats_key = 'vTeam'
                if todays_game['vTeam']['triCode'] == TEAM:
                    team_stats_key = 'hTeam'
                    opponent_stats_key = 'hTeam'
                boxscore = get_boxscore(todays_game['gameId'])
                reddit = praw.Reddit(client_id=CLIENT_ID,
                                 client_secret=CLIENT_SECRET_KEY,
                                 password=BOT_PASSWORD,
                                 user_agent='Game Bot by BobbaGanush87',
                                 username='bobbaganush87')
                
                # Grab general score information
                team_score = todays_game[team_stats_key]['score']
                opponents_score = todays_game[opponent_stats_key]['score']
                opponents_name = todays_game[opponent_stats_key]['triCode']
                
                # Grab points leader information
                points_statline = '\n'
                points_leader_value = boxscore['stats'][team_stats_key]['leaders']['points']['value']
                for index, player in enumerate(boxscore['stats'][team_stats_key]['leaders']['points']['players']):
                    if index > 0:
                        points_statline += ' /'
                    points_statline += f' **{player["firstName"]} {player["lastName"]}**'
                points_statline += f': {points_leader_value} PTS'
                
                # Grab reboundss leader information
                rebounds_statline = '\n'
                rebounds_leader_value = boxscore['stats'][team_stats_key]['leaders']['rebounds']['value']
                for index, player in enumerate(boxscore['stats'][team_stats_key]['leaders']['rebounds']['players']):
                    if index > 0:
                        rebounds_statline += ' /'
                    rebounds_statline += f' **{player["firstName"]} {player["lastName"]}**'
                rebounds_statline += f': {rebounds_leader_value} REBS'
                
                # Grab assists leader information
                assists_statline = '\n'
                assists_leader_value = boxscore['stats'][team_stats_key]['leaders']['assists']['value']
                for index, player in enumerate(boxscore['stats'][team_stats_key]['leaders']['assists']['players']):
                    if index > 0:
                        assists_statline += ' /'
                    assists_statline += f' **{player["firstName"]} {player["lastName"]}**'
                assists_statline += f': {assists_leader_value} ASTS'
                
                if team_score < opponents_score:
                    result = 'lose to'
                else:
                    result = 'defeat'
                
                title = f'[Post Game Thread] {TEAM_NAMES[TEAM]} {result} {TEAM_NAMES[opponents_name]} {team_score} - {opponents_score}'
                selftext = f'* [Box Score](https://www.nba.com/games/{todays_game["gameUrlCode"]}#/boxscore)'
                selftext += '\n\nStats Leaders'
                selftext += points_statline
                selftext += rebounds_statline
                selftext += assists_statline
                result = reddit.subreddit('heat').submit(title, selftext=selftext, flair_id='d79dc9aa-cf0d-11e2-9b1b-12313d163d8f')
                #result = reddit.subreddit('testingground4bots').submit(title, selftext=selftext)
                print(f'[{datetime.now().strftime("%a, %b %d, %Y %I:%M %p")}]: Game ended thread posted')
                break
            
            if todays_game['period']['current'] >= 4 and todays_game['statusNum'] == 2 and not todays_game['clock']:
                print(f'[{datetime.now().strftime("%a, %b %d, %Y %I:%M %p")}]: Game might have ended')
                time.sleep(3)
            elif todays_game['period']['current'] >= 4 and todays_game['clock'] and int(todays_game['clock'].replace(':', '').split('.')[0]) < 30:
                print(f'[{datetime.now().strftime("%a, %b %d, %Y %I:%M %p")}]: Game is almost over')
                time.sleep(10)
            else:
                print(f'[{datetime.now().strftime("%a, %b %d, %Y %I:%M %p")}]: Game not over yet')
                time.sleep(90)
        time.sleep(600)
    
