"""Opportunity identity and persistence.

`opportunity_key` is the stable hash over (pain_theme + top buyer_role + top tool)
that gives an opportunity a durable identity across report runs.

`save_opportunities` upserts: insert if the key is new, otherwise refresh the
mutable fields (score, tools, suggested_offer) while preserving the user-owned
`validation_status` column.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterable

from demand_radar.db import utc_now


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def opportunity_key(
    *,
    pain_theme: str,
    top_buyer_role: str | None,
    top_tool: str | None,
) -> str:
    """SHA-1 (truncated) over the normalized (theme, role, tool) tuple."""
    payload = f"{_norm(pain_theme)}|{_norm(top_buyer_role)}|{_norm(top_tool)}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def save_opportunities(
    conn: sqlite3.Connection,
    opportunities: Iterable[dict],
) -> int:
    """Upsert opportunities by `key`. Preserves existing `validation_status`.

    Returns the number of newly inserted rows. Re-running with the same keys
    is a no-op for the validation_status column; score/tools/offer are
    refreshed.
    """
    inserted = 0
    for opp in opportunities:
        key = opp["key"]
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO opportunities
            (key, opportunity_name, target_buyer, pain_theme, current_workaround,
             tools_mentioned, score, suggested_offer, mvp_angle, validation_status,
             created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'unvalidated', ?)
            """,
            (
                key,
                opp.get("opportunity_name") or opp["pain_theme"],
                opp.get("target_buyer"),
                opp["pain_theme"],
                opp.get("current_workaround"),
                opp.get("tools_mentioned"),
                opp.get("score", 0),
                opp.get("suggested_offer"),
                opp.get("mvp_angle"),
                utc_now(),
            ),
        )
        inserted += cur.rowcount
        conn.execute(
            """
            UPDATE opportunities
               SET score = ?,
                   tools_mentioned = ?,
                   suggested_offer = ?,
                   target_buyer = COALESCE(?, target_buyer),
                   pain_theme = ?,
                   opportunity_name = ?
             WHERE key = ?
            """,
            (
                opp.get("score", 0),
                opp.get("tools_mentioned"),
                opp.get("suggested_offer"),
                opp.get("target_buyer"),
                opp["pain_theme"],
                opp.get("opportunity_name") or opp["pain_theme"],
                key,
            ),
        )
    conn.commit()
    return inserted
