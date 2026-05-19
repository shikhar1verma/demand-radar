PAIN_KEYWORDS = [
    "what tool",
    "which tool",
    "any software",
    "software for",
    "alternative to",
    "too expensive",
    "manual",
    "spreadsheet",
    "google sheet",
    "excel",
    "how do you manage",
    "how are you managing",
    "workflow",
    "automation",
    "crm",
    "dashboard",
    "reporting",
    "client onboarding",
    "lead tracking",
    "integration",
    "zapier",
    "api",
    "waste time",
    "takes hours",
    "hate",
    "frustrated",
]

BUYING_INTENT_PHRASES = [
    "what tool do you use",
    "what software do you use",
    "any recommendations",
    "looking for a tool",
    "looking for software",
    "paid tool",
    "worth paying",
    "budget",
    "subscribe",
]

MANUAL_WORKAROUND_PHRASES = [
    "spreadsheet",
    "google sheet",
    "excel",
    "manual",
    "copy paste",
    "screenshots",
    "csv",
    "doing this by hand",
]

COMPETITOR_COMPLAINT_PHRASES = [
    "too expensive",
    "bloated",
    "hard to use",
    "missing feature",
    "doesn't support",
    "does not support",
    "bad support",
    "buggy",
    "slow",
]


def normalize(text: str | None) -> str:
    return (text or "").lower()


def relevance_score(title: str, body: str = "", comment_count: int = 0) -> int:
    text = normalize(f"{title}\n{body}")
    score = 0
    for phrase in PAIN_KEYWORDS:
        if phrase in text:
            score += 2
    if "?" in title:
        score += 1
    if comment_count >= 20:
        score += 1
    if comment_count >= 50:
        score += 2
    return score


def is_relevant_post(
    title: str, body: str = "", comment_count: int = 0, threshold: int = 2
) -> bool:
    return relevance_score(title, body, comment_count) >= threshold


def count_matches(text: str, phrases: list[str]) -> int:
    low = normalize(text)
    return sum(1 for phrase in phrases if phrase in low)
