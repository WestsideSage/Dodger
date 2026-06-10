# 2026-06-09 — Adversarial QA / Integrity / Truthfulness Red Team

Role: adversarial QA lead, simulation-integrity auditor, player-trust red team.
Scope question: **where can Dodgeball Manager betray player trust, and what can
be fixed or guarded now?** Method: trust-risk map → UI→API→persistence→engine
decision traces → fix/guard → verify. Tooling note (per `AGENTS.md`): Pare MCP
was available but the built-in structured search/read tools and raw
shell/pytest output were more suitable for this audit's trace-and-verify work,
so those were used instead — stated here as the required fallback disclosure.
Browser verification ran through the Claude Preview MCP against the prod
server (`python -m dodgeball_sim`, port 8000, fresh PID, real launch token).

---

## 1. Trust verdict

**Sound core, dishonest periphery — now corrected.** The outcome-bearing spine
(seeded RNG everywhere, plan→sim→recap traceability, official game-point
scorelines, recruiting interest→signing, readiness gates) held up under
adversarial tracing. The real trust failures were at the edges: one genuine
outcome-affecting persistence bug (the player's dev focus could be silently
replaced by an AI club's plan), and a cluster of player-facing copy that
claimed mechanical systems — injuries, morale, fatigue recovery, "training
units", opening-rush enforcement — that do not exist in code. All of those are
fixed or disclosed in this pass. The V15 legibility layer itself was the worst
offender (term registry stamping "AFFECTS PLAY" on six no-op orders), which is
exactly the failure mode ADR 0002 exists to prevent: the truth-labeling system
must never be the thing that lies.

## 2. Highest-risk findings, ranked

1. **[FIXED — real bug, outcome-affecting] Offseason dev focus read had no
   club filter.** `offseason_ceremony.initialize_manager_offseason` read the
   season's dev focus with `SELECT plan_json FROM weekly_command_plans WHERE
   season_id = ? ORDER BY week DESC LIMIT 1` — no `club_id`. AI weekly plans
   are persisted into the SAME table (`prepare_ai_plans_for_matches` →
   `save_weekly_command_plan`) carrying `dev_focus` values `YOUTH`/`VETERAN`
   (`ai_orders.get_ai_department_orders`) that `apply_season_development`
   silently treats as BALANCED. So the player's chosen focus could be replaced
   by an arbitrary AI club's plan from the final (often playoff) week — the
   core "decisions traceable to outcomes" contract broken at the season's most
   consequential moment. Every other `weekly_command_plans` query in the repo
   filters by club; this was the only unfiltered read.
2. **[FIXED — copy] The legibility term registry claimed six no-op department
   orders "AFFECT PLAY".** `terms.ts` marked `dept.tactics/training/
   conditioning/medical/scouting/culture` as `kind: 'mechanical'` with claims
   like "Affects whether injured or tired players are rested or pushed" and
   "Culture orders influence morale" — there is no injury, morale, or
   inter-week fatigue system, and apart from `dev_focus` these orders have
   **zero mechanical consumers** (verified by tracing every
   `department_orders` read in `src/`). The Dynasty Office Settings modal
   compounded it ("reduces injury chance", "fewer rushed throws", "short-term
   edge, long-term cost"). Contrast: the adjacent `staff.*` registry entries
   and `staff_market.py` were scrupulously honest about the same departments.
3. **[FIXED — disclosure] Opening Rush knobs are placebo on official careers
   (the default).** `rush_commit`/`rush_target` are consumed by the rec engine
   only; the official conformance ledger itself records "ABSENT: opening-rush
   activation is not in the official engine" (WT-20 open). New careers default
   to `official_foam`, so the Policy Editor's Opening Rush panel (with
   previews like "send the whole front to win the opening ball race") was a
   fake decision for every new player. `approach`/`target_focus`/
   `catch_posture` ARE consumed by the official engine (`official_tactics.py`)
   — the disclosure is scoped to the two rush rows only.
4. **[FIXED — copy] Weekly development feedback claimed "+1 training unit
   toward X for [names]".** No training-unit accumulator exists anywhere.
   Mechanically, only the dev focus in effect at season's end steers offseason
   growth (plus real match-minute reps); weekly focus choices count toward
   promise evaluation and recruiting credibility, not ratings. The bye-week
   "your starters avoided fatigue exposure" / "Squad Rested" / "Recovered this
   week" card fabricated a recovery system (stamina is a fixed rating; nothing
   persists between weeks), and the post-week "Roster health" lane invented
   "medical incidents". The readiness gate / staff recommendation said a
   starter was "critically fatigued" and that Preserve Health "protects them"
   — both transient-state claims about a static rating and a tactics preset.
5. **[FIXED — test] A false-confidence test guarded the staff-development
   hook.** `test_offseason_dev_path_loads_department_head_and_applies_modifier`
   inserted a `development` head while the code reads the `training` head, so
   the modifier was 0.0 on both sides of a `>=` assertion — it passed
   trivially and could never detect a broken staff hook.
6. **[OPEN — owner decision] The V8 recruiting-promise lane has no UI.**
   Backend-complete (`POST /api/dynasty-office/promises`, 3-active cap,
   offseason evaluation with evidence strings), but **no frontend component
   creates or displays promises**, and promise results feed nothing
   mechanical. Currently dormant rather than lying (nothing is claimed to the
   player), but `STATUS.md`/V8 docs said "exposed through the Dynasty Office"
   — stale. Logged in `docs/STATUS.md` Open Work #5.

Lower-severity notes (not fixed, recorded honestly): (a) signing-day
`conduct_recruitment_round` falls back to `credibility_score=50` when a
prospect was never touched by an action, so the board's displayed base
interest (real credibility) and the signing-day base can drift for
zero-action prospects — touched prospects are consistent; (b) `bye` weeks do
not append `command_history`, so promise/credibility week-counts exclude byes
(defensible, but the promise threshold copy — if a UI ever ships — should say
"match weeks").

## 3. What was attacked and found SOLID (verified, no change)

- **Seeded randomness:** every outcome path injects a seeded
  `random.Random`/`DeterministicRNG`; the only unseeded call is CLI root-seed
  *generation* (`dynasty_cli.py:1985`), which is then persisted. Frontend has
  zero `Math.random`/`Date.now` outcome use (one display-only timestamp).
- **Plan→sim→recap truth:** `use_cases.simulate_week` reloads clubs after
  plan application (the WT-9 fix is intact); inline lineup overrides route
  through `apply_manual_lineup` validation (WT-10); AI plans prepare before
  sim on primary, bye, and playoff paths.
- **Recruiting work pays off:** Scout narrows the persisted public band;
  Contact/Visit raise persisted interest; interest mechanically strengthens
  the Signing Day offer (`recruitment.py:627`, `offer_strength=100.0 +
  interest * 0.2`).
- **Official scoreline truth:** post-week dashboard and replay surfaces use
  game points for official matches (`command_center._result_scoreline`);
  `OfficialRulesPanel` renders only real engine state; SaveMenu ruleset
  descriptions correctly disclose announced-only officiating.
- **All other `weekly_command_plans` reads** filter by club.

## 4. Fixed issues with evidence

| # | Fix | Files |
|---|-----|-------|
| 1 | Dev-focus read now filters by player club via new `_load_player_dev_focus(conn, season_id, player_club_id)` helper (documented as load-bearing) | `src/dodgeball_sim/offseason_ceremony.py` |
| 2 | `dept.*` registry entries flipped to `kind: 'flavor'` with honest copy (tooltip badge now reads FLAVOR, not AFFECTS PLAY); Settings modal descriptions rewritten as "Staff note: …" with an amber modal-level boundary statement | `frontend/src/legibility/terms.ts`, `frontend/src/components/DynastyOffice.tsx` |
| 3 | Opening Rush announced-only disclosure on official careers: `ruleset_selection` added to the command-center payload AND declared on `CommandCenterResponse` (the MatchReplayResponse field-stripping lesson), threaded to `PolicyEditor` which renders `data-testid="rush-announced-only-note"` | `src/dodgeball_sim/command_week_service.py`, `src/dodgeball_sim/server.py`, `frontend/src/types.ts`, `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`, `.../PolicyEditor.tsx` |
| 4 | Development feedback states the real rule (season-end focus steers offseason growth; per-focus attribute effects mirrored from `apply_season_development`); bye card no longer claims rest/recovery (kicker "Bye Week", no fabricated "recovered" player chips); "Roster health" lane states injuries are not modeled; "Player movement" lane states the true reps rule; health gate says "stamina rating is critically low — rotate"; staff recommendation says Preserve Health "shifts to a patient, play-safe plan" (not "protects") | `src/dodgeball_sim/use_cases.py`, `src/dodgeball_sim/command_center.py`, `src/dodgeball_sim/week_briefing.py`, `frontend/src/components/MatchWeek.tsx` |
| 5 | False-confidence staff test repaired: inserts a `training` head and asserts strict `>` (now actually fails if the hook breaks — confirmed it passes against the live hook, i.e. the modifier is visible) | `tests/test_offseason_ceremony.py` |

Evidence for #1's mechanism (pre-fix): `prepare_ai_plans_for_matches`
(`ai_program_manager.py:186`) saves AI plans through the same
`save_weekly_command_plan`; `get_ai_department_orders` (`ai_orders.py`) sets
`dev_focus` to `YOUTH`/`VETERAN`; `apply_season_development`
(`development.py:154-169`) matches none of those branches → silent BALANCED.

## 5. Tests/probes added or updated

- **NEW** `tests/test_offseason_ceremony.py::test_player_dev_focus_reads_player_plan_not_ai_plan`
  — player plan week 3 (TACTICAL_DRILLS) + later AI plan week 5 (YOUTH) must
  resolve to the player's focus.
- **NEW** `...::test_player_dev_focus_defaults_balanced_without_any_player_plan`
  — AI-only plans present → honest BALANCED.
- **REPAIRED** `...::test_offseason_dev_path_loads_department_head_and_applies_modifier`
  — `development`→`training` head, `>=`→`>` (see finding 5).
- **NEW** `tests/test_command_center_ruleset_disclosure.py` (2 tests) —
  serialization-layer guard that `/api/command-center` carries
  `ruleset_selection` (`official_foam` for official careers; key present and
  `None` for generic) so FastAPI can never silently strip the disclosure's
  data dependency.
- **UPDATED** `tests/test_aftermath_payload.py` — pins the new truthful
  dev-feedback claim instead of the fabricated "+1 training unit".
- **UPDATED** `tests/test_use_cases.py` — pins the truthful bye summary ("no
  match minutes") and asserts the fabricated "recovered players" list is gone.
- **UPDATED** `tests/test_manager_lesson.py` — fixture strings aligned to the
  corrected staff-recommendation copy (inputs, not assertions).

## 6. Verification commands and status

| Command | Result |
|---|---|
| `python -m pytest tests/test_offseason_ceremony.py -q` | **PASS** (19) |
| `python -m pytest tests/test_command_center_ruleset_disclosure.py tests/test_aftermath_payload.py tests/test_use_cases.py tests/test_manager_lesson.py tests/test_week_briefing.py tests/test_offseason_ceremony.py -q` | **PASS** (85) |
| `python -m pytest -q` (full suite, repo root) | **PASS** — exit 0, 1,271 tests collected |
| `npm run build` (frontend/) | **PASS** (vite build clean; pre-existing >500 kB chunk warning) |
| `npm run lint` (frontend/) | **PASS** (exit 0) |
| Browser (prod server, port 8000, fresh PID, loaded official_foam career) | **PASS** — `/api/command-center` serializes `ruleset_selection: "official_foam"`; Policy Editor renders the rush announced-only note (screenshot taken); Dynasty Office settings modal shows the flavor banner; `dept.medical` TermTip renders **FLAVOR** badge + "injuries are not modeled"; zero console errors |

Honest non-verification (stated, not claimed): the Playwright e2e suite was
**not** run this pass — every changed string was grepped against `tests/e2e/`
(the only `AFFECTS PLAY` assertions target archetype/playoff-line terms,
which remain mechanical; no e2e pins lane/bye/dev-feedback copy). The
offseason dev-focus fix was verified at the helper/unit level plus the full
suite, not via a full browser season playthrough. The bye-week card's new
copy is pinned by `test_use_cases.py` but was not browser-reached (requires
navigating a career to a bye).

## 7. Red-team questions, answered

- **Most dangerous player-facing lie present/likely to recur:** the legibility
  layer itself overclaiming (the `dept.*` "AFFECTS PLAY" badges). Recurrence
  vector: anyone adding a term entry defaults to `mechanical` without tracing
  a consumer. Guard suggestion (owner call): a PR rule that `kind:
  'mechanical'` requires naming the consuming module in the `why` text.
- **Decisions most at risk of becoming fake/no-op:** the six department
  orders (now disclosed as flavor — decide to wire or drop them, STATUS Open
  Work #6); the Opening Rush knobs on official careers until WT-20 ships;
  promises if a UI ever ships without mechanical consumers.
- **Docs most likely to mislead future agents:** the V8 claim that promises
  are "exposed through the Dynasty Office" (false for current UI — STATUS
  Open Work #5 now records it); STATUS.md's pointer to the moved fable UX
  review (fixed); any doc treating department orders as gameplay systems.
- **Tests giving false confidence:** the staff-dev-modifier test (repaired —
  finding 5). Pattern to watch: `>=` assertions comparing two identically
  broken runs, and fixtures whose key strings ('development') silently miss
  the code's lookup keys ('training').
- **Edge state most likely to break a real playthrough:** none found at
  crash level this pass; the dev-focus hijack (finding 1) was the most likely
  *silent* corruption — it required only reaching one offseason after any
  same-or-later-week AI plan write, i.e. essentially every career.
- **Unresolved issue that must NOT be "fixed" without owner input:** WT-20
  opening-rush/No-Blocking/throw-clock enforcement (primary-source parameters
  still OPEN); promise-lane revive-or-remove; making department orders real;
  weekly dev-focus accumulation (changing development to honor per-week
  choices would be a balance change, not a bugfix).

## 8. Remaining risks and owner-decision items

1. **WT-20** stays open (unchanged); the rush disclosure is the interim truth.
2. **Promise lane** (STATUS Open Work #5): revive UI or remove backend lane.
3. **Department orders** (STATUS Open Work #6): wire real effects or drop the
   modal; current state is honest flavor.
4. Signing-day credibility fallback (=50) for zero-action prospects — minor
   display/mechanics drift, fix opportunistically when touching recruitment.
5. `dynasty_office.py` evaluation evidence strings (promise results) have no
   surface to render them — covered by item 2.

## 9. Docs/source-of-truth updates made

- `docs/STATUS.md`: corrected the moved-file pointer
  (`docs/ux-reviews/fable/…` → `docs/fable/…`); added Open Work #5 (promises
  have no UI; V8 claim stale) and #6 (department orders flavor-only, copy
  corrected, wire-or-drop decision).
- This handoff: `docs/fable/2026-06-09-adversarial-qa-trust-audit.md`.
