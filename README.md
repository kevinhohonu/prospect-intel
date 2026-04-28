# Prospect Intelligence System

Operator docs - what the system does, how to run it, how Lisa interacts with it.

This file is for humans. For Claude/agent context, see `CLAUDE.md`.

---

## What this does

TBD as built. See `ROADMAP.md` for current state.

## How to run

TBD per module as built. Conventions:
- All scripts run from project root
- All HubSpot-writing scripts support `--dry-run`
- Logs go to `logs/` with date-stamped filenames

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
