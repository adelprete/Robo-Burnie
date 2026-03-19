# AGENTS.md

## What This Repo Is

Robo-Burnie is a Reddit bot (`u/RoboBurnie`) that automates community management tasks for the [r/heat](https://www.reddit.com/r/heat/) subreddit (Miami Heat). It creates and manages game-day discussion threads, updates sidebar widgets with live standings and schedule data, and keeps both New Reddit and Old Reddit in sync. The bot is designed to run on a Raspberry Pi via cron jobs.

## Architecture

```
src/robo_burnie/
├── scripts/            # Standalone entry points, each invoked by cron
│   ├── game_thread.py
│   ├── post_game_thread.py
│   ├── around_the_league_thread.py
│   ├── standings_sidebar.py
│   ├── schedule_sidebar.py
│   ├── update_old_reddit.py
│   └── reset_config.py
├── _helpers.py         # NBA data fetching (standings, scores, schedules, box scores)
├── _constants.py       # Team metadata lookup tables (tricode→name, ID→info)
├── _settings.py        # SUBREDDIT ("heat") and TEAM ("MIA") constants
├── _file_lock.py       # fcntl-based file lock to prevent concurrent script runs
├── private.py          # Credentials (gitignored)
└── default_config.json # Per-script enable/disable defaults
```

Every script in `scripts/` is a self-contained entry point. They all share the helper modules for NBA data and Reddit interaction.

## Scripts

### game_thread.py

Creates a stickied game-day discussion thread when the Heat play. Includes opponent, records, TV/radio info, standings context, and a box score link. Unstickies any existing post-game thread to make room.

- Invoked with: `./run.sh game_thread create`
- Runs once daily (morning, before games start).

### post_game_thread.py

Creates a post-game discussion thread after a Heat game ends, with box score and stat leaders. Currently **disabled** via config (`default_config.json`).

### around_the_league_thread.py

On days without a Heat game, creates and periodically updates a stickied "Around the League" thread listing all NBA games for the day with live scores and TV channels.

- `create`: posts a new thread (runs once daily).
- `update`: edits the thread body with fresh scores (runs every 10 minutes during game hours).

### standings_sidebar.py

Updates the Standings widget on New Reddit's sidebar with current Eastern Conference standings. The Heat row is bolded.

### schedule_sidebar.py

Fetches the Heat schedule from the NBA CDN, syncs it to a Google Calendar, then triggers Reddit's schedule widget to pull from that calendar. Requires Google OAuth credentials (`token.json`, `google_credentials.json`).

### update_old_reddit.py

Edits the `config/sidebar` wiki page to keep Old Reddit's sidebar current with standings and upcoming/recent games.

### reset_config.py

Resets the runtime config file (`.config.json`) back to defaults from `default_config.json`.

## Key Modules

### _helpers.py

Central module for all NBA data. Key functions:

- **Standings:** `get_todays_standings()`, `get_team_standings()` — via `nba_api`.
- **Schedule:** `get_full_team_schedule()`, `get_game_from_cdn_endpoint()` — via NBA CDN.
- **Today's games:** `get_todays_game_v3()`, `get_todays_games_cdn()` — checks if the Heat play today and fetches all games.
- **Broadcasters:** `get_game_id_to_channels_map()` — TV/radio channel info.
- **Box scores:** `get_boxscore()`, `get_boxscore_link()`, `get_espn_boxscore_link()`.
- **Utilities:** `get_current_datetime()` (uses UTC-4 offset for Eastern time), `is_script_enabled()`.

### _constants.py

Two lookup dictionaries:
- `TEAM_TRI_TO_INFO` — tricode (e.g. `"MIA"`) to full team name and subreddit link.
- `TEAM_ID_TO_INFO` — NBA team ID to nickname, tricode, conference, subreddit, etc.

### _settings.py

Two constants: `SUBREDDIT = "heat"` and `TEAM = "MIA"`. Change these if forking for another team.

### _file_lock.py

Context manager (`file_lock`) using `fcntl.flock` to prevent overlapping runs of the same script (used by `post_game_thread`).

## Data Sources

| Source | Used For |
|--------|----------|
| [nba_api](https://github.com/swar/nba_api) (Python package) | Standings, scoreboard, box scores |
| NBA CDN (`cdn.nba.com`) | Schedule, today's games, broadcaster info |
| ESPN API | Box score links |
| Reddit API via [PRAW](https://praw.readthedocs.io/) | Thread creation, stickying, sidebar widgets, wiki edits |
| Google Calendar API | Schedule sidebar sync |

## Configuration

- **`default_config.json`** — defines which scripts are enabled/disabled by default.
- **`.config.json`** (gitignored, runtime) — active config; overrides defaults. Created/reset by `reset_config.py`.
- **`private.py`** (gitignored) — Reddit OAuth creds (`CLIENT_ID`, `CLIENT_SECRET_KEY`, `BOT_PASSWORD`) and Google API keys.

## Running

Scripts are invoked via `run.sh`:

```
./run.sh <script_name> [arg]
```

In production, cron jobs handle scheduling. See `crontab.example` for the full schedule. The typical daily flow:

1. **9:00 AM** — Create game thread (if Heat play today).
2. **9:05 AM** — Update schedule sidebar.
3. **9:10 AM** — Update standings sidebar.
4. **9:15 AM** — Update Old Reddit sidebar.
5. **11:00 AM** — Create Around the League thread (if no Heat game).
6. **Every 10 min (1 PM–midnight)** — Update Around the League scores.

## Development

- **Package manager:** [Poetry](https://python-poetry.org/) — `poetry install` to set up.
- **Python version:** 3.13.
- **Formatting:** Black + isort (configured in `pyproject.toml` and `.pre-commit-config.yaml`).
- **Linting:** flake8 (`.flake8`).
- **Tests:** pytest — `poetry run pytest`. Test data lives in `tests/test_data/`.
- **Deployment:** Raspberry Pi (`setup-pi.sh`) or Docker (`Dockerfile`).

## Conventions

- All times are handled in approximate Eastern time via a UTC-4 offset (`datetime.now() - timedelta(hours=4)`).
- Thread management uses Reddit sticky slots (max 2). Creating a new thread unstickies the previous one of the same type.
- Flair IDs are hardcoded per thread type for consistent subreddit styling.
- Scripts that need to guard against concurrent execution use `file_lock`.
- The `is_script_enabled()` check allows scripts to be toggled on/off without changing cron.
