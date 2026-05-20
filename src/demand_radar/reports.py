from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from demand_radar import db
from demand_radar.config import Settings
from demand_radar.html_report import build_html_report
from demand_radar.opportunities import opportunity_key, save_opportunities
from demand_radar.scoring import score_from_signal_counts


def generate_report(settings: Settings, days: int = 7) -> Path:
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    conn = db.connect(settings.database_path)

    rows = conn.execute(
        """
        SELECT * FROM signals
        WHERE datetime(created_at) >= datetime('now', ?)
        ORDER BY created_at DESC
        """,
        (f"-{days} days",),
    ).fetchall()

    by_theme = defaultdict(list)
    tool_counter: Counter[str] = Counter()
    signal_counter: Counter[str] = Counter()

    for row in rows:
        theme = row["pain_theme"] or "uncategorized"
        by_theme[theme].append(row)
        signal_counter[row["signal_type"]] += 1
        tools = [x.strip() for x in (row["tools_mentioned"] or "").split(",") if x.strip()]
        tool_counter.update(tools)

    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    markdown_path = settings.reports_dir / f"daily_signals_{stamp}.md"
    opportunities_csv = settings.reports_dir / f"opportunities_{stamp}.csv"
    tools_csv = settings.reports_dir / f"tools_mentioned_{stamp}.csv"

    opportunity_rows = []
    for theme, theme_rows in by_theme.items():
        frequency = len(theme_rows)
        buying = max([r["buying_intent_score"] for r in theme_rows] or [1])
        manual = max([r["manual_workaround_score"] for r in theme_rows] or [1])
        complaint = max([r["competitor_complaint_score"] for r in theme_rows] or [1])
        tools_counter: Counter[str] = Counter()
        roles_counter: Counter[str] = Counter()
        for r in theme_rows:
            tools_counter.update(
                [x.strip() for x in (r["tools_mentioned"] or "").split(",") if x.strip()]
            )
            role = r["buyer_role"]
            if role:
                roles_counter[role] += 1
        top_tool = tools_counter.most_common(1)[0][0] if tools_counter else None
        top_role = roles_counter.most_common(1)[0][0] if roles_counter else None
        tools_sorted = sorted(tools_counter)
        score = score_from_signal_counts(
            frequency=frequency,
            buying_intent_score=buying,
            manual_workaround_score=manual,
            complaint_score=complaint,
            tool_count=len(tools_sorted),
        )
        opportunity_rows.append(
            {
                "key": opportunity_key(
                    pain_theme=theme, top_buyer_role=top_role, top_tool=top_tool
                ),
                "opportunity_name": theme,
                "pain_theme": theme,
                "target_buyer": top_role,
                "frequency": frequency,
                "score": score,
                "tools_mentioned": ", ".join(tools_sorted),
                "suggested_offer": suggest_offer(theme),
            }
        )

    opportunity_rows.sort(key=lambda x: x["score"], reverse=True)

    save_opportunities(conn, opportunity_rows)

    with markdown_path.open("w", encoding="utf-8") as f:
        f.write("# Demand Radar Report\n\n")
        f.write(f"Window: last {days} days\n\n")
        f.write(f"Generated at: {datetime.now(UTC).isoformat()}\n\n")
        f.write("## Signal mix\n\n")
        for signal_type, count in signal_counter.most_common():
            f.write(f"- {signal_type}: {count}\n")
        f.write("\n## Top tools mentioned\n\n")
        for tool, count in tool_counter.most_common(20):
            f.write(f"- {tool}: {count}\n")
        f.write("\n## Top opportunities\n\n")
        for idx, opp in enumerate(opportunity_rows[:10], 1):
            f.write(f"### {idx}. {opp['pain_theme']}\n\n")
            f.write(f"Score: {opp['score']}\n\n")
            f.write(f"Frequency: {opp['frequency']}\n\n")
            f.write(f"Tools mentioned: {opp['tools_mentioned'] or 'None'}\n\n")
            f.write(f"Suggested offer: {opp['suggested_offer']}\n\n")
            example = by_theme[opp["pain_theme"]][0]
            f.write(f"Example: {example['summary']}\n\n")
            if example["evidence_url"]:
                f.write(f"Evidence: {example['evidence_url']}\n\n")

    with opportunities_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "key",
                "pain_theme",
                "target_buyer",
                "frequency",
                "score",
                "tools_mentioned",
                "suggested_offer",
            ],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(opportunity_rows)

    with tools_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["tool", "mentions"])
        writer.writeheader()
        for tool, mentions in tool_counter.most_common():
            writer.writerow({"tool": tool, "mentions": mentions})

    conn.close()

    html_path = markdown_path.with_suffix(".html")
    html_path.write_text(build_html_report(settings), encoding="utf-8")

    return markdown_path


def suggest_offer(theme: str) -> str:
    if "report" in theme:
        return "$399 done-for-you weekly client reporting automation pilot"
    if "sales" in theme:
        return "$499 lead follow-up + CRM cleanup automation pilot"
    if "recruit" in theme:
        return "$399 candidate follow-up workflow audit + automation pilot"
    if "ecommerce" in theme:
        return "$299 Shopify operations reconciliation audit"
    if "spreadsheet" in theme:
        return "$299 spreadsheet-to-automation cleanup service"
    return "$399 paid workflow audit + concierge automation pilot"
