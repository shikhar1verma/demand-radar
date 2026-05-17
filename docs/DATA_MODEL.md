# Data Model

## Tables

### subreddits

Tracks the watchlist and subreddit quality.

```text
id
name
category
audience
is_active
activity_score
noise_score
buyer_quality_score
last_scanned_at
created_at
```

### reddit_posts

Stores post metadata and body.

```text
id
subreddit
title
body
author
score
comment_count
url
permalink
created_utc
scraped_at
```

### reddit_comments

Stores selected comments from relevant posts.

```text
id
post_id
subreddit
body
author
score
created_utc
scraped_at
```

### signals

Stores derived market signals.

```text
id
source_type
source_id
subreddit
signal_type
pain_theme
buyer_role
industry
tools_mentioned
buying_intent_score
urgency_score
competitor_complaint_score
manual_workaround_score
summary
evidence_url
created_at
```

### opportunities

Stores clustered/scored opportunities.

```text
id
opportunity_name
target_buyer
pain_theme
current_workaround
tools_mentioned
score
suggested_offer
mvp_angle
validation_status
created_at
```
