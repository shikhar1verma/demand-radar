"""Read the subreddit watchlist CSV.

The watchlist lives at `data/watchlist.csv`; column 1 is the subreddit name.
Order is preserved — the watchlist is meant to be looped top-to-bottom.
"""

from __future__ import annotations

import csv
from pathlib import Path

DEFAULT_WATCHLIST_PATH = Path("data/watchlist.csv")


def load_watchlist(path: Path | None = None) -> list[str]:
    """Return subreddit names from the CSV in file order, skipping blanks."""
    target = path or DEFAULT_WATCHLIST_PATH
    with open(target, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        names: list[str] = []
        for row in reader:
            name = (row.get("subreddit") or "").strip()
            if name:
                names.append(name)
    return names
