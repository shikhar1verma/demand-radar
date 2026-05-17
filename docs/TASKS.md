# Task Board

## Foundation

- [ ] Confirm Python project installs locally.
- [ ] Add initial SQLite schema and `init-db` command.
- [ ] Add `.env` loading and settings validation.
- [ ] Add test fixtures for sample Reddit posts/comments.

## Reddit collection

- [ ] Implement PRAW client wrapper.
- [ ] Implement `collect --subreddit NAME --limit N`.
- [ ] Save posts with dedupe.
- [ ] Add keyword relevance filter.
- [ ] Fetch comments only for relevant posts.
- [ ] Add basic rate-limit friendly sleep/config.

## Signal extraction

- [ ] Extract pain keywords.
- [ ] Extract tool mentions.
- [ ] Classify signal type using rules.
- [ ] Add optional LLM classifier interface.
- [ ] Save signals to SQLite.

## Reports

- [ ] Generate daily Markdown report.
- [ ] Export `opportunities.csv`.
- [ ] Export `tools_mentioned.csv`.
- [ ] Export `ranked_subreddits.csv`.

## Production readiness for local V1

- [ ] Add tests for DB layer.
- [ ] Add tests for filters and scoring.
- [ ] Add README examples.
- [ ] Add sample watchlist.
- [ ] Add error handling for missing credentials.
