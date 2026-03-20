from __future__ import annotations

SUBREDDIT = "heat"
TEAM = "MIA"

FLAIR_IDS: dict[str, dict[str, str]] = {
    "heat": {
        "game_thread": "92815388-3a88-11e2-a4e1-12313d14a568",
        "post_game_thread": "d79dc9aa-cf0d-11e2-9b1b-12313d163d8f",
        "around_the_league": "29f18426-a10b-11e6-af2b-0ea571864a50",
    },
    "heatcss": {
        "game_thread": "8a22ad40-c182-11e3-877e-12313b0d38eb",
        "post_game_thread": "aa3be42a-c182-11e3-b8ca-12313b0e88c2",
        "around_the_league": "29f18426-a10b-11e6-af2b-0ea571864a50",
    },
}


def get_flair_id(thread_type: str, subreddit: str = SUBREDDIT) -> str:
    return FLAIR_IDS[subreddit][thread_type]
