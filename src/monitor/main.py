"""Opportunity monitor — daily entry point.

Pipeline:
  1. Fetch candidates from SAM.gov, Grants.gov, Google News (parallel-ish per source).
  2. Filter against persistent seen-set + intra-run title dedup.
  3. Triage each fresh candidate via Claude with rubric → SURFACE / WORTH_NOTING / SKIP.
     A hard score-floor (in triage.py) demotes obvious-noise low-scores to SKIP.
  4. SURFACE → individual Slack post. WORTH_NOTING → daily CSV + one Slack
     digest message with the top-5. SKIP → audit-log only.
  5. Borderline CSV: top-30 highest-scoring SKIPs, so weekly review can spot
     calibration drift (false negatives).
  6. Save updated seen-set.

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

# How many SKIPs to dump into the daily borderline CSV. Sorted by total score
# desc so the file shows the items closest to qualifying. Weekly review:
# "did the system reject anything that was actually signal?" If yes → loosen.
_BORDERLINE_TOP_N = 30


def _total(t: TriageResult) -> int:
    return sum(t.scores.get(k, 0) for k in ("topic", "buyer", "geography", "actionability", "boosters"))


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


def _write_items_csv(items: list[tuple[Candidate, TriageResult]], path: Path) -> None:
    """Shared writer for worth_noting + borderline CSVs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    items_sorted = sorted(items, key=lambda ct: -_total(ct[1]))
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["score", "classification", "source", "title", "url", "posted", "deadline", "topic", "buyer", "geo", "actionable", "boosters", "reasoning", "query"])
        for c, t in items_sorted:
            s = t.scores
            w.writerow([
                _total(t), t.classification, c.source, c.title, c.url, c.posted_date, c.deadline or "",
                s.get("topic", ""), s.get("buyer", ""), s.get("geography", ""),
                s.get("actionability", ""), s.get("boosters", ""),
                t.reasoning, c.query or "",
            ])


def _write_worth_noting_csv(items: list[tuple[Candidate, TriageResult]], stamp: str) -> Path:
    path = WORTH_NOTING_CSV_DIR / f"worth_noting-{stamp}.csv"
    _write_items_csv(items, path)
    return path


def _write_borderline_csv(skipped_items: list[tuple[Candidate, TriageResult]], stamp: str) -> Path:
    """Top-30 highest-scoring SKIPs — the ones closest to qualifying. Used for
    weekly calibration review: skim the CSV, ask 'did we reject anything that
    was actually signal?' Includes both Claude-classified-SKIP and
    score-floor-demoted items."""
    top = sorted(skipped_items, key=lambda ct: -_total(ct[1]))[:_BORDERLINE_TOP_N]
    path = WORTH_NOTING_CSV_DIR / f"borderline-{stamp}.csv"
    _write_items_csv(top, path)
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


def _gather() -> tuple[list[Candidate], int]:
    """Returns (all candidates, news_dropped_stale) for funnel reporting."""
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

    news_results, news_dropped_stale = google_news.fetch(NEWS_QUERIES_PATH)
    LOG.info("google_news: %d candidates (dropped %d stale)", len(news_results), news_dropped_stale)
    candidates.extend(news_results)

    return candidates, news_dropped_stale


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

    raw, news_dropped_stale = _gather()
    LOG.info("raw candidates: %d", len(raw))

    seen = dedup.load_seen()
    fresh = dedup.filter_new(raw, seen)
    deduped = len(raw) - len(fresh)
    LOG.info("fresh after dedup: %d (seen-set size %d, deduped %d)", len(fresh), len(seen), deduped)

    triager = Triager(api_key=anthropic_key, rubric_path=RUBRIC_PATH)

    surfaced_items: list[tuple[Candidate, TriageResult]] = []
    worth_noting_items: list[tuple[Candidate, TriageResult]] = []
    skipped_items: list[tuple[Candidate, TriageResult]] = []
    floored = errored = 0

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
            skipped_items.append((c, result))
            # The score-floor in triage.py prefixes the reasoning with this tag
            # when it demotes a non-SKIP to SKIP. Counting the prefix is the
            # cheapest way to surface "how much is the floor doing" in the funnel.
            if result.reasoning.startswith("[auto-floor:"):
                floored += 1

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # WORTH_NOTING: write a CSV (cheap, useful artifact), and post one digest
    # message at the end with the top-5.
    csv_path = None
    if worth_noting_items:
        csv_path = _write_worth_noting_csv(worth_noting_items, stamp)
        LOG.info("worth_noting CSV: %s (%d items)", csv_path, len(worth_noting_items))

    # BORDERLINE: top-30 highest-scoring SKIPs for weekly calibration review.
    # Helps catch false negatives ("did we reject anything that was signal?").
    borderline_path = None
    if skipped_items:
        borderline_path = _write_borderline_csv(skipped_items, stamp)
        LOG.info("borderline CSV: %s (top %d of %d skips)", borderline_path, min(_BORDERLINE_TOP_N, len(skipped_items)), len(skipped_items))

    # Funnel for the digest footer + log line. Visible-by-default observability:
    # if any number suddenly spikes or zeros out, it's noticed in Slack.
    funnel = {
        "fetched": len(raw),
        "stale_dropped": news_dropped_stale,
        "deduped": deduped,
        "fresh": len(fresh),
        "surfaced": len(surfaced_items),
        "worth_noting": len(worth_noting_items),
        "skipped": len(skipped_items),
        "floored": floored,
        "errored": errored,
    }

    borderline_link = _csv_link(borderline_path) if borderline_path else None
    if not dry_run and webhook:
        if worth_noting_items:
            slack_notify.post_worth_noting_digest(
                webhook,
                worth_noting_items,
                _csv_link(csv_path),
                funnel=funnel,
                borderline_link=borderline_link,
            )
        elif not surfaced_items:
            # Nothing to surface, nothing worth-noting — but the run did happen.
            # Heartbeat keeps the channel honest about whether the cron is alive.
            slack_notify.post_quiet_heartbeat(webhook, funnel, borderline_link)

    if not dry_run:
        dedup.mark_seen(fresh, seen)
        dedup.save_seen(seen)

    LOG.info(
        "done: fetched=%d stale_dropped=%d deduped=%d fresh=%d "
        "surfaced=%d worth_noting=%d skipped=%d floored=%d errored=%d",
        funnel["fetched"], funnel["stale_dropped"], funnel["deduped"], funnel["fresh"],
        funnel["surfaced"], funnel["worth_noting"], funnel["skipped"], funnel["floored"], funnel["errored"],
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily opportunity monitor")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and triage but do not post or update seen-set")
    args = parser.parse_args()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
