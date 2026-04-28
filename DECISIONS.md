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

---

## 2026-04-27: Opportunity monitor runs on GitHub Actions, posts to private Slack channel
**Decision:** Daily run via GitHub Actions cron-style workflow. Notification via Slack incoming webhook to a private channel for Kevin (e.g. `#hohonu-intel`). Secrets in GitHub repo secrets.

**Alternatives considered:** macOS launchd (local cron); small cloud server; email digest.

**Why rejected:** Local cron silently skips when laptop is off or asleep, creating "missed it that day" risk. Cloud server is overkill for a daily 5-minute job. Slack channel beats email for persistent searchable history, one-click forwarding, and reaction-based triage. Adding Brian/Lisa later is a one-click channel invite, no infra change.

---

## 2026-04-27: MVP is Slack-only; no HubSpot logging until we learn from it
**Decision:** First version of opportunity monitor posts to Slack and logs to a JSONL audit file only. No HubSpot deals, notes, or pipeline created in MVP. Revisit HubSpot integration after a week of operating data.

**Alternatives considered:** Build full HubSpot deal pipeline + custom properties + auto-association in MVP.

**Why rejected:** Premature integration adds 2-3 days of work for a feature we may not need or may want differently. Slack-only ships fast and reveals real requirements. HubSpot integration design should be informed by what we actually want to do with surfaced opportunities, which we'll know after operating the Slack flow for a week.

---

## 2026-04-27: Filter via judgment, not numeric thresholds
**Decision:** Claude evaluates each candidate against a rubric (topic match, buyer match, geography match, actionability, plus boosters and auto-disqualifiers) but the surface/skip decision is qualitative. Three possible outputs: `SURFACE` (full Slack post), `WORTH_NOTING` (one-line Slack post in same channel), `SKIP` (JSONL only). Dimension scores and reasoning are included in every output for auditability.

**Alternatives considered:** Hard threshold mapping (8-10 surfaces, 5-7 digests, <5 skips).

**Why rejected:** Rigid thresholds create false negatives - e.g., a perfect-topic-match RFP outside active-market geography would auto-fail despite being worth knowing about. Pure judgment without structure risks drift. The hybrid: rubric forces structured analysis, judgment makes the call, reasoning stays transparent.

**Rubric (current version):**
- Topic match (0-4): water level / flood early warning specificity
- Buyer match (0-3): direct ICP through unrelated
- Geography match (0-2): active markets / coastal expansion / inland low-risk
- Actionability (0-1): live opportunity vs. historical
- Boosters (+1 max): warm-path county, co-op vehicle, "early warning system" wording
- Auto-disqualifiers: already awarded, expired, outside North America, pure private sector

Rubric lives as a config so it can be tuned without code changes.

---

## 2026-04-27: Source selection deliberated at start of Slice 1 chat (not assumed at scaffolding time)
**Decision:** The set of sources the monitor scans (SAM.gov, Grants.gov, Google News, state portals, county portals, industry pubs, etc.) is the most consequential design choice for the monitor. It deserves dedicated discussion at the start of the Slice 1 chat, not an assumption baked in here.

**Alternatives considered:** Lock SAM.gov as the MVP source now.

**Why rejected:** Sources determine what the system can ever see. A perfect filter on a bad source pile is worthless. Worth a focused conversation rather than a quick assumption. Likely starting point for that conversation: SAM.gov + Grants.gov + Google News (all have stable APIs); Florida + Texas state portals as Slice 1.5; county-level scraping deferred.

---

## 2026-04-27: Slice 1 source list confirmed: SAM.gov + Grants.gov + Google News RSS
**Decision:** MVP scans three sources only. SAM.gov for federal RFPs/solicitations (api.data.gov key), Grants.gov for federal NOFOs (no auth), Google News RSS for demand/procurement/funding/competitor news (no auth). FL MFMP and TX ESBD state portals deferred to Slice 1.5. USASpending.gov reserved for Slice 5 enrichment. County portals and paid platforms (GovWin, BidNet) deferred indefinitely.

**Alternatives considered:** Add NewsAPI.org for news (more flexibility); add USASpending.gov for forward signal; add state portals immediately.

**Why rejected:** NewsAPI free tier is too limited and paid is $449/mo — wait for evidence we're missing signal before paying. USASpending is historical awards, better fit for enrichment than monitoring. State portals require HTML scraping with no clean API; defer until we have operating data on whether federal sources are sufficient.

---

## 2026-04-27: State footprint expanded beyond FL/TX to full active customer book
**Decision:** Geography matching uses two tiers. Tier 1 (active customers): AK, CA, FL, HI, ME, MD, MA, MI, NY, NC, SC, TX, VA, WA. Tier 2 (coastal-adjacent expansion): LA, MS, AL, GA, NJ, CT, RI, NH, OR. State news queries split by region (Atlantic/Gulf, Pacific, Great Lakes/Mid-Atlantic) to keep URL length manageable and allow per-region tuning.

**Alternatives considered:** FL + TX only for MVP, expanding later.

**Why rejected:** Hohonu's actual customer book (per revenue sheet) spans both coasts plus Gulf/Great Lakes/Pacific Northwest/Alaska. Filtering geography to FL/TX would silently drop relevant signal in 12 other active states. Source: revenue book sheet `1wVsIyr2GN72ibZ2j0k8aFpA8sTnnb9mZKNjnYATrR-w`.

---

## 2026-04-27: Triage uses Claude Sonnet 4.6, one candidate per call, with prompt caching
**Decision:** Each candidate gets its own Anthropic API call with the rubric in the system prompt and `cache_control: ephemeral`. Returns strict JSON parsed into a `TriageResult`.

**Alternatives considered:** Batch N candidates per call to cut API requests; use Haiku 4.5 for cost.

**Why rejected:** Batching makes structured-output parsing fragile and complicates per-candidate error isolation. Cost at expected daily volume (~80 candidates) is trivial either way (under $1/day). Sonnet 4.6 makes noticeably better judgment calls on the rubric than Haiku for this kind of nuanced classification, and prompt caching makes the cost gap negligible after the first call. Revisit if daily volume grows past a few hundred or judgment quality is fine on Haiku.

---

## 2026-04-28: WORTH_NOTING goes to a daily CSV + Slack digest, not individual messages
**Decision:** SURFACE keeps individual rich Slack posts. WORTH_NOTING is written to `data/outputs/worth_noting-YYYY-MM-DD.csv` (committed back by the workflow) and surfaced to Slack as a single end-of-run digest message with the top-5 by total score, plus a count + path to the full CSV. SKIP is audit-log only.

**Alternatives considered:** Post each WORTH_NOTING as its own Slack message (original design); chunked digest with all items inline.

**Why rejected:** First real run produced 284 WORTH_NOTING items. Per-item posting (a) hits Slack's ~1 msg/sec webhook rate limit, (b) buries the SURFACE posts under hundreds of one-liners, and (c) makes the channel unusable to skim. Chunked digest fits in Slack but is still a wall of text. CSV is sortable/filterable in a spreadsheet, top-5 digest preserves cluster-pattern discovery in Slack ("three FL counties this week"), and channel stays clean.

---

## 2026-04-28: Hard score-floor demotes obvious-noise WORTH_NOTING to SKIP
**Decision:** After Claude returns its classification, demote any WORTH_NOTING/SURFACE with total score <5 to SKIP. Implemented in `triage.apply_score_floor()`. Reasoning gets prefixed with `[auto-floor: total<5]` so the audit trail is honest about what happened.

**Alternatives considered:** Tighten the rubric prompt and trust Claude's judgment; use a higher floor (≥6); make the floor configurable.

**Why rejected:** Audit log after first run showed ~17 of 284 WORTH_NOTING items scored ≤4/10 — uniformly competitor PR fluff, off-topic FEMA org news, generic water articles. Claude was being generous on classification despite scoring them low. A code-side floor is deterministic, cheap, and easy to remove if it ever bites a real signal. Floor at 5 (rather than 6) preserves Claude's discretion on borderline items.

---

## 2026-04-28: News queries require buyer intent, not just topic
**Decision:** `demand` queries in `configs/news_queries.yaml` rewritten to co-require an intent verb ("seeking", "hires", "selects", "deploys", "installs", "RFP", etc.) alongside the topic phrase. Bare `"water level monitoring"` removed.

**Alternatives considered:** Keep broad topic queries and rely on Claude triage to filter; drop `demand` category entirely.

**Why rejected:** Bare topic queries returned mostly product reviews and trade-press articles — high topic match (Claude scored topic=3-4) but zero buyer signal, classified WORTH_NOTING but useless. Filtering at query time is free; filtering at triage time costs a Claude call per noise item. Dropping the category loses real demand events (cities issuing RFPs, agencies hiring firms). Intent-loaded queries keep the signal and lose most of the noise.

---

## 2026-04-27: Monitor state (seen-set + audit log) committed back to the repo by the workflow
**Decision:** GitHub Actions workflow does `git add -f data/state/ data/outputs/ logs/` and pushes after each run. State files are gitignored locally but force-added by the bot.

**Alternatives considered:** External store (S3, GitHub Actions cache, dedicated branch).

**Why rejected:** S3 adds infra and a credential. Actions cache is best-effort, can evict, and is awkward to inspect. A dedicated `monitor-state` branch is cleaner long-term but adds complexity. Committing to main is the simplest thing that gives durability + inspectability — the audit log lives next to the code, easy to grep. Reconsider if commit noise on main becomes annoying; switching to a state branch later is a small change.
