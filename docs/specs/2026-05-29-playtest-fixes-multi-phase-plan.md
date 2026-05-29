# Playtest Fixes — Multi-Phase Plan (2026-05-29)

Planning output built from `docs/reviews/2026-05-29-playtest-synthesis-for-planning.md`.
This is a **plan**, not implementation. Each phase is independently shippable
where possible, ordered by **dependency and trust-impact**, not by the report's
list order.

Source-of-truth tags from the synthesis (✅ verified / 🟡 reported / ⚙️ design
question) are treated as binding. §1 "confirmed working" items are NOT re-opened.

---

## Resolved design decisions (the ⚙️ gates + sequencing branches)

Decided with the owner before drafting. These bind the phases below.

| # | Decision | Resolution |
|---|----------|------------|
| D1 | **Fielded-lineup root** (2.1+2.2 shared cause) | One **canonical fielded-6** consumed by both sim and briefing. Auto-lineup = best-by-role/OVR (`optimize_ai_lineup`). User's **manual lineup persists across seasons**; auto only backfills gaps. |
| D2 | **Favorite-tag meaning** (2.2 ⚙️) | Headline = **banded label** (Favorite / Even / Underdog) from the fielded-6 net OVR. Raw `+NNN NET OVR` demoted to a small advisory "roster strength" detail. No false win-probability precision. |
| D3 | **Readiness semantics** (2.3 ⚙️) | **Scout-opponent** + a new **confirm-lineup** gate start UNMET and require a real action. Gameplan/training/health stay default-satisfied (preserves the deliberate Balanced-default convenience). **Bye week auto-clears scout.** |
| D4 | **Replay scoring model** (2.5 ⚙️) | Set-based scoring is **already built** (`official_engine.run_autonomous_match` → `OfficialMatchScore`) and faithful to USA Dodgeball; it was only gated to official-ruleset careers. **New "Build from Scratch" careers default to the foam official ruleset** so they get real set scoring. No new generic rule authored (respects the V11 non-goal against flattening foam/cloth). Existing legacy saves stay legacy. **Critical coupling:** real matches ship through `OfficialEngineAdapter.run_generic` → `run_autonomous_match` (the multi-set engine), and that path emits **no `moment_events`** — which would strip the Tier-1 moment beats, tier1 voice register, and V13 highlight packages. So D4 **also requires emitting `moment_events` from the shipping match engine** (`run_autonomous_match` / its adapter). **NOTE the trap:** `OfficialDriver` (`official_driver.py`) is a *different, single-game stub* (`run_autonomous_game`, moments hardcoded `()`); do NOT target it. See the 2026-05-29 verification note below. |
| D5 | **New-club records seeding** (5.2 ⚙️) | `ratify_records` **already seeds league-wide** from all clubs' retirees. Keep league-wide; add an **honest empty-state** until the first retirements ("history begins when your first legends retire") plus a **My Club / League scope filter** (5.1). No synthetic/invented history. |
| D6 | **Straddler sequencing** (§7.1) | **Logic first, restyle later** for Operational Plan (2.4), Policy Editor (4.7), Match Aftermath (4.4). Trust fixes land in early correctness phases; visual redesign enters the design-brief phase. |
| D7 | **Multi-week sim behavior** (6.1) | **Auto-pilot with persisted defaults**: skipped weeks use the persisted manual lineup (fallback to best-by-role/OVR auto) + last intent; gates auto-satisfy for skipped weeks. Doubles as a test of the canonical fielded-6 path. |
| D8 | **Plan scope** | Full depth on correctness + growth-legibility + enablers. The 8 §4 redesigns ship as **Claude Design handoff briefs** (teardown + primary/secondary/cut + data inventory + constraints already done), NOT finished UI — so the design tool starts elevated and iterates creatively. |
| D9 | **Growth-legibility reach** (§3) | **Player Card + Dev beat + Roster Lab** — the three places a player judges development. |

### Key code findings behind the decisions

- `_build_edge` ([week_briefing.py:158](../../src/dodgeball_sim/week_briefing.py)) reads `plan["lineup"]["players"]` = the *recommended best-6*, while the sim fields `plan["lineup"]["player_ids"]` resolved from the *saved default* ([match_orchestration.py:320](../../src/dodgeball_sim/match_orchestration.py)). For a fresh club the saved default is roster-order (weak 6), so the briefing shows FAVORITE while the sim fields the weak 6. **Root = no shared fielded-6**, not "sums 10-man roster." (D1)
- `official_scoring.py` + `official_engine.run_autonomous_match` ([official_engine.py:772](../../src/dodgeball_sim/official_engine.py)) already run a full set-based match. `formatScoreline` ([matchResult.ts:33](../../frontend/src/components/match-week/matchResult.ts)) already shows game points for official saves, survivors for legacy. (D4)
- `ratify_records` ([offseason_beats.py:123](../../src/dodgeball_sim/offseason_beats.py)) pulls `player_career_stats` for all players league-wide. (D5)
- V11 design Non-Goal: "Do not flatten foam, no-sting, and cloth into one generic ruleset" ([design.md:32](2026-05-20-v11-official-usad-rules/design.md)). (D4)

---

## Standing verification protocol (§0 — built into EVERY phase)

The dev server can silently run **stale code** (the synthesis's two false
"regressions" came from a lingering server process). Every phase's acceptance
criteria MUST include:

1. **Fresh-process guard.** Before any browser verification: confirm the bound
   process is fresh — `Get-NetTCPConnection -LocalPort 8000` → `Stop-Process`
   the old PID → restart → confirm new PID. (Phase 0 wraps this in a reusable
   helper so it is one command, not a ritual to forget.)
2. **Backend truth first.** Assert the change in `pytest` (pure domain/engine)
   before trusting the UI.
3. **Then browser proof.** Only after 1+2, capture the browser evidence
   (screenshot / network / snapshot) against a confirmed-fresh server.

No phase may claim "verified" on browser observation alone.

---

## Phase 0 — Verification hardening (enabler)

- **Goal:** Make stale-server false negatives impossible to forget.
- **Scope IN:** A small dev helper (PowerShell script or npm task) that
  stops any process on the dev port, restarts, and prints the new PID; a short
  `docs/` note wiring it into the verification protocol above.
- **Scope OUT:** Any gameplay/logic change. No new dependency.
- **Dependencies:** None.
- **Size:** Small.
- **Verification:** Run the helper twice; confirm it kills the prior PID and
  reports a distinct new one. Referenced by every later phase.

## Phase 1 — Canonical fielded-6 (root; unblocks 2.1 + 2.2) — D1

- **Goal:** One fielded-6 the sim AND the briefing both consume; fix
  bench-the-best; persist manual lineup across seasons.
- **Scope IN:**
  - Fresh-club / season-rollover default lineup = `optimize_ai_lineup`
    (best-by-role/OVR) instead of roster order.
  - `_lineup_recommendation` and the sim's `_apply_command_plan_to_match`
    resolve from the **same** canonical fielded-6 (single resolver path).
  - Persist the user's manual lineup across `begin_next_season`; auto only
    backfills new gaps (rookies in, retirees out).
- **Scope OUT:** Favorite-tag copy (Phase 3), readiness gate (Phase 3),
  any scoring change.
- **Dependencies:** Phase 0.
- **Size:** Medium.
- **Verification:** pytest — assert the briefing's fielded-6 == the sim's
  active starters for a fresh club; assert a manual lineup survives a season
  rollover; reproduce the synthesis's cause→effect (bad lineup = shutout, fixed
  = 6-0/4-0). Then fresh-server browser walk of one week.
- **Trade-off:** Persisting manual lineups must degrade gracefully when a
  starter retires/leaves — define the backfill rule explicitly (auto-fill the
  vacated slot by best-by-role/OVR, flag it to the user).

## Phase 2 — Multi-week sim, auto-pilot (testing force-multiplier) — D7

- **Goal:** Sim to Playoffs / Offseason / Next Season with persisted defaults,
  to accelerate verification of every later phase.
- **Scope IN:** Fast-forward controls; each skipped week auto-uses persisted
  manual lineup (fallback best-by-role/OVR) + last intent; readiness gates
  auto-satisfy for skipped weeks; deterministic (seeded) so results are
  reproducible.
- **Scope OUT:** "Stop on decision" smart-advance (explicitly deferred);
  any new tactic UI.
- **Dependencies:** Phase 1 (auto-pilot consumes the canonical fielded-6).
- **Size:** Large.
- **Verification:** pytest — sim-to-target lands on the correct week/state and
  is deterministic across two runs with the same seed; the auto-piloted weeks
  field the persisted/canonical lineup. Fresh-server browser: fast-forward a
  full season, confirm no console errors and standings advance.
- **Note:** No public-API/routing change beyond additive endpoints; justify any
  new route in the implementation spec.

## Phase 3 — Matchup legibility: favorite tag + readiness — D2, D3

- **Goal:** Make the matchup edge honest and readiness meaningful, both built on
  the Phase 1 canonical fielded-6.
- **Scope IN:**
  - Favorite tag → banded Favorite/Even/Underdog headline; `+NNN NET OVR`
    demoted to advisory detail; never implies a mechanical edge (AGENTS.md).
  - Readiness: `scout` + new `confirm-lineup` gate start unmet, cleared by a
    real action; bye auto-clears scout; other gates stay default-satisfied.
- **Scope OUT:** Operational Plan visual (Phase 6 logic / brief later);
  aftermath labeling (Phase 4).
- **Dependencies:** Phase 1.
- **Size:** Medium.
- **Verification:** pytest on `week_briefing` — banded standing matches the
  fielded-6 delta; gates start unmet and flip on action; bye auto-clears scout.
  Fresh-server browser: confirm tag reads honestly for a known weak/strong
  lineup and readiness is not 5/5 before acting.

## Phase 4 — Set-based scoring becomes the default match + scoreboard honesty — D4, plus 4.4 PRIMARY FACTOR logic

- **Goal:** New careers play real set-based matches; replay/aftermath/wire all
  report the set score consistently; PRIMARY FACTOR matches margin.
- **Scope IN:**
  - **Decide and wire the ONE shipping official match engine.** Real matches use
    `OfficialEngineAdapter.run_generic` → `run_autonomous_match` (multi-set).
    `OfficialDriver` (`official_driver.py`) is a separate single-game stub
    (`run_autonomous_game`, moments `()`) used only by the probe — do NOT build
    on it. Reconcile so plan, probe, and adapter all reference the same engine
    (likely: make the `EngineDriver` wrap `run_autonomous_match` and route real
    matches + the probe through it).
  - **Emit `moment_events` from that shipping engine** so the Tier-1 moment
    beats, tier1 voice register, and V13 highlight packages keep working. This
    is the gating sub-task — do it BEFORE flipping the default.
  - New "Build from Scratch" careers default to the foam official ruleset
    (set `ruleset_selection` at creation; routing already exists in
    `simulate_match`).
  - Replay header + aftermath + League Wire copy report set/match score
    consistently; survivors demoted to per-set context.
  - Fix PRIMARY FACTOR so a 0-4 loss and a 6-0 win are not both "inconclusive"
    (the 4.4 *logic* slice; visual hierarchy is a Phase 8 brief).
- **Scope OUT:** Aftermath visual redesign (Phase 8 brief); cloth/no-sting
  pickers (not chosen — foam default); any change to existing legacy saves;
  authoring a new generic ruleset (rejected — respects V11 non-goal).
- **Dependencies:** Phase 2 (fast-forward to verify a full season of scoring),
  Phase 1.
- **Size:** Large.
- **Split recommendation:** **4a** — reconcile/wire the shipping official engine
  + emit moments from it + **fix the probe** (it imports `OfficialDriver` from
  the wrong module and measures the single-game stub) + **retune the official
  combat math until the OVR curve passes** (measured 2026-05-29: slope +3.3pp /
  top floor 43.7% — FAILS the +10pp/60% gate; catch-dominance in
  `official_resolution.resolve_throw` is the prime suspect) + graduate
  `tools/official_match_probe.py` into a real OVR-sensitivity test; **4b** — flip
  the default for new careers + scoreboard/copy consistency + PRIMARY FACTOR.
  **The official OVR-curve gate + moment-coverage check block 4b.** Without the
  balance retune, foam-official would make every new career's matches a coin-flip
  regardless of squad quality — directly contradicting the decision-traceability
  north star.
- **Verification:** pytest — a new career's match produces `OfficialMatchScore`
  with set points; **`OfficialDriver` emits every moment kind the rec driver
  does** (the new gate — not just OVR parity); `voice_aftermath`, replay moment
  banners, and V13 highlights are non-empty under the official driver;
  scoreline parity across replay/aftermath/wire; PRIMARY FACTOR label correlates
  with margin sign. Engine/golden-log impact: **update golden logs and document
  why** (AGENTS.md). Health-probe sanity pass
  (`tools/tier_engine_health_probe.py --driver official`) confirms archetype/OVR
  parity holds. Fresh-server browser: play a match in a new career, confirm set
  score AND moment beats/highlights show end-to-end.
- **Open question:** whether the rec Tier1 driver remains reachable for new
  careers at all once foam-official is the default, or is retained only for
  legacy saves. Decide before 4b merge.

## Phase 5 — Growth legibility — D9

- **Goal:** Make genuine, already-happening development visible.
- **Scope IN (presentation only; engine unchanged):**
  - Player Card: numeric ceiling + projected growth (not just "Elite").
  - Offseason Development beat: per-attribute deltas under the composite +1.
  - Roster Lab: season-over-season attribute trend.
- **Scope OUT:** Any development-engine math (§1 confirms it works).
- **Dependencies:** None (independent; can parallelize with Phase 3/4).
- **Size:** Medium.
- **Verification:** pytest — payloads carry ceiling + per-attribute deltas +
  trend for a known Elite vs Low player and differ as expected. Fresh-server
  browser: an Elite prospect visibly out-develops a Low one across a season
  (use Phase 2 fast-forward).

## Phase 6 — Small correctness cleanups + straddler logic — 2.6, 2.7, 2.4(logic), 4.7(logic)

- **Goal:** Knock out the contained correctness bugs and the logic half of the
  straddlers (D6).
- **Scope IN:**
  - 2.6 float leak in Next Best Improvement (round/format OVR to int at the
    boundary; sweep for sibling raw-key/float leaks).
  - 2.7 new-save name collision (validate uniqueness on Step 1; block Commit
    with a visible banner, not tiny red text).
  - 2.4 Operational Plan: resolve the green-while-misaligned contradiction
    (indicators must reflect real misalignment).
  - 4.7 Policy Editor: de-duplicate the triple-shown option data at the data
    boundary (visual restyle deferred to Phase 8 brief).
- **Scope OUT:** Visual redesign of Operational Plan / Policy Editor.
- **Dependencies:** None individually; group for one shippable correctness PR.
- **Size:** Small (each contained).
- **Verification:** pytest per fix; fresh-server browser confirm for 2.7 banner
  and 2.4 indicator honesty.

## Phase 7 — Records: empty-state + scope filter — D5, 5.1

- **Goal:** Records read honestly for a fresh club and have a clear scope.
- **Scope IN:** Honest empty-state until first retirements; My Club / League
  scope filter on Records Ratified; trim low-impact records so broken records
  feel impactful (5.1 audit's logic/scope slice).
- **Scope OUT:** Visual redesign of Records Ratified (Phase 8 brief);
  synthetic/invented history (rejected).
- **Dependencies:** None.
- **Size:** Medium.
- **Verification:** pytest — empty book renders the empty-state, not zero/fake
  records; scope filter returns club-only vs league-wide sets correctly. Use
  Phase 2 fast-forward to reach a retirement and confirm the book populates.

## Phase 8 — Design briefs for §4 redesigns (Claude Design handoff) — D8

- **Goal:** Produce, for each redesign screen, a **design brief** that hands
  Claude Design an elevated starting point — NOT finished UI.
- **Scope IN — each brief delivers:**
  1. **Teardown** of the current screen (what exists, what's silent/redundant).
  2. **Information hierarchy:** explicit primary / secondary / cut.
  3. **Data inventory:** the real fields/payloads available to render (so the
     designer invents layout, not data).
  4. **Constraints:** mobile viewport (390×844, no horizontal overflow),
     AI-friendly/semantic markup, no new dependency, no routing/auth change,
     "explain don't decide" (event log stays canon).
  5. **Success criteria** the eventual implementation must hit.
  - Screens: 4.1 Class Report, 4.2 Season Preview, 4.3 Bye Week aftermath,
    4.4 Match Aftermath hierarchy, 4.5 Rookie Class Preview, 4.6 War Room
    (playoff flair), 4.7 Policy Editor restyle, 4.8 Records Ratified.
- **Scope OUT:** Drawing/implementing final UI; that is each brief's downstream
  task. Briefs depend on the logic being settled first (Phases 1–7) so the
  designer "starts from an elevated position."
- **Dependencies:** Phases 1–7 (so briefs reflect ironed-out behavior).
- **Size:** Large (8 briefs), but each brief is small and independently
  shippable.
- **Verification:** Owner review of each brief; a brief is "done" when it could
  be handed to Claude Design with no further teardown needed.

---

## Suggested sequencing (dependency + trust-impact)

```
Phase 0 (verify harness)
   └─ Phase 1 (canonical fielded-6)  ← highest trust-impact root
        ├─ Phase 2 (multi-week sim)  ← force-multiplier, do early
        │     └─ accelerates verifying 4,5,7
        ├─ Phase 3 (favorite + readiness)
        └─ Phase 4 (set-based default + scoreboard + PRIMARY FACTOR)
   Phase 5 (growth legibility)  ── independent, parallelizable
   Phase 6 (small correctness + straddler logic)  ── independent
   Phase 7 (records empty-state + scope)  ── benefits from Phase 2
   Phase 8 (design briefs)  ── after 1–7 settle
```

Independently shippable: 0, 1, 3, 5, 6, 7, and each brief in 8. Phase 2 and
Phase 4 are larger and benefit from landing in that order.

## Open questions / trade-offs surfaced (not papered over)

1. **Phase 4 is the biggest risk** and now carries the `OfficialDriver`
   moment_events work as a hard prerequisite (without it, the set-scoring
   default silently kills the Tier-1 moment/voice/highlight layer for every new
   player). Split 4a (teach moments + flag + probe) / 4b (flip default) so the
   presentation-coverage gate blocks the flip. Open: rec Tier1 driver's fate for
   new careers.
2. **Manual-lineup persistence (D1)** needs a defined backfill rule when a
   starter departs — confirm "auto-fill best-by-role/OVR + flag to user."
3. **Readiness confirm-lineup gate (D3)** must not resurrect the friction the
   Balanced-default decision removed — confirm one click satisfies it and bye
   weeks never trip it.
4. **No new dependencies / no public-API/routing/auth changes** assumed
   throughout; Phase 2's fast-forward endpoints are additive and must be
   justified in their implementation spec.
5. **Records scope filter default (Phase 7):** decide whether the screen opens
   on My Club or League by default (lean My Club for a fresh player).
```

---

## 2026-05-29 — Gemini report verification note

Two research reports were commissioned to de-risk Phase 4. Both verified against
source before trust.

**Balance baseline** (`docs/reviews/2026-05-29-phase4-balance-baseline.md`,
Gemini 3.5 Flash) — its "STRICT VETO on D4" is **unsubstantiated; treat as
invalid, NOT as disproof**:
- The probe (`tools/tier_engine_health_probe.py`) imports `OfficialDriver` from
  `official_engine`, but that class lives in `official_driver.py` and is not
  re-exported → `--driver official` **cannot run as written** (raises, curve
  aborts). The 8,000-trial official table is therefore fabricated or was
  produced by silently editing the tool (the prompt forbade edits).
- Even if run, `OfficialDriver` is a **single-game stub** (`run_autonomous_game`,
  `moment_events=()` hardcoded) — NOT the `run_autonomous_match` engine D4 ships.
  Its "single-game → only 1-0/0-0" mechanism describes that stub, not reality.
- **Accurate kernels worth keeping:** the catch formula was transcribed
  correctly (`p_catch = σ(3.0·(catch_eff − 0.6·power_eff))`, ~68% at even
  ratings; a catch outs the thrower and resurrects a defender — verified in
  `official_resolution.py`). And the official path genuinely emits zero
  `moment_events` (already a known Phase 4a item).
- **NOW MEASURED on the real engine (2026-05-29).** Wrote a corrected probe
  (`tools/official_match_probe.py`) that wraps the shipping `run_autonomous_match`
  as an `EngineDriver` and runs the same OVR curve the rec driver uses. Result at
  300 trials/rung (1,200 matches, foam, deterministic seeds):

  | Net OVR edge | Real official win rate (95% CI) | Rec driver (Flash, for ref) |
  | :--- | :--- | :--- |
  | +0  | 40.3% [34.9–46.0] | 50.0% |
  | +24 | 44.3% [38.8–50.0] | 56.0% |
  | +48 | 47.7% [42.1–53.3] | 64.0% |
  | +72 | 43.7% [38.2–49.3] | 70.2% |

  Slope **+3.3pp** (gate needs +10pp → FAIL), top floor **43.7%** (needs 60% →
  FAIL), non-monotonic, **21.6% draws**, median match length **386 events** (the
  real engine; Flash's "76" was the single-game stub). On identical synthetic
  inputs the rec driver climbs to ~70% — so the flat curve is
  **engine-attributable, not a test artifact**.
- **Mechanism now isolated (2026-05-29 follow-up).** Re-ran the corrected probe
  (500 trials/rung): slope **+5.6pp** (need +10 → FAIL), top floor **44.0%**
  (need 60% → FAIL), **22.9% draws** — reproduces the blocker. Then instrumented
  `official_resolution.resolve_throw` over 9,002 throws at a deliberately large
  +72 net edge (per-player 75 vs 63):

  | Throw outcome | Share | Effect on the throwing team |
  | :--- | :--- | :--- |
  | dodged | 42.1% | neutral (no out) |
  | **caught** | **40.5%** | **net-negative — thrower OUT + a defender resurrected** |
  | hit | 17.4% | the only positive outcome |

  **A throw is ~2.3× more likely to get the thrower out (caught) than to score a
  hit.** Throwing is net-negative EV, so games rarely reach full elimination
  (defenders keep resurrecting) → clock expiry → `no_point` 0-0 games → the ~23%
  draw rate. OVR cannot express because the catch coin-flip dominates the
  elimination differential. Even at the +72 edge the favorite wins only ~45%
  (dog ~35%, draw ~20%). The asymmetry that *should* reward OVR is present but
  swamped: sampled `p_catch_given_attempt` was 0.63 (fav→dog) / 0.75 (dog→fav)
  and the attempt threshold (`normalized_catch >= 0.5`) means nearly every
  defender always attempts. **Prime levers for 4a:** catch success probability,
  the attempt-selectivity threshold, and/or the catch resurrection reward.
  **Caveat for 4a scoping:** these synthetic teams are uniform-rating, and the
  `−0.6·power_eff` term means a *power-specialized* thrower suppresses the
  target's catch prob — uniform rosters may overstate the catch rate vs real
  specialized rosters. The OVR-flatness conclusion holds regardless (rec-driver
  control hits ~70% on identical inputs), but verify the catch-dominance
  magnitude on a realistic specialized roster before treating 40.5% as the number
  4a must beat. **The graduated probe-gate must assert the draw rate AND the OVR
  slope** — they are coupled (catches prevent elimination → expiry → 0-0), and
  one knob may not fix both.
- **Reconciled verdict:** Flash's *evidence* is invalid (wrong engine / broken
  probe), but its *conclusion is vindicated by our own correct measurement*: the
  official engine **does not reward OVR** as it stands. **D4's default-flip is
  GATED on an official-engine balance pass** (the catch-dominance dynamic in
  `official_resolution.resolve_throw` is the prime suspect — verified formula,
  ~68% catch at even ratings, catch outs the thrower + resurrects a defender).
  Phase 4a must include that balance pass + an official OVR-sensitivity test
  (graduate `tools/official_match_probe.py` into a real gate, mirroring the rec
  driver's `test_ovr_curve_rec_driver_smoke`). Do NOT flip 4b until it passes.

**Rules + moments** (`docs/reviews/2026-05-29-phase4-rules-and-moments-research.md`,
Gemini 3.1 Pro) — **usable**, spot-check before baking in:
- Confirms the foam set-win assumption (set point on full elimination only;
  time-expiry = 0) and finds no `official_scoring.py` mismatch. **Spot-check two
  rulebook citations (e.g. `6.b.ii.2`, `7.a.i.1`) against the PDF** before
  quoting section numbers in 4a — confident-wrong citations hide here.
- Moment mapping is actionable: emit `DRAMATIC_CATCH`, `LATE_GAME_ESCAPE`,
  `ONE_V_ONE_FINALE`, `COMEBACK` from the official loop (engine already tracks
  the facts); defer `GASSED_COLLAPSE` (no fatigue model) and `FLOOD_THROW` (no
  batch-throw tracker). Adds sensible official-only moments (`SET_WIN`/
  `GAME_DECIDED`, `MATCH_COMEBACK`, `BURDEN_VIOLATION`) — fold into the Phase 4a
  emit-moments work.
