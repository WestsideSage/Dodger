# V28 — The Weather: Retrospective (2026-06-18)

Milestone: **V28 The Weather (anti-solvedness)** — the Climb-Era finale.
Branch: `feature/v24-the-board` (not yet on main; the arc merges as a unit).
Spec: `docs/specs/2026-06-17-v28-the-weather-spec.md`;
plan: `docs/specs/2026-06-17-v28-the-weather-sprint-plan.md`.

## What shipped

Three independent halves, all derived from real match telemetry, behind
`pyramid_world_active` (legacy single-league + season 1 byte-identical):

1. **Meta journalism** (`meta_journalism.py`, Phase 1 — pre-existing on the
   branch; this session added the missing `tools/meta_journalism_probe.py`
   gate). `compute_league_trends` aggregates per-division catch rate, elimination
   rate, game-point margin, and posture win-correlation from `team_policies`
   (playoff match-ids excluded; `fetch_season_player_stats` not the lossy
   season-stats table). `generate_league_bulletin` writes `meta_report` headlines
   whose every formatted claim recomputes from the queried rows — the
   derived-from-data fence the probe enforces.

2. **Emergent meta** (`meta_drift.py`, Phase 2 — committed earlier this arc; this
   session finished Task 2.2). `winning_tactics` reads which `CoachPolicy` value
   won most each season; `apply_meta_drift` nudges each AI club's
   `v28_tactic_drift_json` overlay toward the winners (bounded by
   `WeatherConfig.drift_rate`), with a deterministic contrarian fraction
   (`v28_meta_drift` stream) pushing the **runner-up value UP** — so the
   contrarian generation produces a *visible alternative tactic*, not merely a
   suppressed winner. `tactic_drift_for` is consumed by `get_ai_tactics` after the
   intent override (precedence: archetype base → intent → drift); the user club is
   never drifted; the overlay only changes a real `CoachPolicy` the engine already
   consumes, so determinism is preserved. `tools/meta_drift_probe.py` shows
   drift-toward-winner climbing across 8 simulated seasons plus a contrarian
   generation that prevents a permanent solve.

3. **Officiating points of emphasis** (`season_emphasis.py` + the engine —
   Phase 3, the bulk of this session). A frozen `SeasonEmphasis(catch_delta,
   block_delta, announcement, selection_basis)` threaded as a SEPARATE argument
   (NOT a field on the frozen `RulesetProfile`) through
   `run_autonomous_match → run_autonomous_game → resolve_throw →
   compute_throw_probabilities`, plus the `OfficialMatchEngineDriver` config
   channel. The deltas shade the EXISTING catch/block sigmoid bias BEFORE the
   EXISTING roll; every flipped call is logged as a
   `RuleDiscretionEvent(rule_section='emphasis', selection_basis='emphasis_<season>')`.
   `select_season_emphasis` picks a bounded emphasis on the new
   `v28_season_emphasis` stream (idempotent via the per-season store);
   `generate_officiating_bulletin` announces it preseason (a `league_bulletin`
   headline for the UPCOMING season at the offseason sweep); `load_season_emphasis`
   is threaded `game_loop → simulate_match → OfficialEngineAdapter →
   run_autonomous_match` so league matches play under the active emphasis. An
   honest `NON_SECTION_ENFORCEMENT_NOTES` entry records it as ENFORCED-as-
   DISCLOSED-SIM-DESIGN (emphasis is NOT a sourced USAD section).

4. **Frontend** (Phase 4): the Week-1 Season Preview gains a "League Bulletin"
   block; the league news wire (`class_wire`/`event_news`/`meta_report`/
   `league_bulletin`) now rides the `/api/standings` payload (`wire_headlines`)
   and renders at the front of the existing League Wire ticker — surfacing
   headlines that had been written since V24/V27/V28 but had **no frontend
   consumer**. `tests/test_v28_frontend_payloads.py` is the real-TestClient
   strip-trap regression.

## Hard-won lessons / traps

- **The #1 landmine held by construction, not by luck.** The byte-identical
  requirement was met with arithmetic that is *provably* identity at the default:
  `catch_bias = _CATCH_BIAS - catch_emphasis` (`0.7 - 0.0 == 0.7` exactly in
  IEEE-754) and `block_bias = _BLOCK_BIAS + block_delta` (`-0.1 + 0.0 == -0.1`).
  Capturing the roll into a variable (`catch_roll = rng.random()`) for the
  counterfactual is the same single draw — no reorder. The pre-V28 golden suite
  (`test_official_engine_balance` `_WT7_BASELINE_*`, `test_attribute_consumers`
  fingerprints, `test_wt20_live_rules` block pins) is the real fence; it stayed
  green at every step.

- **`collect_official_metadata` is NOT on the live replay path.** The adapter
  imports it but builds replay metadata from `asdict(official_match_score)`; only
  the tests and the engine event tuple carry `discretion_events`. So the emphasis
  DISCRETION test asserts against `collect_official_metadata(out.events)` directly
  off the driver output, and the disclosure is honest: the discretion log is in
  the event stream (and the conformance ledger), not yet surfaced in the
  player-facing replay UI (a clean follow-up).

- **The news wire had no frontend consumer at all.** The recon found the "League
  Wire" panel was fed by `recent_matches`, never `/api/news` — so `class_wire`
  (V24) and `event_news` (V27) headlines were *also* stranded. Folding
  `wire_headlines` into the standings payload (the data the ticker already loads)
  surfaced all four wire kinds with one additive field rather than a new fetch +
  loading state.

- **`StandingsResponse` is a strict model; `season_preview` is a free-form dict.**
  `wire_headlines` had to be declared on `StandingsResponse` or FastAPI strips it
  (the WT-2/WT-3/WT-12 family); `officiating_emphasis` rides inside the free-form
  `season_preview` dict and needed no model edit. The TestClient guards pin both.

- **Selection cadence.** The emphasis is selected for the UPCOMING season at the
  prior offseason (the sweep already computes `next_season_id`), so season 1 has
  no preceding offseason and is emphasis-free — honest, and consistent with the
  meta-report cadence (journalism starts after season 1).

- **Emphasis is official-engine-only.** The non-official (rec) match path ignores
  `season_emphasis`; the bound delta has no meaning outside the official catch/
  block sigmoids.

## Verification

- Full `python -m pytest -q` green (real exit code, never piped to `tail`).
- Three probes green: `meta_journalism_probe` (derived-from-data),
  `meta_drift_probe` (drift + contrarian generation), `emphasis_probe` (default
  byte-identical; active bites 21/24 seeds + symmetric + logged; deterministic
  bounded selection — observed catch ±0.08, block ±0.06, and a called-straight
  season).
- `npm run build` + `npm run lint` clean.
- TestClient strip-trap guards: `wire_headlines` survives `/api/standings`,
  `officiating_emphasis` survives `/api/command-center`.

## Disclosed deferrals

- **The full multi-season live browser acceptance walk is the owner's** (the V27
  precedent — V27's live crowning walk was likewise deferred to owner acceptance).
  The V28 surfaces require a multi-season playthrough to appear (emphasis from
  season 2, meta reports after a season's offseason, drift across several seasons);
  the data path to the client is pinned by the strip-trap TestClient guards, the
  three probes, and build/lint, per the established frontend-has-no-test-runner
  policy.
- The emphasis DISCRETION log is in the event stream + conformance ledger but not
  yet rendered in the player-facing replay UI (`collect_official_metadata` is not
  on the live replay path).
- Emphasis applies to league matches (the `game_loop` chokepoint); the auto-simmed
  event knockouts (cup / invitationals / MSI) keep the default no-emphasis — a
  clean, low-risk extension if desired (each takes the same `season_emphasis`
  kwarg, defaulted today).
- Archetype-keyed journalism remains out of scope (needs a `match_moment_counts`
  migration); `MetaPatch` stays retired.

---

## Climb-Era arc close-out (V23–V28)

The Climb-Era arc — the post-V22 direction decided 2026-06-12
(`docs/specs/2026-06-12-climb-era-vision.md`) — is now **code-complete on
`feature/v24-the-board`**:

| Milestone | What it added |
|---|---|
| **V23 The World** | The 28-club pyramid (3 domestic tiers + International Circuit), real promotion/relegation including the user club, WORLDS from Season 1, tier-scaled payouts. |
| **V24 The Board** | Recruiting as the centerpiece: whole-world AI recruiting, district-rooted caliber-banded classes, receipts-backed motivations + dealbreaker veto, the funnel + focus list, rival suitors + interest race, the money-gated Scouting Network, the class wire. |
| **V25 The Market** | Contracts: per-player salary + term, the wage bill, the Transfer Period beat, retention as recruiting's mirror, uphill poaching, AI symmetry via a tier wage-budget cap. |
| **V26 The Crowd** | Fans / facilities / bench roles / media, mostly by reviving dormant code; the first Climb-Era schema migration; append-only receipted fan ledgers. |
| **V27 The Calendar** | A season calendar of real auto-simmed knockouts: the revived Domestic Cup, cloth/no-sting Ruleset Invitationals (balance-gated), MSI + Founders' Exhibition, and the elevated Worlds-crowning ceremony beat. |
| **V28 The Weather** | The ecosystem's own weather: data-derived meta journalism, emergent AI tactic drift + a contrarian generation, and officiating points of emphasis — so the game never fully solves. |

**The throughline:** the vision's integrity contract (ADR 0002) held across all
six — every surface is derivable from real data, sourced rules stay sourced and
sim-design stays disclosed, determinism is preserved, and legacy single-league
saves remain byte-identical behind `pyramid_world_active`. No injected dials;
`meta.py`/MetaPatch stayed retired to the end.

**Vision laws kept:** no NG+, no difficulty ratchet — post-summit is legacy play
(records, defense, HoF). The Worlds crowning is a presentation beat that sets no
state; the V28 emphasis is the only seasonal "weather," and it is announced,
symmetric, logged, and byte-identical by default.

**Next:** the whole arc (V23–V28) is ready to merge to `main` as a unit, pending
the owner's live multi-season playthrough acceptance.
