import re

from demand_radar.filters import (
    BUYING_INTENT_PHRASES,
    COMPETITOR_COMPLAINT_PHRASES,
    MANUAL_WORKAROUND_PHRASES,
    count_matches,
)
from demand_radar.models import Signal, SignalType

KNOWN_TOOLS = [
    "HubSpot",
    "Salesforce",
    "Notion",
    "Airtable",
    "Zapier",
    "Make",
    "ClickUp",
    "Asana",
    "Monday",
    "Slack",
    "Shopify",
    "WordPress",
    "Webflow",
    "Looker Studio",
    "AgencyAnalytics",
    "DashThis",
    "Supermetrics",
    "Databox",
    "Google Sheets",
    "Excel",
    "Calendly",
    "Apollo",
    "Clay",
    "Pipedrive",
    "Linear",
    "Jira",
    "Trello",
]


def extract_tools(text: str) -> list[str]:
    found = []
    for tool in KNOWN_TOOLS:
        pattern = r"\b" + re.escape(tool.lower()) + r"\b"
        if re.search(pattern, text.lower()):
            found.append(tool)
    return sorted(set(found))


def infer_signal_type(text: str) -> SignalType:
    low = text.lower()
    if "alternative to" in low or "alternative for" in low:
        return SignalType.ALTERNATIVE_REQUEST
    if count_matches(low, COMPETITOR_COMPLAINT_PHRASES):
        return SignalType.COMPETITOR_DISSATISFACTION
    if count_matches(low, BUYING_INTENT_PHRASES):
        return SignalType.BUYING_INTENT
    if count_matches(low, MANUAL_WORKAROUND_PHRASES):
        return SignalType.MANUAL_WORKAROUND
    if extract_tools(low):
        return SignalType.TOOL_MENTION
    return SignalType.PAIN


def simple_pain_theme(text: str) -> str:
    low = text.lower()
    if "report" in low or "dashboard" in low:
        return "reporting and dashboards"
    if "crm" in low or "lead" in low or "sales" in low:
        return "sales and lead management"
    if "onboarding" in low:
        return "onboarding workflow"
    if "recruit" in low or "candidate" in low or "hiring" in low:
        return "recruiting operations"
    if "shopify" in low or "ecommerce" in low or "refund" in low or "return" in low:
        return "ecommerce operations"
    if "spreadsheet" in low or "google sheet" in low or "excel" in low:
        return "spreadsheet workflow"
    return "uncategorized workflow pain"


def extract_signal_from_text(
    *,
    source_type: str,
    source_id: str,
    subreddit: str,
    text: str,
    evidence_url: str | None = None,
) -> Signal:
    signal_type = infer_signal_type(text)
    tools = extract_tools(text)
    buying = min(5, count_matches(text, BUYING_INTENT_PHRASES) * 2)
    manual = min(5, count_matches(text, MANUAL_WORKAROUND_PHRASES) * 2)
    complaint = min(5, count_matches(text, COMPETITOR_COMPLAINT_PHRASES) * 2)
    urgency = 1
    if any(word in text.lower() for word in ["urgent", "asap", "daily", "weekly", "every week"]):
        urgency = 4

    summary = text.strip().replace("\n", " ")[:280]

    return Signal(
        source_type=source_type,
        source_id=source_id,
        subreddit=subreddit,
        signal_type=signal_type,
        pain_theme=simple_pain_theme(text),
        tools_mentioned=tools,
        buying_intent_score=buying,
        urgency_score=urgency,
        competitor_complaint_score=complaint,
        manual_workaround_score=manual,
        summary=summary,
        evidence_url=evidence_url,
    )
