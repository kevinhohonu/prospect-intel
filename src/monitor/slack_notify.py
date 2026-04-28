"""Slack incoming webhook posting.

SURFACE       → full block-formatted post.
WORTH_NOTING  → single-line post in the same channel.
SKIP          → not posted (audit-log only).
"""
from __future__ import annotations

import logging

import requests

from src.monitor.candidate import Candidate
from src.monitor.triage import TriageResult

LOG = logging.getLogger(__name__)


def _surface_blocks(c: Candidate, t: TriageResult) -> list[dict]:
    deadline = f" · deadline {c.deadline}" if c.deadline else ""
    score_line = (
        f"topic {t.scores.get('topic', '?')}/4 · "
        f"buyer {t.scores.get('buyer', '?')}/3 · "
        f"geo {t.scores.get('geography', '?')}/2 · "
        f"actionable {t.scores.get('actionability', '?')}/1"
    )
    if t.scores.get("boosters"):
        score_line += f" · +{t.scores['boosters']} booster"

    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*<{c.url}|{c.title}>*\n_{c.source} · posted {c.posted_date}{deadline}_",
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f">{t.reasoning}"},
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": score_line}],
        },
    ]


def _worth_noting_text(c: Candidate, t: TriageResult) -> str:
    return f"_worth noting_ · <{c.url}|{c.title}> ({c.source}) — {t.reasoning}"


def post(webhook_url: str, candidate: Candidate, triage: TriageResult) -> bool:
    if triage.classification == "SKIP":
        return False

    if triage.classification == "SURFACE":
        payload = {"blocks": _surface_blocks(candidate, triage)}
    else:  # WORTH_NOTING
        payload = {"text": _worth_noting_text(candidate, triage)}

    try:
        resp = requests.post(webhook_url, json=payload, timeout=15)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        LOG.warning("Slack post failed for %r: %s", candidate.title[:60], e)
        return False
