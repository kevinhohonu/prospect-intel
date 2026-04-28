"""Google News RSS source.

No auth, no documented rate limit. Pattern:
  https://news.google.com/rss/search?q=<urlencoded>&hl=en-US&gl=US&ceid=US:en

We pass query strings straight from configs/news_queries.yaml. URL length is the
only practical limit; the long state OR-lists in funding queries are why we
split by region.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
import requests
import yaml

from src.monitor.candidate import Candidate

LOG = logging.getLogger(__name__)
BASE = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

# Google News RSS blocks feedparser's urllib fetch path (URLError, no body) even
# with `agent=`. Fetching with `requests` and a real-browser UA, then handing
# the bytes to feedparser, returns proper RSS. Diagnosed 2026-04-28.
_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
_TIMEOUT = 20

# Google News RSS happily resurfaces years-old articles whenever its search
# ranking re-elevates them (evergreen topics like "tidal flooding" are the
# worst). Topical relevance stays high but actionability is dead. Cheaper to
# drop them at fetch time than to spend a Claude call learning they're stale.
# 30 days is roughly "this BDR cycle" — older signal can't drive an outreach.
_MAX_AGE_DAYS = 30


def _is_recent(entry) -> bool:
    pp = entry.get("published_parsed")
    if not pp:
        # Permissive fallback: if Google didn't provide a parseable date, let
        # the item through and rely on triage. Better than dropping signal
        # because of a parse miss.
        return True
    posted = datetime(*pp[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - posted <= timedelta(days=_MAX_AGE_DAYS)


def _load_queries(config_path: Path) -> list[tuple[str, str]]:
    """Returns list of (category, query_string)."""
    with config_path.open() as f:
        data = yaml.safe_load(f) or {}
    flat: list[tuple[str, str]] = []
    for category, queries in data.items():
        for q in queries or []:
            flat.append((category, q))
    return flat


def fetch(config_path: Path) -> list[Candidate]:
    queries = _load_queries(config_path)
    candidates: list[Candidate] = []
    for category, q in queries:
        url = BASE.format(q=quote_plus(q))
        try:
            resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=_TIMEOUT)
            resp.raise_for_status()
        except Exception as e:
            LOG.warning("Google News fetch failed for query=%r: %s", q, e)
            continue

        feed = feedparser.parse(resp.content)
        if feed.bozo and not feed.entries:
            LOG.warning("Google News empty/invalid feed for query=%r", q)
            continue

        kept = dropped_stale = 0
        for entry in feed.entries:
            if not _is_recent(entry):
                dropped_stale += 1
                continue
            link = entry.get("link", "")
            candidates.append(
                Candidate(
                    source="google_news",
                    source_id=link,
                    title=entry.get("title", "").strip(),
                    url=link,
                    posted_date=entry.get("published", ""),
                    snippet=entry.get("summary", "")[:600],
                    query=f"{category}: {q}",
                    raw={"source_name": (entry.get("source") or {}).get("title", "")},
                )
            )
            kept += 1
        if dropped_stale:
            LOG.info("google_news: query=%r kept=%d dropped_stale=%d (>%dd old)", q, kept, dropped_stale, _MAX_AGE_DAYS)
    return candidates
