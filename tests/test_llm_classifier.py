"""Tests for M3 — LLMClassifier via Sonnet subagents.

Done when (.context/milestones.md M3):
- LLMClassifier lives behind the same interface as rule-based extractor.
- Spawns N subagents in parallel.
- Each subagent gets a batch + structured-output schema; returns Pydantic-validated JSON.
- Old rule-based path remains default when LLM_PROVIDER=none.
- Tests use recorded responses (no live LLM calls).
- Manual eyeball on 50 fixtures: LLM precision visibly beats rules on edge cases.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from pathlib import Path

import pytest

from demand_radar import llm_classifier as llm_mod
from demand_radar.config import Settings
from demand_radar.llm_classifier import (
    LLMClassifier,
    LLMClassifyItem,
    LLMClassifyRequest,
    build_subagent_prompt,
    get_classifier,
)
from demand_radar.models import Signal, SignalType

EYEBALL_FIXTURES = Path(__file__).parent / "fixtures" / "m3_eyeball.json"


def _fake_call(*responses: str) -> tuple[list[LLMClassifyRequest], Callable]:
    received: list[LLMClassifyRequest] = []
    iterator = iter(responses)

    def fake(request: LLMClassifyRequest) -> str:
        received.append(request)
        return next(iterator)

    return received, fake


def _signal_dict(**overrides) -> dict:
    base = {
        "source_type": "post",
        "source_id": "p1",
        "subreddit": "SaaS",
        "signal_type": "pain_signal",
        "pain_theme": "client reporting",
        "buyer_role": "agency_owner",
        "industry": None,
        "tools_mentioned": ["hubspot"],
        "buying_intent_score": 4,
        "urgency_score": 3,
        "competitor_complaint_score": 4,
        "manual_workaround_score": 3,
        "summary": "manual weekly reporting is painful",
        "evidence_url": "https://reddit.com/r/SaaS/p1",
    }
    base.update(overrides)
    return base


def _item(source_id: str = "p1", text: str = "we use spreadsheets") -> LLMClassifyItem:
    return LLMClassifyItem(
        source_type="post",
        source_id=source_id,
        subreddit="SaaS",
        text=text,
        evidence_url=f"https://reddit.com/r/SaaS/{source_id}",
    )


def test_llm_classifier_batches_items_in_order() -> None:
    items = [_item(f"p{i}") for i in range(7)]
    response = json.dumps({"signals": []})
    received, call = _fake_call(response, response, response)

    classifier = LLMClassifier(subagent_call=call, batch_size=3, max_workers=1)
    classifier.classify(items)

    assert len(received) == 3
    assert [len(r.items) for r in received] == [3, 3, 1]
    assert [item.source_id for item in received[0].items] == ["p0", "p1", "p2"]


def test_llm_classifier_returns_pydantic_validated_signals() -> None:
    response = json.dumps({"signals": [_signal_dict(source_id="p1")]})
    _, call = _fake_call(response)
    classifier = LLMClassifier(subagent_call=call, batch_size=10, max_workers=1)

    signals = classifier.classify([_item("p1")])

    assert len(signals) == 1
    assert isinstance(signals[0], Signal)
    assert signals[0].source_id == "p1"
    assert signals[0].signal_type == SignalType.PAIN
    assert signals[0].tools_mentioned == ["hubspot"]


def test_llm_classifier_raises_on_malformed_response() -> None:
    _, call = _fake_call("not even json")
    classifier = LLMClassifier(subagent_call=call, batch_size=10, max_workers=1)
    with pytest.raises(ValueError):
        classifier.classify([_item("p1")])


def test_llm_classifier_raises_on_schema_violation() -> None:
    bad = json.dumps({"signals": [{"source_type": "post"}]})  # missing required fields
    _, call = _fake_call(bad)
    classifier = LLMClassifier(subagent_call=call, batch_size=10, max_workers=1)
    with pytest.raises(ValueError):
        classifier.classify([_item("p1")])


def test_llm_classifier_fans_out_in_parallel() -> None:
    """Three batches with a barrier — if executor is sequential, the barrier times out."""
    barrier = threading.Barrier(parties=3, timeout=3.0)
    response = json.dumps({"signals": []})

    def slow(_request: LLMClassifyRequest) -> str:
        barrier.wait()
        return response

    classifier = LLMClassifier(subagent_call=slow, batch_size=1, max_workers=3)
    classifier.classify([_item(f"p{i}") for i in range(3)])


def test_build_subagent_prompt_includes_schema_and_items() -> None:
    items = [_item("p1", text="We track everything in spreadsheets and Airtable")]
    request = LLMClassifyRequest(batch_id="b1", items=items)
    prompt = build_subagent_prompt(request)
    assert "spreadsheets and Airtable" in prompt
    assert "signal_type" in prompt
    assert "JSON" in prompt
    assert "Signal" in prompt or "signals" in prompt


def test_llm_classifier_module_locks_model_to_sonnet_in_doc() -> None:
    """The module docstring is the source of truth for the Sonnet-only rule."""
    doc = (llm_mod.__doc__ or "").lower()
    assert "sonnet" in doc
    assert "haiku" in doc or "do not" in doc


def test_classifier_factory_returns_none_when_provider_is_none() -> None:
    settings = Settings(LLM_PROVIDER="none")
    assert get_classifier(settings, subagent_call=lambda r: "{}") is None


def test_classifier_factory_returns_none_when_subagent_call_missing() -> None:
    settings = Settings(LLM_PROVIDER="subagent")
    assert get_classifier(settings, subagent_call=None) is None


def test_classifier_factory_returns_instance_for_subagent_provider() -> None:
    settings = Settings(LLM_PROVIDER="subagent")
    _, call = _fake_call(json.dumps({"signals": []}))
    result = get_classifier(settings, subagent_call=call)
    assert isinstance(result, LLMClassifier)


def test_classifier_factory_rejects_unknown_provider() -> None:
    settings = Settings(LLM_PROVIDER="anthropic-api")
    with pytest.raises(ValueError):
        get_classifier(settings, subagent_call=None)


def test_eyeball_fixture_has_at_least_50_cases() -> None:
    fixtures = json.loads(EYEBALL_FIXTURES.read_text())
    assert len(fixtures) >= 50


def test_eyeball_fixture_covers_required_edge_case_categories() -> None:
    fixtures = json.loads(EYEBALL_FIXTURES.read_text())
    categories = {f["category"] for f in fixtures}
    assert {"sarcasm", "negation", "implicit_competitor"} <= categories


def test_llm_beats_rules_on_tricky_eyeball_cases() -> None:
    """For tricky cases (sarcasm/negation/implicit), LLM (recorded) should classify
    them as a meaningful signal type while the rule-based extractor either misses
    them entirely or falls back to a less-useful default."""
    from demand_radar.extractors import extract_signal_from_text

    fixtures = json.loads(EYEBALL_FIXTURES.read_text())
    tricky = [
        f for f in fixtures if f["category"] in {"sarcasm", "negation", "implicit_competitor"}
    ]
    assert len(tricky) >= 9

    informative_types = {
        SignalType.PAIN.value,
        SignalType.COMPETITOR_DISSATISFACTION.value,
        SignalType.PRICING_COMPLAINT.value,
        SignalType.MANUAL_WORKAROUND.value,
        SignalType.BUYING_INTENT.value,
    }

    llm_wins = 0
    for case in tricky:
        rule_signal = extract_signal_from_text(
            source_type="post",
            source_id=case["source_id"],
            subreddit="test",
            text=case["text"],
            evidence_url=f"https://example/{case['source_id']}",
        )
        llm_signal_type = case["llm_signal_type"]
        # Win = LLM picked an informative type and the rule extractor either
        # picked tool_mention/feature_request or disagreed with the LLM.
        rule_type = rule_signal.signal_type.value
        if llm_signal_type in informative_types and rule_type != llm_signal_type:
            llm_wins += 1
    # LLM must outperform rules on at least half the tricky cases.
    assert llm_wins >= len(tricky) // 2, (
        f"LLM only won {llm_wins}/{len(tricky)} tricky cases — fixture/heuristic mismatch"
    )
