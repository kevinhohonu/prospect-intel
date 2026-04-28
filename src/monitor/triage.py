"""Claude rubric-guided triage.

Per DECISIONS.md (2026-04-27): qualitative SURFACE / WORTH_NOTING / SKIP call,
informed by structured rubric scores, with reasoning saved for audit.

Uses prompt caching on the system prompt — same rubric across ~80 calls/day means
the cache cuts cost and latency substantially after the first call.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import yaml
from anthropic import Anthropic

from src.monitor.candidate import Candidate

LOG = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 600
VALID_CLASSIFICATIONS = {"SURFACE", "WORTH_NOTING", "SKIP"}


@dataclass
class TriageResult:
    classification: str
    scores: dict[str, int] = field(default_factory=dict)
    disqualifiers: list[str] = field(default_factory=list)
    reasoning: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _build_system_prompt(rubric: dict) -> str:
    return (
        "You are a triage assistant for Hohonu's prospect intelligence monitor. "
        "Evaluate each candidate opportunity against the rubric and return strict JSON.\n\n"
        f"COMPANY CONTEXT:\n{rubric['company_context']}\n\n"
        f"ACTIVE MARKETS:\n"
        f"  Tier 1 (existing footprint): {rubric['active_markets']['tier_1_active']}\n"
        f"  Tier 2 (expansion targets):  {rubric['active_markets']['tier_2_expansion']}\n\n"
        f"RUBRIC:\n{yaml.safe_dump(rubric['rubric'], sort_keys=False)}\n"
        f"AUTO-DISQUALIFIERS:\n" + "\n".join(f"  - {d}" for d in rubric['auto_disqualifiers']) + "\n\n"
        f"CLASSIFICATION GUIDANCE:\n{rubric['classification_guidance']}\n\n"
        f"COMPETITORS:\n"
        f"  Established: {rubric['competitors']['established']}\n"
        f"  Newer entrants: {rubric['competitors']['newer_entrants']}\n"
        f"  {rubric['competitors']['treatment']}\n\n"
        "OUTPUT FORMAT — return ONLY a single JSON object, no prose, no code fences:\n"
        '{\n'
        '  "classification": "SURFACE" | "WORTH_NOTING" | "SKIP",\n'
        '  "scores": {"topic": 0-4, "buyer": 0-3, "geography": 0-2, "actionability": 0-1, "boosters": 0-1},\n'
        '  "disqualifiers": ["..."],\n'
        '  "reasoning": "1-2 sentences"\n'
        '}\n'
    )


def _build_user_prompt(c: Candidate) -> str:
    return (
        f"Source: {c.source}\n"
        f"Title: {c.title}\n"
        f"Posted: {c.posted_date}\n"
        f"Deadline: {c.deadline or 'n/a'}\n"
        f"Query/keyword: {c.query or 'n/a'}\n"
        f"Snippet: {c.snippet}\n"
        f"URL: {c.url}\n"
    )


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse(text: str) -> TriageResult:
    m = _JSON_RE.search(text)
    if not m:
        return TriageResult(classification="SKIP", error=f"no JSON found in response: {text[:200]}")
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return TriageResult(classification="SKIP", error=f"invalid JSON: {e}")

    classification = data.get("classification", "SKIP")
    if classification not in VALID_CLASSIFICATIONS:
        return TriageResult(classification="SKIP", error=f"invalid classification: {classification}")

    return TriageResult(
        classification=classification,
        scores=data.get("scores", {}),
        disqualifiers=data.get("disqualifiers", []),
        reasoning=data.get("reasoning", ""),
    )


class Triager:
    def __init__(self, api_key: str, rubric_path: Path):
        self.client = Anthropic(api_key=api_key)
        with rubric_path.open() as f:
            rubric = yaml.safe_load(f)
        self._system = _build_system_prompt(rubric)

    def triage(self, candidate: Candidate) -> TriageResult:
        try:
            resp = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": self._system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": _build_user_prompt(candidate)}],
            )
        except Exception as e:
            LOG.warning("triage API call failed for %r: %s", candidate.title[:60], e)
            return TriageResult(classification="SKIP", error=f"api error: {e}")

        text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
        return _parse(text)
