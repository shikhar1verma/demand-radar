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

## 006: Static HTML analytics report (post-V1)

Decision:
`generate_report` emits a self-contained static HTML file
(`reports/daily_signals_<ts>.html`) alongside the Markdown and CSV outputs. It
renders the collect -> classify -> score pipeline as a funnel plus signal-type,
theme, tool, opportunity, and top-signal breakdowns.

Reason:
V1's goal (one real brief) is met, and the owner asked for a way to see
analytics across pipeline stages and read individual signals. A static HTML
file serves this without standing up a server.

Constraints that keep it inside the spirit of decision 001 / the goal.md
anti-goal:
- No JavaScript, no external assets (inline `<style>`, CSS-only bars). Opens
  offline; nothing is hosted.
- It is a generated artifact, not an application — same lifecycle as the
  Markdown/CSV reports, regenerated each `report` run, git-ignored.
- All Reddit-sourced text is `html.escape`d to avoid HTML injection.

Not done (deliberately): no interactive filtering, no backend, no deployment.
If live filtering/drill-down is needed later, a local Streamlit app is the
next step up — but that is a separate, explicit decision.
