# Prospect Intelligence System

## Goal
Help Hohonu's BDR + founders build prospects across critical ICPs (county Emergency Management, Public Works, DOT, Resilience Officers, consulting firms, academia) and never miss a public opportunity (RFPs, federal/state grants, news triggers).

## How to use this file
Any chat working on this project should start by reading: `CLAUDE.md`, `DECISIONS.md`, `ROADMAP.md`. End every chat by updating `ROADMAP.md` and appending to `DECISIONS.md` if any architectural decisions were made.

## Architecture (4 value layers)
- `src/monitor/` - Opportunity monitor: scans SAM.gov, grants.gov, state portals, news. Logs findings to HubSpot. Pings on high-confidence hits only.
- `src/enrich/` - Account enrichment: FEMA disaster declarations, USASpending grants, news, engineering firm of record.
- `src/sync/` - One-way sync: Google Sheet (research) → HubSpot (execution). Contacts graduate when status = "Ready for Outreach".
- `src/briefing/` - BDR briefing generator: 1-page PDF per Tier 1/2 prospect with talking points, social proof, objection handling.

## Source of truth
- **Research/enrichment workspace:** Google Sheet (Upworker + Kevin work here). The sheet at `1RC-5R21KohTWevg64oB_yb3jsrNvhigPr-LFTYHfW9c` has 7 states, structured department + risk fields, drip campaign tracking.
- **Sales execution layer:** HubSpot (Lisa works here). ~4,400 contacts, ~1,300 in Florida, custom properties to be added.
- **Sync direction:** spreadsheet → HubSpot (one-way). Engagement data may flow back via export.

## Data layout
- `data/inputs/` - raw exports, dated (e.g. `fl_prospects_2026-04-27.csv`). Never overwrite.
- `data/outputs/` - generated briefings, reports, lists for Lisa.
- `data/state/` - last-run timestamps, processed-record IDs, monitor seen-set.

## Secrets
`.env` at project root, gitignored. Currently: `HUBSPOT_TOKEN`. Never paste tokens into chat.

## Operating principles
- **Dry-run first** for any HubSpot writes. Every write script must support `--dry-run`.
- **Idempotent scripts.** Re-running shouldn't duplicate. Use email as external ID for contacts; `county+state` for company records.
- **Log every run** to `logs/` with timestamp, what was processed, what changed.
- **Vertical slices.** Each build ships something usable. No foundation-first.

## Key context (as of 2026-04-27)
- BDR (Lisa) onboarding imminent
- Webinar May 19, 2026 - Florida focus
- Texas co-op announcement expected Q2 2026 (~30 eligible counties, $50M pool)
- 24 FL EM Directors opened drip campaign emails - warm list exists today
- Spreadsheet has TX risk-scored and ready when co-op drops

## Related projects
- `../recon/` - inventory reconciliation tool
- `../orchestrator/` - Claude+GPT proposal orchestrator. Do not break.
