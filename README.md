# Robo-Burnie
Scripts for the reddit bot 'RoboBurnie' to update the r/heat subreddit.

All are ran via cronjobs at different times.

## Setup

From the repo root, install dependencies with [Poetry](https://python-poetry.org/):

```bash
poetry install
```

### Raspberry Pi (one-shot setup)

Run **setup-pi.sh** as the user that will own the install (e.g. `pi`). It installs system deps, Poetry, clones the repo, and configures the crontab. Idempotent—safe to run again if something fails.

```bash
./setup-pi.sh
<<<<<<< HEAD
=======

# Or from anywhere (script will clone to ~/code/Robo-Burnie and re-run):
curl -sL https://raw.githubusercontent.com/YOUR_USERNAME/Robo-Burnie/master/setup-pi.sh -o /tmp/setup-pi.sh && bash /tmp/setup-pi.sh
>>>>>>> 88983ce (update readme)
```

Copy your config and credentials to the Pi separately after setup: `.config.json`, `token.json`, Google service account JSON, and **private.py** (in `src/robo_burnie/`).

## How to run scripts

<<<<<<< HEAD
Run from the repo root with `poetry run python`:
=======
Run from the repo root with **poetry run python**:
>>>>>>> 88983ce (update readme)

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
<<<<<<< HEAD
| **around_the_league_thread** | `poetry run python src/robo_burnie/scripts/around_the_league_thread.py create` or `update` | Runs daily; creates or updates the [Around the League] thread when there are no Heat games (lists that day's games and updates scores every 10 mins). |
=======
| **around_the_league_thread** | `poetry run python src/robo_burnie/scripts/around_the_league_thread.py create` or `... update` | Runs daily; creates or updates the [Around the League] thread when there are no Heat games (lists that day’s games and updates scores every 10 mins). |
>>>>>>> 88983ce (update readme)
| **reset_config** | `poetry run python src/robo_burnie/scripts/reset_config.py` | Resets the config file to defaults or creates it if missing. |

## Cron (Poetry environment)

See **crontab.example** for a sample crontab that runs the scripts in the Poetry venv.

1. Get your venv path: `cd /path/to/Robo-Burnie && poetry env info -p`
2. Edit `crontab.example`: set `PROJECT_DIR` and `VENV` (use the path from step 1).
3. Install: `crontab crontab.example` (or copy the job lines into your existing crontab with `crontab -e`).

Adjust the schedule (minute/hour) to match when you want each script to run.
