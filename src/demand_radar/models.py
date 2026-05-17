from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SignalType(StrEnum):
    PAIN = "pain_signal"
    BUYING_INTENT = "buying_intent"
    COMPETITOR_DISSATISFACTION = "competitor_dissatisfaction"
    MANUAL_WORKAROUND = "manual_workaround"
    ALTERNATIVE_REQUEST = "alternative_request"
    FEATURE_REQUEST = "feature_request"
    PRICING_COMPLAINT = "pricing_complaint"
    TOOL_MENTION = "tool_mention"
    RECURRING_WORKFLOW = "recurring_workflow"


class RedditPost(BaseModel):
    id: str
    subreddit: str
    title: str
    body: str = ""
    author: str | None = None
    score: int = 0
    comment_count: int = 0
    url: str | None = None
    permalink: str | None = None
    created_utc: int


class RedditComment(BaseModel):
    id: str
    post_id: str
    subreddit: str
    body: str
    author: str | None = None
    score: int = 0
    created_utc: int


class Signal(BaseModel):
    source_type: str
    source_id: str
    subreddit: str
    signal_type: SignalType
    pain_theme: str | None = None
    buyer_role: str | None = None
    industry: str | None = None
    tools_mentioned: list[str] = Field(default_factory=list)
    buying_intent_score: int = 0
    urgency_score: int = 0
    competitor_complaint_score: int = 0
    manual_workaround_score: int = 0
    summary: str
    evidence_url: str | None = None


class Opportunity(BaseModel):
    opportunity_name: str
    target_buyer: str
    pain_theme: str
    current_workaround: str | None = None
    tools_mentioned: list[str] = Field(default_factory=list)
    score: int
    suggested_offer: str
    mvp_angle: str
    validation_status: str = "unvalidated"
    evidence: list[dict[str, Any]] = Field(default_factory=list)
