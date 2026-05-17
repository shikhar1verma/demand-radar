# Demand Radar Claude Guide

You are building a local-first Python ETL.

## Product goal

Demand Radar should produce this output:

```text
Top market pains this week
Top subreddits to monitor
Top tools mentioned
Top competitor complaints
Top SaaS opportunities to validate
Suggested manual offer for each opportunity
```

## V1 scope

In scope:

- Reddit API OAuth via PRAW.
- Subreddit watchlist.
- SQLite database.
- Post collector.
- Selective comment collector.
- Keyword signal filter.
- Tool mention extractor.
- Rule-based scoring.
- Optional LLM classifier interface.
- Markdown and CSV reports.
- CLI commands.
- Tests with mocked data.

Out of scope for V1:

- Web dashboard.
- User accounts.
- Team collaboration.
- Payment integration.
- Automated Reddit posting.
- Automated Reddit DMs.
- Large-scale scraping.

## Code standards

- Python 3.11+.
- Use Typer for CLI.
- Use Pydantic for structured models.
- Use sqlite3 for V1 database.
- Keep modules small.
- Avoid global mutable state.
- Make network calls replaceable/mocked.
- Tests must not require live Reddit credentials.

## Suggested issue order

1. Project setup and CLI skeleton.
2. SQLite schema and repositories.
3. Reddit settings and PRAW client.
4. Subreddit listing collector.
5. Post storage and dedupe.
6. Keyword filter.
7. Selective comment fetcher.
8. Signal extraction.
9. Opportunity scoring.
10. Report generator.
11. Tests and README polish.
