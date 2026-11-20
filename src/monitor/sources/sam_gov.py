"""SAM.gov opportunities search.

Docs: https://open.gsa.gov/api/get-opportunities-public-api/
Endpoint: GET https://api.sam.gov/opportunities/v2/search
Auth: api.data.gov key, free signup.
Date format the API expects: MM/dd/yyyy.

Keywords go in `title`. The API silently ignores a `keyword` param: until
2026-10 every keyword returned the same unfiltered list of all federal
postings (19,349 over 90 days), and the limit kept only the newest few.
Title search misses opportunities that only mention a term in the full
description; v2 search results don't include description text, so matching
on it would mean triaging every federal posting.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

import requests

from src.monitor.candidate import Candidate

LOG = logging.getLogger(__name__)
ENDPOINT = "https://api.sam.gov/opportunities/v2/search"


class SamAuthError(Exception):
    """SAM.gov rejected the API key (401/403). Keys expire every 90 days, and
    this used to fail silently for months: each keyword logged a warning and
    the run reported 'sam.gov: 0 candidates' as if it were a quiet day."""

# `title` is a case-insensitive substring match on the notice title, so terms
# are short stems: federal titles read like "66--SENSOR,LIQUID LEVEL", and
# phrases such as "water level" or "storm surge" matched nothing in 90 days.
# Probed 2026-10-13 over 90 days: ~250 matches total, ~3/day. Triage is the
# real filter. Left out as too noisy: "river" (bridge/freezer repair),
# "stream", "tide" (matches "peptide").
KEYWORDS = [
    "gauge",
    "gage",            # USACE/USGS spelling
    "flood",
    "levee",
    "tidal",
    "water level",
    "liquid level",
    "hydrolog",
    "hydrograph",
    "inundation",
    "coastal",
    "shoreline",
    "resilien",
    "surge",
    "stormwater",
    "early warning",
    "warning system",
    "monitoring",
    "telemetry",
    "sensor",
    "NOAA",
    "USGS",
]


def fetch(api_key: str, lookback_days: int = 2, limit: int = 1000) -> list[Candidate]:
    """Pull opportunities posted in the lookback window for each keyword.

    Lookback default 2 days because the cron runs daily but we want a small
    overlap to absorb timezone / posting-delay edges. Dedup downstream handles repeats.
    Longer lookbacks are for one-off backfills (SAM_LOOKBACK_DAYS in the workflow);
    limit is the API max so a backfill window isn't silently truncated.

    Raises SamAuthError on 401/403 so the caller can alert instead of
    treating a dead key as an empty day.
    """
    today = date.today()
    posted_from = (today - timedelta(days=lookback_days)).strftime("%m/%d/%Y")
    posted_to = today.strftime("%m/%d/%Y")

    candidates: list[Candidate] = []
    for kw in KEYWORDS:
        params = {
            "api_key": api_key,
            "title": kw,
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "limit": limit,
            # solicitation, combined synopsis/solicitation, presolicitation, sources sought
            "ptype": "o,k,p,r",
        }
        try:
            resp = requests.get(ENDPOINT, params=params, timeout=60)
            if resp.status_code in (401, 403):
                raise SamAuthError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            # Don't log the exception verbatim: `requests` puts the full URL,
            # including api_key, in HTTPError messages. Same leak slack_notify avoids.
            status = getattr(getattr(e, "response", None), "status_code", "?")
            LOG.warning("SAM.gov fetch failed for title=%r (%s, status=%s)", kw, type(e).__name__, status)
            continue

        total = data.get("totalRecords") or 0
        if total > limit:
            LOG.warning("SAM.gov title=%r has %d results, only first %d fetched", kw, total, limit)

        for item in data.get("opportunitiesData", []) or []:
            candidates.append(
                Candidate(
                    source="sam.gov",
                    source_id=item.get("solicitationNumber") or item.get("noticeId") or item.get("uiLink", ""),
                    title=item.get("title", "").strip(),
                    url=item.get("uiLink", ""),
                    posted_date=item.get("postedDate", ""),
                    deadline=item.get("responseDeadLine"),
                    snippet=(item.get("description") or "")[:1000],
                    query=kw,
                    raw=item,
                )
            )
    return candidates
