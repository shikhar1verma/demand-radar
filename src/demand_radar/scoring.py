from dataclasses import dataclass


@dataclass(frozen=True)
class OpportunityFactors:
    pain_frequency: int = 1
    buying_intent: int = 1
    manual_workaround: int = 1
    competitor_dissatisfaction: int = 1
    clear_buyer: int = 1
    existing_spend: int = 1
    urgency: int = 1
    easy_first_version: int = 1
    easy_distribution: int = 1
    build_complexity: int = 1
    market_saturation: int = 1
    trust_risk: int = 1


def clamp(value: int, low: int = 1, high: int = 5) -> int:
    return max(low, min(high, value))


def opportunity_score(factors: OpportunityFactors) -> int:
    positive = (
        clamp(factors.pain_frequency)
        + clamp(factors.buying_intent)
        + clamp(factors.manual_workaround)
        + clamp(factors.competitor_dissatisfaction)
        + clamp(factors.clear_buyer)
        + clamp(factors.existing_spend)
        + clamp(factors.urgency)
        + clamp(factors.easy_first_version)
        + clamp(factors.easy_distribution)
    )
    negative = (
        clamp(factors.build_complexity)
        + clamp(factors.market_saturation)
        + clamp(factors.trust_risk)
    )
    return positive - negative


def score_from_signal_counts(
    *,
    frequency: int,
    buying_intent_score: int,
    manual_workaround_score: int,
    complaint_score: int,
    tool_count: int,
) -> int:
    factors = OpportunityFactors(
        pain_frequency=clamp(1 + frequency // 5),
        buying_intent=clamp(buying_intent_score),
        manual_workaround=clamp(manual_workaround_score),
        competitor_dissatisfaction=clamp(complaint_score),
        existing_spend=clamp(1 + tool_count),
        clear_buyer=3,
        urgency=3,
        easy_first_version=3,
        easy_distribution=3,
        build_complexity=2,
        market_saturation=2,
        trust_risk=2,
    )
    return opportunity_score(factors)
