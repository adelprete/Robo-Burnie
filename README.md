# Robo-Burnie
Scripts for the reddit bot 'RoboBurnie' to update the r/heat subreddit.

All are ran via cronjobs at different times

* **game_thread.py** - This script runs daily and checks if a game is playing today.  If so, it creates a game thread and unpins any post game threads.
* **post_game_thread.py (inactive)** - Once a Miami Heat game is finished, a new thread will be created for Post Game discussion.
* **schedule_sidebar.py** - This script runs daily and updates the google calendar with the latest schedule and also syncs the calendar with the Schedule widget on the sidebar.
* **standings_sidebar.py** - This script runs daily and updates the Standings widget on the sidebar.
* **update_old_sidebar.py** - This script runs daily and makes sure that the standings and schedule on the old reddit sidebar is up to date.
* **around_the_league_thread.py** - This script runs daily and creates the [Around the League] thread if there arent any Heat games.  This thread lists out each game playing that day and updates the scores every 10 mins.
