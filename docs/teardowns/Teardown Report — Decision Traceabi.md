# Teardown Report — Decision Traceability

## Verdict
Dodgeball Manager is **partially traceable, with two trust-risky seams around weekly lineup agency and autopilot**. The strongest chains are Policy Editor -> saved weekly plan -> match coach policy -> tactical recap, recruiting actions -> persisted interest/band -> Signing Day offer strength, training/dev focus -> offseason development, staff training hire -> offseason growth, and primary factor -> aftermath. The main failure is that the visible Roster Lineup Editor can save a lineup that the already-open weekly command plan does not consume.

Pare MCP was not available in this session, so I used normal read-only shell inspection. Focused tests passed: `42 passed`.

## Highest-Signal Findings

### 1. Roster Lineup Editor Can Save a Lineup That the Current Weekly Plan Ignores
- Severity: **High**
- Evidence: [LineupEditor.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/lineup/LineupEditor.tsx:78>) calls `commandApi.saveLineup`; [client.ts](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/api/client.ts:94>) posts `/api/lineup`; [web_status_service.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/web_status_service.py:224>) saves only `lineup_default`. But [command_week_service.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/command_week_service.py:60>) reuses an existing weekly plan, and [command_center.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/command_center.py:255>) refreshes opponent/context, not `plan["lineup"]` from the new default. Simulation then consumes the stale weekly plan through [use_cases.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/use_cases.py:982>) and [match_orchestration.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/match_orchestration.py:320>).
- Why it matters: A player can promote a bench player in the Roster modal, return to Command Center, confirm/lock, and still field the old weekly six.
- Reproduction / inspection path: In-memory repro showed `lineup_default_first6` changed to `['aurora_6', ...]` while `refetched_plan_lineup` stayed `['aurora_3', ...]`.
- Suggested fix direction: When `/api/lineup` saves during `SEASON_ACTIVE_PRE_MATCH`, update the current weekly plan lineup and mark `lineup_confirmed = true`, or route the editor through `save_command_center_plan_payload(... line_up_player_ids ...)`.
- Regression gate: Add an API/service test: create weekly plan, save `/api/lineup` with a different six, fetch `/api/command-center`, then simulate and assert `match_lineup_override` matches the edited six.

### 2. Fast-Forward Bypasses Scout/Confirm Readiness Decisions
- Severity: **Medium**
- Evidence: [PreSimDashboard.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/match-week/command-center/PreSimDashboard.tsx:822>) renders Fast-forward with no `isReadyToLock` guard. [use_cases.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/use_cases.py:1174>) explicitly runs `simulate_week(update=None)` and says readiness gates “never block simulation.”
- Why it matters: Scout Opponent and Confirm Lineup are presented as readiness gates, but Fast-forward skips them wholesale. That can be valid autopilot behavior, but the UI should not make those gates feel mandatory and then offer a nearby bypass without clearer framing.
- Reproduction / inspection path: Open a fresh week where scout/confirm are unmet; Fast-forward remains callable while Lock Plan is disabled.
- Suggested fix direction: Either require readiness before fast-forward, or label it as “Auto-pilot with default plan” and show exactly which decisions will be skipped.
- Regression gate: E2E/API test that asserts chosen product behavior: blocked until ready, or explicit skip disclosure visible before autopilot.

### 3. Rival/AI Adaptation Can Be Consumed Before It Is Explained
- Severity: **Medium**
- Evidence: [matchup_details.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/matchup_details.py:142>) surfaces `adaptation_summary` only if an opponent weekly plan already exists. But AI plans are prepared inside simulation at [use_cases.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/use_cases.py:1066>) via [ai_program_manager.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/ai_program_manager.py:148>), after the pre-match command-center payload has already been built.
- Why it matters: The opponent may adapt mechanically for a dominant user, but the pre-match UI may show no adaptation read for that same match unless the AI plan happened to be pre-created.
- Reproduction / inspection path: Inspect `build_command_center_state -> build_matchup_details` before `prepare_ai_plans_for_matches`; tests only cover `tactical_diff` with a manually supplied adaptation summary.
- Suggested fix direction: Precompute opponent AI plan before building matchup details, or explicitly defer adaptation messaging to aftermath/replay.
- Regression gate: Integration test where user win rate >= 70%, command-center payload for next user match includes adaptation intel before simulation.

## Traceability Table

| Decision | UI | Persistence | Sim/domain consumer | Feedback surface | Test coverage | Verdict |
|---|---|---|---|---|---|---|
| Weekly intent | `MatchWeek`, `PreSimDashboard` | `weekly_command_plans.plan_json` | `simulate_week`, `_apply_command_plan_to_match` | dashboard + aftermath | `test_command_plan_lock_preserves_tactics.py` | Traceable |
| Policy Editor | `PolicyEditor` | weekly plan `tactics` | `CoachPolicy`, match engine | tactical recap/verdict | `test_locked_plan_drives_sim_and_recap.py` | Strong |
| Roster Lineup Editor | `LineupEditor` | `lineup_default` | only if no stale weekly plan | roster/command lineup | partial manual tests | **Broken if plan exists** |
| Confirm Lineup | `PreSimDashboard` | weekly plan `lineup_confirmed` | readiness only | readiness gates | `test_readiness_gates.py` | UI gate only |
| Scout Opponent | `PreSimDashboard` | weekly plan `opponent_scouted` | readiness only | readiness gates | `test_readiness_gates.py` | UI gate only |
| Dev focus | `PreSimDashboard` select | plan `department_orders.dev_focus` | `apply_season_development` in offseason | aftermath + dev beat | `test_development_growth_band.py`, `test_dynasty_office.py` | Traceable |
| Recruit Scout/Contact/Visit | `ProspectCard` | `prospect_recruitment_actions_json`, slot state | `current_interest`, Signing Day offer strength | board + action delta | `test_recruiting_actions.py`, `test_recruiting_interest_transfer.py` | Strong |
| Staff hire | `DynastyOffice` Staff tab | `department_heads`, `staff_market_actions_json` | training modifier in offseason growth | staff proof chips | `test_dynasty_office.py` | Strong for training |
| Fast-forward | `PreSimDashboard` | reuses saved/default plans | `auto_pilot_weeks` | summaries/final aftermath | `test_auto_pilot.py` | Traceable but bypasses gates |
| Primary factor | `Aftermath` | derived from match result/events | `derive_match_explanation` | `PrimaryFactorCard` | `test_match_explanation.py` | Strong |
| AI adaptation | pre-match matchup panel | AI weekly plan summary | AI plan applied during sim | tactical diff if plan exists | unit only | Explanation gap |

## Confirmed Strengths
- Policy choices now preserve and reach both simulation and recap.
- Recruiting actions have visible deltas and real Signing Day offer strength.
- Training staff has an honest mechanical hook into offseason development.
- Primary Factor is deterministic and tested against catch disparity, rush deficit, stamina collapse, liabilities, and decisive official scorelines.

## Open Questions
- Should Fast-forward be allowed to bypass readiness gates by design, or should it behave like a bulk “lock and simulate” path?
- Should the Roster Lineup Editor be considered the canonical weekly lineup control, or only a season default editor?

## Suggested Next Prompt
“Implement the High finding from the decision traceability teardown: make `/api/lineup` edits update the active weekly command plan lineup during pre-match weeks, mark lineup confirmed, and add a regression test proving the edited six is the one simulated.”

Goal complete. Token usage reported by the goal tracker: 190,845 tokens over about 4m54s.