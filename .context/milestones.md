# Demand Radar — Milestones

Broader chunks of work that, together, get us to the goal in [goal.md](goal.md).

**Ordered. Do not skip ahead.** Each milestone multiplies the value of the next. Skipping = wasted work.

## Status conventions

Each milestone has a `Status:` line that is the **single source of truth for progress**. The worker session (prompt #1 in [session_prompts.md](session_prompts.md)) updates it as criteria are satisfied. The `/loop` watchdog (prompt #2) reads these to determine current focus.

Possible values:

- `Not started`
- `In progress`
- `✓ Done (YYYY-MM-DD)`

The worker session always works on the **first milestone whose Status is not `✓ Done`**.

---

## M1 — `collect-watchlist` CLI

**Status:** In progress

**Output:** one command that politely loops the 48-row watchlist via the `public_json` backend, dedupes by Reddit id, and writes signals.

**Done when:**
- `demand-radar collect-watchlist [--since 7d] [--limit 50]` exists.
- Loops the watchlist in order, sleeps ≥ 2 s between subreddits.
- Re-running is idempotent (dedupe works).
- Tests cover the loop and a 429 backoff path.
- A real run finishes in < 5 minutes for 48 subs × 25 posts.

**Why:** V1 success criteria require evidence from ≥ 4 subreddits per opportunity. The current per-sub CLI is too slow for that.

---

## M2 — Opportunity persistence + validation_status

**Status:** Not started

**Output:** the `opportunities` table is actually populated (currently dead schema), with stable hash keys and a `validation_status` column the user can update via CLI.

**Done when:**
- `save_opportunities()` exists and is called from the report flow.
- Stable hash key over (`pain_theme` + top `buyer_role` + top `tool`).
- `demand-radar status --opportunity <id> --set pursuing|parked|rejected` works.
- Re-running the report doesn't duplicate opportunities.
- Status survives between runs.

**Why:** Briefs need a stable identity to attach evidence to over time. Today opportunities are throwaway.

---

## M3 — LLM classification via Claude Code subagents (Sonnet)

**Status:** Not started

**Output:** a parallel subagent fan-out classifies batches of posts/comments. Each subagent returns Pydantic-validated `Signal` rows with verbatim buyer quotes, named tools, and 1–5 scores.

**Done when:**
- A new `LLMClassifier` lives behind the same interface as the rule-based extractor.
- Spawns N Claude Code Agent subagents in parallel (Agent tool, **`model="sonnet"` — locked**; see "Model choice" below).
- Each subagent receives a batch of posts/comments + the structured-output schema, and returns JSON conforming to the Pydantic `Signal` model.
- Old rule-based path remains the default when `LLM_PROVIDER=none`.
- Tests use recorded subagent responses (no live LLM calls in CI).
- Manual eyeball on 50 fixtures: LLM precision visibly beats rules on edge cases like sarcasm, negation, and implicit competitor mentions.

**Why:** Rule-based filter is ~70% accurate. LLM classification is the single biggest signal-quality unlock. Subagent fan-out parallelizes across batches and runs inside the Claude Max subscription, so cost is bounded.

### Model choice — Sonnet is pinned. Do not change without an explicit decision.

| Model | Verdict | Reason |
|---|---|---|
| **`sonnet`** | ✅ **Required default for every classification subagent.** | Best instruction-following at acceptable cost. Reliable Pydantic-schema adherence. Fast enough for batch classification. |
| `haiku` | ❌ Do not use. | Cheaper, but fragile on negation, sarcasm, and implicit tool mentions — exactly the cases that make M3 worth doing. Using Haiku defeats the milestone's purpose. |
| `opus` | ❌ Do not use for batch classification. | Slower and more expensive without a quality win for this narrow task. Reserve Opus for one-shot reasoning calls (e.g. "which opportunity should I pursue this week?"). |

**Enforcement rules:**

- Every `Agent` tool call doing classification **must explicitly pass `model="sonnet"`**.
- Do **NOT** rely on the parent's model — it is Opus 4.7 by default in this environment, which is wasteful.
- Do **NOT** add a `LLM_MODEL` env var or runtime flag that allows downgrading to Haiku. If a future change needs to consider Haiku, it must amend this file first.

---

## M4 — `brief` bridge command (demand_radar → productionize_engine)

**Status:** Not started

**Output:** `demand-radar brief --theme "<name>"` reads the top opportunity row + its supporting posts/comments and renders the [productionize_engine/templates/opportunity_brief.md](../../productionize_engine/templates/opportunity_brief.md) template with real evidence URLs, verbatim buyer quotes, and a pre-filled scorecard.

**Done when:**
- One brief file is produced per invocation, written into `productionize_engine/briefs/`.
- Real URLs, real quotes, real tools — no placeholders left in.
- Scorecard pre-filled by the system from the underlying signals (user can adjust).
- A brief produced for any seeded theme reads as something a human would actually act on.

**Why:** This is the demand_radar → productionize_engine seam. Without it, the pipeline ends in CSV and the brief step stays manual.

---

## M5 — First real brief, hand-reviewed (= V1 goal met)

**Status:** Not started

**Output:** a single brief in `productionize_engine/briefs/` that scores ≥ 35 / 45 and I would actually send outreach against.

**Done when:**
- The brief satisfies every criterion in [goal.md](goal.md) V1 success.
- I've read it end-to-end and either:
  - **(a) passes** → escalate to outreach (out of scope for demand_radar)
  - **(b) fails** → write down why in `.context/lessons.md`, tune, re-run

**Why:** This is the goal. Everything before this is enabling work. Everything after this is acceleration.

---

## Deferred — do NOT pick these up until M5 is met

- **M6 — Hacker News as second source.** Algolia HN Search API, free, unauthenticated. Adds a different audience (more technical founders, "Show HN" complaints, "Ask HN: best tool for X" threads).
- **M7 — G2 / Capterra review scraping.** Direct competitor complaints, structured by category. Heavier to build. Only worth it after Reddit + HN saturate.
- **M8 — Theme clustering with embeddings.** Cosine clustering over Anthropic/OpenAI embeddings to collapse "client reporting / weekly client updates / agency reports" into one theme. Needs ≥ 500 signals first or it's noise.
- **Persistent ranked subreddits export** (`ranked_subreddits.csv`) — schema exists but unused. Nice-to-have; not blocking the brief.

If any of these feels urgent before M5 is done, that's drift. Re-read [goal.md](goal.md).
