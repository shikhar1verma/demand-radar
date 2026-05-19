"""LLM classification via Claude Code subagent fan-out.

The classifier wraps the round-trip between a batch of posts/comments and a
Pydantic-validated list of `Signal` rows. The actual subagent invocation is
delegated to an injected callable so tests can use recorded responses and
production code can wire a real `Agent(...)` call from a Claude Code session.

**Model is locked to Sonnet.** See `.context/milestones.md` M3 for rationale.
Every `Agent` tool invocation that wires `subagent_call` MUST pass
`model="sonnet"` explicitly. Do not use Haiku — it is too fragile on negation
and sarcasm, which are the exact cases the classifier exists to catch. Do not
use Opus for batch classification — slower and pricier without a quality win.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel, ValidationError

from demand_radar.config import Settings
from demand_radar.models import Signal, SignalType


class LLMClassifyItem(BaseModel):
    source_type: str
    source_id: str
    subreddit: str
    text: str
    evidence_url: str | None = None


class LLMClassifyRequest(BaseModel):
    batch_id: str
    items: list[LLMClassifyItem]


class LLMClassifyResponse(BaseModel):
    signals: list[Signal]


SubagentCall = Callable[[LLMClassifyRequest], str]


_PROMPT_TEMPLATE = """\
You are a market-signal classification subagent.

For each input item below, emit zero or more Signal records as JSON. The
response MUST be a single JSON object of the form:

  {{"signals": [<Signal>, ...]}}

Each Signal object has these fields:

- source_type, source_id, subreddit, evidence_url: copy from the input item
- signal_type: one of {signal_types}
- pain_theme: short noun phrase describing the underlying workflow pain
- buyer_role: who is feeling the pain (e.g. agency_owner, sales, ops, founder)
- industry: optional sector tag
- tools_mentioned: list of canonical tool names actually referenced
- buying_intent_score, urgency_score, competitor_complaint_score,
  manual_workaround_score: integers 1-5 reflecting how strongly the item
  conveys each dimension. Use 1 for "not at all", 5 for "explicit and urgent"
- summary: 200-char tight summary of the signal in the author's own words

Be precise about negation and sarcasm. "I LOVE wasting hours every week
debugging this" is sarcasm and signals competitor_dissatisfaction, not praise.
"I do NOT want another all-in-one PM tool" is a buying_intent for a narrow
solution, not noise.

Pydantic Signal schema:
{schema}

ITEMS:
{items_json}
"""


def build_subagent_prompt(request: LLMClassifyRequest) -> str:
    signal_types = [t.value for t in SignalType]
    schema = json.dumps(Signal.model_json_schema(), indent=2)
    items_json = json.dumps(
        [item.model_dump() for item in request.items], indent=2, ensure_ascii=False
    )
    return _PROMPT_TEMPLATE.format(
        signal_types=", ".join(signal_types),
        schema=schema,
        items_json=items_json,
    )


class LLMClassifier:
    """Batches items, fans out to subagents in parallel, parses Pydantic Signals."""

    def __init__(
        self,
        *,
        subagent_call: SubagentCall,
        batch_size: int = 10,
        max_workers: int = 4,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        if max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        self.subagent_call = subagent_call
        self.batch_size = batch_size
        self.max_workers = max_workers

    def classify(self, items: Iterable[LLMClassifyItem]) -> list[Signal]:
        batch_list = list(self._batch(list(items)))
        if not batch_list:
            return []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            raw_responses = list(pool.map(self.subagent_call, batch_list))
        signals: list[Signal] = []
        for raw in raw_responses:
            try:
                parsed = LLMClassifyResponse.model_validate_json(raw)
            except (ValidationError, ValueError) as exc:
                raise ValueError(f"subagent returned malformed response: {raw!r}") from exc
            signals.extend(parsed.signals)
        return signals

    def _batch(self, items: list[LLMClassifyItem]):
        for i in range(0, len(items), self.batch_size):
            chunk = items[i : i + self.batch_size]
            yield LLMClassifyRequest(batch_id=f"batch_{i:04d}", items=chunk)


def get_classifier(
    settings: Settings,
    subagent_call: SubagentCall | None = None,
) -> LLMClassifier | None:
    """Return an LLMClassifier when configured + wired, else None.

    None signals "use the rule-based extractor". Production callers that set
    `LLM_PROVIDER=subagent` must also pass `subagent_call` for an actual
    classifier to be returned; otherwise the rule-based fallback is used so the
    pipeline keeps producing output.
    """
    provider = settings.llm_provider
    if provider == "none":
        return None
    if provider == "subagent":
        if subagent_call is None:
            return None
        return LLMClassifier(subagent_call=subagent_call)
    raise ValueError(f"unknown LLM_PROVIDER: {provider!r}")
