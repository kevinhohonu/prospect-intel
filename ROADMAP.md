# Roadmap

Current state of play. **Update at the end of every chat.**

---

## Built

(none yet - scaffolding completed 2026-04-27)

## In progress

- Project scaffolding (this commit)

## Next up - in slice order

1. **Slice 1: Opportunity monitor MVP**
   - One source: SAM.gov contract opportunities
   - Keywords: flood early warning, water level, stormwater monitoring, coastal resilience
   - Daily run, logs to `data/state/monitor_seen.json` (dedupe)
   - Claude scores each hit 1-10 for relevance
   - Above threshold (e.g. 7+): create HubSpot note/deal + email/Slack ping
   - Below threshold: log only

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

- Where does the opportunity monitor run? (launchd / GitHub Actions / cron) - decide before Slice 1 ship
- Notification channel: email only, Slack only, or both?
- HubSpot deal pipeline for opportunities: new pipeline or existing?
