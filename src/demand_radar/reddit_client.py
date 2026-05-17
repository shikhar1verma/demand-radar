from __future__ import annotations

import time

from demand_radar.backends import PrawBackend, PublicJsonBackend, RedditBackend
from demand_radar.config import Settings


def get_backend(settings: Settings) -> RedditBackend:
    """Return the Reddit backend selected by REDDIT_BACKEND."""
    if settings.reddit_backend == "praw":
        return PrawBackend(settings)
    if settings.reddit_backend == "public_json":
        return PublicJsonBackend(settings)
    raise ValueError(
        f"Unknown REDDIT_BACKEND: {settings.reddit_backend!r}. "
        "Use 'praw' or 'public_json'."
    )


def polite_sleep(seconds: float = 1.0) -> None:
    time.sleep(seconds)
