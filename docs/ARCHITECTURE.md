# Architecture

## High-level pipeline

```text
Subreddit watchlist
        |
        v
Reddit collector
        |
        v
SQLite raw tables
        |
        v
Keyword pre-filter
        |
        v
Signal extractor
        |
        v
Opportunity scorer
        |
        v
Markdown and CSV reports
```

## Design principles

- Local-first.
- Incremental collection.
- Deduplicate by Reddit ids.
- Fetch comments selectively.
- Keep API usage modest.
- Store evidence links.
- Make LLM classification optional.

## Modules

```text
src/demand_radar/config.py       Environment and app settings
src/demand_radar/db.py           SQLite connection and schema
src/demand_radar/models.py       Pydantic/domain models
src/demand_radar/reddit_client.py Reddit API wrapper
src/demand_radar/collector.py    Collection orchestration
src/demand_radar/filters.py      Keyword and relevance filtering
src/demand_radar/extractors.py   Tool and pain signal extraction
src/demand_radar/scoring.py      Opportunity scoring
src/demand_radar/reports.py      Markdown and CSV reports
src/demand_radar/cli.py          Typer CLI
```

## Data flow

```text
collect command
  -> load settings
  -> open db
  -> fetch subreddit listing
  -> save posts
  -> filter posts locally
  -> fetch comments for relevant posts
  -> save comments
  -> extract signals
  -> save signals
```

## Report flow

```text
report command
  -> load posts/comments/signals from last N days
  -> aggregate by pain theme and tools
  -> score opportunities
  -> write Markdown report
  -> write CSV exports
```
