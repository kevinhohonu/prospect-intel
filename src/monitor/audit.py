"""Append-only JSONL audit log of every candidate evaluated."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.monitor.candidate import Candidate
from src.monitor.triage import TriageResult

_LOG_FILE = Path("data/state/opportunities.jsonl")


def append(candidate: Candidate, triage: TriageResult) -> None:
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "candidate": candidate.to_dict(),
        "triage": triage.to_dict(),
    }
    with _LOG_FILE.open("a") as f:
        f.write(json.dumps(record) + "\n")
