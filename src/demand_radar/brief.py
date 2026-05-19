"""Render a productionize-ready opportunity brief from stored signals + opportunity.

Reads the most-recent opportunity row for a given pain theme and joins it with
its supporting posts/comments to fill the
`productionize_engine/templates/opportunity_brief.md` template with real
evidence — URLs, verbatim buyer quotes, named competitor weaknesses, and a
scorecard pre-filled from the underlying signal scores.

Outputs a single Markdown file per invocation into the configured briefs dir.
"""

from __future__ import annotations

import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from demand_radar import db
from demand_radar.config import Settings


class BriefNotAvailable(RuntimeError):
    """No opportunity stored for the requested theme — run `report` first."""


_SCORE_FLOOR = 1
_SCORE_CEILING = 5


def _clamp(value: int) -> int:
    return max(_SCORE_FLOOR, min(_SCORE_CEILING, value))


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "opportunity"


def _verbatim_for_signal(conn: sqlite3.Connection, signal_row: sqlite3.Row) -> str | None:
    if signal_row["source_type"] == "post":
        post = conn.execute(
            "SELECT title, body FROM reddit_posts WHERE id = ?",
            (signal_row["source_id"],),
        ).fetchone()
        if post is None:
            return None
        body = (post["body"] or "").strip()
        title = (post["title"] or "").strip()
        if body and title and title.rstrip(".") in body:
            return body
        if body and title:
            return f"{title} — {body}"
        return body or title or None
    if signal_row["source_type"] == "comment":
        comment = conn.execute(
            "SELECT body FROM reddit_comments WHERE id = ?",
            (signal_row["source_id"],),
        ).fetchone()
        if comment is None:
            return None
        return (comment["body"] or "").strip() or None
    return None


def _prefilled_scorecard(opp: sqlite3.Row, signals: list[sqlite3.Row]) -> dict[str, int]:
    frequency = len(signals)
    tools_set = set()
    intent_max = 1
    urgency_max = 1
    complaint_max = 1
    manual_max = 1
    for row in signals:
        tools_set.update(
            t.strip() for t in (row["tools_mentioned"] or "").split(",") if t.strip()
        )
        intent_max = max(intent_max, row["buying_intent_score"] or 1)
        urgency_max = max(urgency_max, row["urgency_score"] or 1)
        complaint_max = max(complaint_max, row["competitor_complaint_score"] or 1)
        manual_max = max(manual_max, row["manual_workaround_score"] or 1)

    return {
        "Pain frequency": _clamp(1 + frequency // 3),
        "Buyer clarity": 5 if opp["target_buyer"] else 3,
        "Existing spend": _clamp(2 + len(tools_set)),
        "Urgency": _clamp(urgency_max),
        "Reachability": 4,
        "Service-first": 5,
        "MVP simplicity": 3,
        "Recurring potential": 4 if intent_max >= 3 else 3,
        "Competition gap": _clamp(complaint_max),
    }


def render_brief(*, settings: Settings, theme: str, output_dir: Path) -> Path:
    db.init_db(settings.database_path)
    conn = db.connect(settings.database_path)
    try:
        opp = conn.execute(
            "SELECT * FROM opportunities WHERE LOWER(pain_theme) = LOWER(?) "
            "ORDER BY score DESC LIMIT 1",
            (theme,),
        ).fetchone()
        if opp is None:
            raise BriefNotAvailable(
                f"no opportunity stored for theme {theme!r}; run `demand-radar report` first"
            )

        signals = conn.execute(
            "SELECT * FROM signals WHERE LOWER(pain_theme) = LOWER(?) ORDER BY created_at",
            (theme,),
        ).fetchall()

        evidence_rows = []
        seen_urls: set[str] = set()
        for sig in signals:
            url = sig["evidence_url"] or ""
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            evidence_rows.append(
                {
                    "url": url,
                    "summary": (sig["summary"] or "").strip().replace("\n", " ")[:240],
                    "signal_type": sig["signal_type"],
                }
            )

        verbatim_quotes: list[str] = []
        seen_quotes: set[str] = set()
        for sig in signals:
            quote = _verbatim_for_signal(conn, sig)
            if not quote:
                continue
            stripped = quote.strip()
            if stripped in seen_quotes:
                continue
            seen_quotes.add(stripped)
            verbatim_quotes.append(stripped)
            if len(verbatim_quotes) >= 5:
                break

        tools_counter: Counter[str] = Counter()
        complaints_by_tool: dict[str, list[str]] = defaultdict(list)
        for sig in signals:
            for tool in (sig["tools_mentioned"] or "").split(","):
                tool = tool.strip()
                if not tool:
                    continue
                tools_counter[tool] += 1
                if sig["signal_type"] == "competitor_dissatisfaction":
                    complaint_text = (sig["summary"] or "").strip().replace("\n", " ")
                    if complaint_text:
                        complaints_by_tool[tool].append(complaint_text)

        named_weaknesses = []
        for tool, complaints in complaints_by_tool.items():
            named_weaknesses.append((tool, complaints[0]))
        if not named_weaknesses:
            for tool, _count in tools_counter.most_common(3):
                named_weaknesses.append(
                    (tool, "Frequently mentioned alongside this pain.")
                )

        scorecard = _prefilled_scorecard(opp, signals)
        total = sum(scorecard.values())

        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{_slugify(opp['pain_theme'] or theme)}.md"
        markdown = _render_markdown(
            opp, evidence_rows, verbatim_quotes, named_weaknesses, scorecard, total
        )
        out_path.write_text(markdown, encoding="utf-8")
        return out_path
    finally:
        conn.close()


def _render_markdown(
    opp: sqlite3.Row,
    evidence: list[dict],
    quotes: list[str],
    named_weaknesses: list[tuple[str, str]],
    scorecard: dict[str, int],
    total: int,
) -> str:
    lines: list[str] = []
    lines.append("# Opportunity Brief")
    lines.append("")
    lines.append("## Opportunity name")
    lines.append("")
    lines.append(opp["opportunity_name"] or opp["pain_theme"])
    lines.append("")
    lines.append("## Pain")
    lines.append("")
    lines.append(opp["pain_theme"] or "")
    lines.append("")
    lines.append("## Buyer")
    lines.append("")
    lines.append(opp["target_buyer"] or "unknown")
    lines.append("")
    lines.append("## Trigger")
    lines.append("")
    lines.append("Recurring weekly workflow under deadline pressure.")
    lines.append("")
    lines.append("## Current workaround")
    lines.append("")
    if quotes:
        lines.append(f"> {quotes[0]}")
    else:
        lines.append("No verbatim quote available.")
    lines.append("")
    lines.append("## Existing tools")
    lines.append("")
    for tool in (opp["tools_mentioned"] or "").split(","):
        tool = tool.strip()
        if tool:
            lines.append(f"- {tool}")
    if not (opp["tools_mentioned"] or "").strip():
        lines.append("- (none surfaced)")
    lines.append("")
    lines.append("## Competitor weaknesses")
    lines.append("")
    for tool, complaint in named_weaknesses[:5]:
        lines.append(f"- **{tool}** — {complaint}")
    if not named_weaknesses:
        lines.append("- (none surfaced)")
    lines.append("")
    lines.append("## Verbatim buyer quotes")
    lines.append("")
    for quote in quotes:
        lines.append(f"> {quote}")
        lines.append("")
    lines.append("## Reddit evidence")
    lines.append("")
    lines.append("| Source | Quote / summary | Signal type |")
    lines.append("|---|---|---|")
    for row in evidence:
        summary = row["summary"].replace("|", "\\|")
        lines.append(f"| {row['url']} | {summary} | {row['signal_type']} |")
    lines.append("")
    lines.append("## Smallest paid offer")
    lines.append("")
    lines.append(opp["suggested_offer"] or "(set offer in opportunities row)")
    lines.append("")
    lines.append("## Score")
    lines.append("")
    lines.append("| Criteria | Score |")
    lines.append("|---|---:|")
    for name, score in scorecard.items():
        lines.append(f"| {name} | {score} |")
    lines.append("")
    lines.append(f"Total: **{total}/45**")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append("Pursue / Park / Reject")
    lines.append("")
    lines.append("## Next 7 days")
    lines.append("")
    lines.append("- [ ] Send 5 outreach DMs to surfaced buyer persona")
    lines.append("- [ ] Validate the offer in 2 discovery calls")
    lines.append("- [ ] Decide pursue / park / reject")
    lines.append("")
    return "\n".join(lines)
