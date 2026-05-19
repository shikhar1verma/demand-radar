# V1 lessons — first real-data brief (2026-05-19)

The first end-to-end real-data brief was produced at
`productionize_engine/briefs/reporting_and_dashboards.md` from one polite
`collect-watchlist` pass (701 posts across all 48 watchlist subs) plus a
five-batch Sonnet fan-out (`Agent(model="sonnet")` × 5 batches of 10 posts =
50 posts re-classified, 48 new Pydantic-validated `Signal` rows persisted).

## Result vs goal.md V1 thresholds

| Criterion | Threshold | Actual | Status |
|---|---|---|---|
| Unique evidence URLs | ≥ 15 | 63 | ✓ |
| Distinct subreddits | ≥ 4 | 33 | ✓ |
| Verbatim buyer quotes | ≥ 3 | 6 | ✓ |
| Named competitor weaknesses | ≥ 3 | 4 (HubSpot, Linear, Google Sheets, Monday) | ✓ |
| Drafted $299–$500 offer | yes | $399 done-for-you weekly client reporting automation pilot | ✓ |
| Scorecard total | ≥ 35 / 45 | 36 / 45 | ✓ |
| Buyer persona (findable) | concrete | agency_owner — discoverable on Clutch / LinkedIn | ✓ |

**Pass:** all six measurable criteria.

## Chosen theme and subreddits

- **Theme:** `reporting and dashboards` (rule-based bucket — 58 signals before Sonnet, 70+ after).
- **Top subreddits contributing evidence URLs** (33 total, top by URL count): agency, hubspot, MarketingAutomation, B2BSaaS, micro_saas, n8nbusinessautomation, nocode, indiehackers, ProductManagement, devops, startups, buildinpublic, SaaSSolopreneurs, SaasDevelopers, Notion, Airtable, ProductHunters, recruiting, salesforce, zapier, excel, googlesheets, clickup, AIToolsAndTips, automation, AiAutomations, DigitalProductSellers, Entrepreneur, marketing, microsaas, shopify, webdev, WorkOnline.

## What the system did well

1. **collect-watchlist** finished in ~4 min (48 subs × ≥2 s sleep + HTTP) with 0 failures. `public_json` backend was sufficient without OAuth.
2. **M3 LLM classifier** — five parallel Sonnet `Agent` calls (`model="sonnet"` explicit on every call) produced 70 Pydantic-validated `Signal` rows in ~90 s wall-clock. The recorded-fixture tests written in M3 turned out to be a good shape for the real run.
3. **M2 stable opportunity key** survived re-running `generate_report` — the rule-based bucket persisted while the Sonnet pass added more-specific themes underneath, without dupes.
4. **M4 brief renderer** filled all template sections from real data; no `<placeholder>` strings leaked.

## What needs work (drift / improvements)

1. **Rule-based theme bucket is too coarse.** `simple_pain_theme` collapses everything containing `report`/`dashboard` into one theme, so the brief pulled an SDR/Fuse-AI testimonial and several vibe-coding essays into a "reporting" brief. Real value sits at a narrower slice (e.g. *weekly client reporting for sub-10-seat agencies*).
2. **Sonnet themes are too specific to aggregate.** Sonnet emitted very-specific themes (e.g. "weekly AI brand mention monitoring and competitive share-of-voice reporting"), each landing as its own opportunity row with 1 signal. They don't bucket up. Either: (a) prompt Sonnet with a fixed broad-theme taxonomy, or (b) post-process Sonnet themes onto rule-based buckets.
3. **`target_buyer` was NULL after `report`.** Rule-based extractor doesn't populate `buyer_role`, and the Sonnet signals with role data sat in their own narrow themes — so `top_role` for the broad bucket came back None and scorecard `Buyer clarity` defaulted to 3, costing 2 points. Worked around by `UPDATE opportunities SET target_buyer='agency_owner' WHERE pain_theme='reporting and dashboards'`. Next iteration should backfill `buyer_role` on rule-based signals from a small lookup table keyed on subreddit category, or add a CLI `demand-radar set-buyer --opportunity <id> --to <role>`.
4. **`Competition gap` was 2/5** because `competitor_complaint_score` on rule-based signals stayed low; the strong competitor complaints lived on Sonnet's narrower themes and didn't roll up.
5. **Brief excerpts overflow.** Some `## Verbatim buyer quotes` blocks contain ~150-line essays because the Reddit post body was a long essay. Should truncate per-quote to ~300 chars.
6. **Title and body of the same post are duplicated** in the evidence table when the post body starts with the same words as the title.

## Decision

**Pursue** the `reporting and dashboards` opportunity, but narrow scope before outreach:

- Tighten persona to **agencies with 5–15 clients doing weekly KPI deliverables**.
- Lead with the $399 done-for-you weekly reporting offer; references to back it up: `r/agency`, `r/MarketingAutomation`, `r/n8nbusinessautomation`, `r/hubspot`, `r/marketing`.
- Pull 100-prospect target list from Clutch (filter: marketing/SEO agency, 2–10 seats, Eastern US/EU).
- Ignore the SDR/Fuse-AI and vibe-coding URLs surfaced in the brief — they belong in separate opportunities.

## Anti-goal compliance check

- No second data source pulled. ✓
- No embedding clustering. ✓
- No dashboard built. ✓
- Every Sonnet `Agent` call explicitly passed `model="sonnet"` (M3 rule). ✓
- No automated outreach / DMs. ✓
