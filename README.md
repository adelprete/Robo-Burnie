# Robo-Burnie
Scripts for the reddit bot 'RoboBurnie' to update the r/heat subreddit

All are ran via cronjobs at different times

* **game_thread.py (inactive)** - Every Day at 8 am this script checks if a game is playing today.  If so it creates a game thread and unstickys any post game threads.
* **post_game_thread.py (inactive)** - Once a Miami Heat game is finished, a new thread will be created for Post Game discussion.
This script is ran once a day at 1pm and finishes once the game for that day is over.  If a game is found and it ends, the game thread is unstickied.
* **schedule.py** - Everyday at 5 am r/heat's google calendar is updated with the season's schedule.
* **standings.py** - Every day at 4am EST this script is ran to update the Eastern Conference Standings on the sidebar of the New Reddit version of this subreddit.
* **around_the_league_thread.py** - Creates the the [Around the League] thread in the morning at 8am.  Updates the scores every 10 mins.
