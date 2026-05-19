from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from demand_radar import db
from demand_radar.backends.base import RedditBackend
from demand_radar.backends.public_json import RedditApiError
from demand_radar.config import Settings
from demand_radar.extractors import extract_signal_from_text
from demand_radar.filters import is_relevant_post
from demand_radar.reddit_client import get_backend, polite_sleep
from demand_radar.watchlist import DEFAULT_WATCHLIST_PATH, load_watchlist

MIN_SLEEP_BETWEEN_SUBS = 2.0


def collect_watchlist(
    *,
    settings: Settings,
    watchlist_path: Path | None = None,
    per_sub_limit: int = 50,
    since_days: int | None = None,
    sleep_between_subs: float = MIN_SLEEP_BETWEEN_SUBS,
    sleep_fn: Callable[[float], None] = polite_sleep,
    backend: RedditBackend | None = None,
) -> dict[str, Any]:
    """Politely loop the watchlist, fetch new posts, extract signals, dedupe.

    Posts and signals are deduped via SQLite (`INSERT OR IGNORE`).
    Subreddits that error are skipped so one bad sub does not stop the loop.
    """
    if sleep_between_subs < MIN_SLEEP_BETWEEN_SUBS:
        raise ValueError(
            f"sleep_between_subs must be >= {MIN_SLEEP_BETWEEN_SUBS}s "
            f"to stay polite; got {sleep_between_subs}"
        )

    subs = load_watchlist(watchlist_path or DEFAULT_WATCHLIST_PATH)
    client = backend or get_backend(settings)
    db.init_db(settings.database_path)
    conn = db.connect(settings.database_path)

    cutoff_utc: int | None = None
    if since_days is not None and since_days > 0:
        import time as _time

        cutoff_utc = int(_time.time()) - since_days * 24 * 60 * 60

    subs_visited: list[str] = []
    failed_subs: list[str] = []
    total_posts_saved = 0
    total_signals_saved = 0

    for idx, sub in enumerate(subs):
        if idx > 0:
            sleep_fn(sleep_between_subs)
        try:
            posts = client.fetch_new_posts(sub, limit=per_sub_limit)
        except RedditApiError:
            failed_subs.append(sub)
            continue

        if cutoff_utc is not None:
            posts = [p for p in posts if p.created_utc >= cutoff_utc]

        subs_visited.append(sub)
        total_posts_saved += db.save_posts(conn, posts)

        signals_for_sub = []
        for post in posts:
            if not is_relevant_post(post.title, post.body, post.comment_count):
                continue
            signals_for_sub.append(
                extract_signal_from_text(
                    source_type="post",
                    source_id=post.id,
                    subreddit=post.subreddit,
                    text=f"{post.title}\n{post.body}",
                    evidence_url=post.permalink,
                )
            )
        total_signals_saved += db.save_signals(conn, signals_for_sub)

    conn.close()
    return {
        "subs_visited": subs_visited,
        "subs_failed": failed_subs,
        "posts_saved": total_posts_saved,
        "signals_saved": total_signals_saved,
    }


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
