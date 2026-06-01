# Teardown Report — Architecture Boundary

## Verdict
The engine boundary is healthy, but the franchise/domain boundary is eroding. I did not find engine imports of SQLite, frontend, server, or Tkinter concerns, and the outcome-randomness path appears seeded. The main risk is that Tk-era helper dispersion moved persistence, presentation payload assembly, and business rules into broad domain modules instead of creating thin service/adapters. Pare MCP was not available in the callable tools, so I used static inspection via normal repo search. I did not run focused tests because the findings are source-level boundary issues, not behavior questions.

## Highest-signal findings

### 1. Recruitment domain now mixes rules, persistence, raw SQL, and compatibility glue
- Severity: High
- Evidence: [recruitment.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/recruitment.py:36>) has `get_current_recruiting_budget(conn, ...)`; [recruitment.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/recruitment.py:285>) signs prospects by loading/saving rosters and deleting scouting state with raw SQL; [recruitment.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/recruitment.py:438>) prepares rounds by loading/saving boards/offers; [recruitment.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/recruitment.py:501>) applies V12 AI preference weights inside that orchestration.
- Why it matters: `recruitment.py` is listed by AGENTS as franchise/domain, but it now owns DB shape, persistence transactions, signing-side effects, and AI recruiting policy tweaks. That makes recruiting changes hard to test through pure inputs and increases the chance of class-year or signing-state regressions.
- Reproduction / inspection path: inspect `src/dodgeball_sim/recruitment.py`, then compare to pure `src/dodgeball_sim/recruitment_domain.py`.
- Suggested fix direction: split into pure recruitment rules plus a `recruitment_service` or persistence-facing adapter that owns `conn`, SQL, and save sequencing.
- Regression gate: add a no-DB import/source test for the pure recruitment rules module, plus service tests for `conduct_recruitment_round` and `sign_prospect_to_club`.

### 2. Scouting module has both pure seeded scouting and DB-backed presentation/mutation helpers
- Severity: Medium
- Evidence: [scouting.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/scouting.py:8>) repeats `sqlite3` and typing imports three times; [scouting.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/scouting.py:141>) builds scout strip data from persistence; [scouting.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/scouting.py:168>) builds prospect rows from persistence; [scouting.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/scouting.py:364>) writes scout track records while also returning a display summary.
- Why it matters: a pure deterministic report generator and DB-backed web/view helpers now share one module. The tests explicitly bless this drift: [test_scouting.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_scouting.py:88>) says the old no-DB boundary test was removed because the module responsibilities changed.
- Reproduction / inspection path: inspect `scouting.py` top imports and functions after “formerly manager_helpers”; inspect `tests/test_scouting.py`.
- Suggested fix direction: keep `generate_scout_report` and scouting math in `scouting.py`; move prospect-board/display/read-write helpers to `scouting_service.py` or `scouting_views.py`.
- Regression gate: restore a purity test for `scouting.py`; add service-level tests for the DB-backed helpers.

### 3. AI program manager reads DB state inside the planning module
- Severity: Medium
- Evidence: [ai_program_manager.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/ai_program_manager.py:43>) directly queries `matches`; [ai_program_manager.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/ai_program_manager.py:61>) catches missing schema as control flow; [ai_program_manager.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/ai_program_manager.py:148>) then prepares and persists AI plans through injected persistence callbacks.
- Why it matters: the AI planning rule “adapt when user win rate >= 70%” is legitimate, but the module couples the rule to one table shape. That makes the AI policy harder to simulate independently and easier to break during persistence migrations.
- Reproduction / inspection path: inspect `load_recent_user_win_rate` and `prepare_ai_plans_for_matches`.
- Suggested fix direction: pass `recent_user_win_rate` into the pure planner, and let a service/adapter load it from persistence.
- Regression gate: pure tests for `build_ai_weekly_plan(..., adapt_to_user=True)` plus adapter tests for loading the rolling win rate.

### 4. Broadcast presentation reads persistence directly and formats survivor scores for historical hooks
- Severity: Medium
- Evidence: [broadcast.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/broadcast.py:6>) imports persistence; [broadcast.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/broadcast.py:186>) raw-queries `match_records`; [broadcast.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/broadcast.py:314>) formats `home_survivors` / `away_survivors` as the last-meeting score. But official match records also persist `home_game_points` / `away_game_points` in [persistence.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/persistence.py:1027>).
- Why it matters: frontend code already treats official scorelines as game points to avoid survivor-score contradictions. Broadcast hooks can now drift from the canonical scoring model for official matches.
- Reproduction / inspection path: inspect `broadcast.load_last_meeting`, `_historical_hook`, and `persistence` official score columns.
- Suggested fix direction: move DB reads out of `broadcast.py`; pass a last-meeting DTO that includes `scoring_model`, `home_game_points`, and `away_game_points`, then format through a shared scoreline helper.
- Regression gate: add a broadcast test for an official last meeting where survivor counts differ from game points.

## Boundary Violations

| Layer | Expected responsibility | Observed issue | Evidence | Fix direction |
|---|---|---|---|---|
| Franchise/domain | Recruiting rules, preferably pure helpers | `recruitment.py` owns DB reads/writes, raw SQL, roster mutation, AI weight shim | [recruitment.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/recruitment.py:438>) | Split pure rules from persistence-facing recruitment service |
| Franchise/domain | Scouting rules and explicit data flow | `scouting.py` mixes seeded report generation with DB-backed view builders and writes | [scouting.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/scouting.py:141>) | Keep pure scouting in module; move view/service helpers out |
| Domain/service | AI plan rules independent of DB shape | `ai_program_manager.py` directly queries `matches` | [ai_program_manager.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/ai_program_manager.py:43>) | Inject loaded win-rate into pure planner |
| Presentation/API | Presentation renders supplied facts | `broadcast.py` loads SQL and formats survivor scores despite official game-point columns | [broadcast.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/broadcast.py:186>) | Use persistence adapter + shared scoreline DTO |
| Tests | Encode intended boundaries | `test_scouting.py` documents removal of a no-DB boundary test | [test_scouting.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_scouting.py:88>) | Restore purity tests around renamed pure modules |

## Confirmed strengths
Engine/core modules inspected by import scan (`engine.py`, `models.py`, `rng.py`, `config.py`, `events.py`, `rec_engine.py`, `official_engine.py`, `official_resolution.py`, `official_actions.py`, `official_tactics.py`) had no SQLite, persistence, server, frontend, or Tkinter imports. Randomness hits in outcome modules were seeded: `rec_engine.py` uses `random.Random(mi.seed)`, official engine uses `random.Random(seed)`, and core `rng.py` wraps seeded `random.Random`.

Tkinter source cleanup is real in current source/tests: search found no live `tkinter` imports under `src/dodgeball_sim` or `tests`; remaining references are comments and archived docs.

## Open questions
The main question is whether Maurice wants `scouting.py` and `recruitment.py` reclassified as service modules after the Tk cleanup, or whether the original domain/persistence split should be restored. That decision affects naming and regression-test expectations.

## Suggested next prompt
“Refactor the highest-risk architecture boundary issue first: split `src/dodgeball_sim/recruitment.py` into pure recruitment rules and a persistence-facing recruitment service, preserving behavior and adding regression tests that keep the pure module free of SQLite/persistence imports.”