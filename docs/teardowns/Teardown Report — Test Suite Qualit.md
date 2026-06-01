# Teardown Report — Test Suite Quality

## Verdict
Regression coverage is strong but uneven. The backend suite is doing the important work: deterministic snapshots, official scoring, balance probes, lineup parity, tactics-to-sim plumbing, recruiting continuity, season rollover, playoffs, and save boundaries are all pinned by focused tests. The main risk is not missing total coverage; it is that some “official conformance” and browser gates are too shallow to prove the integrity contract by themselves. No code was modified. Pare MCP was unavailable in this session, so I used read-only shell inspection as the fallback.

## Highest-signal findings

### Finding 1
- Severity: Medium
- Evidence: [tests/test_official_conformance_matrix.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_official_conformance_matrix.py:17>) maps rule sections to files, but [test_section_has_a_test_home](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_official_conformance_matrix.py:41>) only asserts that each file exists and contains `"def test_"`.
- Why it matters: This can pass even if the named file’s assertions stop covering that rule section. It guards test-file presence, not conformance behavior.
- Reproduction / inspection path: Read [lines 41-47](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_official_conformance_matrix.py:41>).
- Suggested fix direction: Map each section to explicit test function names or markers, then assert those exact tests exist. Better: centralize a rule-section registry that each conformance test declares.
- Regression gate: `python -m pytest tests/test_official_conformance_matrix.py tests/test_official_sequence.py tests/test_official_burden.py tests/test_official_discipline.py -q`

### Finding 2
- Severity: Medium
- Evidence: Browser smoke tests often assert that surfaces exist after simulation, not that displayed decision consequences match backend proof. Example: [tests/e2e/v14-legibility.spec.ts](</C:/GPT5-Projects/Dodgeball Simulator/tests/e2e/v14-legibility.spec.ts:25>) checks `tactical-diff`, `staff-impact`, `primary-factor`, score, and replay visibility; [tests/e2e/official-rules-replay.spec.ts](</C:/GPT5-Projects/Dodgeball Simulator/tests/e2e/official-rules-replay.spec.ts:38>) checks official replay labels like `GAME CLOCK`, `BURDEN`, and `RULE CALLS`.
- Why it matters: These tests could pass if the UI renders panels with stale or generic text while the player’s actual plan, lineup, or match explanation has drifted. Backend tests catch much of this, but the browser gate does not fully prove the player sees the truthful result.
- Reproduction / inspection path: Inspect [v14 legibility lines 25-55](</C:/GPT5-Projects/Dodgeball Simulator/tests/e2e/v14-legibility.spec.ts:25>) and [official replay lines 37-43](</C:/GPT5-Projects/Dodgeball Simulator/tests/e2e/official-rules-replay.spec.ts:37>).
- Suggested fix direction: Add one browser test that changes a user-visible decision, simulates, opens aftermath/replay, and asserts the same selected plan/score/explanation appears in the rendered text.
- Regression gate: A Playwright spec that selects a non-default tactic or lineup, simulates a week, and checks aftermath + replay copy against `/api/match-replay/{match_id}`.

### Finding 3
- Severity: Low
- Evidence: The long browser playthrough specs use repeated fixed waits and structural selectors. [tests/e2e/naive_playtest_runner.spec.ts](</C:/GPT5-Projects/Dodgeball Simulator/tests/e2e/naive_playtest_runner.spec.ts:36>) uses many `waitForTimeout` calls; [tests/e2e/maximized-playthrough-qa.spec.ts](</C:/GPT5-Projects/Dodgeball Simulator/tests/e2e/maximized-playthrough-qa.spec.ts:47>) does the same in a multi-step audit.
- Why it matters: These are useful exploratory smoke tests, but fixed timing creates flakes and slows focused phases. They are less reliable as regression gates than web-first assertions.
- Reproduction / inspection path: `rg -n "waitForTimeout" tests/e2e`
- Suggested fix direction: Keep one manual/deep-playtest spec if useful, but graduate critical paths into shorter specs using role/text locators and `expect(...).toBeVisible()` or API-backed polling.
- Regression gate: Replace sleeps around save creation, command lock, simulation completion, and offseason transitions with web-first assertions.

### Finding 4
- Severity: Low
- Evidence: Several payload tests only assert top-level shape. [tests/test_ceremony_payload.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_ceremony_payload.py:1>) states that it checks top-level keys; examples include `assert "awards" in result` and `isinstance(result["awards"], list)` at [lines 34-35](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_ceremony_payload.py:34>), similar checks through [lines 186-193](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_ceremony_payload.py:186>).
- Why it matters: These are acceptable smoke tests, but they should not be mistaken for proof that offseason beats are truthful or player-visible. Stronger tests do exist elsewhere, so this is not a blocker.
- Reproduction / inspection path: Read [tests/test_ceremony_payload.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_ceremony_payload.py:1>).
- Suggested fix direction: Leave shape tests as smoke coverage, but require behavior tests for every beat that claims causality, record proof, development growth, or recruiting payoff.
- Regression gate: Use existing deeper tests as the required gate, e.g. offseason records/development/recruiting tests, not this file alone.

## Regression Coverage Map

| System | Existing tests | Missing failure mode | Recommended test | Priority |
|---|---|---|---|---|
| Generic golden engine | [test_phase_one_golden_log_regression](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_regression.py:57>) snapshots `MatchEngine().run(... seed=31415)` | Only one scenario; broad but brittle by design | Keep golden, add targeted tests for any intended event-contract change | High |
| Official scoring / survivor details | [test_official_scoring.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_official_scoring.py:12>), [test_official_replay_scoreboard.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_official_replay_scoreboard.py:12>), catch/sequence tests | Conformance matrix does not prove section-level assertions | Explicit test-name mapping per rule section | High |
| Engine balance / hidden buffs | [test_engine_health.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_engine_health.py:17>) and [test_official_engine_balance.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_official_engine_balance.py:24>) | Statistical smoke can miss narrower policy regressions | Keep probes, add smaller deterministic decision-effect tests when tuning policy knobs | High |
| Tactics decision effect | [test_locked_tactics_reach_sim_and_recap](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_locked_plan_drives_sim_and_recap.py:28>) | Browser may still render stale text | Add Playwright plan-change to aftermath/replay proof test | High |
| Lineup / fielded six | [test_canonical_fielded_six.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_canonical_fielded_six.py:92>) pins briefing/sim parity and optimized six effect | Browser lineup edits could render without persistence proof | Add Playwright edit-lineup, simulate, assert replay starters | Medium |
| Recruiting continuity | [test_recruiting_interest_transfer.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_recruiting_interest_transfer.py:26>) and [test_new_game_flow.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_new_game_flow.py:59>) | Full signing-day odds/effect path not strongly browser-pinned | Add end-to-end targeted recruit action to signing-day card test | Medium |
| Season rollover / playoffs | [test_season_rollover.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_season_rollover.py:95>) and [test_playoff_resolution.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_playoff_resolution.py:16>) | UI proof for rollover/offseason state is lighter | Add browser post-rollover state consistency check | Medium |
| Frontend build/lint | [frontend/package.json](</C:/GPT5-Projects/Dodgeball Simulator/frontend/package.json:8>) has build/lint scripts | Root `package.json` only exposes e2e, not build/lint | Add root scripts or CI task for `frontend` build + lint | Medium |
| Playwright E2E | [playwright.config.ts](</C:/GPT5-Projects/Dodgeball Simulator/playwright.config.ts:15>) runs e2e with one worker across browsers | Some tests are smoke/structure-heavy | Add shorter proof-based specs for decisions and state transitions | Medium |

## Brittle or low-value tests

- [tests/test_official_conformance_matrix.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_official_conformance_matrix.py:41>) is low-value as written because it proves file existence, not conformance.
- [tests/test_ceremony_payload.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_ceremony_payload.py:1>) is shape-only smoke coverage. Useful, but not a regression gate for truthful offseason content.
- [tests/e2e/naive_playtest_runner.spec.ts](</C:/GPT5-Projects/Dodgeball Simulator/tests/e2e/naive_playtest_runner.spec.ts:36>) is brittle as a gate because it relies heavily on fixed waits. It is better treated as exploratory playtest automation.

## Confirmed strengths

- Golden deterministic regression exists and is direct: [tests/test_regression.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_regression.py:57>) compares the full engine result to [tests/golden_logs/phase1_baseline.json](</C:/GPT5-Projects/Dodgeball Simulator/tests/golden_logs/phase1_baseline.json>).
- Official scoring is pinned at unit and replay-payload levels: [tests/test_official_scoring.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_official_scoring.py:12>) and [tests/test_official_replay_scoreboard.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_official_replay_scoreboard.py:68>).
- Balance gates are real, not cosmetic: [tests/test_engine_health.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_engine_health.py:17>) and [tests/test_official_engine_balance.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_official_engine_balance.py:24>) run OVR curves and moment coverage.
- Recent player-trust regressions are now pinned: tactics reach sim/recap in [tests/test_locked_plan_drives_sim_and_recap.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_locked_plan_drives_sim_and_recap.py:28>), recruiting board/offseason pool continuity in [tests/test_recruiting_interest_transfer.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_recruiting_interest_transfer.py:32>), and warm prospects target active pool in [tests/test_new_game_flow.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_new_game_flow.py:59>).
- Season rollover and playoffs have targeted gates: [tests/test_season_rollover.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_season_rollover.py:95>) and [tests/test_playoff_resolution.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_playoff_resolution.py:16>).

## Open questions

None that block confident recommendations. The main unknown is CI coverage: I found no `.github` workflow files in the repo, so I could not confirm whether Python tests, frontend build/lint, and Playwright are automatically run outside local agent practice.

## Verification Run

Focused Python subset: `32 passed` in `24.5s`.

Frontend build: passed in `6.8s`.

Frontend lint: passed in `8.9s`.

Focused Playwright: `official-rules-replay.spec.ts --project=chromium` passed in `13.2s`.

Full suite was not run, per instruction.

Goal tracker: completed, about 4m29s elapsed.

## Suggested next prompt

“Implement the top two test-suite hardening items: make official conformance map to explicit test functions, and add one Playwright decision-proof test that changes a non-default weekly tactic or lineup, simulates, and asserts aftermath/replay text matches the backend proof.”