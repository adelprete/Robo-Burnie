import praw

from robo_burnie._settings import SUBREDDIT
from robo_burnie.private import BOT_PASSWORD, CLIENT_ID, CLIENT_SECRET_KEY


def _main():

    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET_KEY,
        password=BOT_PASSWORD,
        user_agent="Game Bot for r/heat",
        username="RoboBurnie",
    )

    game_thread = _get_game_thread(reddit)

    if game_thread is None:
        print("No game thread found")
        return

    url = "https://www.reddit.com/r/heat/comments/1i5pm7f/around_the_league_discuss_todays_nba_news_and/"
    submission = reddit.submission(url=url)

    for top_level_comment in submission.comments:
        breakpoint()
        print(top_level_comment.body)


def _get_game_thread(reddit):
    for submission in reddit.subreddit(SUBREDDIT).new(limit=10):
        if submission.link_flair_text == "Game Thread":
            return submission
    return None


_main()

# if __name__ == "__main__":
#     if _helpers.is_script_enabled("post_game_thread"):
#         post_game_thread()
#     else:
#         logging.debug("post_game_thread is disabled")
