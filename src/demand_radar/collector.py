from __future__ import annotations

from demand_radar import db
from demand_radar.config import Settings
from demand_radar.extractors import extract_signal_from_text
from demand_radar.filters import is_relevant_post
from demand_radar.reddit_client import get_backend, polite_sleep


def collect_subreddit(
    *,
    settings: Settings,
    subreddit_name: str,
    limit: int = 100,
    comment_limit: int = 50,
    sleep_seconds: float = 1.0,
) -> dict[str, int]:
    client = get_backend(settings)
    conn = db.connect(settings.database_path)

    posts = client.fetch_new_posts(subreddit_name, limit=limit)
    saved_posts = db.save_posts(conn, posts)

    saved_comments = 0
    saved_signals = 0

    for post in posts:
        text = f"{post.title}\n{post.body}"
        if not is_relevant_post(post.title, post.body, post.comment_count):
            continue

        post_signal = extract_signal_from_text(
            source_type="post",
            source_id=post.id,
            subreddit=post.subreddit,
            text=text,
            evidence_url=post.permalink,
        )
        saved_signals += db.save_signals(conn, [post_signal])

        comments = client.fetch_top_level_comments(subreddit_name, post.id, limit=comment_limit)
        saved_comments += db.save_comments(conn, comments)

        comment_signals = []
        for comment in comments:
            if is_relevant_post(comment.body, "", 0, threshold=2):
                comment_signals.append(
                    extract_signal_from_text(
                        source_type="comment",
                        source_id=comment.id,
                        subreddit=comment.subreddit,
                        text=comment.body,
                        evidence_url=post.permalink,
                    )
                )
        saved_signals += db.save_signals(conn, comment_signals)
        polite_sleep(sleep_seconds)

    conn.close()
    return {
        "posts_fetched": len(posts),
        "posts_saved": saved_posts,
        "comments_saved": saved_comments,
        "signals_saved": saved_signals,
    }
