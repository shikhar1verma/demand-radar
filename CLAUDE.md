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

## Working method — test-driven development

Every milestone in `.context/milestones.md` is shipped via TDD with CI as
the gate. Short version:

1. Read the milestone's "Done when" checklist.
2. Write failing tests that encode those criteria. Commit them.
3. Implement the smallest thing that makes one test pass. Commit. Push.
4. Repeat until all Done-when bullets have passing tests.
5. CI must stay green. Red CI = stop everything and fix it first.

Exceptions (no test-first required): doc-only commits, lint/style/typing
fixes with no behaviour change, throwaway research spikes.

See `.context/workflow.md` for full rationale and anti-patterns.

## Code standards

- Python 3.11+.
- Use Typer for CLI.
- Use Pydantic for structured models.
- Use sqlite3 for V1 database.
- Keep modules small.
- Avoid global mutable state.
- Make network calls replaceable/mocked.
- Tests must not require live Reddit credentials.
- No live LLM calls in tests — use recorded subagent responses as fixtures.

## Sub-agent rules (Claude Code Agent tool)

When spawning Claude Code Agent subagents inside this project:

- **Classification, extraction, or structured-output work** (the M3 LLM
  classifier and anything similar): **always pass `model="sonnet"`**
  explicitly on every `Agent` call. Do not rely on the parent's model — it
  defaults to Opus, which is wasteful for batch classification.
- **`model="haiku"`** is **not allowed** for classification. It is too
  fragile on negation, sarcasm, and implicit tool mentions, which are the
  exact cases the LLM classifier exists to catch.
- **`model="opus"`** only for one-shot high-stakes reasoning (e.g.
  "which opportunity should I pursue this week?"). Never for batch work.
- Do not introduce a runtime flag or env var that allows downgrading the
  classification model to Haiku. If a future change needs to revisit this,
  it must amend `.context/milestones.md` (M3 → Model choice) first.

See `.context/milestones.md` (M3 → Model choice) for the full rationale.

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
