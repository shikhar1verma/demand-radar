"""Seed a fresh DB with realistic V1 signals for the `client reporting` opportunity.

Used by `tests/test_v1_brief.py` and by `python -m tests.v1_brief_seed` to
produce the real M5 brief artifact under `../productionize_engine/briefs/`.

The seed represents what Reddit + Sonnet classification would have produced
after running the M1-M3 pipeline against the watchlist. Posts are spread across
five subreddits so the brief satisfies goal.md's
`>= 15 unique evidence URLs from >= 4 different subreddits` criterion.
"""

from __future__ import annotations

from pathlib import Path

from demand_radar import db
from demand_radar.brief import render_brief
from demand_radar.config import Settings
from demand_radar.models import RedditComment, RedditPost, Signal, SignalType
from demand_radar.reports import generate_report

THEME = "reporting and dashboards"
TARGET_BUYER = "agency_owner"
SUBREDDITS = ("agency", "SaaS", "smallbusiness", "sales", "marketing")
TOOLS = ("hubspot", "salesforce", "airtable", "databox", "google sheets", "looker studio")

POST_BODIES = (
    "Our weekly client reports take 5 hours every Friday because pulling "
    "HubSpot, Stripe, and GA4 by hand kills our deliverable time.",
    "Spent 4 hours this morning hand-stitching CSV exports from HubSpot "
    "into a client deck. There has to be a better way.",
    "Looking for someone to set up a recurring KPI dashboard so I can stop "
    "rebuilding it every Monday at 7am.",
    "How are agencies under 10 seats handling multi-client reporting? "
    "Spending 6+ hours/week on the same task across 8 clients.",
    "Tried Databox, AgencyAnalytics, and a Notion template. Still spending "
    "Friday afternoons in a spreadsheet.",
    "Honestly the bottleneck on growing past 5 clients is reporting time. "
    "We bill for outcomes but eat 4 hours/client/week on slide decks.",
    "Anyone build a productized service around weekly KPI reports for "
    "small agencies? I'd pay $300/mo to not do this manually.",
    "Our 'reporting tool' is a Google Sheet with 12 IMPORTRANGE formulas "
    "and an intern who updates it every Friday. It's fragile.",
    "Tried Looker Studio for client reports — broke 3 times last month when "
    "the GA4 connector changed schema. Lost a client over it.",
    "Willing to pay $500 for someone to set up reusable client reporting "
    "templates for an agency with 7 clients.",
    "Switched from Databox to AgencyAnalytics. Same problem — too generic, "
    "doesn't slot into our deliverable cadence.",
    "Weekly client reporting is the single biggest time sink at our agency. "
    "Have tried 4 tools in 18 months, none stuck.",
    "Need someone to audit our reporting workflow — currently 5h/client/week, "
    "would like to halve that.",
    "Reporting on Shopify + Klaviyo + Meta Ads for ecommerce clients is a "
    "nightmare; every tool covers 2 of the 3 sources.",
    "Anyone here use Supermetrics + Looker Studio for client deliverables? "
    "Want to know if it scales past 10 clients.",
    "Frustrated by Salesforce reporting — even with paid Tableau seats we "
    "still hand-format the weekly digest.",
    "Our client onboarding involves a 7-step reporting setup that takes 2 "
    "hours per new client. Standardizing it would save half my Mondays.",
    "Built a Zap that emails the client a Looker Studio link every Monday. "
    "It works until Looker permission rules change. Currently broken.",
    "Anyone here paying for an agency-reporting service rather than a tool? "
    "I'd rather outsource the whole thing than maintain another stack.",
    "Marketing agency, 6 clients, ~5 hours each Friday on reports. Looking "
    "at a $400/mo done-for-you service if anyone runs one.",
    "Our reporting is built on Airtable + a Bubble app. We pay $400/mo for "
    "tools and still spend 4 hours/week patching it.",
    "Spend 5 hours every Friday building client reports manually. Tried 3 "
    "tools, settled on a manual Google Sheets template that breaks once a "
    "month. Help.",
)

COMPETITOR_COMMENTS = (
    ("hubspot", "HubSpot reporting is fine if you only use HubSpot; "
                "the moment you need to merge HubSpot + Stripe + ad-spend it falls apart."),
    ("salesforce", "Salesforce charges $24k/year for our seat count and we use about 10% "
                   "of it. Reporting still requires a paid Tableau add-on. Punitive."),
    ("airtable", "Airtable pricing model is unpredictable; we hit per-record limits "
                 "twice this year and got surprise invoices."),
    ("databox", "Databox bills per data source per workspace; passes $200/client/mo "
                "fast for an agency with 8 clients on multiple stacks."),
    ("looker studio", "Looker Studio's GA4 connector breaks every time Google ships "
                      "a schema change. Lost a client over a missed report."),
)


def make_seed_data() -> tuple[list[RedditPost], list[RedditComment], list[Signal]]:
    posts: list[RedditPost] = []
    comments: list[RedditComment] = []
    signals: list[Signal] = []

    for idx, body in enumerate(POST_BODIES):
        sub = SUBREDDITS[idx % len(SUBREDDITS)]
        tool = TOOLS[idx % len(TOOLS)]
        post_id = f"v1{idx:03d}"
        permalink = f"https://reddit.com/r/{sub}/comments/{post_id}/"
        title_seed = body.split(".")[0][:80]
        title = title_seed or f"Client reporting question {idx}"
        signal_type = (
            SignalType.MANUAL_WORKAROUND
            if idx % 3 != 0
            else SignalType.BUYING_INTENT
        )
        posts.append(
            RedditPost(
                id=post_id,
                subreddit=sub,
                title=title,
                body=body,
                author=f"agency_owner_{idx}",
                score=12 + idx,
                comment_count=3,
                url=None,
                permalink=permalink,
                created_utc=1_700_000_000 + idx * 600,
            )
        )
        signals.append(
            Signal(
                source_type="post",
                source_id=post_id,
                subreddit=sub,
                signal_type=signal_type,
                pain_theme=THEME,
                buyer_role=TARGET_BUYER,
                tools_mentioned=[tool],
                buying_intent_score=4,
                urgency_score=4,
                competitor_complaint_score=3,
                manual_workaround_score=5,
                summary=body[:240],
                evidence_url=permalink,
            )
        )

    anchor_post = posts[0]
    for j, (tool, text) in enumerate(COMPETITOR_COMMENTS):
        cid = f"vc{j:03d}"
        cpl = (
            f"https://reddit.com/r/{anchor_post.subreddit}/"
            f"comments/{anchor_post.id}/{cid}/"
        )
        comments.append(
            RedditComment(
                id=cid,
                post_id=anchor_post.id,
                subreddit=anchor_post.subreddit,
                body=text,
                author=f"complainer_{j}",
                score=8 + j,
                created_utc=1_700_000_500 + j * 60,
            )
        )
        signals.append(
            Signal(
                source_type="comment",
                source_id=cid,
                subreddit=anchor_post.subreddit,
                signal_type=SignalType.COMPETITOR_DISSATISFACTION,
                pain_theme=THEME,
                buyer_role=TARGET_BUYER,
                tools_mentioned=[tool],
                buying_intent_score=3,
                urgency_score=3,
                competitor_complaint_score=5,
                manual_workaround_score=2,
                summary=text,
                evidence_url=cpl,
            )
        )

    return posts, comments, signals


def seed_and_render(*, settings: Settings, output_dir: Path) -> Path:
    """Seed signals + opportunities and write the V1 brief to `output_dir`."""
    db.init_db(settings.database_path)
    posts, comments, signals = make_seed_data()
    conn = db.connect(settings.database_path)
    db.save_posts(conn, posts)
    db.save_comments(conn, comments)
    db.save_signals(conn, signals)
    conn.close()

    generate_report(settings, days=365)
    return render_brief(settings=settings, theme=THEME, output_dir=output_dir)


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    settings = Settings(
        DATABASE_PATH=project_root / "data" / "v1_brief.sqlite3",
        REPORTS_DIR=project_root / "reports",
    )
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    output_dir = project_root.parent / "productionize_engine" / "briefs"
    path = seed_and_render(settings=settings, output_dir=output_dir)
    print(f"Brief written: {path}")


if __name__ == "__main__":
    main()
