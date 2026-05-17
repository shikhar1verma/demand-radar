from demand_radar.filters import is_relevant_post, relevance_score


def test_relevant_post_from_tool_question():
    assert is_relevant_post("What tool do you use for client reporting?")


def test_relevant_post_from_manual_workaround():
    assert relevance_score("Still using spreadsheets for onboarding", "This takes hours") >= 2


def test_irrelevant_post():
    assert not is_relevant_post("Look at my new logo", "Just sharing a fun design", 0)
