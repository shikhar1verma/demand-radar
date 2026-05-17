# Product Spec: Demand Radar

## One-line description

Demand Radar is a local research engine that turns Reddit conversations into ranked SaaS opportunities.

## User

Primary user:

```text
A builder/founder who wants to find real market pain before building a SaaS product.
```

Secondary user:

```text
A copywriter, marketer, or product strategist looking for voice-of-customer signals and painful workflows.
```

## Core job

Help the user answer:

```text
What are people repeatedly struggling with?
What tools do they already use or complain about?
Is there enough market signal to validate a paid offer?
```

## V1 inputs

- Reddit API credentials.
- Subreddit watchlist.
- Keyword list.
- Optional tool/company names.
- Optional buyer personas.

## V1 outputs

- `ranked_subreddits.csv`
- `daily_signals.md`
- `opportunities.csv`
- `tools_mentioned.csv`

## Signal types

```text
Pain signal
Buying intent
Competitor dissatisfaction
Manual workaround
Alternative request
Feature request
Pricing complaint
Existing paid tool mention
Recurring workflow
```

## Opportunity scoring

```text
Opportunity Score =
Pain Frequency
+ Buying Intent
+ Manual Workaround
+ Competitor Dissatisfaction
+ Clear Buyer
+ Existing Spend
+ Urgency
+ Easy First Version
+ Easy Distribution
- Build Complexity
- Market Saturation
- Trust Risk
```

Each factor should be scored 1 to 5 in V1.

## V1 success criteria

Demand Radar is useful when it can produce:

```text
10 clear opportunities from 20 to 50 subreddits
with evidence links, tools mentioned, pain summary, and suggested first offer.
```
