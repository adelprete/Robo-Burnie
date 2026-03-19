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
./setup-pi.sh
```

Copy your config and credentials (e.g. `.config.json`, `token.json`, Google service account JSON) to the Pi separately after setup.

## How to run scripts

Run from the repo root with `poetry run python`:

```bash
poetry run python src/robo_burnie/scripts/<script>.py [arg]
```

### Scripts and usage

| Script | Command | Description |
|--------|---------|-------------|
| **game_thread** | `poetry run python src/robo_burnie/scripts/game_thread.py create` | Runs daily; checks if a game is today and, if so, creates a game thread and unpins any post game threads. |
| **post_game_thread** *(inactive)* | `poetry run python src/robo_burnie/scripts/post_game_thread.py` | After a Miami Heat game ends, creates a Post Game discussion thread. |
| **schedule_sidebar** | `poetry run python src/robo_burnie/scripts/schedule_sidebar.py` | Runs daily; updates Google Calendar with the latest schedule and syncs the Schedule widget on the sidebar. |
| **standings_sidebar** | `poetry run python src/robo_burnie/scripts/standings_sidebar.py` | Runs daily; updates the Standings widget on the sidebar. |
| **update_old_reddit** | `poetry run python src/robo_burnie/scripts/update_old_reddit.py` | Runs daily; keeps standings and schedule on the old Reddit sidebar up to date. |
| **around_the_league_thread** | `poetry run python src/robo_burnie/scripts/around_the_league_thread.py create` or `update` | Runs daily; creates or updates the [Around the League] thread when there are no Heat games (lists that day's games and updates scores every 10 mins). |
| **reset_config** | `poetry run python src/robo_burnie/scripts/reset_config.py` | Resets the config file to defaults or creates it if missing. |

## Cron (Poetry environment)

See **crontab.example** for a sample crontab that runs the scripts in the Poetry venv.

1. Get your venv path: `cd /home/adelprete/code/Robo-Burnie && poetry env info -p`
2. Edit `crontab.example`: set `PROJECT_DIR` and `VENV` (use the path from step 1).
3. Install: `crontab crontab.example` (or copy the job lines into your existing crontab with `crontab -e`).

Adjust the schedule (minute/hour) to match when you want each script to run.
