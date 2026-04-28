from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Candidate:
    source: str            # "sam.gov" | "grants.gov" | "google_news"
    source_id: str         # stable per-source ID (solicitation #, opp ID, or URL hash)
    title: str
    url: str
    posted_date: str       # ISO 8601, source's posting date
    snippet: str           # short description / summary
    deadline: str | None = None
    query: str | None = None  # which query/keyword surfaced it (news only)
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
