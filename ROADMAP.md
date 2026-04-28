# Roadmap

Current state of play. **Update at the end of every chat.**

---

## Built

- Project scaffolding: directory structure, CLAUDE.md, DECISIONS.md, ROADMAP.md, README.md, .gitignore, git init (2026-04-27)
- **Slice 1: Opportunity monitor MVP** (2026-04-27, refined 2026-04-28)
  - Sources: SAM.gov, Grants.gov, Google News RSS (per `configs/news_queries.yaml`)
  - Two-layer dedup: persistent `data/state/seen_ids.json` + intra-run title-hash
  - Triage via Claude (Sonnet 4.6) against `configs/relevance_rubric.yaml`, with prompt caching
  - Hard score-floor (`triage.apply_score_floor`) demotes total<5 to SKIP — kills competitor PR fluff and off-topic noise deterministically
  - Outputs: SURFACE → individual rich Slack post; WORTH_NOTING → daily CSV at `data/outputs/worth_noting-YYYY-MM-DD.csv` + single Slack digest with top-5; SKIP → audit-only
  - Audit log: `data/state/opportunities.jsonl` (every candidate + triage decision)
  - Run via `python -m src.monitor.main` (supports `--dry-run`) or GitHub Actions daily cron at 13:00 UTC; workflow commits state + CSV + logs back to repo

## In progress

(nothing — end of Slice 1 build)

## Next up - in slice order

1. **Slice 1 operate-and-tune (1 week)**
   - Run daily, watch Slack volume + the CSV
   - React to SURFACE posts in Slack with 👍 / 👎 / 🎯 / 💤 (free training signal, harvest later)
   - Append misses (things you wish had surfaced) to a running notes file
   - Tune rubric / queries based on what surfaces vs. what should have
   - Build out training infrastructure (scoped for next chat — see plan in chat 2026-04-28):
     - `rubric_version` field tagged in audit log
     - `tools/eval.py` against a hand-labeled gold set (~30 items)
     - `tools/harvest_slack.py` to pull reactions
   - Then revisit: HubSpot integration design, FL/TX state portal addition, NewsAPI upgrade decision

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
- Source list? -> SAM.gov + Grants.gov + Google News RSS (FL/TX state portals deferred to 1.5; see DECISIONS.md 2026-04-27)
- State persistence? -> Committed back to repo by the workflow (see DECISIONS.md 2026-04-27)
- Triage model? -> Sonnet 4.6 with prompt caching, one candidate per call (see DECISIONS.md 2026-04-27)
