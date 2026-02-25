# Robo-Burnie
Scripts for the reddit bot 'RoboBurnie' to update the r/heat subreddit.

All are ran via cronjobs at different times.

## Setup

From the repo root, install dependencies with [Poetry](https://python-poetry.org/):

```bash
poetry install
```

### Raspberry Pi (one-shot setup)

To set up a Raspberry Pi with system deps, Poetry, the repo, and crontab in one go, run **setup-pi.sh** as the user you want to use (e.g. `pi` or any other login). Everything—clone, poetry env, crontab—is created for that user. Safe to run multiple times (e.g. if something fails, fix and re-run).

```bash
# From repo root (e.g. after cloning):
./setup-pi.sh

# Or from anywhere (script will clone to ~/code/Robo-Burnie and re-run):
curl -sL https://raw.githubusercontent.com/adelprete/Robo-Burnie/master/setup-pi.sh -o /tmp/setup-pi.sh && bash /tmp/setup-pi.sh
```

Copy your config and credentials (e.g. `.config.json`, `token.json`, Google service account JSON) to the Pi separately after setup.

## How to run scripts

Run from the repo root. You can use either **run.sh** or **poetry run python**:

| Method | Example |
|--------|--------|
| `./run.sh <script_name> [arg]` | `./run.sh game_thread create` |
| `poetry run python src/robo_burnie/scripts/<script>.py [arg]` | `poetry run python src/robo_burnie/scripts/game_thread.py create` |

### Scripts and usage

| Script | Command | Description |
|--------|---------|-------------|
| **game_thread** | `./run.sh game_thread create` | Runs daily; checks if a game is today and, if so, creates a game thread and unpins any post game threads. |
| **post_game_thread** *(inactive)* | `./run.sh post_game_thread` | After a Miami Heat game ends, creates a Post Game discussion thread. |
| **schedule_sidebar** | `./run.sh schedule_sidebar` | Runs daily; updates Google Calendar with the latest schedule and syncs the Schedule widget on the sidebar. |
| **standings_sidebar** | `./run.sh standings_sidebar` | Runs daily; updates the Standings widget on the sidebar. |
| **update_old_reddit** | `./run.sh update_old_reddit` | Runs daily; keeps standings and schedule on the old Reddit sidebar up to date. |
| **around_the_league_thread** | `./run.sh around_the_league_thread create` or `./run.sh around_the_league_thread update` | Runs daily; creates or updates the [Around the League] thread when there are no Heat games (lists that day’s games and updates scores every 10 mins). |
| **reset_config** | `./run.sh reset_config` | Resets the config file to defaults or creates it if missing. |

## Cron (Poetry environment)

See **crontab.example** for a sample crontab that runs the scripts in the Poetry venv.

1. Get your venv path: `cd /home/adelprete/code/Robo-Burnie && poetry env info -p`
2. Edit `crontab.example`: set `PROJECT_DIR` and `VENV` (use the path from step 1).
3. Install: `crontab crontab.example` (or copy the job lines into your existing crontab with `crontab -e`).

Adjust the schedule (minute/hour) to match when you want each script to run.
