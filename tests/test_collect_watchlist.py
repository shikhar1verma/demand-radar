"""Tests for M1 — `collect-watchlist` CLI.

Encodes the M1 Done-when checklist from .context/milestones.md:

- `demand-radar collect-watchlist [--since 7d] [--limit 50]` exists.
- Loops the watchlist in order, sleeps >= 2 s between subreddits.
- Re-running is idempotent (dedupe works).
- Tests cover the loop and a 429 backoff path.
"""

from __future__ import annotations

import inspect
import sqlite3
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from demand_radar import db
from demand_radar.backends import public_json as pj_module
from demand_radar.backends.public_json import PublicJsonBackend
from demand_radar.cli import app, collect_watchlist_cmd
from demand_radar.collector import collect_watchlist
from demand_radar.config import Settings
from demand_radar.models import RedditPost
from demand_radar.watchlist import load_watchlist


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        DATABASE_PATH=tmp_path / "test.sqlite3",
        REPORTS_DIR=tmp_path / "reports",
    )


def _write_watchlist(tmp_path: Path, subs: list[str]) -> Path:
    path = tmp_path / "watchlist.csv"
    rows = ["subreddit,category,audience,notes"]
    for s in subs:
        rows.append(f"{s},founder,test,test")
    path.write_text("\n".join(rows) + "\n")
    return path


def _post(post_id: str, subreddit: str, title: str = "") -> RedditPost:
    return RedditPost(
        id=post_id,
        subreddit=subreddit,
        title=title or f"is there a tool for {post_id}? I'm stuck",
        body="I keep doing this manually with spreadsheets, too painful",
        author="someone",
        score=10,
        comment_count=3,
        url=None,
        permalink=f"https://www.reddit.com/r/{subreddit}/comments/{post_id}/",
        created_utc=1_700_000_000,
    )


class _FakeBackend:
    """Fake RedditBackend that records calls and returns canned posts."""

    def __init__(self, posts: dict[str, list[RedditPost]] | None = None) -> None:
        self.posts = posts or {}
        self.calls: list[str] = []

    def fetch_new_posts(self, subreddit_name: str, limit: int = 100) -> list[RedditPost]:
        self.calls.append(subreddit_name)
        return list(self.posts.get(subreddit_name, []))

    def fetch_top_level_comments(self, subreddit_name, post_id, limit=50):
        return []


def test_collect_watchlist_cli_command_exists() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["collect-watchlist", "--help"])
    assert result.exit_code == 0


def test_collect_watchlist_cli_accepts_since_and_limit_options() -> None:
    params = inspect.signature(collect_watchlist_cmd).parameters
    assert "since" in params
    assert "limit" in params


def test_load_watchlist_reads_subreddit_names_in_order(tmp_path: Path) -> None:
    path = _write_watchlist(tmp_path, ["SaaS", "agency", "marketing"])
    assert load_watchlist(path) == ["SaaS", "agency", "marketing"]


def test_collect_watchlist_loops_subs_in_order(tmp_path: Path) -> None:
    watchlist_path = _write_watchlist(tmp_path, ["SaaS", "agency", "marketing"])
    backend = _FakeBackend(
        {
            "SaaS": [_post("p1", "SaaS")],
            "agency": [_post("p2", "agency")],
            "marketing": [_post("p3", "marketing")],
        }
    )
    sleeps: list[float] = []
    result = collect_watchlist(
        settings=_settings(tmp_path),
        watchlist_path=watchlist_path,
        per_sub_limit=10,
        sleep_between_subs=2.0,
        sleep_fn=sleeps.append,
        backend=backend,
    )
    assert backend.calls == ["SaaS", "agency", "marketing"]
    assert result["posts_saved"] == 3
    assert result["subs_visited"] == ["SaaS", "agency", "marketing"]


def test_collect_watchlist_sleeps_at_least_two_seconds_between_subs(tmp_path: Path) -> None:
    watchlist_path = _write_watchlist(tmp_path, ["SaaS", "agency", "marketing"])
    backend = _FakeBackend({"SaaS": [], "agency": [], "marketing": []})
    sleeps: list[float] = []
    collect_watchlist(
        settings=_settings(tmp_path),
        watchlist_path=watchlist_path,
        per_sub_limit=10,
        sleep_between_subs=2.0,
        sleep_fn=sleeps.append,
        backend=backend,
    )
    long_sleeps = [s for s in sleeps if s >= 2.0]
    assert len(long_sleeps) >= 2


def test_collect_watchlist_rejects_sleep_below_two_seconds(tmp_path: Path) -> None:
    watchlist_path = _write_watchlist(tmp_path, ["SaaS"])
    backend = _FakeBackend()
    with pytest.raises(ValueError):
        collect_watchlist(
            settings=_settings(tmp_path),
            watchlist_path=watchlist_path,
            per_sub_limit=10,
            sleep_between_subs=0.1,
            sleep_fn=lambda _: None,
            backend=backend,
        )


def test_collect_watchlist_is_idempotent_on_posts(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    db.init_db(settings.database_path)
    watchlist_path = _write_watchlist(tmp_path, ["SaaS"])
    backend = _FakeBackend({"SaaS": [_post("p1", "SaaS"), _post("p2", "SaaS")]})

    first = collect_watchlist(
        settings=settings,
        watchlist_path=watchlist_path,
        per_sub_limit=10,
        sleep_between_subs=2.0,
        sleep_fn=lambda _: None,
        backend=backend,
    )
    second = collect_watchlist(
        settings=settings,
        watchlist_path=watchlist_path,
        per_sub_limit=10,
        sleep_between_subs=2.0,
        sleep_fn=lambda _: None,
        backend=backend,
    )

    assert first["posts_saved"] == 2
    assert second["posts_saved"] == 0

    conn = sqlite3.connect(settings.database_path)
    (row_count,) = conn.execute("SELECT COUNT(*) FROM reddit_posts").fetchone()
    conn.close()
    assert row_count == 2


def test_collect_watchlist_is_idempotent_on_signals(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    db.init_db(settings.database_path)
    watchlist_path = _write_watchlist(tmp_path, ["SaaS"])
    backend = _FakeBackend({"SaaS": [_post("p1", "SaaS")]})

    for _ in range(2):
        collect_watchlist(
            settings=settings,
            watchlist_path=watchlist_path,
            per_sub_limit=10,
            sleep_between_subs=2.0,
            sleep_fn=lambda _: None,
            backend=backend,
        )

    conn = sqlite3.connect(settings.database_path)
    (sig_count,) = conn.execute(
        "SELECT COUNT(*) FROM signals WHERE source_id = 'p1'"
    ).fetchone()
    conn.close()
    assert sig_count >= 1
    assert sig_count <= 1, f"signals duplicated on re-run: {sig_count}"


def test_public_json_backend_retries_after_429_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pj_module.time, "sleep", lambda _: None)

    call_count = {"n": 0}
    success_payload = {"data": {"children": []}}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return httpx.Response(429, text="rate limited")
        return httpx.Response(200, json=success_payload)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(
        base_url="https://www.reddit.com",
        headers={"User-Agent": "demand-radar-test/0.1"},
        transport=transport,
    )
    backend = PublicJsonBackend(
        Settings(REDDIT_USER_AGENT="demand-radar-test/0.1"),
        client=client,
        request_sleep_seconds=0.0,
    )

    posts = backend.fetch_new_posts("SaaS", limit=10)

    assert call_count["n"] == 2
    assert posts == []
