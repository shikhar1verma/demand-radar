from __future__ import annotations

import time
from typing import Any

import httpx

from demand_radar.config import Settings
from demand_radar.models import RedditComment, RedditPost

BASE_URL = "https://www.reddit.com"
DEFAULT_TIMEOUT = 30.0


class RedditApiError(RuntimeError):
    """Raised when the Reddit public JSON endpoint returns a non-success status."""


class PublicJsonBackend:
    """Unauthenticated Reddit backend using public *.json endpoints.

    Use this when you do not have OAuth credentials. Rate limit is stricter than
    the authenticated API (Reddit treats unauth traffic as ~10 requests/minute
    per IP), so keep request_sleep_seconds at >= 2.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.Client | None = None,
        request_sleep_seconds: float = 2.0,
    ):
        self._user_agent = settings.reddit_user_agent
        self._sleep = request_sleep_seconds
        self._client = client or httpx.Client(
            base_url=BASE_URL,
            headers={"User-Agent": self._user_agent},
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
        )

    def fetch_new_posts(self, subreddit_name: str, limit: int = 100) -> list[RedditPost]:
        payload = self._get_json(
            f"/r/{subreddit_name}/new.json",
            params={"limit": limit, "raw_json": 1},
        )
        children = payload.get("data", {}).get("children", [])
        return [_parse_post(child["data"]) for child in children if child.get("kind") == "t3"]

    def fetch_top_level_comments(
        self, subreddit_name: str, post_id: str, limit: int = 50
    ) -> list[RedditComment]:
        payload = self._get_json(
            f"/comments/{post_id}.json",
            params={"limit": limit, "depth": 1, "raw_json": 1},
        )
        if not isinstance(payload, list) or len(payload) < 2:
            return []
        children = payload[1].get("data", {}).get("children", [])
        comments: list[RedditComment] = []
        for child in children:
            if child.get("kind") != "t1":
                continue
            comments.append(_parse_comment(child["data"], post_id, subreddit_name))
            if len(comments) >= limit:
                break
        return comments

    def _get_json(self, path: str, params: dict[str, Any]) -> Any:
        response = self._client.get(path, params=params)
        if response.status_code == 429:
            time.sleep(max(self._sleep * 4, 10))
            response = self._client.get(path, params=params)
        if response.status_code >= 400:
            raise RedditApiError(
                f"Reddit returned {response.status_code} for {path}. "
                "Lower request rate or switch to authenticated PRAW backend."
            )
        time.sleep(self._sleep)
        return response.json()


def _author_name(raw: dict[str, Any]) -> str | None:
    name = raw.get("author")
    if not name or name in {"[deleted]", "[removed]"}:
        return None
    return str(name)


def _parse_post(raw: dict[str, Any]) -> RedditPost:
    permalink = raw.get("permalink") or ""
    return RedditPost(
        id=str(raw["id"]),
        subreddit=str(raw.get("subreddit") or ""),
        title=str(raw.get("title") or ""),
        body=str(raw.get("selftext") or ""),
        author=_author_name(raw),
        score=int(raw.get("score") or 0),
        comment_count=int(raw.get("num_comments") or 0),
        url=raw.get("url"),
        permalink=f"{BASE_URL}{permalink}" if permalink else None,
        created_utc=int(raw.get("created_utc") or 0),
    )


def _parse_comment(raw: dict[str, Any], post_id: str, subreddit_name: str) -> RedditComment:
    return RedditComment(
        id=str(raw["id"]),
        post_id=post_id,
        subreddit=subreddit_name,
        body=str(raw.get("body") or ""),
        author=_author_name(raw),
        score=int(raw.get("score") or 0),
        created_utc=int(raw.get("created_utc") or 0),
    )
