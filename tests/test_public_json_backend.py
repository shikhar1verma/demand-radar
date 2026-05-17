from __future__ import annotations

import httpx
import pytest

from demand_radar.backends.public_json import PublicJsonBackend, RedditApiError
from demand_radar.config import Settings


def _settings() -> Settings:
    return Settings(REDDIT_USER_AGENT="demand-radar-test/0.1 by u_test")


def _backend(handler) -> PublicJsonBackend:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(
        base_url="https://www.reddit.com",
        headers={"User-Agent": "demand-radar-test/0.1 by u_test"},
        transport=transport,
    )
    return PublicJsonBackend(_settings(), client=client, request_sleep_seconds=0.0)


def test_fetch_new_posts_parses_listing():
    payload = {
        "kind": "Listing",
        "data": {
            "children": [
                {
                    "kind": "t3",
                    "data": {
                        "id": "abc1",
                        "subreddit": "SaaS",
                        "title": "What tool do you use for client reporting?",
                        "selftext": "Still using spreadsheets and it takes hours.",
                        "author": "founder123",
                        "score": 42,
                        "num_comments": 11,
                        "url": "https://example.com",
                        "permalink": "/r/SaaS/comments/abc1/title/",
                        "created_utc": 1_700_000_000,
                    },
                },
                {"kind": "more", "data": {"id": "skip", "children": []}},
            ]
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/r/SaaS/new.json"
        assert request.headers["User-Agent"].startswith("demand-radar-test")
        return httpx.Response(200, json=payload)

    backend = _backend(handler)
    posts = backend.fetch_new_posts("SaaS", limit=25)

    assert len(posts) == 1
    post = posts[0]
    assert post.id == "abc1"
    assert post.subreddit == "SaaS"
    assert post.title.startswith("What tool")
    assert post.author == "founder123"
    assert post.permalink == "https://www.reddit.com/r/SaaS/comments/abc1/title/"
    assert post.created_utc == 1_700_000_000


def test_fetch_new_posts_handles_deleted_author():
    payload = {
        "kind": "Listing",
        "data": {
            "children": [
                {
                    "kind": "t3",
                    "data": {
                        "id": "x1",
                        "subreddit": "agency",
                        "title": "old post",
                        "selftext": "",
                        "author": "[deleted]",
                        "score": 0,
                        "num_comments": 0,
                        "permalink": "/r/agency/comments/x1/",
                        "created_utc": 1,
                    },
                }
            ]
        },
    }

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    posts = _backend(handler).fetch_new_posts("agency")
    assert posts[0].author is None


def test_fetch_top_level_comments_parses_second_listing():
    payload = [
        {"kind": "Listing", "data": {"children": [{"kind": "t3", "data": {"id": "abc1"}}]}},
        {
            "kind": "Listing",
            "data": {
                "children": [
                    {
                        "kind": "t1",
                        "data": {
                            "id": "c1",
                            "body": "We still use Google Sheets for this.",
                            "author": "ops_lead",
                            "score": 5,
                            "created_utc": 1_700_000_100,
                        },
                    },
                    {"kind": "more", "data": {"id": "skip"}},
                    {
                        "kind": "t1",
                        "data": {
                            "id": "c2",
                            "body": "Tried HubSpot, too expensive.",
                            "author": None,
                            "score": 2,
                            "created_utc": 1_700_000_200,
                        },
                    },
                ]
            },
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/comments/abc1.json"
        return httpx.Response(200, json=payload)

    comments = _backend(handler).fetch_top_level_comments("SaaS", "abc1", limit=10)

    assert [c.id for c in comments] == ["c1", "c2"]
    assert comments[0].post_id == "abc1"
    assert comments[0].subreddit == "SaaS"
    assert comments[1].author is None


def test_fetch_top_level_comments_respects_limit():
    comment_children = [
        {
            "kind": "t1",
            "data": {"id": f"c{i}", "body": f"comment {i}", "score": 0, "created_utc": i},
        }
        for i in range(10)
    ]
    payload = [
        {"kind": "Listing", "data": {"children": []}},
        {"kind": "Listing", "data": {"children": comment_children}},
    ]

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    comments = _backend(handler).fetch_top_level_comments("SaaS", "abc1", limit=3)
    assert len(comments) == 3


def test_non_success_raises_reddit_api_error():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="forbidden")

    backend = _backend(handler)
    with pytest.raises(RedditApiError) as exc:
        backend.fetch_new_posts("SaaS")
    assert "403" in str(exc.value)
