# V15 — Systems Legibility: Planning Report

**Status:** Planning (no code). **Author:** Claude (brainstorming pass). **Date:** 2026-05-30.
**Branch:** `main`. **Repo:** `C:\GPT5-Projects\Dodgeball Simulator`.

This report decides the next milestone from Maurice's 2026-05-29/30 live playtest. It is
repo-grounded: every player-facing symptom below was validated against current source
before being classified, and the raw notes are reconciled in full in
[Appendix A](#appendix-a--complete-observation-inventory).

---

## 0. Orientation & Verification (required pre-flight)

| Check | Result |
|---|---|
| Repo path | `C:\GPT5-Projects\Dodgeball Simulator` |
| Branch | `main` |
| `git status --short` | Dirty: **uncommitted WIP** in `command_center.py`, `command_week_service.py`, `use_cases.py`, `web_status_service.py` (+ tests) and a batch of regenerated `playtest_output/*.png`. The source WIP **partly fixes the top finding from the last multi-week report** (foam aftermath scoreline → official game points; offseason "sim disabled" enum leak → player copy; playoff bracket game-points exposure). **This WIP is NOT on `main`.** |
| Does `main` contain the latest implemented design work? | Yes. Playtest-fixes Phases 0–8 all landed (incl. the §4 design **briefs** 4.1–4.8 — these are *handoff briefs, not finished UI*). The foam-scoreline / offseason-copy fixes are the exception: staged, not committed. |
| Does `docs/STATUS.md` match source? | Broadly yes. Gaps: (a) it does not mention the uncommitted foam-scoreline WIP; (b) it labels **V14 "in progress"** while V14's named thesis ("First Season Retention & **Sim Legibility**") is exactly what this playtest re-flags, and V14 Tasks 3 & 4 are unfinished. |
| Version/scope label for next milestone | **V15 — Systems Legibility.** Repo uses `VNN` milestone labels (V11–V14); STATUS §"Open Work" item 1 already states next post-V13 work "should be scoped as a new milestone." **V14 should be formally closed** (Tasks 1/2/5 shipped) with its two unfinished tasks carried into V15. |

### V14 completion status (checked, because it reframes "new vs follow-up")

| V14 Task | State on `main` | Evidence |
|---|---|---|
| 1 — Aftermath Primary Factor | **Shipped** | `match_explanation.py`; confirmed live in playtest ("Catch disparity … +10 swing") |
| 2 — Tactical Matchup Diff | **Shipped** | per STATUS; matchup band live |
| 3 — V2 Attribute explanations (`throw_selection_iq`, `catch_courage`) | **Partial / not legible** | attributes *displayed* in `PlayerDetailModal.tsx`, `DevelopmentResults.tsx`, but no explanatory tooltip; matches playtest "shown, not explained" |
| 4 — Match-day Staff Impact visibility | **Not landed legibly** | matches playtest "Staff Room basically useless, only OVR" |
| 5 — Lineup Liability tags | **Shipped (backend)** | `replay_proof.py`, `tests/test_liability_tags.py` |

**Conclusion:** this is not new territory — it is **finishing and generalizing V14's own thesis** under a fresh, properly-scoped milestone. V14 Tasks 3 & 4 fold into V15.

---

## 1. What Is Actually True on Current `main`

Validated against source (not inherited from the notes). Each row states the *verdict*, not the symptom.

| Surface | Verified reality on `main` |
|---|---|
| **Foam aftermath survivor hero** | **Already FIXED on `main`** (validated this pass — the playtest report inherited an older state). `MatchScoreHero.tsx:66` already calls `survivorDetail(survivors, isOfficial)` and `matchResult.ts` `formatScoreline` picks game points for official matches (committed, `16e485b "preserve foam-scoreline"`). The **uncommitted WIP** is a *secondary* surface — the backend post-week *dashboard* "Result" text lane (`command_center._result_scoreline`) + the bracket payload's game-points + the offseason "sim disabled" enum-leak copy. So Phase 0 = **land that staged WIP**, not re-fix the hero. |
| **Playoff seed-tiebreak reason** | **Already surfaced on `main`** (validated): `PlayoffBracket.tsx:90-116` renders a `SEED` chip *and* the `narrative_note` body when `decided_by !== 'regulation'` (Brief 4.6 War Room work). Multi-week report Finding #3 is stale. The WIP only adds game-points to the bracket payload so a foam 0-0 shows the set score, not "0-0 survivors". |
| **Recruit-board filter counts** ("All 8 / Strong Fit 0 / Visit-Ready 1") | **Not a miscount.** `DynastyOffice.tsx:236–239`: `Strong Fit = fit_score≥80`, `Visit-Ready = fit_score≥65` — overlapping thresholds on one metric. The **same ≥65 band is labeled "Visit-Ready" in the filter but "Neutral" on the card** (`ProspectCard.tsx:101`), and "Visit-Ready" has nothing to do with the Visit action. **Label-semantics defect**, not arithmetic. |
| **Recruit card "Orion / Ramirez" sub-name** | It is `prospect.hometown` (`ProspectCard.tsx:136`), styled like a surname. Legibility defect. |
| **Recruit card "#02"** | `priority` rank, zero-padded (`:134`). Low value as shown. |
| **Recruit grey/amber tone; archetype badge color** | `fit-${fitTier}` (strong/neutral/risk) and archetype-family color (`:26–37`). Both real, both unexplained. |
| **"INT 44%" / "FIT" / "OVR x–y"** | `interest` % / `fit_score` 0–100 (rendered big + as a meter, visually colliding with OVR) / `public_ovr_band`. Pure labeling/visual-collision. |
| **"Public Range" vs "OVR Range"** | Same `public_ovr_band` surfaced twice. Redundant. |
| **Visit action** | Currently a **repeatable weekly-slot** action (`ProspectCard.tsx:188–196`, `budget.visit`). Maurice wants once-per-season, high-impact → **mechanic redesign, deferred**; only its labeling is in V15. |
| **Program Credibility "01/02/03"** | `credibility.evidence[]` strings, zero-pad-indexed (`CredibilityStrip.tsx:65–72`). **Honesty risk (real):** jargon evidence copy ("youth development command week") of unverified truthfulness — audit each string is payload-backed. |
| **"Club prestige score 0" vs "Tier C · Regional"** | **Naming collision, not a within-card bug.** `club_prestige.prestige_score` is a *separate* persisted system (`persistence.py:516`; 0 on a fresh club; awarded for titles/facilities) that *feeds into* recruiting credibility (`recruiting_office.py:99–101`). The recruiting card shows the derived **credibility tier**; the "prestige score 0" is the upstream system surfaced under a clashing name. **Legibility defect (disambiguate the two concepts).** *Impl note: also confirm the credibility grade label can't default out of step with its own score.* |
| **Board Size / Reach Remaining / Visit Window** | Live **inside** the Credibility card's side column (`CredibilityStrip.tsx:75–93`) — recruiting-budget concepts misplaced under a prestige card. |
| **Staff hire/fire/interview** | **Exists** (`dynasty_office.py`, `server.py`: vacancy/interview/hire paths). Staff is a **legibility gap, not a missing system**. |
| **Staff/coach OVR floats** | **Real.** `staff_market.py:62–81` rounds ratings to `.1f` and formats `:.1f`. |
| **Season Preview bye-bar** | The colored bar **is** week-aligned (`SeasonPreview.tsx:88–101`); the **legend row** (`:127–135`) places `bye_text` by flex spacing, not under its bar — *reads* mislabeled. Verify precisely during impl (possible off-by-one in `bye_week` vs render). |
| **Settings nav** | **Real & intentional** — `disabled` + `title="Settings are coming soon"` (`App.tsx:160–166`). |
| **Growth "growing for every recruit"** | Development *is* headroom-proportional in the engine (playtest-fixes Phase 5), but the UI does not distinguish ordinary from high-upside growth → **legibility gap, not an engine bug. Do not reopen the engine.** |

---

## 2. Classification — Bug vs Clarity vs Deeper System/Data-Model

The whole point of strictness: these are **three different kinds of work** and must not be blended.

### Bucket A — Traceability bugs (the game's own numbers lie; fix first)
Legibility is worthless if the numbers are wrong. These break the decision-traceability north star directly.
**Validated this pass — several originally-listed items are already fixed on `main`:**
- ✅ Foam aftermath hero — **already fixed** (`MatchScoreHero` + `matchResult.ts`); Phase-0 work = **land the staged backend WIP** (dashboard "Result" text lane + bracket game-points payload + offseason enum-leak copy), which is already written with tests in the working tree.
- ✅ Playoff seed-tiebreak reason — **already surfaced** (`PlayoffBracket.tsx` renders the `narrative_note`).
- ✅ Credibility evidence — **already honest** (`recruiting_office.py:110-114`); reclassified to B/P3 (naming collision + jargon), not a bug.

**Genuinely open Bucket-A work for Phase 0:**
- **Staff/coach OVR float leak** — real (`staff_market` candidate path + `current_staff` rendered raw off a `REAL` schema at `DynastyOffice.tsx:198/313/320/323-324/379`). Fix at the backend payload boundary (round to int in `build_staff_market_state`) — no schema migration, fixes every display surface at once.
- **Recruit filter label semantics** — "Visit-Ready" vs "Neutral" for the same `fit≥65` band; "Visit-Ready" falsely implies visit eligibility.
- **Season Preview bye-bar legend alignment** — verify no off-by-one in `bye_week`; the colored bar is correct, the legend row may misread.
- **Land the staged foam-scoreline backend WIP** (commit it as the first, isolated step).

### Bucket B — Legibility / comprehension gaps (the milestone core)
The bulk. Each is "the value is correct but the player can't read it." Solved by the **shared toolkit** (§4), not bespoke copy:
- Player/coach **archetype** meanings (no glossary anywhere); attribute meaning (`throw_selection_iq`, `catch_courage`, V14 Task 3); growth language ("Ceiling NNN", "+22 room" → OVR headroom); ordinary-vs-upside growth distinction.
- Recruit card: hometown-as-name, "#02", grey/amber tone, archetype color, FIT-looks-like-OVR, INT, Public/OVR redundancy, "how scouting changes what you know" (gem/bust/range-tightening).
- Dynasty Office: Credibility "01/02/03" jargon, recruiting-budget placement, Weekly Recruiting jargon/empty space.
- Staff: **evidence of impact**, not one-line descriptions (V14 Task 4); Vacancies empty-space; Pipeline Candidates parity with recruiting.
- Standings copy: "V Chase Mode Through W01", "Record · Diff", "Playoff Line · Top 4" (redundant w/ the Playoff Cut diagram), "0 back of cut / 0 back of #1", "Next Results Needs", "Live Season Table / Week 01 / Top 4 / 7 Clubs", "Yr N", table legend, trailing `>` icon, Tiebreaker Read early-season redundancy.
- History copy: "Archive Through Season 4", "3 tracked archive moments", AVG OVR as a headline (low value), "Intent Balanced" + where to change Program Identity, milestone descriptions with **proof** ("Best Newcomer" → who + stats).
- Honest empty-states everywhere fake-ish: Championship Banners ("0/0 awards logged"), Alumni Lineage, League Wire (early-season), records.

### Bucket C — Deeper system / data-model / vision (DEFERRED to own specs)
New systems or restructures, not legibility. **Out of V15** (Maurice's call, 2026-05-30):
- **Program Archive evolving milestone-tree**, generated per-club from one shared source (incl. League History). *Own spec.*
- **Dynasty Office department-hub** restructure (Program Settings → tactics/training/medical/culture subpages). *Own spec.*
- **Recruiting visits as a major once-per-season action**. *Own spec.*
- **Sim-balance** (NOT legibility): foam draw density blunting standings; catch-lever dominance as Primary Factor. *Separate balance ticket; must not be touched by a presentation milestone.*

---

## 3. Milestone Thesis — V15: Systems Legibility

> The build now has the systems. The player cannot **read** them. V15 does not add systems and
> does not touch sim math. It builds a small **reusable legibility toolkit**, fixes the
> traceability bugs that make the numbers lie, and applies the toolkit — plus two new shared
> visual systems — to a prioritized set of decision surfaces, with honest empty states throughout.

Success = a first-season player can answer, on any screen: *what does this number mean, why does
this tag matter, what changed because of me, what is known vs unknown, what is flavor vs
mechanical, and where do I drill down for proof.*

**Hard invariant:** zero engine/sim/RNG changes. The engine-health probe staying green is a gate
(proves no drift). Everything in V15 is presentation-layer over existing payloads.

**Scope reality (honest framing).** With Maurice's chosen cut, V15 is a **large, multi-slice
milestone** that touches nearly every screen — it is *not* a small pass. Its discipline does **not**
come from screen count; it comes from three things and nothing else: (1) the **hard invariant**
above (no engine/math); (2) the **deferrals** in §5 (tree, office-hub, visit-mechanic, balance);
and (3) the **reusable toolkit** in §4.1, which prevents per-screen bespoke drift. The
fix-every-screen risk the brief warns about is contained by sequencing into independent slices
(§7), each its own spec→plan cycle — not by doing less.

---

## 4. In Scope

### 4.1 The Legibility Toolkit (build once — Phase 1)
Reusable primitives so screens are not fixed with bespoke one-off copy:
1. **Term explainer + terms registry.** One tooltip/popover component (AI-friendly: `role`,
   `aria-describedby`, keyboard/tap) backed by a single registry mapping every tagged term
   (player archetype, coach archetype, v2 attribute, stat, band, status) → plain meaning +
   "why it matters" + a **flavor-vs-mechanical** flag. Single source kills the unexplained-term
   class across Roster, Recruit Board, Standings, Staff.
2. **Known-vs-unknown (fog-of-war) system.** A consistent visual convention for
   scouted / estimated / hidden, applied to recruit OVR ranges, fit, interest, and "what scouting
   reveals." Honest by construction.
3. **Proof chip.** Generalize the existing Primary Factor `evidence_chips` into a reusable
   "this claim is backed by X" chip for milestone descriptions, records, dev, staff impact.
4. **Honest empty-state.** One convention, no fabricated data, for banners / alumni / league wire / records.

### 4.2 New shared visual systems (Maurice's expanded cut)
5. **Tiered pipeline emblem.** CFB-26-style marker: Tier 5 pink, Tier 4 cyan, Tier 3/2/1
   gold/silver/bronze. Shared component, reused wherever pipeline tier appears. (The
   known-vs-unknown system in §4.1 is the second of the two new visual systems.)
   *Caveat for handoff: this emblem is the one net-new "flashy UI" element in an
   otherwise comprehension-focused milestone — see owner decision #7.*

### 4.3 Non-structural consolidation (no new data model)
- Remove confirmed-dead **Trajectory Log**; collapse empty cards into honest empty-states.
- Wire **Standings row-click → the existing Club/League History modal**; drop the misleading trailing `>`.
- **League Wire → compact ticker** (state-aware; not a big empty card early season).
- Fold **Banner Shelf / Alumni Lineage** into tabs (interim; the future tree spec will absorb them — note the dependency).
- Remove redundant fields (Public Range), redundant titles (Standings header cluster).

### 4.4 Surfaces in scope, prioritized by decision-leverage
- **Tier 1 (in-season decision loop):** Recruit Board, Roster/Player Card (archetypes, growth, sort affordances), Lineup Editor (reorder clarity + Reset-to-Auto styling), Matchup/Standings copy + legend + row-click.
- **Tier 2 (program comprehension):** Dynasty Office / Program Credibility, Staff (impact evidence, V14 Task 4), Season Preview density.
- **Tier 3 (identity/history, lower leverage):** History copy + proof-backed milestones + honest empty-states + Program Identity discoverability; Settings-nav resolution; nav hamburger.

---

## 5. Out of Scope (explicit)
- Program Archive milestone-tree · Dynasty Office department-hub / Program-Settings subpages · recruiting-visits-as-major-action — **each its own future spec.**
- Sim-balance: foam draw density, catch-lever dominance — **separate balance ticket.**
- Any engine/RNG/scoring math change.
- Player **bio generation as new content/data** beyond surfacing what exists honestly (flavor-only copy is fine; net-new generative systems are not).

---

## 6. Owner Decisions Needed (before/within implementation)
1. **Settings nav:** hide until it has purpose (recommended) vs. give it a real purpose now. *(Default: hide.)*
2. **Phase 0 shipping:** land the traceability-bug pass (incl. the staged foam WIP) as its **own commit/PR before** the V15 toolkit, so trust fixes are not gated on UI work. *(Default: yes, separate.)*
3. **Credibility evidence honesty:** if an `evidence[]` string cannot be backed by real history, **remove it** rather than reword it. Confirm this honesty rule. *(Default: remove unbacked.)*
4. **Bio:** confirm V15 only **re-surfaces** existing identity data with personality copy; no new generative bio system. *(Default: surface-only.)*
5. **Foam draw density:** acknowledge it as a separate balance ticket and set its priority relative to V15. *(Default: parallel, owner-prioritized.)*
6. **Tabs-now vs tree-later (History):** confirm folding Banner Shelf/Alumni into interim tabs is acceptable knowing the future tree spec will re-home them. *(Default: yes, interim.)*
7. **Tiered pipeline emblem:** **RESOLVED 2026-05-30 — keep it in V15** (Maurice confirmed the net-new visual element is wanted).

---

## 7. Implementation Phase Order
- **Phase 0 — Traceability bug pass** (Bucket A, scoped after validation). Land the staged foam-scoreline + offseason-copy WIP; staff floats → int (payload boundary); recruit filter labels; bye-bar legend. *(Foam hero, seed-tiebreak reason, and credibility evidence were validated already-fixed/honest — out of Phase 0.)* Small, high-trust, shippable alone. **This is the slice planned in `phase-0-implementation-plan.md`.**
- **Phase 1 — Build the toolkit** (§4.1 primitives 1–4 + terms registry) with no screen consuming it yet, fully unit-tested.
- **Phase 2 — Tier-1 surfaces** consume the toolkit + the pipeline emblem + fog-of-war: Recruit Board, Roster/Player Card, Lineup Editor, Matchup/Standings copy & row-click.
- **Phase 3 — Tier-2 surfaces:** Dynasty Office/Credibility (recruiting-budget relocation), Staff impact (V14 Task 4), Season Preview density.
- **Phase 4 — Tier-3 + consolidation:** History copy/proof/empty-states/Program Identity, Trajectory Log removal, League Wire ticker, Banner/Alumni tabs, Settings-nav resolution, nav hamburger.
- **Phase 5 — Verification hardening** (gates below + Playwright legibility assertions).

Sequencing rationale: bugs before beauty (trust), toolkit before application (no bespoke drift),
highest decision-leverage screens first (retention impact), history/identity last (lowest leverage,
and partially blocked by the deferred tree spec).

---

## 8. Verification Gates
Required before V15 can be declared done:
- `python -m pytest -q` green (incl. new toolkit + honesty tests).
- `npm run build` && `npm run lint` clean (`frontend/`).
- `npm run e2e` zero failures.
- **`python tools/tier_engine_health_probe.py` unchanged** vs baseline — proves no sim drift (the legibility invariant).
- **New gate — no-orphan-term test:** every term tagged for the explainer resolves in the registry (fails CI if a screen references an undefined term).
- **New gate — honesty test:** no fabricated history/records; every proof chip and credibility-evidence string is backed by a real payload field (fails if a claim has no source).
- Per-phase browser verification on a **confirmed-fresh** dev PID (`scripts/dev-restart.ps1`) at 390×844, no horizontal overflow, no console errors.

---

## Appendix A — Complete Observation Inventory
Every raw note, mapped to classification and disposition. (A = traceability bug, B = legibility,
C = deferred system. P# = V15 phase; DEF = deferred spec; BAL = balance ticket.)

### Player Card
- Growth "growing for every recruit, even mid players" — **B/P2** (surface ordinary-vs-upside distinction; engine already differentiates).
- "Ceiling NNN" number-only, "+22 room" confusing — **B/P2** (label as OVR headroom via explainer).
- Bio boring — **B/P2** (personality copy over existing data; no new generative system — owner decision #4).

### Roster
- No explanation of any player archetype (tooltips needed, incl. **coach** archetypes) — **B/P1+P2** (terms registry).
- Archetype shown redundantly (as role + next to name) — **B/P2** (de-dup).
- Age sort direction unintuitive; no directional sort affordance on tables — **B/P2**.

### Lineup Editor
- Reorder not intuitive without reading copy — **B/P2**.
- "Reset to Auto" off the color scheme / unclear action class — **A-ish/P2** (styling clarity).

### Dynasty Office
- Program Credibility card bland; progress-bar clipping (score scale vs tier letters) — **B/P3** (+ layout polish).
- "01/02/03" jargon; "youth development command week" meaningless; "01" possibly untruthful — **A (evidence honesty audit)/P0** + **B/P3** copy.
- "Club prestige score 0" contradicts "Tier C·Regional" — **B/P3** (naming collision: separate `club_prestige` system vs recruiting credibility tier; disambiguate).
- Board Size / Reach Remaining / Visit Window misplaced under Credibility — **B/P3** (relocate to recruiting).
- Weekly Recruiting empty space + jargony descriptions — **B/P3**.
- Staff Room in office: only OVR, one dinky description — **B/P3** (impact evidence; = Staff page work).

### Recruit Board
- Overwhelming / needs streamlining — **B/P2**.
- Grey vs amber cards unexplained — **B/P2** (fog-of-war/explainer).
- "#02" low value — **B/P2** (explain or drop).
- "Orion/Ramirez" sub-name = hometown, misread as name — **B/P2** (relabel).
- Archetype not explained — **B/P1+P2**.
- FIT looks like OVR; FIT a confusing number; progress-bar terminology — **B/P2**.
- "INT 44%" ambiguous (= interest) — **B/P2** (relabel).
- "At Risk" unclear — **B/P2**.
- How scouting changes knowledge (gem/bust/range tighten/interest move) — **B/P2** (fog-of-war system).
- "Public Range" == "OVR Range" redundant — **A/B P0–P2** (remove redundancy).
- Pipeline → CFB-style tiered emblem (T5 pink … bronze) — **B/P2** (new shared emblem).
- Sorted "fit-desc" but no sort controls — **B/P2**.
- "ALL 8 / STRONG FIT 0 / VISIT-READY 1" — **A/P0** (label-semantics defect, not a miscount; reconcile thresholds & names).
- Player-card design upgrade / redundancy — **B/P2**.
- Visit should be once-per-season, high-impact — **C/DEF** (visit-mechanic spec; only labeling in V15).

### Program Settings
- No tooltips/descriptions/styling; unclear what each setting does/benefits — **B/P3** (legibility).
- Break into Dynasty Office department subpages — **C/DEF** (office-hub spec).

### History
- "Archive Through Season 4" / "3 tracked archive moments" jargon — **B/P4**.
- AVG OVR 64 useless headline — **B/P4** (demote/replace).
- Program Identity unfindable; "Intent Balanced" meaningless — **B/P4** (explain + discoverability).
- Championship Banners "0/0 awards logged / first banner still ahead" — **B/P4** (honest empty-state).
- Alumni Lineage same treatment — **B/P4** (empty-state + fold to tab).
- Program Archive evolving tree (lost vision; per-club from shared source incl. League History) — **C/DEF** (archive-tree spec).
- Program Arc upgrade — **B/P4**.
- Trajectory Log → remove (tree will represent it) — **B/P4** (remove now; tree later).
- Banner Shelf / Alumni → fold into tabs — **B/P4** (interim; tree re-homes later).
- Milestone descriptions bland; "Best Newcomer" lacks who/stats — **B/P4** (proof chips).
- League History page redundancy/card-folding pass (same as My Club) — **B/P4**.

### Staff
- No visual evidence of how each role helps; description insufficient — **B/P3** (V14 Task 4; proof chips).
- Vacancies card = big empty space when none — **B/P3** (honest empty-state).
- Pipeline Candidates needs audit / parity with recruiting (hire/fire exists) — **B/P3**.
- Coach OVR floats still present — **A/P0** (`staff_market.py` → int).

### Standings / League Office
- Best page overall; still needs tightening — **B/P2**.
- "V Chase Mode Through W01" confusing — **B/P2**.
- "Record · Diff" awkward title — **B/P2**.
- "Playoff Line · Top 4" redundant with Playoff Cut diagram — **B/P2**.
- "0 back of cut / 0 back of #1" confusing — **B/P2**.
- "Next Results Needs" confusing — **B/P2**.
- "Live Season Table / Week 01 / Top 4 / 7 Clubs" redundant cluster — **B/P2**.
- "Yr N" confusing — **B/P2**.
- Club archetype info density (cherry-pick from Roster) — **B/P2**.
- Row-click → same modal as Club/League History — **B/P2** (non-structural consolidation).
- Table legend needs improvement — **B/P2**.
- Trailing `>` icon misleading — **B/P2** (remove).
- League Wire → persistent ESPN-style ticker — **B/P4** (ticker).
- Tiebreaker Read redundancy / early-season meaninglessness — **B/P2** (state-aware).

### Season Preview
- Week bar chart "mislabeled" (Week 2 Bye under 4th bar) — **A/B P0** (legend alignment; verify no `bye_week` off-by-one).
- Page dull / needs density — **B/P3**.

### Navigation / Shell / Settings
- Settings greyed out forever — **B/P4 + owner decision #1** (hide until purposeful).
- Nav hamburger collapse — **B/P4**.

### From the 2026-05-29 multi-week report (carried, for completeness)
- Foam aftermath survivor hero contradicts games — **A/P0** (WIP staged).
- Foam regular-season draw density blunts standings — **C/BAL** (balance ticket).
- Playoff seed-tiebreak under-explained — **A/P0** (surface `tiebreaker_reason`).
- Week-1 "No growth logged" vs later weeks inconsistent — **B/P3** (clarify).
- Catch disparity = Primary Factor in 100% of sampled losses — **C/BAL** (lever-dominance probe).

---

## Appendix B — Sources Consulted
`AGENTS.md`, `CLAUDE.md`, `docs/README.md`, `docs/STATUS.md`, `docs/specs/MILESTONES.md`,
`docs/specs/2026-05-28-v14-first-season-retention-sim-legibility/sprint-plan.md`,
`docs/specs/2026-05-29-section4-design-briefs/README.md`,
`docs/reviews/2026-05-29-playtest-multiweek-report.md`, and current source:
`command_center.py`, `use_cases.py`, `command_week_service.py`, `web_status_service.py`,
`staff_market.py`, `dynasty_office.py`, `frontend/src/App.tsx`,
`frontend/src/components/DynastyOffice.tsx`, `dynasty/ProspectCard.tsx`,
`dynasty/CredibilityStrip.tsx`, `PlayerDetailModal.tsx`,
`match-week/command-center/SeasonPreview.tsx`.
*(Pare MCP was available; standard shell/git + repo search tools were used for this read-only pass.)*
