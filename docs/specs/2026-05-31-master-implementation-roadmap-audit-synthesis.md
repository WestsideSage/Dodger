# Master Implementation Roadmap — Audit Synthesis

Date: 2026-05-31
Status: Active planning artifact (synthesis of 14 teardown lanes in `docs/teardowns/`)
Authority: Subordinate to `AGENTS.md`, `docs/STATUS.md`, source/tests. This roadmap
sequences work; it does not redefine the integrity contract.

> **⚠ AMENDED 2026-06-01 — read with `docs/specs/2026-06-01-master-roadmap-grill-resolutions.md`
> and `docs/adr/0002-faithfulness-over-scope-restraint.md`.** A `/grill-with-docs` review
> resolved 17 open design forks and, with the owner's explicit aggregate-scope sign-off,
> **reversed this doc's no-scope-creep stance: faithfulness-of-claims now outranks
> integrity-of-restraint (ADR 0002).** Where this roadmap and the resolutions log disagree,
> **the resolutions log wins.** Headline changes:
> - **WT-20 wording corrected:** the engine *announces* No Blocking (official_engine.py:593)
>   but does **not enforce** it; throw-clock is config-only; opening-rush absent. Enforcing
>   No Blocking is **primary-source-confirmed (usadodgeball.com/rules, 2026)** as the real
>   tie/decisiveness mechanism — it is the keystone of the new milestone, not "do-not-do-yet."
> - **WT-8, WT-20, WT-31 are no longer deferred** — they move into a new gated **"Official
>   Live Rules" milestone** (sequenced after the Phase 0–7 trust pass). **WT-31 folds into
>   WT-20** (No Blocking enforcement); there is **no** separate sudden-death overtime.
> - **WT-25** flips the backend (Tier 5 = strongest) and **must land in the same phase as
>   the WT-23 parity probe.** **WT-30** = observed-tendencies-from-tape with an always-on
>   cold-start. **WT-1** must narrate `headshot_thrower_out`, not a generic miss. **WT-5**
>   gets a single-source ruleset display-name. See the resolutions log for all 17.

> **Ordering principle (read this first).** Phases below are ordered by **ascending
> blast-radius / risk**, *not* by descending severity. True severity lives in the
> Canonical Work Items table. The dependency graph reconciles the two by naming *why*
> a high-severity item may be scheduled after a lower-severity one. The one **Blocker**
> (catch-posture inversion, WT-6) is Phase 2 — not buried — because it is contained and
> gated, and Phase 1 carries literally zero engine/persistence risk while WT-6 carries a
> probe-retune. WT-6 has **no dependency** on Phase 1 and may be parallelized.

---

## Executive verdict

The 14 audit lanes are **high quality and mostly implementation-ready, but require light
pruning and explicit sequencing before any code is written.** Three caveats:

1. **Some findings are already shipped or doc-stale.** The Documentation lane itself proves
   V14 is implemented while STATUS/MILESTONES still call it "in progress," and the archetype-
   naming spec is already in source. Do not re-implement shipped work; close the docs first.
2. **At least one "High" needs downgrade after path verification.** The AI-tactics "stale
   clubs" finding (AI Opponent F1) does **not** affect the primary user match path:
   `/api/command-center/simulate` → `use_cases.simulate_week` already reloads clubs. The bug
   is real only in the secondary `/api/sim*` routes and playoff sim → **Medium**, not High.
3. **The Official-Rules-Fidelity lane partially conflicts with the integrity / no-scope-creep
   contract.** Wiring No Blocking, throw-clock penalties, and opening-rush activation into the
   live autonomous engine is a new milestone's worth of engine work with golden-log/conformance
   regression risk. **Do the honest-copy + conformance-depth fixes now; defer the engine-wiring.**

Net: **Ready to implement Phases 0–7 (incl. 3b) as sequenced. Do NOT implement** the official-rules
engine-wiring (WT-20), the architecture boundary refactor (WT-27), or speculative frontend
perf work (WT-28) as part of this pass. Six items were design-gated; **all six were resolved
2026-05-31** and are now scheduled (WT-17→P4, WT-25→P7, WT-29/30/32→P3b, WT-31→P2 follow-up) — see
"Resolved design decisions." Two resolved toward the higher-scope option (WT-25 backend flip,
WT-30 real intel), which moved them out of the cheap copy buckets.

Verifications performed during synthesis (source-confirmed, not taken on audit's word):
- Replay `-` placeholder lives in **two** render paths: `replay_proof.py:172` (proof labels,
  used at `:213`/`:215`) and `replay_service.py:472-475` (event-log labels). Fix touches both.
- Primary sim path `/api/command-center/simulate` → `_simulate_week` (reloads clubs);
  `run_simulation_command` (stale clubs) only backs `/api/sim`, `/api/sim/week`, playoff sim.
- Catch-posture inversion confirmed: `official_engine.py:686` passes `policies[offense_team]`
  into `resolve_throw`; `official_resolution.py:108-111` uses it for the **defender's**
  `decide_catch_attempt`. Gate `test_official_engine_balance.py::test_official_ovr_curve_gate`
  is statistical/re-runnable; generic `phase1_baseline.json` is untouched by official-engine edits.

---

## Canonical work items

Severity is the **true** audit severity. "Phase" is the risk-managed schedule slot.

| ID | Canonical issue / work item | Source audits | Severity | Player-trust impact | Likely files | Needs design? | Needs tests? | Phase |
|----|------------------------------|---------------|----------|---------------------|--------------|---------------|--------------|-------|
| WT-1 | Replay shows placeholder `-` targets on miss events | Product Coherence, New Player, Copy/Voice | High | Sim looks broken at the exact moment of "watch and trust it" | `replay_proof.py:172,213`, `replay_service.py:472` | No | Yes | 1 |
| WT-2 | Official aftermath headline narrates survivor counts, not game points | Copy/Voice | High | 0-0 game-point draw can read as a blowout | `voice_verdict.py:192`, `use_cases.py:644` | No | Yes | 1 |
| WT-3 | Broadcast last-meeting scoreline formats survivors for official matches | Architecture, Copy/Voice | Medium | History contradicts the official scoreboard | `broadcast.py:314` (read existing `home/away_game_points`) | No | Yes | 1 |
| WT-4 | Readiness-gate blocking detail hidden in `title`/tooltip only | Copy/Voice, Accessibility(F7), New Player | Medium | "Why can't I sim?" is hover-only / not announced | `PreSimDashboard.tsx:716` | No | Yes | 1 |
| WT-5 | Scoring-model labels read like keys (`USAD FOAM`/`OFFICIAL_FOAM`) | Copy/Voice | Low | Implementation register leaks to players | `MatchReplay.tsx:247`, `matchResult.ts:36` | No | Yes | 1 |
| WT-6 | **Official catch-posture policy inversion** ("go for catches" helps the opponent catch *your* throws) | Simulation Balance | **Blocker** | Default `official_foam` tactics are actively inverted vs the player | `official_engine.py:686`, `official_resolution.py:108` | No (narrow re-tune) | Yes | 2 |
| WT-7 | Moment spam: official `dramatic_catch` ~24/match, no cap/rarity | Simulation Balance | High | Recognition moments become replay noise | `official_engine.py:727` | No | Yes | 2 |
| WT-8 | Rec `rush_target` / shown rush modifiers are presented as proof but inert in resolution | Simulation Balance | Medium | Presents mechanical proof that does nothing | `rec_engine.py:837` | Light | Yes | 2* |
| WT-9 | Roster Lineup Editor saves a lineup the open weekly plan ignores | Decision Traceability | High | Promote a starter, lock, still field the old six | `web_status_service.py:224`, `command_center.py:255`, `use_cases.py:982` | No | Yes | 3 |
| WT-10 | Inline `/simulate` lineup update bypasses validation, can persist non-roster IDs | Security, Decision Traceability | Medium | Saved plan/history can lie about the fielded six | `use_cases.py:1005` vs `web_status_service.py:224` | No | Yes | 3 |
| WT-11 | AI tactics use stale clubs in `run_simulation_command` (secondary + playoff path) | AI Opponent, Decision Traceability | Medium (was High) | Rival looks adaptive in data, not on court — non-primary path | `command_week_service.py:415,449` | No | Yes | 3 |
| WT-12 | Localhost form POST can mutate the active career (no CSRF/launch token) | Security | High | Drive-by simulate/fast-forward/unload while server runs | `server.py:546` | Light (token shape) | Yes | 4 |
| WT-13 | Production SPA fallback allows path traversal out of `frontend/dist` | Security | High | Local repo files exposed via the local server | `server.py:1348` | No | Yes | 4 |
| WT-14 | Build-from-scratch accepts duplicate / invalid founding roster IDs | Security, Save/Resume | High | Permanent save corruption (one player, six slots) | `save_service.py:269,301` | No | Yes | 4 |
| WT-15 | `read_save_meta()` migrates/mutates the save on listing | Save/Resume | High | Listing a save silently upgrades it with no backup | `save_service.py:65`, `persistence.py:1099` | No | Yes | 4 |
| WT-16 | Corrupt career cursor silently becomes `SPLASH` instead of failing loud | Save/Resume | High | Damaged career pretends to be a fresh start | `persistence.py:2705`, `test_career_state.py:96` | No | Yes (rewrite existing) | 4 |
| WT-17 | Backend ruleset default (`None`) lags frontend `official_foam` | Save/Resume | Medium | API/automation-created careers silently go generic | `server.py:373,380`, `career_setup.py` | ✓ Resolved: flip to `official_foam` | Yes | 4 |
| WT-18 | Ruleset selector copy is factually wrong (cloth "6x" balls; actually 5) + no-sting overpromise | Official Rules, Copy/Voice | Medium | Setup copy lies about the rules the player picked | `SaveMenu.tsx:46`, `rulesetExplanations` | No | Yes | 5 |
| WT-19 | Conformance matrix only asserts file existence + `"def test_"` | Official Rules, Test Suite | Medium | "Complete conformance" can stay green while behavior drifts | `test_official_conformance_matrix.py:41` | No | Yes | 5 |
| WT-20 | Live autonomous engine does not exercise No Blocking / throw-clock penalties / opening-rush activation | Official Rules | High | Player-facing "USA Dodgeball 2026.1" overclaims live enforcement | `official_engine.py:470,570,589` | **Yes (new milestone)** | Yes | **Do-not-do-yet** |
| WT-21 | Accessibility hardening cluster (mouse-only rows/club select, modal focus, label assoc, status/alert roles, tab semantics) | Accessibility(F1–8) | High (cluster) | Keyboard/SR users blocked from core + entry-path flows | `Roster.tsx:359`, `SaveMenu.tsx:768`, modals, `ui.tsx:187` | Light (per-surface) | Yes | 6 |
| WT-22 | No browser test proves a changed decision reaches aftermath/replay text | Test Suite, Decision Traceability | Medium | Regression gap: UI could render stale text vs backend proof | `tests/e2e/*` | No | Yes (is the test) | 7 |
| WT-23 | No executable AI archetype parity probe (STATUS claims a 50-season sweep) | AI Opponent | Medium | Rival ecosystem could drift to one dominant archetype unseen | new `tools/` probe + test | No | Yes (is the test) | 7 |
| WT-24 | Standings identity label can diverge from mechanical `program_archetype` | AI Opponent | Medium | UI explains a rival with a label that is not its real archetype | `web_status_service.py` (`_CLUB_IDENTITY_LABELS`) | Light | Yes | 7 |
| WT-25 | Pipeline tier semantics inverted: UI "tier 5 Elite = better" vs backend "tier 1 stronger" | Copy/Voice | High | Teaches players to value prospects backwards | `recruiting_actions.py:37` (base_interest), `terms.ts:138`, `PipelineEmblem.tsx` | ✓ Resolved: **flip backend** (tier 5 = strongest); now a signing-math + test change, not copy-only | Yes | 7 |
| WT-26 | Docs / source-of-truth close-out (V14, broken links, mobile gates, route teardowns/) | Documentation | Medium (high-leverage) | Agent-facing, not player-facing | `docs/STATUS.md`, `docs/specs/MILESTONES.md`, specs | No | N/A | 0 |
| WT-27 | Split recruitment/scouting/ai_pm/broadcast: pure rules vs persistence service | Architecture | High (internal) | None direct (broadcast scoreline rides WT-3) | `recruitment.py`, `scouting.py`, `ai_program_manager.py`, `broadcast.py` | Yes | Yes | **Do-not-do-yet** |
| WT-28 | Frontend perf: replay O(n)/tick, tab refetch, PolicyEditor save-per-change, unbounded lists, timer cleanup | Frontend Perf | High (suspected) | Mostly desktop-fine today; profile-first | `MatchReplay.tsx`, `useApiResource.ts`, etc. | No | Yes | **Do-not-do-yet** (timer cleanup may ride 6) |
| WT-29 | Fast-forward bypasses readiness / premature first-week CTA | Decision Traceability, Product Coherence | Medium | New players skip the teaching loop | `PreSimDashboard.tsx:822`, `use_cases.py:1174` | ✓ Resolved: **confirm dialog** disclosing skipped decisions | Yes | 3b |
| WT-30 | Scout Opponent clears a gate but reveals no intel | New Player, Decision Traceability | High | "Scout" reads as a checklist button, not learning | `server.py:546`, `week_briefing.py:103`, `PreSimDashboard.tsx:581` | ✓ Resolved: **reveal real scouted intel** (new mechanic — Tactical Diff flips from Unscouted); not a rename | Yes | 3b |
| WT-31 | Official even-rung draw density ~30% | Simulation Balance | Medium | Standings can feel draw-heavy at even matchups | `official_scoring.py:56`, `official_engine.py:974` | ✓ Resolved: **accept honest draws + framing; re-measure after WT-6** (no engine change now) | Maybe (post-WT-6) | 2-followup |
| WT-32 | First-loss aftermath "no one thing to fix" with no controllable lesson | New Player | High | Answers the wrong question after a loss | `match_explanation.py:225`, `PrimaryFactorCard.tsx` | ✓ Resolved: **add separate Manager Lesson** when factor inconclusive (Primary Factor stays event-derived) | Yes | 3b |

`*` WT-8: keep the **safe** interpretation ("stop presenting inert rush modifiers as proof").
Only *wire* `rush_target` into resolution if design explicitly wants it — that changes outcomes
and would require golden/probe updates, promoting it out of the cheap copy-truth bucket.

---

## Dependency graph

**Hard prerequisites (must precede):**
- **WT-26 (docs) → before everything.** No code dependency, but it removes the "is V14 active?"
  ambiguity every later agent will otherwise re-derive. Cheapest, highest orientation leverage.
- **WT-9 → WT-22.** The Playwright decision-proof test must assert the *fixed* lineup-to-sim
  behavior; writing it before WT-9 lands would encode the bug.
- **WT-9 ↔ WT-10 (same phase).** Both touch the lineup persistence/validation path; do WT-9
  (editor→active plan) first, then WT-10 (inline-sim validation) reuses the same validator.
- **WT-23 ↔ WT-26.** STATUS currently overclaims a "50-season parity sweep." Land the probe
  (WT-23) so WT-26 can state the truth instead of deleting the claim with nothing behind it.
- **WT-16 carries a test rewrite.** `test_career_state.py:96` currently *locks* the SPLASH
  fallback. The fix must replace those expectations with "raises clear corrupt-save error" in
  the same change — not a follow-up.

**Independent / parallelizable:**
- **WT-6 (Blocker) has no external dependency.** Its only coupling is internal: after switching
  the defender's catch decision to the defense policy (rec already does this at `rec_engine.py:640`),
  re-run the OVR probe and re-tune `_CATCH_SLOPE`/`_CATCH_BIAS` *only if the curve moved*, then
  re-assert `test_official_engine_balance`. It can run in parallel with Phase 1.
- **WT-7 (moment caps)** is independent of WT-6 (presentation rate, not outcome).
- **WT-1..WT-5** are mutually independent presentation fixes.

**Design gates — RESOLVED 2026-05-31** (see "Resolved design decisions"): WT-17 → Phase 4,
WT-25 → Phase 7, WT-29 / WT-30 / WT-32 → new **Phase 3b**, WT-31 → Phase 2 follow-up. None blocked
Phases 0–3. Two were resolved toward the **higher-scope** option: WT-25 (flip backend, not relabel UI)
becomes a signing-math + test change; WT-30 (reveal real intel, not rename) becomes a new mechanic.

**Cross-cutting guard:** WT-4 must satisfy **Accessibility F7** (visible text **and** accessible
name) in Phase 1, so it is not half-done as "copy" and re-opened in Phase 6. WT-3 is the
**scoreline read/format only**, explicitly **not** the `broadcast.py` boundary/DTO refactor (WT-27).

---

## Recommended implementation phases

### Phase 0 — Docs & source-of-truth close-out
- **Goal:** A new agent can tell, in one read, what the single active work item is.
- **Work items:** WT-26.
- **Non-goals:** No code, no test, no spec rewrites beyond status/links; do not delete history (archive/banner).
- **Likely files:** `docs/STATUS.md`, `docs/specs/MILESTONES.md`, the V14 sprint plan, the
  archetype-naming spec, `docs/README.md`/`GEMINI.md` source-of-truth wording, route `docs/teardowns/`.
- **Risk:** Minimal (docs only).
- **Tests / commands:** path-reference check over root docs (`Test-Path` the backticked `docs/...` links); no pytest needed.
- **User-visible impact:** None for players; large for agents.
- **Stop conditions:** Stop if closing V14 requires asserting an *un*shipped task is shipped — verify each against source first.

### Phase 1 — Player-facing presentation truth (IMMEDIATE FIRST)
- **Goal:** Every number and label a first-time player reads matches what actually happened. No engine math touched.
- **Work items:** WT-1, WT-2, WT-3, WT-4, WT-5.
- **Non-goals:** No engine/scoring/balance change; no persistence change; no `broadcast.py` boundary refactor (read existing game-point columns only); no new deps; no routing/auth change.
- **Likely files:** `replay_proof.py`, `replay_service.py`, `voice_verdict.py`, `broadcast.py` (read path only), `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`, `MatchReplay.tsx`, `matchResult.ts`.
- **Risk:** Low (presentation only; no golden-log or balance surface touched).
- **Tests / commands:** new unit tests (no `targets -`/`vs -` in replay labels; official 0-0/0-3 headline ≠ survivor score; broadcast official last-meeting uses game points); `python -m pytest -q`; `npm run build`; `npm run lint`; focused Playwright `official-rules-replay.spec.ts`.
- **User-visible impact:** Replay reads cleanly; official headlines/scoreboards agree; readiness blockers are visible and announced; ruleset labels read like names.
- **Stop conditions:** Stop if WT-2/WT-3 cannot get game-point facts without reshaping the scoring model — that is a deeper contract change, not a copy fix.

### Phase 2 — Official catch-posture Blocker (+ moment caps)
- **Goal:** On the default `official_foam` engine, choosing "go for catches" helps the team that chose it — tactics are honest. Recognition moments stay rare.
- **Work items:** WT-6 (Blocker), WT-7. (WT-8 optional, safe variant only.)
- **WT-31 follow-up (resolved):** after WT-6 lands, re-run the official probe and record the new
  even-rung draw density. If draws are acceptable, WT-31 needs only framing copy (no engine change);
  only escalate to a seeded tiebreak if they remain uncomfortable. Do **not** add a tiebreak pre-WT-6.
- **Non-goals:** Do **not** change the USA-Dodgeball catch rule itself (catch outs thrower + resurrects a defender stays). Do not touch the generic `MatchEngine` or `phase1_baseline.json`. Do not wire `rush_target` into outcomes (that is a separate, design-gated change).
- **Likely files:** `official_engine.py` (pass defense policy for the target's catch decision; cap `DramaticCatch` emission), `official_resolution.py`, `tests/test_official_engine_balance.py`, possibly `_CATCH_SLOPE`/`_CATCH_BIAS` constants.
- **Risk:** Medium (engine balance) but **contained and gated** — statistical gate is re-runnable, generic golden log unaffected.
- **Tests / commands:** new official integration test (defender's `catch_posture` changes B's catch attempts when B defends; equal-rating "go for catches" is not catastrophically self-harming); moment upper-rate band per driver; re-run `tools/tier_engine_health_probe.py --driver both --trials 400` and `tools/official_match_probe.py --ruleset official_foam`/`official_cloth`; `python -m pytest -q`.
- **User-visible impact:** Official tactics finally reward the chooser; replays stop spamming "DRAMATIC CATCH."
- **Stop conditions:** Stop and report if the catch-posture fix drops the OVR slope below the 0.10 gate or the top-rung floor below 60% even after a bounded `_CATCH_SLOPE`/`_CATCH_BIAS` re-tune — that means a deeper resolution issue, escalate rather than over-tune.

### Phase 3 — Lineup & plan truth
- **Goal:** The six the player sees is the six that plays; the plan shown is the plan that runs; rival tactics reach every sim path.
- **Work items:** WT-9, WT-10, WT-11.
- **Non-goals:** No new lineup UI; no engine change; do not redesign the weekly-plan schema.
- **Likely files:** `web_status_service.py`, `command_center.py`, `command_week_service.py`, `use_cases.py`, `match_orchestration.py`.
- **Risk:** Medium (touches the live weekly-plan persistence path).
- **Tests / commands:** service test (save `/api/lineup` with a different six during pre-match → `/api/command-center` → simulate → assert the edited six is fielded); `/api/command-center/simulate` with non-roster/dup/wrong-count IDs returns 400 and persists nothing; command-week test that a persisted AI archetype tactic reaches the simulated match policy; `python -m pytest -q`.
- **User-visible impact:** Lineup edits stick into the match; saved history stops lying about the fielded six.
- **Stop conditions:** Stop if making `/api/lineup` update the active plan regresses the season-default editor behavior preserved across rollover/signings (Phase 1 of the May playtest-fixes plan) — preserve both.

### Phase 3b — Onboarding legibility features (resolved design gates)
- **Goal:** Three net-new player-facing features that make first-season decisions legible, scheduled after the core decision-truth fixes land.
- **Work items:** WT-30 (reveal real scouted intel), WT-32 (Manager Lesson on inconclusive loss), WT-29 (fast-forward confirm dialog).
- **Non-goals:** Do **not** fold the Manager Lesson into Primary Factor (it stays event-derived). Do not add hidden pre-match information the player could not otherwise see — scouted intel must be derived from real opponent data and disclosed as scouted. Fast-forward stays available (do not remove it).
- **Likely files:** `server.py` (scout route), `week_briefing.py`, `match_explanation.py` (+ a Manager Lesson helper), `PreSimDashboard.tsx` (Tactical Diff + fast-forward confirm), `PrimaryFactorCard.tsx` / aftermath, `tactical_diff.py`.
- **Risk:** Medium (WT-30 is a new reveal mechanic; WT-32 adds derived aftermath logic).
- **Tests / commands:** scout reveals a concrete delta (Tactical Diff leaves `Unscouted`); inconclusive-loss aftermath renders a controllable Manager Lesson alongside next-best-improvement; fast-forward requires confirmation listing skipped decisions; `python -m pytest -q`; `npm run build`/`lint`; focused Playwright.
- **User-visible impact:** "Scout" actually teaches; a close loss explains what the manager can change; fast-forward no longer competes silently with the first-week loop.
- **Stop conditions:** Stop if "real scouted intel" would require exposing AI plan internals the player should not see pre-match — keep it to honest, derivable opponent facts (file, threat, lineup-shape), not the opponent's secret adaptation.

### Phase 4 — Save & security integrity
- **Goal:** Local-first does not mean unguarded: no drive-by mutation, no file leak, no corrupt save written or silently migrated.
- **Work items:** WT-12, WT-13, WT-14, WT-15, WT-16, **WT-17** (resolved: flip backend default to `official_foam`, legacy `generic`/`None` still honored).
- **Non-goals:** Do not add authentication/accounts; do not change the SQLite schema; do not break legacy generic saves.
- **Likely files:** `server.py` (mutation-token check, SPA fallback hardening), `save_service.py` (unique-roster validation, atomic create, non-mutating meta read), `persistence.py` (corrupt-cursor fail-loud), `test_career_state.py` (rewrite SPLASH expectations).
- **Risk:** Higher blast radius (every POST route + persistence). Sequence after the trust fixes precisely so this lands on a clean base.
- **Tests / commands:** form POST to every mutating route → 403/415; encoded `..` traversal → 404/index, not file; duplicate/invalid founding IDs → 400 with no `.db` left behind; `read_save_meta()`/`/api/saves` do not change `schema_version`; corrupt cursor raises a clear error; `python -m pytest -q`.
- **User-visible impact:** Mostly invisible; prevents catastrophic save/path/CSRF failures.
- **Stop conditions:** Stop if the mutation-token scheme would break the existing same-origin frontend flows — the token must ride the launcher, not require user action.

### Phase 5 — Official fidelity: copy + conformance depth (NOT engine-wiring)
- **Goal:** Player-facing rules copy is factually correct, and "conformance" proves behavior, not file existence.
- **Work items:** WT-18, WT-19. (WT-20 is explicitly deferred — see Do-not-do-yet.)
- **Non-goals:** Do **not** wire No Blocking / throw-clock / opening-rush activation into the live engine in this phase.
- **Likely files:** `SaveMenu.tsx` / ruleset-explanation copy, `tests/test_official_conformance_matrix.py`, the per-section official test files.
- **Risk:** Low-Medium.
- **Tests / commands:** frontend ruleset-copy snapshot (cloth = 5 balls); conformance matrix maps each must-have section to explicit named test functions/markers; `python -m pytest -q`; `npm run build`/`lint`.
- **User-visible impact:** Cloth/no-sting setup copy stops lying.
- **Stop conditions:** Stop if making conformance "behavioral" reveals a must-have section with no real assertion — that surfaces WT-20 scope; record it, do not silently widen.

### Phase 6 — Accessibility hardening
- **Goal:** Keyboard and screen-reader users can complete entry-path and core loops at the supported desktop viewports.
- **Work items:** WT-21 (cluster). WT-28 timer-cleanup may ride here (trivial, real bug).
- **Non-goals:** No mobile-first redesign (desktop is the product target). No visual restyle.
- **Likely files:** `Roster.tsx`, `SaveMenu.tsx`, modal components (shared dialog primitive), `ui.tsx` (`StatusMessage` roles), segmented controls, `LineupEditor.tsx`/`ProspectCard.tsx` (timer cleanup).
- **Risk:** Medium (frontend DOM/handler changes across many surfaces).
- **Tests / commands:** Playwright role-based tests (focus a player row + Enter opens dialog; keyboard club selection; modal focus-trap/restore/Escape; `getByRole('alert')`/`status`); `npm run build`/`lint`; `npm run e2e` (desktop projects).
- **User-visible impact:** Full keyboard operability; SR announcements for errors/blockers.
- **Stop conditions:** Stop if a shared Dialog refactor risks regressing the already-healthy PolicyEditor radiogroup or CeremonyShell reduced-motion/skip behavior — wrap, don't rewrite those.

### Phase 7 — Recruiting/rival truth + test & parity hardening
- **Goal:** Make recruiting valuation and rival identity truthful, then lock all the gains with proof-based gates and a cheap rival-parity probe.
- **Work items:** WT-25 (flip backend pipeline-tier semantics + frontend labels + test rewrite), WT-24 (standings label == mechanical archetype), WT-23 (parity probe), WT-22 (decision-proof Playwright). **Do WT-25 first** — it changes signing semantics that WT-23's parity probe observes.
- **Non-goals:** Do not convert exploratory `naive_playtest_runner`-style specs into gates; keep them exploratory. Do not change recruiting *math* beyond the tier-direction flip (no new preference weights).
- **Likely files:** `recruiting_actions.py` (`base_interest`), `test_recruiting_actions.py` (rewrite tier assertions), `frontend/src/legibility/terms.ts` + `PipelineEmblem.tsx`, `web_status_service.py` (+ standings-label truth test), new `tools/` parity probe + `tests/test_*`, `tests/e2e/*` (one decision-proof spec).
- **Risk:** Low-Medium (WT-25 is a recruiting behavior + test change; the rest are tests).
- **Tests / commands:** displayed strongest tier == `base_interest()` ordering (the audit's contract test, now pointing the new direction); Playwright "change a non-default tactic/lineup → simulate → aftermath/replay text == `/api/match-replay/{id}`"; deterministic league sweep asserting ≥3 champion archetypes / no archetype over cap; standings label == `program_archetype`; `python -m pytest -q`.
- **User-visible impact:** Pipeline tiers sort the intuitive way (Elite = strongest) and match the mechanics; standings name a rival's real archetype.
- **Stop conditions:** Stop if flipping `base_interest` direction visibly shifts AI recruiting/championship parity in the probe — that means the tier direction was load-bearing for balance; re-tune or escalate rather than ship a parity regression. Stop if the parity probe is too slow to gate — move it to a nightly tool.

---

## Immediate first phase

**Phase 1 — Player-facing presentation truth.** It is the **safest** (zero engine, zero
persistence, zero golden-log/balance surface) and the **highest-leverage safe** work (the
replay `-` placeholder is the single most cross-cited trust break — three independent lanes —
and it fires exactly when the player is told to "watch and trust the sim"). Phase 0 (docs) is
even cheaper and should be done first or bundled, but it is agent-facing, not the player-trust
"first phase." The **Blocker (WT-6)** is scheduled immediately after as Phase 2 and may be run
in parallel — it is second, not buried, solely because it carries a probe-retune that Phase 1
does not.

---

## Do-not-do-yet list

**Defer as engine-scope (own milestone), do not start now:**
- **WT-20 — live official-rules enforcement** (No Blocking changes outcomes, throw-clock
  penalties, opening-rush activation). This is a milestone, not a fix: golden-log/conformance
  regression risk, and it conflicts with the no-scope-creep contract. *Now:* fix the overclaiming
  copy (WT-18) and conformance depth (WT-19); write a one-paragraph honest-deferral note that
  "official mode is an officially-inspired deterministic abstraction with documented limits."
  *Later:* a scoped `Vnn-official-live-rules` spec.

**Convert to tracked issues (internal quality, no player-trust payoff this pass):**
- **WT-27 — architecture boundary refactor** (split `recruitment.py`/`scouting.py`/
  `ai_program_manager.py`/`broadcast.py` into pure-rules + persistence-service). Real erosion,
  but behavior-neutral; high regression surface for zero visible payoff. The one player-facing
  symptom (broadcast official scoreline) is already fixed inside WT-3 without the refactor.

**Profile before optimizing (no measured evidence yet):**
- **WT-28 — frontend perf** (replay O(n)/tick, tab refetch cache, PolicyEditor save-per-change,
  unbounded history lists). The audit itself says "uneven but not broadly broken." Do not
  blanket-memoize or virtualize. *Exception:* timer-cleanup-on-unmount is a real, trivial bug
  and may ride Phase 6. Profile one long official replay first; let measurement justify the rest.

**Resolved design decisions (2026-05-31) — now scheduled, no longer gated:**
- **WT-25 → flip the backend** so a higher tier number is mechanically stronger ("tier 5 Elite"),
  matching the UI. This is the **higher-scope** choice: it changes `recruiting_actions.base_interest()`
  ordering + signing math and **rewrites `test_recruiting_actions.py`** (currently asserts tier 1
  stronger). Scheduled **Phase 7** (recruiting/rival truth). Update the frontend labels to agree, and
  keep the displayed strongest tier == `base_interest()` ordering (the contract test from the audit).
- **WT-17 → flip the backend default to `official_foam`**, preserving explicit `generic`/`None` for
  legacy saves only. Touches request models + `initialize_curated_manager_career` + routing tests.
  Scheduled **Phase 4**.
- **WT-29 → confirm dialog** before fast-forward that discloses the skipped decisions (reuses
  persisted defaults, skips weekly ceremony). Keep the tool; remove the mixed signal. **Phase 3b.**
- **WT-30 → reveal real scouted intel** (the **higher-scope** choice, not a rename): clicking Scout
  must surface a concrete scouted delta so Tactical Diff flips from `Unscouted` and shows "new intel
  revealed." This is a **new reveal mechanic** with its own tests, not a copy fix. **Phase 3b.**
- **WT-31 → accept honest no-point draws now** (framing/copy only, no engine change) and
  **re-measure draw density after WT-6 lands** — the catch-posture fix is expected to lower draws on
  its own (the earlier official retune cut even-rung draws 28%→18%). Revisit a seeded tiebreak only if
  draws are still uncomfortable post-WT-6. **Phase 2 follow-up.**
- **WT-32 → add a separate "Manager Lesson"** surfaced when Primary Factor is inconclusive, drawn
  from controllable prep (roster edge, fatigue, ignored recommendation, weakest role group). Primary
  Factor **stays strictly event-derived** — the lesson is an adjacent surface, not folded in. **Phase 3b.**

---

## Risk register

**Save corruption** — *Highest-consequence cluster.*
- WT-14 duplicate founding IDs → write to a temp path, validate `6 ≤ unique valid IDs ≤ cap`,
  atomic-rename, assert no `.db` remains on rejection.
- WT-15 metadata-read migration → make list/meta strictly non-mutating; migrate only on explicit
  resume through `migrate_schema(..., db_path=...)` (the path that backs up).
- WT-16 corrupt cursor → fail loud; **rewrite** `test_career_state.py` expectations in the same change.
- Guard: every Phase-4 rejection test must assert *no partial DB is left behind*.

**Official-rules regressions**
- WT-6 catch-posture re-tune can move the OVR curve → re-run `test_official_engine_balance` +
  both-ruleset probes; escalate (do not over-tune) if the gate breaks after a bounded re-tune.
- WT-20 deferred precisely to avoid golden-log/conformance regressions from live rule-wiring.
- WT-19 making conformance behavioral may expose an unasserted must-have section — record as WT-20 scope, do not widen silently.

**Balance changes**
- WT-6 is an *intended* balance change (honesty fix) — document why, update the gate, no hidden buffs.
- WT-7 moment caps are presentation-rate only; assert match **outcomes** are unchanged by the cap.
- WT-8 keep to "stop presenting"; *wiring* `rush_target` would change outcomes → golden/probe updates, promote out of the cheap bucket.
- WT-25 (resolved: flip backend tier direction) changes `base_interest()` ordering and rewrites its test → run the WT-23 parity probe **after** it; a champion-parity shift means the tier direction was load-bearing — re-tune or escalate, do not ship a parity regression.

**Architecture boundary**
- WT-3 must stay a scoreline read/format; it must **not** become the `broadcast.py` DTO refactor (WT-27). Scope guard in the Phase-1 prompt.

**Frontend behavior regressions**
- Phases 1/5/6 touch copy, labels, and DOM/handlers → run `npm run build` + `npm run lint` +
  focused Playwright each phase. Phase 6 must wrap (not rewrite) the healthy PolicyEditor/CeremonyShell.
- WT-28 deferred to avoid premature memo/virtualization regressions.
- Phase 3b adds two new surfaces: WT-30 (scout reveal) must derive intel from real opponent data and **not** leak the AI's secret adaptation pre-match; WT-32 (Manager Lesson) must stay a *separate* surface from the event-derived Primary Factor. Both are net-new player-facing features → full build/lint/Playwright per the phase.

**Docs / source-of-truth drift**
- WT-26 is the cure; the risk is doing it *halfway* — leaving `docs/teardowns/` unrouted, half-closing
  V14, or deleting the parity-sweep claim with nothing behind it (land WT-23 first, or restate honestly).

**Integrity-contract check (all scheduled phases):** none introduce hidden buffs, rubber-banding,
user aura, unseeded outcome randomness, or UI-decided outcomes. WT-6 *removes* a perverse tactic
inversion; WT-2/WT-3 make scoreboards truthful; WT-1 removes a synthetic-looking placeholder.
Every scheduled item strengthens, not weakens, the contract.

---

## First implementation prompt (Phase 1 only)

> **Task:** Implement **Phase 1 — Player-facing presentation truth** from
> `docs/specs/2026-05-31-master-implementation-roadmap-audit-synthesis.md`. Presentation only:
> **no engine math, no scoring-model change, no persistence change, no new dependencies, no
> routing/auth change.**
>
> **Exact scope (and nothing else):**
> 1. **WT-1 — Replay `-` placeholders.** For miss/target-less events, render player-facing
>    no-target language ("throws into space" / "misses wide") and omit the `vs -` detail, in
>    **both** render paths: `src/dodgeball_sim/replay_proof.py` (`_player_name` at ~:172, labels
>    at ~:213–215) and `src/dodgeball_sim/replay_service.py` (~:472–475). Never emit `targets -`,
>    `vs -`, or `toward -`.
> 2. **WT-2 — Official aftermath headline.** Give `voice_verdict.render_headline`
>    (`src/dodgeball_sim/voice_verdict.py:192`, called from `use_cases.py:644`) the same
>    scoring-model facts the frontend uses, so an official `0-0` game-point draw never produces a
>    survivor-count headline like `0-3`. Mirror the logic in `frontend/.../matchResult.ts`.
> 3. **WT-3 — Broadcast last-meeting scoreline.** In `src/dodgeball_sim/broadcast.py` (~:314),
>    for official matches format the existing `home_game_points` / `away_game_points` columns
>    (already persisted, see `persistence.py:1027`) instead of survivor counts. **Read/format
>    only — do NOT refactor the broadcast persistence boundary (that is deferred WT-27).**
> 4. **WT-4 — Readiness-gate detail.** In `PreSimDashboard.tsx` (~:716) surface the blocking
>    gate's `detail` as **visible** helper text **and** an accessible name (satisfies Accessibility
>    Finding 7), not `title`-only. Keep the short ok/pending chip text.
> 5. **WT-5 — Scoring-model labels.** Map `scoring_model` to player-facing names ("USAD Foam" /
>    "USAD Cloth" / "Legacy survivor scoring") in `MatchReplay.tsx` (~:247) and `matchResult.ts`
>    (~:36). No underscores/all-caps keys in player-facing labels.
>
> **Files to inspect first (before editing):** `replay_proof.py`, `replay_service.py`,
> `voice_verdict.py`, `use_cases.py` (around :644), `broadcast.py` (around :314) + `persistence.py`
> (confirm the official game-point columns), `frontend/src/components/match-week/matchResult.ts`,
> `MatchReplay.tsx`, `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`.
>
> **Behavior to preserve:** the event log remains canonical (renderers display, never decide
> outcomes); official game-point scoring contract is unchanged; generic/legacy survivor scoring
> still works; the voice-register Tier-1 phrasing is preserved; determinism is unchanged; the
> aftermath verdict still hides when `primary_factor` exists. Do not touch engine/balance code or
> golden logs.
>
> **Tests to run / add:**
> - Add unit tests: no replay label/detail contains `targets -` / `vs -` / `toward -`; an official
>   postgame with `winner_team_id=None`, game points `0-0`, survivors `0-3` produces a headline that
>   does **not** say `0-3`; a broadcast official last-meeting where survivors ≠ game points formats
>   game points.
> - `python -m pytest -q` (full suite green).
> - `cd frontend && npm run build && npm run lint`.
> - Focused Playwright: `npm run e2e -- tests/e2e/official-rules-replay.spec.ts --project=chromium`.
> - Browser-verify against a fresh dev server (use `scripts/dev-restart.ps1` to avoid a stale PID):
>   simulate one official week, open the full replay, confirm no `-` targets and that the headline/
>   scoreboard agree on game points.
>
> **Handoff format (end with):** a short report stating, per work item WT-1..WT-5, the files
> changed, the test(s) added and their pass output, the frontend build/lint result, the live
> browser proof, and any item that turned out to be already-correct (report the evidence, do not
> force a diff). Note explicitly that no engine math, scoring model, persistence, or golden log was
> touched. List any follow-up surfaced but intentionally left for a later phase.
