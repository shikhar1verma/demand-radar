"""Tests for M2 — opportunity persistence + validation_status.

Done when (.context/milestones.md M2):
- save_opportunities() exists and is called from the report flow.
- Stable hash key over (pain_theme + top buyer_role + top tool).
- demand-radar status --opportunity <id> --set pursuing|parked|rejected works.
- Re-running the report doesn't duplicate opportunities.
- Status survives between runs.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from demand_radar import db
from demand_radar.cli import app
from demand_radar.config import Settings
from demand_radar.models import Signal, SignalType
from demand_radar.opportunities import opportunity_key, save_opportunities
from demand_radar.reports import generate_report


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        DATABASE_PATH=tmp_path / "test.sqlite3",
        REPORTS_DIR=tmp_path / "reports",
    )


def _seed_signal(
    settings: Settings,
    *,
    source_id: str = "abc",
    pain_theme: str = "client reporting",
    buyer_role: str = "agency_owner",
    tool: str = "hubspot",
) -> None:
    conn = db.connect(settings.database_path)
    signal = Signal(
        source_type="post",
        source_id=source_id,
        subreddit="agency",
        signal_type=SignalType.PAIN,
        pain_theme=pain_theme,
        buyer_role=buyer_role,
        industry=None,
        tools_mentioned=[tool],
        buying_intent_score=4,
        urgency_score=3,
        competitor_complaint_score=4,
        manual_workaround_score=3,
        summary="manual reporting takes hours",
        evidence_url=f"https://reddit.com/r/agency/{source_id}",
    )
    db.save_signals(conn, [signal])
    conn.close()


def _opp(
    pain_theme: str = "client reporting",
    buyer_role: str = "agency_owner",
    tool: str = "hubspot",
    score: int = 25,
) -> dict:
    return {
        "key": opportunity_key(pain_theme=pain_theme, top_buyer_role=buyer_role, top_tool=tool),
        "opportunity_name": pain_theme,
        "pain_theme": pain_theme,
        "target_buyer": buyer_role,
        "tools_mentioned": tool,
        "score": score,
        "suggested_offer": "Done-for-you weekly reporting",
        "current_workaround": None,
        "mvp_angle": None,
    }


def test_opportunity_key_is_stable_across_calls() -> None:
    k1 = opportunity_key(
        pain_theme="reporting", top_buyer_role="agency_owner", top_tool="hubspot"
    )
    k2 = opportunity_key(
        pain_theme="reporting", top_buyer_role="agency_owner", top_tool="hubspot"
    )
    assert k1 == k2
    assert isinstance(k1, str)
    assert len(k1) >= 8


def test_opportunity_key_is_case_insensitive_and_trimmed() -> None:
    k1 = opportunity_key(
        pain_theme="Reporting", top_buyer_role="Agency_Owner", top_tool="HubSpot"
    )
    k2 = opportunity_key(
        pain_theme=" reporting ", top_buyer_role=" agency_owner ", top_tool="hubspot"
    )
    assert k1 == k2


def test_opportunity_key_differs_per_dimension() -> None:
    base = opportunity_key(
        pain_theme="reporting", top_buyer_role="agency", top_tool="hubspot"
    )
    diff_theme = opportunity_key(
        pain_theme="onboarding", top_buyer_role="agency", top_tool="hubspot"
    )
    diff_role = opportunity_key(
        pain_theme="reporting", top_buyer_role="founder", top_tool="hubspot"
    )
    diff_tool = opportunity_key(
        pain_theme="reporting", top_buyer_role="agency", top_tool="airtable"
    )
    assert len({base, diff_theme, diff_role, diff_tool}) == 4


def test_opportunity_key_handles_missing_role_and_tool() -> None:
    k1 = opportunity_key(pain_theme="reporting", top_buyer_role=None, top_tool=None)
    k2 = opportunity_key(pain_theme="reporting", top_buyer_role=None, top_tool=None)
    assert k1 == k2


def test_save_opportunities_dedupes_by_key(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    db.init_db(settings.database_path)
    conn = db.connect(settings.database_path)

    save_opportunities(conn, [_opp()])
    save_opportunities(conn, [_opp()])

    (count,) = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()
    conn.close()
    assert count == 1


def test_save_opportunities_preserves_validation_status_on_reinsert(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    db.init_db(settings.database_path)
    conn = db.connect(settings.database_path)

    initial = _opp(score=20)
    save_opportunities(conn, [initial])
    conn.execute(
        "UPDATE opportunities SET validation_status='pursuing' WHERE key=?",
        (initial["key"],),
    )
    conn.commit()

    refreshed = _opp(score=35)
    save_opportunities(conn, [refreshed])

    row = conn.execute(
        "SELECT score, validation_status FROM opportunities WHERE key=?",
        (initial["key"],),
    ).fetchone()
    conn.close()
    assert row["score"] == 35
    assert row["validation_status"] == "pursuing"


def test_generate_report_persists_opportunities(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    db.init_db(settings.database_path)
    _seed_signal(settings, source_id="s1")

    generate_report(settings, days=30)

    conn = sqlite3.connect(settings.database_path)
    (count,) = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()
    rows = conn.execute(
        "SELECT key, pain_theme, target_buyer, tools_mentioned FROM opportunities"
    ).fetchall()
    conn.close()
    assert count >= 1
    assert rows[0][0] is not None  # key is set
    assert rows[0][1] == "client reporting"


def test_generate_report_is_idempotent_on_opportunities(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    db.init_db(settings.database_path)
    _seed_signal(settings, source_id="s1")

    generate_report(settings, days=30)
    conn = sqlite3.connect(settings.database_path)
    (after_first,) = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()
    conn.close()

    generate_report(settings, days=30)
    conn = sqlite3.connect(settings.database_path)
    (after_second,) = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()
    conn.close()

    assert after_first == after_second
    assert after_first >= 1


def test_status_cli_sets_validation_status_by_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    db.init_db(settings.database_path)
    conn = db.connect(settings.database_path)
    opp = _opp()
    save_opportunities(conn, [opp])
    conn.close()

    monkeypatch.setenv("DATABASE_PATH", str(settings.database_path))
    monkeypatch.setenv("REPORTS_DIR", str(settings.reports_dir))

    result = CliRunner().invoke(
        app, ["status", "--opportunity", opp["key"], "--set", "pursuing"]
    )
    assert result.exit_code == 0, result.stdout

    row = sqlite3.connect(settings.database_path).execute(
        "SELECT validation_status FROM opportunities WHERE key=?", (opp["key"],)
    ).fetchone()
    assert row[0] == "pursuing"


def test_status_cli_sets_validation_status_by_numeric_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    db.init_db(settings.database_path)
    conn = db.connect(settings.database_path)
    opp = _opp()
    save_opportunities(conn, [opp])
    (opp_id,) = conn.execute(
        "SELECT id FROM opportunities WHERE key=?", (opp["key"],)
    ).fetchone()
    conn.close()

    monkeypatch.setenv("DATABASE_PATH", str(settings.database_path))
    monkeypatch.setenv("REPORTS_DIR", str(settings.reports_dir))

    result = CliRunner().invoke(
        app, ["status", "--opportunity", str(opp_id), "--set", "parked"]
    )
    assert result.exit_code == 0, result.stdout

    row = sqlite3.connect(settings.database_path).execute(
        "SELECT validation_status FROM opportunities WHERE id=?", (opp_id,)
    ).fetchone()
    assert row[0] == "parked"


def test_status_cli_rejects_invalid_status_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    db.init_db(settings.database_path)
    monkeypatch.setenv("DATABASE_PATH", str(settings.database_path))
    monkeypatch.setenv("REPORTS_DIR", str(settings.reports_dir))

    result = CliRunner().invoke(
        app, ["status", "--opportunity", "anykey", "--set", "yolo"]
    )
    assert result.exit_code != 0


def test_status_survives_between_runs(tmp_path: Path) -> None:
    """Setting status, closing the connection, and re-opening shows the same status."""
    settings = _settings(tmp_path)
    db.init_db(settings.database_path)

    conn = db.connect(settings.database_path)
    opp = _opp()
    save_opportunities(conn, [opp])
    conn.execute(
        "UPDATE opportunities SET validation_status='rejected' WHERE key=?",
        (opp["key"],),
    )
    conn.commit()
    conn.close()

    conn2 = db.connect(settings.database_path)
    row = conn2.execute(
        "SELECT validation_status FROM opportunities WHERE key=?", (opp["key"],)
    ).fetchone()
    conn2.close()
    assert row["validation_status"] == "rejected"
