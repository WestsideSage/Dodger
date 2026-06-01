# Teardown Report — AI Opponent and Rival Ecosystem

## Verdict
Rivals are partially implemented: the source now has real archetype hooks for intent, orders, tactics, lineup, recruiting preference, adaptation summaries, and trajectory rows, and the core V12 unit tests pass. But the ecosystem is still shallow/risky because several claims are only lightly tested, one simulation path can ignore newly saved AI tactics unless clubs are reloaded, standings identity labels can diverge from persisted archetypes, and the promised long-run parity/anti-dominance proof is not present as an executable current gate.

## Highest-signal findings

### Finding 1
- Severity: High
- Evidence: `src/dodgeball_sim/command_week_service.py::run_simulation_command` calls `prepare_ai_plans_for_matches(...)` and then immediately simulates with the already-loaded `clubs` mapping. `src/dodgeball_sim/game_loop.py::simulate_scheduled_match` passes those stale `Club.coach_policy` objects into `simulate_match`; lineups are loaded from match overrides, but tactics come from the stale club objects. `src/dodgeball_sim/use_cases.py::simulate_week` explicitly reloads clubs after AI/user plan application, which is the correct pattern.
- Why it matters: AI plans may be saved and displayed as adaptive or archetype-aware while the match engine still uses pre-plan tactics in this path. That makes rival behavior look alive in data but not necessarily on-court.
- Reproduction / inspection path: Inspect `command_week_service.py::run_simulation_command`, `match_orchestration.py::_apply_command_plan_to_match`, and `game_loop.py::simulate_scheduled_match`.
- Suggested fix direction: Reload `clubs = load_clubs(conn)` after `prepare_ai_plans_for_matches(...)` in `command_week_service.py`, matching the explicit fix already present in `use_cases.py::simulate_week`.
- Regression gate: Add a command-week test where an AI opponent’s persisted archetype tactic changes `coach_policy`, then assert the simulated match record/replay policy reflects the AI plan.

### Finding 2
- Severity: High
- Evidence: `docs/STATUS.md` claims V12 had a 50-season Monte Carlo parity sweep, but current repo search found no V12-specific executable sweep or parity gate. `tests/test_monte_carlo.py` covers throw/hit/catch probability primitives, not AI archetype championship parity. V12 acceptance wanted distinct archetype champions and no single archetype over 50%.
- Why it matters: Long-run parity and degenerate strategy detection are central to “alive and fair” rivals. Without a current probe, archetype tables can drift into one dominant program style unnoticed.
- Reproduction / inspection path: Search for `50-season`, `championship parity`, `archetype championship`, and inspect `tests/test_monte_carlo.py`.
- Suggested fix direction: Add a cheap deterministic league sweep tool/test that records champion archetype distribution, department-order distribution, and average standings by archetype.
- Regression gate: CI probe with relaxed deterministic thresholds: at least 3 champion archetypes over N seasons, no single archetype above a chosen cap, and distinct order/tactic distributions by archetype.

### Finding 3
- Severity: Medium
- Evidence: `src/dodgeball_sim/web_status_service.py::build_standings_payload` sends both `program_archetype` and `program_trajectory_label`, but the label prefers `_CLUB_IDENTITY_LABELS` over the persisted archetype. Example: a club can have `program_archetype="Contender"` while standings labels it with curated identity text like “Power Throwers” or “Catch Wall.”
- Why it matters: The UI may explain rival identity with a label that is not the actual AI decision archetype. That weakens scouting trust.
- Reproduction / inspection path: Inspect `_CLUB_IDENTITY_LABELS` and `traj_label = f"Yr {year_num} · {identity}"` in `web_status_service.py`.
- Suggested fix direction: Keep flavor identity separate from mechanical AI archetype, and render both only when clearly labeled.
- Regression gate: Standings payload/UI test asserting the displayed “strategy archetype” matches `Club.program_archetype`, with curated identity shown as flavor only.

### Finding 4
- Severity: Medium
- Evidence: `src/dodgeball_sim/recruitment.py::_ensure_recruitment_prepared` applies V12 recruiting score shims for Development Factory, Contender, and Aging Veterans, but search found no tests proving Development Factory picks upside or Contender picks floor at parity.
- Why it matters: Rival signings are supposed to express program identity. Untested scoring overlays can silently fail or be swamped by existing public/need/preference scores.
- Reproduction / inspection path: Inspect `recruitment.py` around the V12 AI recruiting preference shim; search tests for “higher-upside” and “higher-floor.”
- Suggested fix direction: Add narrow fixtures with two prospects equal except public OVR band high/floor and assert archetype-specific ranking changes.
- Regression gate: Tests for Development Factory, Contender, and Aging Veterans recruitment ranking.

## Rival System Matrix

| Subsystem | Evidence of identity | Risk | Missing test/probe | Recommendation |
|---|---|---|---|---|
| AI program manager | `build_ai_weekly_plan` composes intent, orders, tactics, lineup | Some paths may not apply tactics to sim | End-to-end policy reaches match | Reload clubs after AI plan apply and test replay policy |
| Program archetypes | Persisted on `Club`; classified in persistence/career setup | UI label can diverge from real archetype | Payload truth test | Separate flavor identity from mechanical archetype |
| Weekly plans | Saved in `weekly_command_plans`; unit tests cover shape | Shape tests do not prove on-court effect | Plan-to-result integration test | Assert saved AI tactics reach engine |
| Adaptation triggers | `load_recent_user_win_rate >= 0.70`; visible summary | No direct test for trigger and no-op below threshold | Adaptation trigger tests | Add 69%/70% boundary tests and preview surfacing test |
| Rival recruitment | Score shim exists in `recruitment.py` | Untested and may be swamped | Prospect ranking fixtures | Gate archetype-specific signing preferences |
| Roster construction | AI lineup optimizer and Development Factory rookie swap | Liability-aware claim is weaker than code evidence | Liability penalty test | Add realistic liability fixture |
| Staff market | Staff effect summaries exist, but V12 mostly reads static order lanes | No strong evidence AI staff market choices shape rivals | AI staff hire/impact probe | Keep as follow-up, not V12 proof |
| Standings trajectory labels | Standings has year and identity label | Label may not match actual decision archetype | UI/payload consistency test | Show true archetype distinctly |
| Matchup preview scouting | `matchup_details` can surface adaptation summary and tactical diff | Depends on opponent plan already existing | Browser/API adaptation preview test | Build deterministic dominant-user setup |
| Program memory/history | `program_trajectory` rows saved at season finalization; history endpoint returns them | Limited use in standings label beyond year count | Multi-season trajectory test | Assert year 2+ history uses real rows |
| Long-run parity | Status says sweep happened | No current executable proof found | V12 parity sweep | Add cheap deterministic parity probe |
| Anti-dominance | Bounded visible adaptation exists | Only static inspection, no behavior probe | Dominance response simulation | Test no stat boost, one visible shift only |

## Fairness / Integrity Check
I found no evidence of hidden rating boosts, rubber-banding, user aura, unseeded outcome randomness, or engine-side AI cheat branches in the inspected V12 path. The adaptation implementation changes intent or department orders and writes visible summary text. The main fairness risk is not cheating; it is a truthfulness risk where visible AI plans may not always reach the simulation tactics path.

## Confirmed strengths
- V12 unit tests passed: `20 passed` for `test_ai_program_manager.py`, `test_ai_intent.py`, `test_ai_orders.py`, `test_ai_tactics.py`, `test_ai_lineup.py`, and `test_program_archetype_persistence.py`.
- Archetype-specific decision modules exist and are simple to inspect: `ai_intent.py`, `ai_orders.py`, `ai_tactics.py`, `ai_lineup.py`.
- Adaptation is bounded and visible in plan summary text, not hidden engine math.
- Program trajectory persistence exists via `program_trajectory` and `record_season_program_trajectories`.
- Matchup preview has an explicit path to surface adaptation summaries through `matchup_details.py` and `tactical_diff.py`.

## Open questions
- Was the 50-season V12 parity sweep ever committed as a tool or only run ad hoc? I could not find a current executable gate.
- Which command path is the primary production path now: `use_cases.simulate_week` or `command_week_service.run_simulation_command`? The stale-clubs issue severity depends on that routing.
- Should curated club identity labels be treated as separate flavor brands, or should they be retired in favor of mechanical archetypes?

## Suggested next prompt
Implement the V12 rival-integrity hardening pass: reload AI tactics before command-week simulation, add adaptation boundary tests, add recruitment-archetype ranking tests, make standings distinguish flavor identity from mechanical archetype, and add a cheap deterministic long-run archetype parity probe.

Verification note: Pare MCP was not available in this session, so I used normal shell/search commands. Broader `test_server.py + test_auto_pilot.py + test_command_center.py` was blocked by Windows temp-directory permission errors; the V12-focused Python tests passed. Goal usage: 162,548 tokens over about 3 minutes 18 seconds.