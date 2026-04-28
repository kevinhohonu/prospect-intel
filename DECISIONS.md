# Decision Log

Append-only. Each entry: date, decision, alternatives considered, why we chose this. Future chats read this before changing architecture.

---

## 2026-04-27: Spreadsheet remains research workspace; HubSpot is execution layer
**Decision:** Google Sheet stays as the place where Upworker + Kevin do research and enrichment. HubSpot is where Lisa works for outreach. Contacts graduate from sheet to HubSpot when their status = "Ready for Outreach". Engagement data flows back to sheet for visibility into what's been touched.

**Alternatives considered:** Make HubSpot the single source of truth and import all spreadsheet data into custom properties.

**Why rejected:** HubSpot is poor at bulk research workflows and ad-hoc structured fields. Forcing the Upworker to research inside HubSpot would slow the research pipeline. Sheet → HubSpot graduation is how most BDR ops actually run in practice.

---

## 2026-04-27: Build in vertical slices, not foundation-first
**Decision:** Each slice ships something usable. Slice 1 = opportunity monitor MVP. Slice 2 = FL warm follow-up list. Each chat scoped to one slice.

**Alternatives considered:** Build the full data sync layer first (custom HubSpot properties, full sheet → HubSpot reconciliation), then build value layers on top.

**Why rejected:** Foundation-first means no value for weeks. With time pressure (BDR ramp + Texas co-op + May 19 webinar), value needed early. Vertical slices also reduce risk of building the wrong abstraction.

---

## 2026-04-27: Opportunity monitor logs to HubSpot, not just to email
**Decision:** Findings persist as records in HubSpot (Deals in a dedicated pipeline or Notes on company records). Email/Slack is notification only, not the record. Claude scores each hit for relevance; only above-threshold hits trigger notifications.

**Alternatives considered:** Daily email digest as the primary record; simple keyword grep with no scoring.

**Why rejected:** Daily email has a "missed it that day" failure mode - if you skip a digest, you lose findings. Persistent log + scoring gives signal/noise control without losing data. HubSpot as the log means findings are already where the sales work happens.

---

## 2026-04-27: 24 FL EM drip-engaged contacts are first BDR outreach target
**Decision:** Before any cold outreach, Lisa works the 24 FL Emergency Management Directors who opened the drip campaign emails (and the 1 who responded). These are warmer than net-new and faster to convert.

**Alternatives considered:** Start cold with full Tier 1 list of all FL EM Directors.

**Why rejected:** Half-day of work to extract this list, likely produces meetings, doesn't waste BDR ramp on cold dials.

---

## 2026-04-27: Project workspace at `Documents/Claude/prospect-intel/`, sibling to `recon/` and `orchestrator/`
**Decision:** Mirror the pattern Kevin already uses for AI-assisted tools - separate project directory at the same level as other Claude projects. Self-contained: own `.env`, own git history, own docs.

**Alternatives considered:** Build inside an existing project; build inline in the Claude/ root.

**Why rejected:** Clean separation per Kevin's preference. Avoids cross-contamination with orchestrator/ or recon/.
