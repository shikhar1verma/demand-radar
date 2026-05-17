from __future__ import annotations

import praw

from demand_radar.config import Settings
from demand_radar.models import RedditComment, RedditPost


class PrawBackend:
    """Authenticated Reddit backend using PRAW."""

    def __init__(self, settings: Settings):
        settings.require_reddit_credentials()
        self._reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
        )

    def fetch_new_posts(self, subreddit_name: str, limit: int = 100) -> list[RedditPost]:
        subreddit = self._reddit.subreddit(subreddit_name)
        posts = []
        for post in subreddit.new(limit=limit):
            posts.append(
                RedditPost(
                    id=post.id,
                    subreddit=str(post.subreddit),
                    title=post.title,
                    body=post.selftext or "",
                    author=str(post.author) if post.author else None,
                    score=int(post.score or 0),
                    comment_count=int(post.num_comments or 0),
                    url=post.url,
                    permalink=f"https://www.reddit.com{post.permalink}",
                    created_utc=int(post.created_utc),
                )
            )
        return posts

    def fetch_top_level_comments(
        self, subreddit_name: str, post_id: str, limit: int = 50
    ) -> list[RedditComment]:
        submission = self._reddit.submission(id=post_id)
        submission.comments.replace_more(limit=0)
        comments = []
        for comment in list(submission.comments)[:limit]:
            comments.append(
                RedditComment(
                    id=comment.id,
                    post_id=post_id,
                    subreddit=subreddit_name,
                    body=comment.body or "",
                    author=str(comment.author) if comment.author else None,
                    score=int(comment.score or 0),
                    created_utc=int(comment.created_utc),
                )
            )
        return comments
