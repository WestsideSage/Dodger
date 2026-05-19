# V5 Weekly Command Center Design

Status: Designed 2026-05-02.

## Relation to Prior Specs

V5 builds directly on the shipped V4 web architecture foundation:

- `docs/specs/MILESTONES.md`
- `docs/specs/AGENTS.md`
- `docs/specs/v4/2026-04-29-v4-sprint-plan.md`
- `docs/retrospectives/v4/2026-04-29-web-architecture-handoff.md`
- `docs/retrospectives/2026-04-30-v4-balance-report.md`
- `docs/retrospectives/2026-04-30-v4-ui-polish.md`
- `docs/retrospectives/2026-04-30-web-adversarial-qa-report.md`

V5 does not supersede the V1-V4 season, scouting, recruitment, playoffs, web, or replay foundations. It changes the week-to-week player flow from "inspect tabs and simulate" into a playable command cycle.

V5 inherits the integrity contract in `docs/specs/AGENTS.md`: the game must not lie to the player. Outcome-affecting behavior must flow through visible inputs, persisted state, seeded randomness, and uniform simulation rules. UI reports may summarize, but they must not invent causes that the simulation did not track.

## Product Thesis

The player is a hybrid athletic director managing a living dodgeball program week by week.

V5 should prove this loop:

1. Review the current week.
2. Set the program intent.
3. Assign high-level department orders.
4. Review staff recommendations and warnings.
5. Accept or adjust lineup and tactics.
6. Simulate the match/week.
7. Read a causal dashboard.
8. Adjust the next week based on what happened.

Every milestone from V5 onward must remain playable end to end in the browser by a human and by an automated browser agent. A feature that cannot be played, diagnosed, and verified in the browser does not count as shipped product scope.

## Non-Goals

- No full staff hiring, firing, poaching, contracts, or coaching tree system.
- No full personality, morale, promise, or transfer system.
- No deep facility economy or budget-management game.
- No full player-archetype overhaul beyond what is needed to support recommendations.
- No full watchable-match rebuild beyond tactics honesty and report evidence.
- No broadcast presentation layer.
- No hidden difficulty boosts, comeback code, or user/AI aura.
- No decorative department orders. Thin mechanics are acceptable; fake mechanics are not.

## Standing Milestone Gate

V5 and later milestones only ship when all five gates pass:

1. Functional gate: backend, frontend, persistence, and tests work for the intended loop.
2. Playable gate: a human can complete the core loop without external guidance.
3. AI playthrough gate: an automated browser agent can complete the core loop and inspect outcomes through stable labels/selectors.
4. Simulation honesty gate: reports show how choices affected outcomes through visible systems, or explicitly avoid claiming effects that are not modeled.
5. Documentation gate: the milestone spec, handoff retrospective, and learnings explain what changed, what remains thin, and what later milestones inherit.

## Scope Summary

V5 ships a full command-center vertical slice with intentionally thin mechanics where needed.

Required first-pass systems:

- Weekly command center screen.
- Weekly intent.
- Department orders.
- Minimal department heads.
- Staff recommendations and warnings.
- Recommended lineup/tactics summary.
- Tactics honesty fixes for exposed tactics.
- Post-week dashboard and diagnosis.
- Full season command history.
- Browser/AI playthrough contract.

The first version does not need to deeply model every department. It must establish the complete flow and make each exposed decision have a real, inspectable consequence.

## Player Identity And Loop

The player is not primarily a match caller or passive spectator. The player is responsible for program attention.

The main resource is weekly focus:

- Focus on recovery, and development may slow.
- Focus on development, and short-term match strength may suffer.
- Focus on opponent scouting, and prospect discovery may slow.
- Focus on tactical installation, and short-term execution may be unstable.
- Focus on youth reps, and veterans may give the best win-now lineup less often.

The player should usually make one to three meaningful decisions per week. The command center should provide defaults and staff recommendations so a player can advance quickly, but ignoring warnings must remain accountable.

## Weekly Intent

Each week has one explicit intent. Intent tells the game how to interpret lineup, tactics, training, and department choices.

Initial intents:

- `Win Now`: maximize current match odds.
- `Develop Youth`: give meaningful reps to prospects or bench players with development upside.
- `Preserve Health`: reduce fatigue and injury risk, especially during byes, weak opponents, or playoff preparation.
- `Evaluate Lineup`: test role fit or depth options.
- `Prepare For Playoffs`: balance win odds, health, scouting, and tactical polish.

Intent must affect:

- Staff recommendations.
- Lineup warnings.
- Department-order diagnosis.
- Post-week report language.

Example interpretation:

- Starting a weak young player under `Win Now` should trigger an exploitable-lineup warning.
- Starting that same player under `Develop Youth` should be framed as a deliberate short-term cost for reps and growth.

## Department Orders

Department orders are high-level assignments, not spreadsheet micro-controls. Each order must have a real effect or a real report hook.

Initial departments:

- Tactics: opponent prep, base-system polish, aggressive package, conservative package.
- Training: fundamentals, power, catching, dodging, youth reps.
- Conditioning: cardio base, burst speed, balanced maintenance, recovery.
- Medical: injury prevention, rehab priority, cautious return, availability push.
- Scouting: next opponent, prospect class, hidden traits, rival tracking.
- Culture: discipline, morale, leadership, pressure management.

V5 should implement a smaller mechanical subset if needed, but the UI must not overclaim. For example, if `Medical: injury prevention` only lowers fatigue-risk flags in V5, the dashboard should say that. It should not claim a full medical model exists.

### Contextual Tradeoffs

Department orders are not universally good or bad. Their value depends on:

- Staff quality.
- Current roster health.
- Recent usage.
- Bye weeks and schedule density.
- Opponent strength and style.
- Weekly intent.

Recovery during a bye should usually be smart, not a generic penalty. Overusing recovery during a development window should have opportunity cost. Power training during a brutal match stretch should create fatigue or injury-risk warnings. A strong staff member can soften tradeoffs; a poor staff member can make advice less reliable.

## Minimal Staff Entities

V5 introduces persistent department heads, but not a staff market.

Each department head should have:

- Name.
- Role/department.
- 1-2 ratings.
- Short staff voice used in recommendations.

Suggested first ratings:

- Tactician: planning, teaching.
- Strength and Conditioning: conditioning, injury_prevention.
- Development Coach: teaching, potential_eval.
- Scout: evaluation, coverage.
- Medical Lead: recovery, risk_assessment.
- Culture Lead or Head Coach: discipline, pressure_management.

Staff ratings may affect:

- Recommendation quality.
- Size or reliability of department-order effects.
- Diagnosis clarity.
- Warning accuracy.

They should not yet support hiring, firing, poaching, salary, staff development, or contracts. Those belong to a later staff-market loop.

## Lineup And Tactics Accountability

V5 should use a recommended-lineup model:

- Staff proposes a lineup based on intent, health, form, archetype/ratings, opponent, and development goals.
- The user can accept, edit, or lock players.
- The command center warns about obvious risks.
- The game does not silently optimize the lineup after the user ignores a warning.

Required warnings:

- Elite or high-upside player buried without a development reason.
- Weak starter likely to be targeted.
- Fatigued starter at elevated risk.
- Tactical plan conflicts with roster strengths.

Tactics should remain a compact package rather than a detailed coaching sheet. V5 should expose only tactics that are honest enough to affect match behavior or reports.

### Tactics Honesty Requirement

The V4 balance audit found:

- `sync_throws` is stored and displayed but currently inert.
- `rush_frequency` behaves like an on/off switch instead of a true frequency.
- `target_stars`, `target_ball_holder`, and `catch_bias` have observable engine effects.

V5 must fix exposed tactics enough for honesty. If a tactic appears in the weekly plan, one of these must be true:

- It has a measurable engine effect and post-match evidence.
- It is hidden/de-emphasized until implemented.
- It is explicitly reframed as a report-only or scouting-only concept with no implied match effect.

Required V5 tactics checks:

- `sync_throws=0.0` and `sync_throws=1.0` should produce different event distributions over controlled mirror matches if the control remains visible.
- `rush_frequency` should scale active rush context instead of only checking whether the value is positive if the control remains visible.
- Match reports should show evidence such as target distribution, rush activations, catch attempts, fatigue cost, or tactical clash notes.

## Post-Week Dashboard

The post-week dashboard is the must-read feedback surface. It comes before deeper match and program reports.

Required lanes:

- Result: score, record, standings movement.
- Why it happened: tactical fit, matchup pressure, fatigue, execution, lineup fit.
- Roster health: injuries, fatigue, recovery, availability.
- Player movement: development, role changes, youth reps, standout or liability notes.
- Next decisions: upcoming opponent, staff warnings, scouting/recruiting priorities.

The dashboard should use clear bands plus narrative diagnosis, not raw formulas.

Examples:

- "Major recovery benefit; minor development slowdown."
- "Weak-side catcher was targeted repeatedly."
- "Youth reps cost short-term execution but improved development signal."
- "Third straight high-intensity week raised fatigue risk."

Exact formulas should remain inspection/debug detail, not the main read.

## Full Season Command History

V5 must persist full season command history:

- Week.
- Opponent and match context.
- Intent.
- Department orders.
- Staff recommendations and warnings.
- Accepted/overridden lineup and tactics summary.
- Simulated outcome.
- Dashboard diagnosis.

V5 does not need full career reputation or promises, but it should preserve the facts those systems will later need. If the player spends six weeks developing youth, ignoring recovery, overusing power training, or burying a high-upside player, later systems should be able to read that history.

## Browser And AI Playability Contract

The command center must be playable by a human and by an automated browser agent.

UI requirements:

- Stable screen labels.
- Stable primary action labels.
- Stable selectors or semantic landmarks for automated playthrough.
- Visible current objective.
- Clear recommended path.
- No hidden required action.
- Post-action state that confirms what changed.
- Reports that can be inspected as text, not only visual styling.

Required automated flow:

1. Start or load a seeded career.
2. Open command center.
3. Accept recommended weekly plan.
4. Simulate the week.
5. Inspect dashboard lanes.
6. Advance through multiple weeks.
7. Verify the season remains playable and reports are populated.

The AI playthrough is not just a QA convenience. If the automated agent cannot understand the flow, the UI probably is not clear enough.

## Implementation Slices

### Slice 1: Data And Persistence Foundation

Purpose: Persist weekly plans, department heads, and season command history.

Likely files:

- `src/dodgeball_sim/persistence.py`
- `src/dodgeball_sim/career_state.py`
- New domain module for command plans/history if appropriate.
- `tests/test_persistence.py`

Done when:

- A weekly plan can be saved and loaded.
- A post-week command record persists.
- Existing career saves migrate safely.

### Slice 2: Command Plan Domain

Purpose: Pure helpers for intent, department orders, staff recommendations, and diagnosis.

Likely files:

- New `src/dodgeball_sim/command_center.py` or similar.
- `src/dodgeball_sim/game_loop.py`
- Focused tests under `tests/`.

Done when:

- Recommendations respond to intent, roster health, schedule, and staff.
- Department orders produce bounded, explainable effects.
- Diagnosis is derived from stored plan/outcome facts.

### Slice 3: Tactics Honesty Pass

Purpose: Ensure exposed tactics have real effects and evidence.

Likely files:

- `src/dodgeball_sim/engine.py`
- `src/dodgeball_sim/config.py`
- `tests/test_invariants.py`
- `tests/test_phase3_engine.py` or a new tactics test file.
- Golden logs if match outcomes intentionally change.

Done when:

- Exposed tactics shift measurable behavior.
- Event context/report data proves the shift.
- Golden logs are updated with a clear change note if required.

### Slice 4: API Surface

Purpose: Expose command-center state and actions to the React client.

Likely files:

- `src/dodgeball_sim/server.py`
- `tests/test_server.py`
- `frontend/src/types.ts`

Candidate endpoints:

- `GET /api/command-center`
- `POST /api/command-center/plan`
- `POST /api/command-center/simulate`
- `GET /api/command-center/history`

Done when:

- The frontend can render current plan, recommendations, warnings, and dashboard without client-side inference.
- Response shapes are typed or at least stable enough for frontend and automation.

### Slice 5: React Command Center

Purpose: Make the weekly loop the primary browser experience.

Likely files:

- `frontend/src/App.tsx`
- `frontend/src/components/Hub.tsx`
- New command-center components under `frontend/src/components/`.
- `frontend/src/components/ui.tsx`

Done when:

- The command center is the first operational screen after career setup/status.
- The user can accept recommendations and simulate.
- The dashboard explains the result.
- Existing roster, tactics, schedule, news, and replay surfaces remain reachable as supporting views.

### Slice 6: Playthrough And Verification

Purpose: Prove the milestone is playable by human and automated browser flows.

Likely files:

- Existing frontend build/lint scripts.
- Existing or new playthrough script under `tests/`, `scripts/`, or `output/` conventions.
- Documentation in the V5 retrospective when shipped.

Done when:

- Python tests pass for changed backend/domain behavior.
- Frontend builds.
- Automated browser playthrough advances multiple weeks and inspects dashboard text.
- Manual browser pass confirms the main loop is understandable.

## Acceptance Criteria

- The browser app presents a weekly command center as the main operational loop.
- A player can choose intent, assign department orders, review staff recommendations, accept/edit lineup/tactics, simulate, and read a dashboard.
- The same flow can be completed by accepting recommendations only.
- Department orders have real, bounded effects or honest report hooks.
- Exposed tactics have observable effects or are removed from primary planning.
- Staff department heads are persistent enough to ground advice.
- Full season command history is persisted.
- Post-week dashboard explains causes through visible choices and tracked simulation facts.
- Automated browser playthrough can complete multiple weeks without hidden knowledge.
- V5 handoff and learnings docs are written when shipped.

## Verification Plan

Minimum expected verification before shipping:

- `python -m pytest tests/test_server.py -q`
- Focused domain/persistence tests for command-center history.
- Focused tactics honesty tests if engine behavior changes.
- `python -m pytest -q` for broad backend changes.
- From `frontend/`: `npm run build`
- From `frontend/`: `npm run lint` if lint remains configured and actionable.
- Browser or Playwright-style playthrough that advances multiple weeks through the command center and captures/inspects dashboard output.

Use `-p no:cacheprovider` with pytest if the Windows environment hits pytest cache write warnings.

## Future Milestones Unlocked

V5 intentionally creates the spine for later playable loops:

- Player identity and development can plug into intent, youth reps, and player movement.
- Staff market and coaching trees can replace minimal staff heads with full career entities.
- Recruiting/promises can consume command history and credibility.
- Living league memory can consume command records, player arcs, staff history, and program identity.
- Watchable match upgrades can use the tactics proof and dashboard evidence as their source of truth.
