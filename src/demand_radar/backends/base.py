from __future__ import annotations

from typing import Protocol

from demand_radar.models import RedditComment, RedditPost


class RedditBackend(Protocol):
    """Read-only Reddit data source."""

    def fetch_new_posts(self, subreddit_name: str, limit: int = 100) -> list[RedditPost]: ...

    def fetch_top_level_comments(
        self, subreddit_name: str, post_id: str, limit: int = 50
    ) -> list[RedditComment]: ...
