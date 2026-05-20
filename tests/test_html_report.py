"""Tests for the static HTML analytics report.

The HTML report is a self-contained snapshot of the demand_radar SQLite DB:
a collect -> classify -> score funnel plus signal-type, theme, tool, and
opportunity breakdowns. No JavaScript, no external assets.
"""

from __future__ import annotations

from pathlib import Path

from demand_radar import db
from demand_radar.config import Settings
from demand_radar.html_report import build_html_report
from demand_radar.models import RedditComment, RedditPost, Signal, SignalType
from demand_radar.reports import generate_report

_SUBS = ("agency", "SaaS", "sales")


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        DATABASE_PATH=tmp_path / "t.sqlite3",
        REPORTS_DIR=tmp_path / "reports",
    )


def _seed(
    settings: Settings,
    *,
    n_posts: int = 6,
    n_comments: int = 2,
    theme: str = "reporting and dashboards",
) -> None:
    db.init_db(settings.database_path)
    conn = db.connect(settings.database_path)
    posts = [
        RedditPost(
            id=f"p{i}",
            subreddit=_SUBS[i % len(_SUBS)],
            title=f"title {i}",
            body="some body text",
            created_utc=1_700_000_000 + i,
        )
        for i in range(n_posts)
    ]
    comments = [
        RedditComment(
            id=f"c{i}",
            post_id="p0",
            subreddit="agency",
            body="comment text",
            created_utc=1_700_000_500 + i,
        )
        for i in range(n_comments)
    ]
    signals = [
        Signal(
            source_type="post",
            source_id=f"p{i}",
            subreddit=_SUBS[i % len(_SUBS)],
            signal_type=SignalType.PAIN if i % 2 else SignalType.MANUAL_WORKAROUND,
            pain_theme=theme,
            tools_mentioned=["hubspot", "airtable"],
            buying_intent_score=3,
            urgency_score=3,
            competitor_complaint_score=3,
            manual_workaround_score=3,
            summary=f"signal summary {i}",
            evidence_url=f"https://reddit.com/r/{_SUBS[i % len(_SUBS)]}/p{i}",
        )
        for i in range(n_posts)
    ]
    db.save_posts(conn, posts)
    db.save_comments(conn, comments)
    db.save_signals(conn, signals)
    conn.close()


def test_build_html_report_returns_html_document(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed(settings)
    html = build_html_report(settings)
    assert html.lstrip().startswith("<!DOCTYPE html>")
    assert "</html>" in html


def test_html_report_renders_pipeline_funnel_counts(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed(settings, n_posts=7, n_comments=2)
    html = build_html_report(settings)
    assert "Posts collected" in html
    assert "Signals extracted" in html
    # 7 posts -> the count cell is rendered
    assert '<td class="n">7</td>' in html


def test_html_report_lists_signal_types(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed(settings)
    html = build_html_report(settings)
    assert "pain_signal" in html
    assert "manual_workaround" in html


def test_html_report_lists_tools(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed(settings)
    html = build_html_report(settings)
    assert "hubspot" in html
    assert "airtable" in html


def test_html_report_lists_opportunities(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed(settings)
    generate_report(settings, days=3650)
    html = build_html_report(settings)
    assert "reporting and dashboards" in html


def test_html_report_is_self_contained(tmp_path: Path) -> None:
    """No JavaScript, no external stylesheet — opens offline."""
    settings = _settings(tmp_path)
    _seed(settings)
    html = build_html_report(settings)
    assert "<script" not in html
    assert "stylesheet" not in html
    assert "cdn" not in html.lower()


def test_html_report_escapes_user_content(tmp_path: Path) -> None:
    """Reddit-sourced text must be HTML-escaped (no injection)."""
    settings = _settings(tmp_path)
    db.init_db(settings.database_path)
    conn = db.connect(settings.database_path)
    post = RedditPost(
        id="x1", subreddit="agency", title="t", body="b", created_utc=1_700_000_000
    )
    signal = Signal(
        source_type="post",
        source_id="x1",
        subreddit="agency",
        signal_type=SignalType.PAIN,
        pain_theme="<script>alert(1)</script>",
        tools_mentioned=[],
        summary="a & b < c",
        evidence_url="https://reddit.com/x1",
    )
    db.save_posts(conn, [post])
    db.save_signals(conn, [signal])
    conn.close()

    html = build_html_report(settings)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_html_report_includes_signal_detail_table(tmp_path: Path) -> None:
    """Top signals are listed individually with evidence links to read/analyze."""
    settings = _settings(tmp_path)
    _seed(settings, n_posts=6)
    html = build_html_report(settings)
    assert "signal summary 0" in html
    assert 'href="https://reddit.com/r/' in html


def test_html_report_handles_empty_database(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    db.init_db(settings.database_path)
    html = build_html_report(settings)
    assert html.lstrip().startswith("<!DOCTYPE html>")
    assert "Posts collected" in html


def test_generate_report_also_writes_html_file(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed(settings)
    md_path = generate_report(settings, days=3650)
    html_path = md_path.with_suffix(".html")
    assert html_path.exists()
    assert html_path.read_text(encoding="utf-8").lstrip().startswith("<!DOCTYPE html>")
