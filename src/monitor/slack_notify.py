"""Slack incoming webhook posting.

SURFACE       → full block-formatted post (one message each).
WORTH_NOTING  → batched into a single end-of-run digest message
                (chunked into multiple messages if too many items).
SKIP          → not posted (audit-log only).

Why digest WORTH_NOTING: a daily run can produce 200+ "worth noting" items.
Posting them individually floods the channel, hits Slack's ~1 msg/sec
webhook rate limit, and buries the SURFACE posts that actually need
attention. One digest with everything keeps signal/noise readable.
"""
from __future__ import annotations

import logging
import time

import requests

from src.monitor.candidate import Candidate
from src.monitor.triage import TriageResult

LOG = logging.getLogger(__name__)

# Show the top-N highest-scoring worth-noting items as a compact digest;
# the full list lives in the daily CSV. Five keeps the channel skim-friendly
# while still surfacing cluster patterns ("three FL counties this week").
_DIGEST_TOP_N = 5


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


def _total(t: TriageResult) -> int:
    return sum(t.scores.get(k, 0) for k in ("topic", "buyer", "geography", "actionability", "boosters"))


def _digest_blocks(items: list[tuple[Candidate, TriageResult]], csv_relpath: str) -> list[dict]:
    """One Slack message: header + top-N items + footer pointing at the CSV."""
    top = sorted(items, key=lambda ct: -_total(ct[1]))[: _DIGEST_TOP_N]
    bullet_lines = [
        f"• <{c.url}|{c.title}> _({c.source}, {_total(t)}/10)_ — {t.reasoning}"
        for c, t in top
    ]
    blocks: list[dict] = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📋 {len(items)} worth-noting items today* — top {min(_DIGEST_TOP_N, len(items))} below",
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(bullet_lines)},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Full list: `{csv_relpath}` (committed to repo)"}
            ],
        },
    ]
    return blocks


def post_surface(webhook_url: str, candidate: Candidate, triage: TriageResult) -> bool:
    if triage.classification != "SURFACE":
        return False
    return _post(webhook_url, {"blocks": _surface_blocks(candidate, triage)}, candidate.title[:60])


def post_worth_noting_digest(
    webhook_url: str,
    items: list[tuple[Candidate, TriageResult]],
    csv_relpath: str,
) -> bool:
    if not items:
        return False
    return _post(webhook_url, {"blocks": _digest_blocks(items, csv_relpath)}, "worth-noting digest")


def _post(webhook_url: str, payload: dict, label: str) -> bool:
    try:
        resp = requests.post(webhook_url, json=payload, timeout=15)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        LOG.warning("Slack post failed for %s: %s", label, e)
        return False
