"""Self-contained static HTML analytics snapshot of the demand_radar DB.

Renders the collect -> classify -> score pipeline as a funnel plus signal-type,
theme, tool, and opportunity breakdowns. No JavaScript, no external assets: the
output file opens offline in any browser. Written alongside the Markdown and CSV
reports by `generate_report`.
"""

from __future__ import annotations

import html
import sqlite3
from collections import Counter
from datetime import UTC, datetime

from demand_radar import db
from demand_radar.config import Settings

_STYLE = """
body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;
  margin:2rem auto;max-width:880px;padding:0 1rem;color:#1a1a1a;line-height:1.5}
h1{margin-bottom:0}.sub{color:#666;margin-top:.25rem;font-size:.9rem}
h2{margin-top:2.2rem;border-bottom:2px solid #eee;padding-bottom:.3rem;font-size:1.15rem}
table{border-collapse:collapse;width:100%;margin-top:.5rem;font-size:.92rem}
th,td{text-align:left;padding:.38rem .6rem;border-bottom:1px solid #eee}
th{color:#666;font-weight:600;font-size:.82rem;text-transform:uppercase;letter-spacing:.03em}
td.n{text-align:right;font-variant-numeric:tabular-nums;font-weight:600;white-space:nowrap}
td.bar-cell{width:46%}
.bar{background:#f0f0f0;border-radius:3px;height:13px;width:100%}
.fill{background:#3aa86b;height:13px;border-radius:3px;min-width:1px}
.empty{color:#999;font-style:italic}
"""


def _esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _bar(count: int, total: int) -> str:
    pct = round(100 * count / total) if total else 0
    return f'<div class="bar"><div class="fill" style="width:{pct}%"></div></div>'


def build_html_report(settings: Settings) -> str:
    """Return a self-contained HTML analytics snapshot of the database."""
    conn = db.connect(settings.database_path)
    try:
        return _render(conn, settings)
    finally:
        conn.close()


def _scalar(conn: sqlite3.Connection, sql: str) -> int:
    return int(conn.execute(sql).fetchone()[0])


def _render(conn: sqlite3.Connection, settings: Settings) -> str:
    n_subs = _scalar(conn, "SELECT COUNT(DISTINCT subreddit) FROM reddit_posts")
    n_posts = _scalar(conn, "SELECT COUNT(*) FROM reddit_posts")
    n_comments = _scalar(conn, "SELECT COUNT(*) FROM reddit_comments")
    n_signals = _scalar(conn, "SELECT COUNT(*) FROM signals")
    n_opps = _scalar(conn, "SELECT COUNT(*) FROM opportunities")

    funnel = [
        ("Subreddits collected", n_subs),
        ("Posts collected", n_posts),
        ("Comments collected", n_comments),
        ("Signals extracted", n_signals),
        ("Opportunities", n_opps),
    ]
    funnel_max = max((c for _, c in funnel), default=0) or 1

    types = conn.execute(
        "SELECT signal_type, COUNT(*) c FROM signals GROUP BY signal_type ORDER BY c DESC"
    ).fetchall()
    types_max = max((r["c"] for r in types), default=0) or 1

    themes = conn.execute(
        "SELECT pain_theme, COUNT(*) c, COUNT(DISTINCT subreddit) s "
        "FROM signals GROUP BY pain_theme ORDER BY c DESC LIMIT 12"
    ).fetchall()

    tool_counter: Counter[str] = Counter()
    for (raw,) in conn.execute("SELECT tools_mentioned FROM signals"):
        for tool in (raw or "").split(","):
            tool = tool.strip()
            if tool:
                tool_counter[tool] += 1

    opps = conn.execute(
        "SELECT pain_theme, target_buyer, score, validation_status "
        "FROM opportunities ORDER BY score DESC LIMIT 15"
    ).fetchall()

    top_signals = conn.execute(
        "SELECT subreddit, signal_type, pain_theme, summary, evidence_url, "
        "(buying_intent_score + urgency_score + competitor_complaint_score "
        " + manual_workaround_score) AS strength "
        "FROM signals ORDER BY strength DESC, id DESC LIMIT 40"
    ).fetchall()

    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    out: list[str] = []
    out.append("<!DOCTYPE html>")
    out.append('<html lang="en"><head><meta charset="utf-8">')
    out.append("<title>Demand Radar - Analytics Snapshot</title>")
    out.append(f"<style>{_STYLE}</style></head><body>")
    out.append("<h1>Demand Radar</h1>")
    out.append(
        f'<p class="sub">Analytics snapshot of '
        f"{_esc(settings.database_path)} &middot; generated {generated}</p>"
    )

    # Pipeline funnel
    out.append("<h2>Pipeline funnel</h2>")
    out.append("<table><tr><th>Stage</th><th>Count</th><th>Share</th></tr>")
    for label, count in funnel:
        out.append(
            f"<tr><td>{_esc(label)}</td>"
            f'<td class="n">{count}</td>'
            f'<td class="bar-cell">{_bar(count, funnel_max)}</td></tr>'
        )
    out.append("</table>")

    # Signal type mix
    out.append("<h2>Signal type mix</h2>")
    if types:
        out.append("<table><tr><th>Signal type</th><th>Count</th><th>Share</th></tr>")
        for row in types:
            out.append(
                f"<tr><td>{_esc(row['signal_type'])}</td>"
                f'<td class="n">{row["c"]}</td>'
                f'<td class="bar-cell">{_bar(row["c"], types_max)}</td></tr>'
            )
        out.append("</table>")
    else:
        out.append('<p class="empty">No signals yet.</p>')

    # Top pain themes
    out.append("<h2>Top pain themes</h2>")
    if themes:
        out.append("<table><tr><th>Theme</th><th>Signals</th><th>Subreddits</th></tr>")
        for row in themes:
            theme = row["pain_theme"] or "(uncategorized)"
            out.append(
                f"<tr><td>{_esc(theme)}</td>"
                f'<td class="n">{row["c"]}</td>'
                f'<td class="n">{row["s"]}</td></tr>'
            )
        out.append("</table>")
    else:
        out.append('<p class="empty">No themes yet.</p>')

    # Top tools
    out.append("<h2>Top tools mentioned</h2>")
    if tool_counter:
        tools_max = tool_counter.most_common(1)[0][1]
        out.append("<table><tr><th>Tool</th><th>Mentions</th><th>Share</th></tr>")
        for tool, count in tool_counter.most_common(15):
            out.append(
                f"<tr><td>{_esc(tool)}</td>"
                f'<td class="n">{count}</td>'
                f'<td class="bar-cell">{_bar(count, tools_max)}</td></tr>'
            )
        out.append("</table>")
    else:
        out.append('<p class="empty">No tools mentioned yet.</p>')

    # Opportunities
    out.append("<h2>Opportunities by score</h2>")
    if opps:
        out.append(
            "<table><tr><th>Theme</th><th>Buyer</th>"
            "<th>Score</th><th>Status</th></tr>"
        )
        for row in opps:
            out.append(
                f"<tr><td>{_esc(row['pain_theme'])}</td>"
                f"<td>{_esc(row['target_buyer'] or '-')}</td>"
                f'<td class="n">{_esc(row["score"])} / 45</td>'
                f"<td>{_esc(row['validation_status'])}</td></tr>"
            )
        out.append("</table>")
    else:
        out.append(
            '<p class="empty">No opportunities yet - run '
            "<code>demand-radar report</code>.</p>"
        )

    # Top signals (read individual signals + click through to evidence)
    out.append("<h2>Top signals by strength</h2>")
    if top_signals:
        out.append(
            "<table><tr><th>Subreddit</th><th>Type</th>"
            "<th>Theme</th><th>Summary</th><th>Evidence</th></tr>"
        )
        for row in top_signals:
            summary = (row["summary"] or "").strip().replace("\n", " ")
            if len(summary) > 180:
                summary = summary[:177] + "..."
            url = row["evidence_url"] or ""
            link = (
                f'<a href="{_esc(url)}">open</a>'
                if url.startswith(("http://", "https://"))
                else "-"
            )
            out.append(
                f"<tr><td>{_esc(row['subreddit'])}</td>"
                f"<td>{_esc(row['signal_type'])}</td>"
                f"<td>{_esc(row['pain_theme'])}</td>"
                f"<td>{_esc(summary)}</td>"
                f"<td>{link}</td></tr>"
            )
        out.append("</table>")
    else:
        out.append('<p class="empty">No signals yet.</p>')

    out.append("</body></html>")
    return "\n".join(out)
