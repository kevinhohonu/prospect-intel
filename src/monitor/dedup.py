"""Two-layer dedup: persistent seen-set across runs, plus in-run title-similarity.

Layer 1: data/state/seen_ids.json — stable identifiers we've already processed.
Layer 2: title-hash within the current run, so AP/Reuters wire republishes collapse.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from src.monitor.candidate import Candidate

_STATE_FILE = Path("data/state/seen_ids.json")
_PUNCT = re.compile(r"[^\w\s]")
_WS = re.compile(r"\s+")


def _normalize_title(title: str) -> str:
    t = _PUNCT.sub(" ", title.lower())
    t = _WS.sub(" ", t).strip()
    return t[:80]


def _title_hash(title: str) -> str:
    return hashlib.sha1(_normalize_title(title).encode()).hexdigest()[:16]


def _candidate_key(c: Candidate) -> str:
    """Source-namespaced ID for the persistent seen-set."""
    return f"{c.source}::{c.source_id}"


def load_seen() -> set[str]:
    if not _STATE_FILE.exists():
        return set()
    try:
        return set(json.loads(_STATE_FILE.read_text()))
    except (json.JSONDecodeError, OSError):
        return set()


def save_seen(seen: set[str]) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(sorted(seen)))


def filter_new(candidates: list[Candidate], seen: set[str]) -> list[Candidate]:
    """Drop anything we've seen before (cross-run) or duplicates within this batch (intra-run)."""
    fresh: list[Candidate] = []
    title_hashes_this_run: set[str] = set()
    for c in candidates:
        key = _candidate_key(c)
        if key in seen:
            continue
        th = _title_hash(c.title)
        if th in title_hashes_this_run:
            continue
        title_hashes_this_run.add(th)
        fresh.append(c)
    return fresh


def mark_seen(candidates: list[Candidate], seen: set[str]) -> set[str]:
    for c in candidates:
        seen.add(_candidate_key(c))
    return seen
