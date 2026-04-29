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


# Slack section blocks have a 3000-char text limit. Google News URLs alone
# can run 600+ chars; five items packed into one section block blows the
# limit and Slack returns 400. We render one section block per item — Slack
# allows 50 blocks per message, each with its own 3000-char budget.
_REASONING_PREVIEW_CHARS = 220


def _funnel_text(funnel: dict, borderline_link: str | None) -> str:
    """One-line funnel summary so calibration drift is visible every day.
    If any number suddenly spikes or zeros out, it shows up in the channel
    you already read. Borderline link, if present, points to the top-30
    highest-scoring SKIPs for false-negative spot-checking."""
    parts = [
        f"`{funnel['fetched']}` fetched",
        f"`{funnel['stale_dropped']}` stale",
        f"`{funnel['deduped']}` already seen",
        f"`{funnel['fresh']}` triaged",
        f"→ `{funnel['surfaced']}` surfaced + `{funnel['worth_noting']}` worth-noting + `{funnel['skipped']}` skipped (`{funnel['floored']}` floored)",
    ]
    if funnel.get("errored"):
        parts.append(f"⚠️ `{funnel['errored']}` errored")
    line = "  ·  ".join(parts)
    if borderline_link:
        line += f"\n🔍 <{borderline_link}|Top-30 borderline SKIPs (weekly calibration check)>"
    return line


def _digest_blocks(
    items: list[tuple[Candidate, TriageResult]],
    csv_link: str,
    funnel: dict | None = None,
    borderline_link: str | None = None,
) -> list[dict]:
    """One Slack message: header + one section per top-N item + footer pointing at the CSV."""
    top = sorted(items, key=lambda ct: -_total(ct[1]))[: _DIGEST_TOP_N]

    blocks: list[dict] = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📋 {len(items)} worth-noting items today* — top {min(_DIGEST_TOP_N, len(items))} below (full list in CSV)",
            },
        }
    ]
    for c, t in top:
        reasoning = t.reasoning if len(t.reasoning) <= _REASONING_PREVIEW_CHARS else t.reasoning[: _REASONING_PREVIEW_CHARS - 1].rstrip() + "…"
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{c.url}|{c.title}>\n_{c.source} · {_total(t)}/10_ — {reasoning}",
                },
            }
        )
    blocks.append(
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"📊 <{csv_link}|Full list of {len(items)} items (CSV)>"}
            ],
        }
    )
    if funnel is not None:
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": _funnel_text(funnel, borderline_link)}],
            }
        )
    return blocks


def post_quiet_heartbeat(
    webhook_url: str,
    funnel: dict,
    borderline_link: str | None = None,
) -> bool:
    """Posted on days when nothing surfaced and nothing was worth-noting.
    Without this, the channel goes silent and you can't distinguish
    'no signal today' from 'cron is broken'."""
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "_Quiet day — nothing crossed the bar._",
            },
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": _funnel_text(funnel, borderline_link)}],
        },
    ]
    return _post(webhook_url, {"blocks": blocks}, "quiet-day heartbeat")


def post_surface(webhook_url: str, candidate: Candidate, triage: TriageResult) -> bool:
    if triage.classification != "SURFACE":
        return False
    return _post(webhook_url, {"blocks": _surface_blocks(candidate, triage)}, candidate.title[:60])


def post_worth_noting_digest(
    webhook_url: str,
    items: list[tuple[Candidate, TriageResult]],
    csv_link: str,
    funnel: dict | None = None,
    borderline_link: str | None = None,
) -> bool:
    """csv_link should be a clickable URL (GitHub blob URL when running on
    GH Actions, or a local file path / relpath as a fallback). funnel and
    borderline_link drive the observability footer; both optional for
    backward compat."""
    if not items:
        return False
    return _post(
        webhook_url,
        {"blocks": _digest_blocks(items, csv_link, funnel=funnel, borderline_link=borderline_link)},
        "worth-noting digest",
    )


def _post(webhook_url: str, payload: dict, label: str) -> bool:
    try:
        resp = requests.post(webhook_url, json=payload, timeout=15)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        # Don't log the exception verbatim — `requests` includes the full URL
        # (incl. webhook secret) in the message of HTTPError, which then leaks
        # into logs/, which we used to commit back to the repo. Now we only log
        # the exception type + status code if available.
        status = getattr(getattr(e, "response", None), "status_code", "?")
        LOG.warning("Slack post failed for %s (%s, status=%s)", label, type(e).__name__, status)
        return False
