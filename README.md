# Demand Radar

Local Reddit ETL for SaaS opportunity discovery.

## V1 objective

Create a local tool that can:

```text
1. Discover and score useful subreddits.
2. Collect recent Reddit posts and selected comments.
3. Detect pain, buying intent, competitor complaints, manual workarounds, and tool mentions.
4. Cluster signals into opportunities.
5. Generate daily Markdown and CSV reports.
```

## Why local-first

- Faster to ship.
- Easier to inspect data.
- No dashboard distraction.
- Lower infra complexity.
- Good fit for Claude Code iterations.

## Initial commands

```bash
cp .env.example .env
uv sync
uv run demand-radar init-db
uv run demand-radar collect --subreddit SaaS --limit 25
uv run demand-radar report --days 7
```

## API access

Two backends are supported. Pick one with `REDDIT_BACKEND` in `.env`.

### Option A: `public_json` (default, no API keys)

Reddit's `*.json` endpoints work without authentication. Pros: zero setup,
unblocks research immediately. Cons: stricter rate limit (~10 req/min) and
Reddit can block heavy unauth scrapers, so keep the inter-request sleep at
2 seconds or higher.

Only this is required in `.env`:

```env
REDDIT_BACKEND=public_json
REDDIT_USER_AGENT=demand-radar-local/0.1 by u_yourusername
```

A custom, identifying User-Agent is mandatory — bland defaults
(`python-requests/x.y`) will get rate-limited or blocked.

### Option B: `praw` (authenticated, higher limit)

If you have an approved Reddit Data API script app, use PRAW for ~60
requests/min and tidier comment-tree handling. Create a script-type app at
https://www.reddit.com/prefs/apps (subject to Reddit's approval flow as of
2026), then set:

```env
REDDIT_BACKEND=praw
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=demand-radar-local/0.1 by u_yourusername
```

## Safe collection strategy

```text
1. Fetch subreddit listings.
2. Store post metadata.
3. Filter locally by keywords and metadata.
4. Fetch comments only for relevant posts.
5. Deduplicate by Reddit id.
6. Respect API rate limits.
```

Do not fetch every comment from every post.
