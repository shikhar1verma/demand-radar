# Architecture Decisions

## 001: Local-first V1

Decision:
Use a local CLI and SQLite instead of a web dashboard.

Reason:
This ships faster, is easier to inspect, and avoids UI distraction.

## 002: Reddit API first

Decision:
Use Reddit API through PRAW for V1.

Reason:
API access is cleaner and safer than HTML scraping. The pipeline should respect rate limits and terms.

## 003: Selective comment fetching

Decision:
Fetch comments only for relevant posts.

Reason:
Most listings are noise. Filtering before comment fetch saves API calls and improves report quality.

## 004: Rule-based scoring first

Decision:
Use simple scoring before heavy LLM classification.

Reason:
Rules are cheaper, testable, and good enough for V1. LLM classification can be added behind an interface.

## 005: Pluggable Reddit backend with public-JSON default

Decision:
Introduce a `RedditBackend` protocol with two implementations: `PrawBackend`
(authenticated, via PRAW) and `PublicJsonBackend` (unauthenticated, via
`*.json` endpoints). Default to `public_json` so the tool runs without
Reddit credentials.

Reason:
As of 2026 Reddit gates new Data API script-app creation behind a manual
approval form that prioritises moderation use cases. Approval is slow and
uncertain. The public JSON endpoints accept the same identifying User-Agent,
return read-only listings, and unblock local research immediately. The PRAW
path stays in place behind the same interface so we can flip
`REDDIT_BACKEND=praw` once API access is granted.

Trade-offs:
- Public JSON rate limit is stricter (~10 req/min vs ~60 authed). Default
  inter-request sleep is 2 seconds.
- No PRAW conveniences (auto-throttling, comment-tree pagination via
  `replace_more`). Acceptable for V1 since we only need new listings and
  top-level comments.
- Backend swap is one env-var change. `Settings.require_reddit_credentials()`
  is only called by the PRAW backend; `public_json` works with no keys.
