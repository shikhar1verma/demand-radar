from demand_radar.extractors import extract_signal_from_text, extract_tools
from demand_radar.models import SignalType


def test_extract_tools():
    assert "HubSpot" in extract_tools("We use HubSpot but it is too expensive")


def test_alternative_request_signal():
    signal = extract_signal_from_text(
        source_type="post",
        source_id="abc",
        subreddit="SaaS",
        text="Any alternative to HubSpot for a small agency? It is too expensive.",
    )
    assert signal.signal_type == SignalType.ALTERNATIVE_REQUEST
    assert "HubSpot" in signal.tools_mentioned


def test_manual_workaround_signal():
    signal = extract_signal_from_text(
        source_type="post",
        source_id="abc",
        subreddit="agency",
        text="We still use Google Sheets and screenshots for weekly client reporting.",
    )
    assert signal.manual_workaround_score > 0
    assert signal.pain_theme == "reporting and dashboards"
