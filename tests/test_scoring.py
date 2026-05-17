from demand_radar.scoring import OpportunityFactors, opportunity_score


def test_opportunity_score_rewards_good_factors():
    score = opportunity_score(
        OpportunityFactors(
            pain_frequency=5,
            buying_intent=5,
            manual_workaround=5,
            competitor_dissatisfaction=4,
            clear_buyer=5,
            existing_spend=5,
            urgency=4,
            easy_first_version=4,
            easy_distribution=4,
            build_complexity=2,
            market_saturation=2,
            trust_risk=1,
        )
    )
    assert score >= 30
