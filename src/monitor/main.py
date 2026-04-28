"""Opportunity monitor — daily entry point.

Pipeline:
  1. Fetch candidates from SAM.gov, Grants.gov, Google News (parallel-ish per source).
  2. Filter against persistent seen-set + intra-run title dedup.
  3. Triage each fresh candidate via Claude with rubric → SURFACE / WORTH_NOTING / SKIP.
     A hard score-floor (in triage.py) demotes obvious-noise low-scores to SKIP.
  4. SURFACE → individual Slack post. WORTH_NOTING → daily CSV + one Slack
     digest message with the top-5. SKIP → audit-log only.
  5. Save updated seen-set.

Run:
  python -m src.monitor.main           # full run
  python -m src.monitor.main --dry-run # fetch + triage, no Slack post, no seen-set update
"""
from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src.monitor import audit, dedup, slack_notify
from src.monitor.candidate import Candidate
from src.monitor.sources import google_news, grants_gov, sam_gov
from src.monitor.triage import Triager, TriageResult

LOG = logging.getLogger("monitor")

RUBRIC_PATH = Path("configs/relevance_rubric.yaml")
NEWS_QUERIES_PATH = Path("configs/news_queries.yaml")
WORTH_NOTING_CSV_DIR = Path("data/outputs")


def _csv_link(csv_path: Path) -> str:
    """Return a clickable URL to the CSV when we can build one (GH Actions sets
    GITHUB_REPOSITORY automatically), otherwise fall back to the relative path.
    The workflow commits the CSV back to the default branch, so a /blob/ URL on
    the configured branch will resolve once the run completes."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    branch = os.environ.get("GITHUB_REF_NAME") or "main"
    if repo:
        return f"https://github.com/{repo}/blob/{branch}/{csv_path.as_posix()}"
    return str(csv_path)


def _write_worth_noting_csv(items: list[tuple[Candidate, TriageResult]], stamp: str) -> Path:
    """One CSV per run. Sorted by total score desc so the top of the file is the
    most interesting stuff. Lives at data/outputs/worth_noting-YYYY-MM-DD.csv
    so it gets committed back by the GitHub Actions workflow."""
    WORTH_NOTING_CSV_DIR.mkdir(parents=True, exist_ok=True)
    path = WORTH_NOTING_CSV_DIR / f"worth_noting-{stamp}.csv"

    def total(t: TriageResult) -> int:
        return sum(t.scores.get(k, 0) for k in ("topic", "buyer", "geography", "actionability", "boosters"))

    items_sorted = sorted(items, key=lambda ct: -total(ct[1]))
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["score", "source", "title", "url", "posted", "deadline", "topic", "buyer", "geo", "actionable", "boosters", "reasoning", "query"])
        for c, t in items_sorted:
            s = t.scores
            w.writerow([
                total(t), c.source, c.title, c.url, c.posted_date, c.deadline or "",
                s.get("topic", ""), s.get("buyer", ""), s.get("geography", ""),
                s.get("actionability", ""), s.get("boosters", ""),
                t.reasoning, c.query or "",
            ])
    return path


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

    surfaced_items: list[tuple[Candidate, TriageResult]] = []
    worth_noting_items: list[tuple[Candidate, TriageResult]] = []
    skipped = errored = 0

    for c in fresh:
        result = triager.triage(c)
        if result.error:
            errored += 1
            LOG.warning("triage error for %r: %s", c.title[:80], result.error)

        audit.append(c, result)

        if result.classification == "SURFACE":
            surfaced_items.append((c, result))
            # Post SURFACEs as they happen — they're individually high-signal
            # and the count is always small, so per-message posting is fine.
            if not dry_run and webhook:
                slack_notify.post_surface(webhook, c, result)
        elif result.classification == "WORTH_NOTING":
            worth_noting_items.append((c, result))
        else:
            skipped += 1

    # WORTH_NOTING: write a CSV regardless of dry-run (cheap, useful artifact),
    # and post one digest message at the end with the top-5.
    csv_path = None
    if worth_noting_items:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        csv_path = _write_worth_noting_csv(worth_noting_items, stamp)
        LOG.info("worth_noting CSV: %s (%d items)", csv_path, len(worth_noting_items))
        if not dry_run and webhook:
            slack_notify.post_worth_noting_digest(
                webhook, worth_noting_items, _csv_link(csv_path)
            )

    if not dry_run:
        dedup.mark_seen(fresh, seen)
        dedup.save_seen(seen)

    LOG.info(
        "done: surfaced=%d worth_noting=%d skipped=%d errored=%d",
        len(surfaced_items), len(worth_noting_items), skipped, errored,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily opportunity monitor")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and triage but do not post or update seen-set")
    args = parser.parse_args()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
