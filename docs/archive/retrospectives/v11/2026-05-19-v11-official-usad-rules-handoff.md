# V11 USAD Rules Integration Retrospective & Handoff
Date: 2026-05-19

## Phases Completed
- **Phases 1–9**: All rules domain modules, autonomous official engine, career-creation-only opt-in, frontend picker, and replay banner are complete and integrated.
- **Phase 10**: Completed USA Dodgeball warnings and blue cards implementation under a unified `DisciplineState` and `OfficialEvent` framework, wired into the autonomous engine passive sink with comprehensive coverage in the test suite and conformance matrix.

## Architecture Summary
The V11 rules system incorporates a robust and modular architecture consisting of **15+ source modules** that do not disrupt the generic engine baseline.
- **Ruleset Profiles**: Exposes profiles like Foam, No-Sting, and Cloth via `rulesets.py` and state configuration routing.
- **Official Events**: Implements `OfficialEvent` as a standard envelope carrying version metadata and references (`RuleReference`).
- **Translation Layer**: Translates rich, granular `OfficialEvent` records into generic-shaped `MatchEvent`s using `OfficialEventTranslator` to preserve compatibility with existing statistics, replays, and save-state databases.
- **Autonomous Official Engine**: Runs discrete, tactical game steps using `run_autonomous_game()` that composes tactical decisions and rule resolutions in an active tick loop.
- **Discipline Model**: Manages verbal warnings (Section 34) and blue cards (Section 35) statefully and deterministically per game via `DisciplineState`. Includes automatic blue-card escalation on repeated offenses, catch-queue FIFO insertion, temporary player blocking, yellow-card placeholder emissions on repeated carding, and game-forfeiture evaluation on zero live players.
- **Career-Creation-Only Routing**: Keeps the default system generic to protect legacy save files from database migration risk while offering a seamless creation-only opt-in for official rules.

## File Modifications Summary
All edits outside the newly created official modules were additive-only to guarantee maximum isolation and prevent regressions:
- `src/dodgeball_sim/sequence.py`: Added custom discipline and rules payload fields for fine-grained action history.
- `src/dodgeball_sim/franchise.py`: Added rule profile kwargs to bridges connecting Club/roster data to official match simulations.
- `src/dodgeball_sim/game_loop.py`: Implemented state reads to distinguish rulesets during career gameplay ticks.
- `src/dodgeball_sim/save_service.py`: Added ruleset keyword arguments to protect existing saves from ruleset drift.
- `src/dodgeball_sim/server.py`: Integrated new request and response payload schemas to expose ruleset options in web APIs.
- `src/dodgeball_sim/web_status_service.py` & `replay_service.py`: Exposed ruleset profiles and detailed discipline events to the frontend.
- `frontend/src/components/SaveMenu.tsx`: Exposed the Ruleset profile picker in the new career dialog.
- `frontend/src/components/MatchReplay.tsx`: Displayed the official-ruleset banner (`official:*`) during match replay viewings.
- `src/dodgeball_sim/official_engine.py`: Added type imports and the optional `discipline_state` kwarg as a passive sink.
- `tests/test_official_conformance_matrix.py`: Linked Section 34 and Section 35 rules to their test home.

## Test Footprint
Final Python test count: **656 passing tests** (`python -m pytest -q`).
Final TypeScript/React E2E verification: **12 passing tests** across 3 major browsers (Chromium, Firefox, Webkit) run via Playwright (`npm run e2e`).

## Known Limitations & Deferred Work
To keep V11 lean and stable, several advanced rules were explicitly deferred to future milestones:
- **Yellow/Red Card Persistence**: Placeholders are emitted when repeated offenses happen, but actual multi-game tournament suspension persistence is deferred.
- **Designated Retriever Realism**: Realism around bounds-leaving retrievers is simplified.
- **In-Engine Realism Triggers**: Advanced physics/rules triggers (such as pinching, flight kills, interference, injuries, or player collisions) are scaffolded via the passive discipline sink but not autonomously simulated.
- **Tournament and Brackets**: Bracket expansion and administrative rules are deferred.
