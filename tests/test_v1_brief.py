"""Tests for M5 — first real brief, V1 success criteria.

Done when (.context/goal.md V1 success):
- >= 15 unique evidence URLs drawn from >= 4 different subreddits
- >= 3 verbatim buyer quotes
- >= 3 named competitor weaknesses tied to specific tools
- Drafted $299-$500 manual offer with a concrete weekly deliverable
- Scorecard total >= 35 / 45
- A buyer persona where I can plausibly find 100 prospects on LinkedIn / Clutch
"""

from __future__ import annotations

import re
from pathlib import Path

from demand_radar.config import Settings
from demand_radar.v1_brief_seed import COMPETITOR_COMMENTS, seed_and_render


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        DATABASE_PATH=tmp_path / "v1.sqlite3",
        REPORTS_DIR=tmp_path / "reports",
    )


def _brief_text(tmp_path: Path) -> str:
    path = seed_and_render(settings=_settings(tmp_path), output_dir=tmp_path / "briefs")
    return path.read_text()


def test_v1_brief_has_at_least_15_unique_evidence_urls(tmp_path: Path) -> None:
    text = _brief_text(tmp_path)
    urls = re.findall(r"https?://reddit\.com/\S+?(?=[\s|])", text)
    assert len(set(urls)) >= 15, f"expected >=15 unique URLs, got {len(set(urls))}"


def test_v1_brief_covers_at_least_4_subreddits(tmp_path: Path) -> None:
    text = _brief_text(tmp_path)
    matches = re.findall(r"reddit\.com/r/([A-Za-z0-9_]+)/", text)
    assert len(set(matches)) >= 4, f"expected >=4 subreddits, got {sorted(set(matches))}"


def test_v1_brief_has_at_least_3_verbatim_buyer_quotes(tmp_path: Path) -> None:
    text = _brief_text(tmp_path)
    quote_blocks = [line for line in text.splitlines() if line.startswith("> ")]
    assert len(quote_blocks) >= 3, f"expected >=3 quote blocks, got {len(quote_blocks)}"


def test_v1_brief_names_at_least_3_competitor_weaknesses(tmp_path: Path) -> None:
    text = _brief_text(tmp_path).lower()
    tool_hits = sum(1 for tool, _ in COMPETITOR_COMMENTS if tool in text)
    assert tool_hits >= 3, f"expected >=3 named competitors, hit {tool_hits}"


def test_v1_brief_drafted_offer_is_priced_in_target_range(tmp_path: Path) -> None:
    text = _brief_text(tmp_path)
    prices = [int(m) for m in re.findall(r"\$(\d{3,4})", text)]
    in_range = [p for p in prices if 299 <= p <= 500]
    assert in_range, f"no offer price in $299-$500 range, found {prices}"


def test_v1_brief_scorecard_total_is_at_least_35(tmp_path: Path) -> None:
    text = _brief_text(tmp_path)
    match = re.search(r"Total[:\s]*\**\s*(\d+)\s*/\s*45", text)
    assert match is not None, "no scorecard total found"
    total = int(match.group(1))
    assert total >= 35, f"scorecard total {total}/45 < 35"


def test_v1_brief_names_specific_buyer_persona(tmp_path: Path) -> None:
    """`target_buyer` must be a concrete role we can find on LinkedIn/Clutch, not blank."""
    text = _brief_text(tmp_path).lower()
    assert "agency" in text or "owner" in text or "founder" in text
    assert "unknown" not in text or "agency" in text


def test_v1_brief_writes_one_artifact_per_run(tmp_path: Path) -> None:
    out_dir = tmp_path / "briefs"
    seed_and_render(settings=_settings(tmp_path), output_dir=out_dir)
    files = list(out_dir.glob("*.md"))
    assert len(files) == 1
