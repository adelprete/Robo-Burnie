import requests
import praw
import time
from datetime import datetime, timedelta
from settings import TEAM, TEAM_NAMES
from private import BOT_PASSWORD, CLIENT_SECRET_KEY, CLIENT_ID

def get_todays_game():
    today = datetime.utcnow() - timedelta(hours=5)
    games = requests.get('https://data.nba.net/prod/v2/{}{}{}/scoreboard.json'.format(today.strftime("%Y"), today.strftime("%m"), today.strftime("%d"))).json()
    
    todays_game = {}
    for game in games['games']:
        if game['vTeam']['triCode'] == TEAM or game['hTeam']['triCode'] == TEAM:
            todays_game = game
    
    return todays_game

def get_boxscore(gameid):
    today = datetime.utcnow() - timedelta(hours=5)
    boxscore = requests.get('https://data.nba.net/data/10s/prod/v1/{}{}{}/{}_boxscore.json'.format(today.strftime("%Y"), today.strftime("%m"), today.strftime("%d"), gameid)).json()
    return boxscore

if __name__ == '__main__':
    thread_posted = False
    while thread_posted == False:
        todays_game = get_todays_game()
        
        if todays_game == {}:
            print('[{}]: No Game Today'.format(datetime.now().strftime("%a, %b %d, %Y %I:%M %p")))
            break
        elif todays_game['statusNum'] == 3:
            print('[{}]: Post Game Thread already Posted'.format(datetime.now().strftime("%a, %b %d, %Y %I:%M %p")))
            break
        
        if todays_game['statusNum'] == 1:
            print("[{}]: Game hasn't started yet".format(datetime.now().strftime("%a, %b %d, %Y %I:%M %p")))
            time.sleep(5400)
        
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
                points_statline = '\n\n'
                points_leader_value = boxscore['stats'][team_stats_key]['leaders']['points']['value']
                for index, player in enumerate(boxscore['stats'][team_stats_key]['leaders']['points']['players']):
                    if index > 0:
                        points_statline += ' /'
                    points_statline += ' **{} {}**'.format(player["firstName"], player["lastName"])
                points_statline += ': {} PTS'.format(points_leader_value)
                
                # Grab reboundss leader information
                rebounds_statline = '\n\n'
                rebounds_leader_value = boxscore['stats'][team_stats_key]['leaders']['rebounds']['value']
                for index, player in enumerate(boxscore['stats'][team_stats_key]['leaders']['rebounds']['players']):
                    if index > 0:
                        rebounds_statline += ' /'
                    rebounds_statline += ' **{} {}**'.format(player["firstName"], player["lastName"])
                rebounds_statline += ': {} REBS'.format(rebounds_leader_value)
                
                # Grab assists leader information
                assists_statline = '\n\n'
                assists_leader_value = boxscore['stats'][team_stats_key]['leaders']['assists']['value']
                for index, player in enumerate(boxscore['stats'][team_stats_key]['leaders']['assists']['players']):
                    if index > 0:
                        assists_statline += ' /'
                    assists_statline += ' **{} {}**'.format(player["firstName"], player["lastName"])
                assists_statline += ': {} ASTS'.format(assists_leader_value)
                
                if team_score < opponents_score:
                    result = 'lose to'
                else:
                    result = 'defeat'
                
                title = '[Post Game Thread] {} {} {} {} - {}'.format(TEAM_NAMES[TEAM], result, TEAM_NAMES[opponents_name], team_score, opponents_score)
                selftext = '* [Box Score](https://www.nba.com/games/{}#/boxscore)'.format(todays_game["gameUrlCode"])
                selftext += '\n\nStat Leaders'
                selftext += points_statline
                selftext += rebounds_statline
                selftext += assists_statline
                result = reddit.subreddit('heat').submit(title, selftext=selftext, flair_id='d79dc9aa-cf0d-11e2-9b1b-12313d163d8f')
                #result = reddit.subreddit('testingground4bots').submit(title, selftext=selftext)
                thread_posted = True
                print('[{}]: Game ended thread posted'.format(datetime.now().strftime("%a, %b %d, %Y %I:%M %p")))
                break
            
            elif todays_game['period']['current'] >= 4 and todays_game['statusNum'] == 2 and not todays_game['clock']:
                print('[{}]: Game might have ended'.format(datetime.now().strftime("%a, %b %d, %Y %I:%M %p")))
                time.sleep(3)
            elif todays_game['period']['current'] >= 4 and todays_game['clock'] and int(todays_game['clock'].replace(':', '').split('.')[0]) < 40:
                print('[{}]: Game is almost over'.format(datetime.now().strftime("%a, %b %d, %Y %I:%M %p")))
                time.sleep(10)
            else:
                print('[{}]: Game not over yet'.format(datetime.now().strftime("%a, %b %d, %Y %I:%M %p")))
                time.sleep(90)
    
