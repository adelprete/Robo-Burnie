import requests
import praw
from settings import TEAM
from private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY

def get_todays_standings():
    standings = requests.get('http://data.nba.net/data/10s/prod/v2/current/standings_conference.json').json()
    return standings['league']['standard']['conference']['east']

# The css on the custom widget gets saved as a giant string
css_str = """
p {
padding: 12px;
color: white;
font-size: 10px;
letter-spacing: .5px;
background: #f3a03d;
border-radius: 5px 5px 0px 0px;
margin-bottom: 12px;
font-family: Sans-Serif;
}

td, th{
 padding: 3px 15px;
}

table tr:nth-child(1)>th{
background: #dcdcdc
}

table tr:nth-child(1)>td,table tr:nth-child(2), table tr:nth-child(3), table tr:nth-child(4), table tr:nth-child(5), table tr:nth-child(6), table tr:nth-child(7), table tr:nth-child(8) {
 background: #ffffd7
}

table {
  border-collapse: collapse;
}
table th, table td{
  border: .5px solid black; 
}
table tr:first-child th {
  border-top: 0;
}
table tr td:first-child, table tr th:first-child{
  border-left: 0;
}
table tr:last-child td,table tr:last-child th {
  border-bottom: 0;
}
table tr td:last-child, table tr th:last-child{
  border-right: 0;
}
"""


if __name__ == '__main__':
    """
    This script will update the standings on the Miami Heat 'new' reddit.
    """
    
    # Connect to Reddit
    reddit = praw.Reddit(client_id=CLIENT_ID,
                     client_secret=CLIENT_SECRET_KEY,
                     password=BOT_PASSWORD,
                     user_agent='Game Bot by BobbaGanush87',
                     username='bobbaganush87')
                     
    # Find standings widget
    widgets = reddit.subreddit('heat').widgets
    standings_widget = None
    for widget in widgets.sidebar:
        if widget.shortName.lower() == 'standings':
            standings_widget = widget
            break
    
    # Get latest standings from NBA api and build Markdown
    if standings_widget:
        nba_standings = get_todays_standings()
        standings_markdown = 'STANDINGS\n\n| | Team | W | L | Pct |\n|--|--|--|--|--|'
        
        for position, standing in enumerate(nba_standings, start=1):
            team_nickname = '{}'.format(standing["teamSitesOnly"]["teamNickname"])
            if standing["teamSitesOnly"]["teamTricode"] == TEAM:
                team_nickname = '**{}**'.format(standing["teamSitesOnly"]["teamNickname"])
            standing_markdown = '\n| {} |  {} | {} | {} | {}'.format(position, team_nickname, standing["win"], standing["loss"], standing["winPct"])
            standings_markdown += standing_markdown
        
        standings_widget.mod.update(text=standings_markdown, css=css_str)
    