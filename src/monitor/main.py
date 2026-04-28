"""Opportunity monitor — daily entry point.

Pipeline:
  1. Fetch candidates from SAM.gov, Grants.gov, Google News (parallel-ish per source).
  2. Filter against persistent seen-set + intra-run title dedup.
  3. Triage each fresh candidate via Claude with rubric → SURFACE / WORTH_NOTING / SKIP.
  4. Post SURFACE/WORTH_NOTING to Slack; append every candidate to JSONL audit log.
  5. Save updated seen-set.

Run:
  python -m src.monitor.main           # full run
  python -m src.monitor.main --dry-run # fetch + triage, no Slack post, no seen-set update
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src.monitor import audit, dedup, slack_notify
from src.monitor.candidate import Candidate
from src.monitor.sources import google_news, grants_gov, sam_gov
from src.monitor.triage import Triager

LOG = logging.getLogger("monitor")

RUBRIC_PATH = Path("configs/relevance_rubric.yaml")
NEWS_QUERIES_PATH = Path("configs/news_queries.yaml")


def _setup_logging() -> None:
    Path("logs").mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(f"logs/monitor-{stamp}.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def _gather() -> list[Candidate]:
    candidates: list[Candidate] = []

    sam_key = os.environ.get("SAM_API_KEY")
    if sam_key:
        sam_results = sam_gov.fetch(api_key=sam_key)
        LOG.info("sam.gov: %d candidates", len(sam_results))
        candidates.extend(sam_results)
    else:
        LOG.warning("SAM_API_KEY not set; skipping SAM.gov")

    grants_results = grants_gov.fetch()
    LOG.info("grants.gov: %d candidates", len(grants_results))
    candidates.extend(grants_results)

    news_results = google_news.fetch(NEWS_QUERIES_PATH)
    LOG.info("google_news: %d candidates", len(news_results))
    candidates.extend(news_results)

    return candidates


def run(dry_run: bool = False) -> int:
    load_dotenv()
    _setup_logging()
    LOG.info("monitor run start (dry_run=%s)", dry_run)

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        LOG.error("ANTHROPIC_API_KEY missing")
        return 1
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook and not dry_run:
        LOG.error("SLACK_WEBHOOK_URL missing")
        return 1

    raw = _gather()
    LOG.info("raw candidates: %d", len(raw))

    seen = dedup.load_seen()
    fresh = dedup.filter_new(raw, seen)
    LOG.info("fresh after dedup: %d (seen-set size %d)", len(fresh), len(seen))

    triager = Triager(api_key=anthropic_key, rubric_path=RUBRIC_PATH)

    surfaced = noted = skipped = errored = 0
    for c in fresh:
        result = triager.triage(c)
        if result.error:
            errored += 1
            LOG.warning("triage error for %r: %s", c.title[:80], result.error)

        audit.append(c, result)

        if result.classification == "SURFACE":
            surfaced += 1
        elif result.classification == "WORTH_NOTING":
            noted += 1
        else:
            skipped += 1

        if not dry_run and webhook and result.classification != "SKIP":
            slack_notify.post(webhook, c, result)

    if not dry_run:
        dedup.mark_seen(fresh, seen)
        dedup.save_seen(seen)

    LOG.info(
        "done: surfaced=%d worth_noting=%d skipped=%d errored=%d",
        surfaced, noted, skipped, errored,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily opportunity monitor")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and triage but do not post or update seen-set")
    args = parser.parse_args()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
