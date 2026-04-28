"""SAM.gov opportunities search.

Docs: https://open.gsa.gov/api/get-opportunities-public-api/
Endpoint: GET https://api.sam.gov/opportunities/v2/search
Auth: api.data.gov key, free signup.
Date format the API expects: MM/dd/yyyy.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

import requests

from src.monitor.candidate import Candidate

LOG = logging.getLogger(__name__)
ENDPOINT = "https://api.sam.gov/opportunities/v2/search"

# Keyword set tuned to Hohonu's topical fit. Broad enough to catch adjacent work,
# narrow enough to keep the daily candidate count manageable. Triage is the real filter.
KEYWORDS = [
    "water level",
    "tide gauge",
    "flood sensor",
    "flood monitoring",
    "hydrologic monitoring",
    "coastal resilience",
    "storm surge",
    "flood early warning",
]


def fetch(api_key: str, lookback_days: int = 2, limit: int = 100) -> list[Candidate]:
    """Pull opportunities posted in the lookback window for each keyword.

    Lookback default 2 days because the cron runs daily but we want a small
    overlap to absorb timezone / posting-delay edges. Dedup downstream handles repeats.
    """
    today = date.today()
    posted_from = (today - timedelta(days=lookback_days)).strftime("%m/%d/%Y")
    posted_to = today.strftime("%m/%d/%Y")

    candidates: list[Candidate] = []
    for kw in KEYWORDS:
        params = {
            "api_key": api_key,
            "keyword": kw,
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "limit": limit,
            "ptype": "o,k,p",  # solicitation, combined synopsis/solicitation, presolicitation
        }
        try:
            resp = requests.get(ENDPOINT, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            LOG.warning("SAM.gov fetch failed for keyword=%r: %s", kw, e)
            continue

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
