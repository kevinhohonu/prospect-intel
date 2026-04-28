# Roadmap

Current state of play. **Update at the end of every chat.**

---

## Built

- Project scaffolding: directory structure, CLAUDE.md, DECISIONS.md, ROADMAP.md, README.md, .gitignore, git init (2026-04-27)

## In progress

(nothing - end of scaffolding chat)

## Next up - in slice order

1. **Slice 1: Opportunity monitor MVP**
   - **First decision in Slice 1 chat:** confirm source list (likely starting set: SAM.gov + Grants.gov + Google News; FL + TX state portals deferred to 1.5)
   - Runs on GitHub Actions, daily cron
   - Filtering: rubric-guided judgment by Claude, returns SURFACE / WORTH_NOTING / SKIP with reasoning
   - Output: posts to private Slack channel via incoming webhook
   - Audit log: every candidate written to `data/state/opportunities.jsonl` (append-only) with full reasoning
   - **No HubSpot integration in MVP.** Revisit after operating data
   - Rubric stored as config (e.g. `configs/relevance_rubric.yaml`) for tuning without code changes

2. **Slice 2: FL warm follow-up list**
   - Extract the 24 drip-engaged FL EM Directors from spreadsheet
   - Format as CSV for Lisa: name, county, email, phone, last engagement, suggested re-engagement angle
   - One-time deliverable, no ongoing infrastructure

3. **Slice 3: FL prospect tiering**
   - Score full FL spreadsheet (~300+ FL contacts across sub-sections)
   - Use department + coastal/river risk + population rank
   - Output: tiered list (T1/T2/T3) for Lisa

4. **Slice 4: Sheet → HubSpot sync (graduated only)**
   - Define custom properties: `department_type`, `coastal_risk`, `river_risk`, `bdr_priority_tier`, `campaign_status`, `last_enriched_date`
   - Sync only "Ready for Outreach" contacts
   - Match by email; create company records where missing; link contacts to companies
   - Dry-run first

5. **Slice 5: Account enrichment for top 50 FL accounts**
   - FEMA disaster declarations API
   - USASpending grants API (federal $ to that county/agency)
   - Recent flood news (Google News)
   - Engineering firm of record (county procurement records)
   - Push to HubSpot company custom properties

6. **Slice 6: Engineering firm of record extraction (FL focus)**
   - Source: county procurement portals, TWDB equivalents, USASpending subrecipient data
   - Build relationship graph: county ↔ firm ↔ projects ↔ funding
   - Surface warm-path opportunities (firm X has a contract with county Y - who do we know there?)

7. **Slice 7: BDR briefing generator**
   - Input: HubSpot company record (enriched)
   - Output: 1-page PDF briefing for Lisa
   - Includes: why this prospect, social proof to name-drop, suggested talking points by stakeholder type, likely objections + responses, Dr. Glazer angle

## Deferred / parked

- Texas co-op rapid-response prep (waits for announcement, but TX spreadsheet data ready)
- Origami AI as conversational interface for Lisa (evaluate after core pipeline works)
- Website rebuild (separate project)
- ICP coverage expansion to SC, NJ, MD, MA, ME
- Outbound cadence orchestration in HubSpot (sequences)
- Slack-based opportunity feed (vs. email)

## Open questions

- **For Slice 1 chat:** confirm source list and prioritization
- **For post-MVP:** if/how to log surfaced opportunities to HubSpot (deal pipeline, notes, custom object) - decide after a week of Slack-only operation
- **For Slice 4+:** which custom HubSpot properties to add for graduated contacts (department_type, coastal_risk, river_risk, bdr_priority_tier, campaign_status, last_enriched_date is the working list)

## Resolved (moved from open)

- Where does the monitor run? -> GitHub Actions (see DECISIONS.md 2026-04-27)
- Notification channel? -> Private Slack channel via incoming webhook (see DECISIONS.md 2026-04-27)
- HubSpot integration in MVP? -> No, Slack-only, revisit after operating data (see DECISIONS.md 2026-04-27)
- Filter mechanism? -> Judgment-based with rubric-guided analysis, not numeric thresholds (see DECISIONS.md 2026-04-27)
