"""Tests for M4 — `brief` bridge command.

Done when (.context/milestones.md M4):
- One brief file is produced per invocation, written into the configured briefs dir.
- Real URLs, real quotes, real tools — no placeholders left in.
- Scorecard pre-filled by the system from the underlying signals (user can adjust).
- A brief produced for any seeded theme reads as something a human would actually act on.
"""

from __future__ import annotations

import inspect
import re
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from demand_radar import db
from demand_radar.brief import BriefNotAvailable, render_brief
from demand_radar.cli import app, brief_cmd
from demand_radar.config import Settings
from demand_radar.models import RedditComment, RedditPost, Signal, SignalType
from demand_radar.opportunities import opportunity_key, save_opportunities


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        DATABASE_PATH=tmp_path / "test.sqlite3",
        REPORTS_DIR=tmp_path / "reports",
    )


def _seed(
    settings: Settings,
    *,
    theme: str = "client reporting",
    tools: tuple[str, ...] = ("hubspot", "salesforce", "airtable"),
    num_posts: int = 6,
) -> None:
    db.init_db(settings.database_path)
    conn = db.connect(settings.database_path)

    posts = []
    comments = []
    signals: list[Signal] = []
    verbatim_quotes = [
        (
            "Our weekly client reports take 5 hours every Friday "
            "because pulling HubSpot data is manual."
        ),
        (
            "Spent 4 hours every Friday copying Stripe payouts into a sheet "
            "so the owner can see weekly cash flow."
        ),
        (
            "Looking for someone to set up a weekly KPI dashboard so I can "
            "stop building it manually."
        ),
    ]
    for i in range(num_posts):
        post_id = f"p{i:02d}"
        title = f"Anyone solved {theme}? post {i}"
        body = verbatim_quotes[i % len(verbatim_quotes)]
        posts.append(
            RedditPost(
                id=post_id,
                subreddit="agency",
                title=title,
                body=body,
                author=f"u{i}",
                score=10 + i,
                comment_count=3,
                url=None,
                permalink=f"https://reddit.com/r/agency/comments/{post_id}/",
                created_utc=1_700_000_000 + i,
            )
        )
        signals.append(
            Signal(
                source_type="post",
                source_id=post_id,
                subreddit="agency",
                signal_type=SignalType.MANUAL_WORKAROUND,
                pain_theme=theme,
                buyer_role="agency_owner",
                tools_mentioned=[tools[i % len(tools)]],
                buying_intent_score=4,
                urgency_score=4,
                competitor_complaint_score=3,
                manual_workaround_score=5,
                summary=body[:200],
                evidence_url=f"https://reddit.com/r/agency/comments/{post_id}/",
            )
        )

    # Competitor-dissatisfaction signals (each tied to a specific tool)
    competitor_complaints = [
        (
            "HubSpot is too expensive for sub-10-seat agencies and missing decent reporting.",
            "hubspot",
        ),
        (
            "Salesforce charges $24k/year and we only use 10% of it — feels punitive.",
            "salesforce",
        ),
        (
            "Airtable pricing model is unpredictable; quarterly invoices feel like surprises.",
            "airtable",
        ),
    ]
    for j, (text, tool) in enumerate(competitor_complaints):
        cid = f"c{j:02d}"
        comments.append(
            RedditComment(
                id=cid,
                post_id=posts[0].id,
                subreddit="agency",
                body=text,
                author=f"complainer{j}",
                score=5,
                created_utc=1_700_000_500 + j,
            )
        )
        signals.append(
            Signal(
                source_type="comment",
                source_id=cid,
                subreddit="agency",
                signal_type=SignalType.COMPETITOR_DISSATISFACTION,
                pain_theme=theme,
                buyer_role="agency_owner",
                tools_mentioned=[tool],
                buying_intent_score=3,
                urgency_score=3,
                competitor_complaint_score=5,
                manual_workaround_score=2,
                summary=text,
                evidence_url=f"https://reddit.com/r/agency/comments/{posts[0].id}/{cid}/",
            )
        )

    db.save_posts(conn, posts)
    db.save_comments(conn, comments)
    db.save_signals(conn, signals)

    # Persist the opportunity row that the brief flow expects
    save_opportunities(
        conn,
        [
            {
                "key": opportunity_key(
                    pain_theme=theme, top_buyer_role="agency_owner", top_tool=tools[0]
                ),
                "opportunity_name": theme,
                "pain_theme": theme,
                "target_buyer": "agency_owner",
                "tools_mentioned": ", ".join(tools),
                "score": 32,
                "suggested_offer": "$399 weekly client reporting automation pilot",
                "current_workaround": None,
                "mvp_angle": None,
            }
        ],
    )
    conn.close()


def test_brief_cli_command_is_registered() -> None:
    params = inspect.signature(brief_cmd).parameters
    assert "theme" in params


def test_render_brief_writes_file_into_output_dir(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed(settings)
    out_dir = tmp_path / "briefs"

    path = render_brief(settings=settings, theme="client reporting", output_dir=out_dir)

    assert path.exists()
    assert path.parent == out_dir
    assert path.suffix == ".md"
    assert "client" in path.name.lower()


def test_render_brief_creates_output_dir_when_missing(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed(settings)
    out_dir = tmp_path / "deep" / "briefs"
    assert not out_dir.exists()

    render_brief(settings=settings, theme="client reporting", output_dir=out_dir)

    assert out_dir.is_dir()


def test_render_brief_raises_when_no_opportunity_for_theme(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    db.init_db(settings.database_path)
    with pytest.raises(BriefNotAvailable):
        render_brief(
            settings=settings,
            theme="nonexistent theme",
            output_dir=tmp_path / "briefs",
        )


def test_render_brief_includes_real_evidence_urls(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed(settings)

    path = render_brief(settings=settings, theme="client reporting", output_dir=tmp_path / "out")
    text = path.read_text()

    urls = re.findall(r"https?://reddit\.com/\S+", text)
    assert len(urls) >= 3


def test_render_brief_includes_verbatim_buyer_quote(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed(settings)

    path = render_brief(settings=settings, theme="client reporting", output_dir=tmp_path / "out")
    text = path.read_text()

    assert "Spent 4 hours every Friday" in text


def test_render_brief_names_three_competitor_weaknesses(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed(settings)

    path = render_brief(settings=settings, theme="client reporting", output_dir=tmp_path / "out")
    text = path.read_text().lower()

    assert "hubspot" in text
    assert "salesforce" in text
    assert "airtable" in text


def test_render_brief_scorecard_is_prefilled(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed(settings)

    path = render_brief(settings=settings, theme="client reporting", output_dir=tmp_path / "out")
    text = path.read_text()

    match = re.search(r"Total[:\s]*\**\s*(\d+)\s*/\s*45", text)
    assert match is not None, text
    total = int(match.group(1))
    assert 9 <= total <= 45


def test_render_brief_has_no_unfilled_template_placeholders(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed(settings)

    path = render_brief(settings=settings, theme="client reporting", output_dir=tmp_path / "out")
    text = path.read_text()

    for placeholder in ("`<url>`", "`<name>`", "`<summary>`", "`<pain"):
        assert placeholder not in text, f"unfilled placeholder {placeholder!r}"


def test_render_brief_quotes_the_suggested_offer(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed(settings)

    path = render_brief(settings=settings, theme="client reporting", output_dir=tmp_path / "out")
    text = path.read_text()
    assert "$399" in text


def test_brief_cli_writes_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    _seed(settings)
    monkeypatch.setenv("DATABASE_PATH", str(settings.database_path))
    monkeypatch.setenv("REPORTS_DIR", str(settings.reports_dir))
    out_dir = tmp_path / "cli_briefs"

    result = CliRunner().invoke(
        app,
        ["brief", "--theme", "client reporting", "--output-dir", str(out_dir)],
    )
    assert result.exit_code == 0, result.stdout
    assert any(out_dir.glob("*.md"))


def test_render_brief_handles_case_insensitive_theme_lookup(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed(settings, theme="client reporting")

    path = render_brief(
        settings=settings, theme="Client Reporting", output_dir=tmp_path / "out"
    )
    assert path.exists()


def test_render_brief_writes_one_file_per_invocation(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed(settings)
    out_dir = tmp_path / "out"

    render_brief(settings=settings, theme="client reporting", output_dir=out_dir)
    files_after_first = sorted(out_dir.glob("*.md"))
    render_brief(settings=settings, theme="client reporting", output_dir=out_dir)
    files_after_second = sorted(out_dir.glob("*.md"))

    assert len(files_after_first) == 1
    # Same theme -> same filename, so it stays at 1 file (overwrite is fine).
    assert len(files_after_second) == 1


def test_render_brief_db_evidence_count(tmp_path: Path) -> None:
    """Sanity: more signals → more evidence URLs in the brief."""
    settings = _settings(tmp_path)
    _seed(settings, num_posts=6)
    path = render_brief(settings=settings, theme="client reporting", output_dir=tmp_path / "out")
    text = path.read_text()

    urls = re.findall(r"https?://reddit\.com/\S+", text)
    # 6 posts + 3 competitor-comment urls → at least 6 URLs surfaced
    assert len(set(urls)) >= 6


def test_render_brief_db_row_counts_match(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed(settings)
    conn = sqlite3.connect(settings.database_path)
    (post_count,) = conn.execute("SELECT COUNT(*) FROM reddit_posts").fetchone()
    (signal_count,) = conn.execute("SELECT COUNT(*) FROM signals").fetchone()
    conn.close()
    assert post_count == 6
    assert signal_count == 9
