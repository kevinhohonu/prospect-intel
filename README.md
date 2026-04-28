# Prospect Intelligence System

Operator docs - what the system does, how to run it, how Lisa interacts with it.

This file is for humans. For Claude/agent context, see `CLAUDE.md`.

---

## What this does

TBD as built. See `ROADMAP.md` for current state.

## How to run

Conventions:
- All scripts run from project root
- All HubSpot-writing scripts support `--dry-run`
- Logs go to `logs/` with date-stamped filenames

### Opportunity monitor (Slice 1)

Daily scan of SAM.gov + Grants.gov + Google News, triaged by Claude against the rubric in `configs/relevance_rubric.yaml`. SURFACE / WORTH_NOTING hits post to Slack. Every candidate (including SKIPs) appends to `data/state/opportunities.jsonl` for audit.

**Setup:**
```
pip install -r requirements.txt
cp .env.example .env   # then fill in keys
```

Required env vars: `ANTHROPIC_API_KEY`, `SAM_API_KEY` (free at https://api.data.gov/signup/), `SLACK_WEBHOOK_URL`.

**Run locally:**
```
python -m src.monitor.main --dry-run   # fetch + triage, no Slack post, no state update
python -m src.monitor.main             # full daily run
```

**Production:** GitHub Actions workflow `.github/workflows/monitor.yml` runs daily at 13:00 UTC. Add the three secrets under repo Settings → Secrets → Actions.

**Tuning without code changes:**
- `configs/relevance_rubric.yaml` — rubric, active markets, disqualifiers, classification guidance
- `configs/news_queries.yaml` — Google News query strings by category

## How Lisa interacts with this

TBD. Likely: filtered HubSpot view + briefing PDFs in `data/outputs/briefings/`.

## What to do if X breaks

TBD as failure modes appear.

## Where things live

| Thing | Location |
|---|---|
| Module code | `src/<module>/` |
| Raw inputs (spreadsheet exports, API snapshots) | `data/inputs/` |
| Generated outputs (briefings, lists) | `data/outputs/` |
| Run state (last-run timestamps, seen-sets) | `data/state/` |
| Run logs | `logs/` |
| Secrets | `.env` |
| Decision history | `DECISIONS.md` |
| Current roadmap | `ROADMAP.md` |
