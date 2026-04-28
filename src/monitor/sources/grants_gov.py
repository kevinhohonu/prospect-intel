"""Grants.gov Search2 API.

Docs: https://www.grants.gov/api/common-apis
Endpoint: POST https://api.grants.gov/v1/api/search2
Auth: none.
"""
from __future__ import annotations

import logging

import requests

from src.monitor.candidate import Candidate

LOG = logging.getLogger(__name__)
ENDPOINT = "https://api.grants.gov/v1/api/search2"

KEYWORDS = [
    "flood",
    "coastal resilience",
    "water level",
    "storm surge",
    "hazard mitigation",
    "early warning",
]


def fetch(rows: int = 100) -> list[Candidate]:
    """Pull posted/forecasted grant opportunities matching topical keywords."""
    candidates: list[Candidate] = []
    for kw in KEYWORDS:
        body = {
            "keyword": kw,
            "rows": rows,
            "oppStatuses": "posted|forecasted",
        }
        try:
            resp = requests.post(ENDPOINT, json=body, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            LOG.warning("Grants.gov fetch failed for keyword=%r: %s", kw, e)
            continue

        hits = (data.get("data") or {}).get("oppHits") or []
        for item in hits:
            opp_id = str(item.get("id") or item.get("number") or "")
            url = f"https://www.grants.gov/search-results-detail/{opp_id}" if opp_id else ""
            candidates.append(
                Candidate(
                    source="grants.gov",
                    source_id=opp_id,
                    title=(item.get("title") or "").strip(),
                    url=url,
                    posted_date=item.get("openDate", ""),
                    deadline=item.get("closeDate"),
                    snippet=(item.get("agencyName") or "") + " — " + (item.get("oppStatus") or ""),
                    query=kw,
                    raw=item,
                )
            )
    return candidates
