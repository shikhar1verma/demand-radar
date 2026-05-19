from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from demand_radar.models import RedditComment, RedditPost, Signal

SCHEMA = """
CREATE TABLE IF NOT EXISTS subreddits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    category TEXT,
    audience TEXT,
    is_active INTEGER DEFAULT 1,
    activity_score INTEGER DEFAULT 0,
    noise_score INTEGER DEFAULT 0,
    buyer_quality_score INTEGER DEFAULT 0,
    last_scanned_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reddit_posts (
    id TEXT PRIMARY KEY,
    subreddit TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    author TEXT,
    score INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    url TEXT,
    permalink TEXT,
    created_utc INTEGER NOT NULL,
    scraped_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reddit_comments (
    id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL,
    subreddit TEXT NOT NULL,
    body TEXT NOT NULL,
    author TEXT,
    score INTEGER DEFAULT 0,
    created_utc INTEGER NOT NULL,
    scraped_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    subreddit TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    pain_theme TEXT,
    buyer_role TEXT,
    industry TEXT,
    tools_mentioned TEXT,
    buying_intent_score INTEGER DEFAULT 0,
    urgency_score INTEGER DEFAULT 0,
    competitor_complaint_score INTEGER DEFAULT 0,
    manual_workaround_score INTEGER DEFAULT 0,
    summary TEXT NOT NULL,
    evidence_url TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT,
    opportunity_name TEXT NOT NULL,
    target_buyer TEXT,
    pain_theme TEXT,
    current_workaround TEXT,
    tools_mentioned TEXT,
    score INTEGER DEFAULT 0,
    suggested_offer TEXT,
    mvp_angle TEXT,
    validation_status TEXT DEFAULT 'unvalidated',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_posts_subreddit_created ON reddit_posts(subreddit, created_utc);
CREATE INDEX IF NOT EXISTS idx_comments_post ON reddit_comments(post_id);
CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(signal_type);
CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_source_unique
    ON signals(source_type, source_id, signal_type);
CREATE UNIQUE INDEX IF NOT EXISTS idx_opportunities_key
    ON opportunities(key) WHERE key IS NOT NULL;
"""


def _ensure_opportunities_key_column(conn: sqlite3.Connection) -> None:
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(opportunities)")}
    if "key" not in cols:
        conn.execute("ALTER TABLE opportunities ADD COLUMN key TEXT")


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: Path) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        _ensure_opportunities_key_column(conn)
        conn.commit()


def save_posts(conn: sqlite3.Connection, posts: Iterable[RedditPost]) -> int:
    count = 0
    for post in posts:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO reddit_posts
            (id, subreddit, title, body, author, score, comment_count,
             url, permalink, created_utc, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post.id,
                post.subreddit,
                post.title,
                post.body,
                post.author,
                post.score,
                post.comment_count,
                post.url,
                post.permalink,
                post.created_utc,
                utc_now(),
            ),
        )
        count += cur.rowcount
    conn.commit()
    return count


def save_comments(conn: sqlite3.Connection, comments: Iterable[RedditComment]) -> int:
    count = 0
    for comment in comments:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO reddit_comments
            (id, post_id, subreddit, body, author, score, created_utc, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                comment.id,
                comment.post_id,
                comment.subreddit,
                comment.body,
                comment.author,
                comment.score,
                comment.created_utc,
                utc_now(),
            ),
        )
        count += cur.rowcount
    conn.commit()
    return count


def save_signals(conn: sqlite3.Connection, signals: Iterable[Signal]) -> int:
    count = 0
    for signal in signals:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO signals
            (source_type, source_id, subreddit, signal_type, pain_theme, buyer_role, industry,
             tools_mentioned, buying_intent_score, urgency_score, competitor_complaint_score,
             manual_workaround_score, summary, evidence_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal.source_type,
                signal.source_id,
                signal.subreddit,
                signal.signal_type.value,
                signal.pain_theme,
                signal.buyer_role,
                signal.industry,
                ",".join(signal.tools_mentioned),
                signal.buying_intent_score,
                signal.urgency_score,
                signal.competitor_complaint_score,
                signal.manual_workaround_score,
                signal.summary,
                signal.evidence_url,
                utc_now(),
            ),
        )
        count += cur.rowcount
    conn.commit()
    return count
