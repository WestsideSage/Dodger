# V3 Experience Rebuild Design

Status: Designed 2026-04-29.

## Relation to Prior Specs

V3 follows the shipped V2 manager loop documented in:

- `docs/specs/2026-04-26-manager-mode/design.md`
- `docs/specs/2026-04-26-v2-a-scouting/design.md`
- `docs/specs/2026-04-28-v2-b-recruitment/design.md`
- `docs/specs/2026-04-28-v2-c-build-a-club/design.md`
- `docs/specs/2026-04-28-v2-d-expanded-coach-policy/design.md`
- `docs/specs/2026-04-28-v2-e-offseason-beats/design.md`
- `docs/specs/2026-04-28-v2-f-playoffs/design.md`

This milestone does not supersede those systems. It changes how they are experienced. V3 inherits the integrity contract in `docs/specs/AGENTS.md`: the game must never feel like it lied, and every match outcome must remain explainable through visible inputs, logged RNG, and uniform rules.

V3 also incorporates the closed V2 playthrough QA report in `docs/retrospectives/2026-04-28-v2-playthrough-qa.md`. That report's pre-V3 fixes are already closed, but the player feedback after V2 identified a larger issue: the game is mechanically functional but still feels like a diagnostic tool rather than a sports management game.

## Goal

V3 is an experience rebuild. It should make the existing manager loop feel playable, readable, stylish, and paced like a game.

The milestone priorities are:

1. Fix active-roster integrity so matches use only legal starters.
2. Make match day and replay feel like the central game surface.
3. Reduce repetitive clicking with multi-week simulation controls and smart stop points.
4. Apply a cohesive visual pass across the app.
5. Improve writing, names, labels, and generated flavor.

V3 should mostly improve how existing systems are experienced. It may add small support mechanics where needed, but it should not expand into a large new systems milestone such as facilities, rivalries, meta patches, or deep new tactical mechanics.

## Non-Goals

- No new facilities system.
- No new seasonal meta patch system.
- No new rivalry or full identity layer beyond copy/name improvements.
- No hidden difficulty modifiers or on-court boosts.
- No renderer-driven outcomes. The event log remains canon.
- No wholesale migration to a new UI framework in this milestone unless explicitly approved later.

## Pillar 1: Court Truth And Roster Integrity

A club may have more than six players, but a match may activate only `STARTERS_COUNT = 6`.

The current V2 behavior can let recruited depth become extra active players because lineup resolution preserves and backfills the entire roster, then match setup converts all resolved player IDs into engine participants. Recruitment expands the saved roster and default lineup, so extra recruits can appear as additional court circles and real match participants. This is a sim-integrity bug, not a cosmetic issue.

V3 must make the match roster contract explicit:

- `LineupResolver` can continue returning full ordered roster IDs for UI display and diagnostics.
- A match-facing helper must derive `active_starters = resolved_lineup[:STARTERS_COUNT]`.
- `build_match_team_snapshot()` must build engine teams from active starters only.
- AI-only simulation, user-match simulation, replay setup, match persistence, stat extraction, and reports must agree on the active participants.
- Bench players remain visible in roster and lineup screens, but they must not appear as court circles, targets, survivors, or match participants.
- Roster snapshots should preserve the data needed to audit who was active and who was bench at match time.

The roster UI should clearly separate Starters and Bench. Recruiting a strong player should create a lineup decision, not silently increase the number of active bodies.

### Acceptance Criteria

- A club with 9 rostered players enters a match with exactly 6 active players.
- Both clubs have the same active-player cap regardless of user or AI ownership.
- Recruited bench players do not appear in the replay court.
- Recruited bench players do not receive match stats unless they were active starters.
- Match survivor totals cannot exceed 6 for either side.
- Existing lineup diagnostics still surface invalid or stale player IDs.

## Pillar 2: Match Day And Replay Rebuild

The match screen should become the most game-like surface in V3. It should stop feeling like a small diagnostic panel and start feeling like the central arena where the simulation proves itself.

The replay should be derived entirely from the event log. The player should understand the current moment visually before needing to inspect raw text.

Required match-day changes:

- The court occupies most of the match screen.
- The court shows two team halves, six visible starters per side, clear ball positions, eliminated/out state, and current actor emphasis.
- Team identity is visible: club names, colors, score/survivor state, and match context.
- Replay controls are simplified into game controls: step back, step forward, play/pause, speed, jump to key event, and skip to final report.
- A compact event panel explains the current event: actor, target, outcome, probability, roll, and deciding ratings/context.
- Advanced event details remain available, but they are an inspection layer rather than the first read.

The post-match report should read like a sports recap:

- final result and survivor totals
- MVP
- turning point
- top performers
- concise "why this happened" summary
- optional raw log/detail section

### Acceptance Criteria

- A five-second glance at the match screen communicates who is playing, who is winning, who is out, where the action is, and why the current event happened.
- The replay never implies an outcome that differs from the event log.
- The replay court never renders more active players than the engine simulated.
- The report resolves player names, not raw player IDs, in primary presentation.
- Raw event details remain reachable for auditability.

## Pillar 3: Pacing And Simulation Controls

V3 should reduce repetitive menu clicking. The player needs ways to advance time while still stopping at meaningful moments.

The hub should provide clear pacing controls:

- `Play Next Match`: keep the current hands-on flow.
- `Sim Week`: resolve all remaining matches in the current week after confirmation.
- `Sim To Next User Match`: skip AI-only weeks or non-user events until the next player-club match.
- `Sim Multiple Weeks`: choose a number of weeks, then stop early for important events.
- `Sim To Milestone`: stop at playoffs, offseason, recruitment day, season end, or major inbox/news event.

Smart stop points:

- user match, unless the player explicitly allows simming user matches
- playoffs
- recruitment day
- offseason ceremony
- champion, record, Hall of Fame, or signature event
- scouting reveal or high-value prospect update
- retirement or development event when applicable

After any bulk simulation, the game should show a concise digest rather than forcing every individual match report. The digest should summarize:

- record changes
- standings movement
- notable player performances
- scouting and recruitment updates
- next recommended action

### Acceptance Criteria

- A player can advance multiple weeks without visiting every intermediate screen.
- Bulk simulation stops before major player-facing decisions.
- Bulk simulation produces persisted match results identical to resolving those matches one at a time.
- The digest contains enough context to continue without reading every raw match report.
- The player can still choose hands-on match play when desired.

## Pillar 4: Visual System And Screen Hierarchy

V3 should turn the existing UI/UX guide into a stricter implementation pass. The target is a retro athletic department dashboard: warm, readable, stylish, but still data-rich.

Required visual changes:

- Replace default-looking font usage with a consistent hierarchy: title, section header, body, table, numeric, badge.
- Tighten spacing around a consistent grid.
- Give each screen one clear primary area, one secondary area, and optional detail drawers.
- Standardize capitalization and labels across screen titles, buttons, table headings, awards, roles, and event descriptions.
- Make action buttons visually distinct from passive navigation.
- Use tables where useful, but pair them with summaries, badges, cards, and digest copy.
- Make empty states and status text feel intentional.

Key affected screens:

- splash and career start
- hub
- roster and lineup
- match preview
- replay arena
- match report
- scouting center
- recruitment day
- offseason ceremony
- league wire and standings

The app should still feel like a management sim, not an arcade game. The target first impression is "stylish sports sim interface," not "debugging utility."

### Acceptance Criteria

- Common screens use consistent spacing, capitalization, and typography tokens.
- Primary actions are visually distinct from navigation and passive labels.
- Screens do not present raw tables as the only first-read surface when a summary or digest would help.
- The replay arena uses most of the available screen for the court and event presentation.
- GUI screenshots are captured for major screens before and after the pass.

## Pillar 5: Writing, Names, And Flavor

V3 should make the text feel authored rather than generated from bare data fields.

Required writing changes:

- Fix inconsistent capitalization across buttons, headings, table labels, awards, roles, and event descriptions.
- Audit repeated or flat descriptions, especially recruitment/scouting blurbs and ceremony copy.
- Reduce duplicate recruit names by expanding the name pool and adding deterministic uniqueness rules within a class.
- Give player profiles short role or archetype phrases that do not imply hidden mechanics.
- Rewrite match, report, and recruitment text around concise sports recap language tied to visible facts.
- Keep flavor honest: no text should imply an unmodeled injury, morale effect, hidden modifier, or story event.
- Add checks for empty strings, unresolved IDs, repeated names in a generated class, unfilled template blanks, and obvious title-casing issues.

Tone target: fictional dodgeball league office. The language can have personality, but every claim must map to actual data.

### Acceptance Criteria

- Generated recruit classes do not contain duplicate display names unless the deterministic fallback has been exhausted and disambiguated.
- Primary UI text uses consistent title casing.
- Match reports, awards, and wire items use player names instead of raw IDs.
- Template output contains no unresolved placeholders.
- New copy remains data-grounded and does not imply mechanics that do not exist.

## Architecture Notes

The active-roster fix should happen at the dynasty-to-engine boundary. The engine should continue to simulate the `Team` it receives. This preserves the core separation:

- dynasty layer owns club roster, bench, lineups, and match setup
- engine owns only active match participants and event-log simulation
- renderer consumes event-log truth and active match setup
- reports derive from persisted match data and event logs

The pacing controls should reuse existing season, schedule, and matchday functions where possible. Bulk simulation should be a loop over the same deterministic match resolution path, not a second shortcut simulator.

The visual pass should centralize reusable style constants in existing UI style/component modules where possible, rather than scattering one-off widget styling through `manager_gui.py`.

## Testing And Verification

V3 requires focused tests for integrity and flow:

- lineup resolution and active-starter enforcement
- recruited bench players excluded from engine teams
- survivor totals capped at `STARTERS_COUNT`
- AI and user clubs use the same active-player cap
- bulk simulation result parity with one-at-a-time simulation
- smart stop behavior for user match, playoffs, recruitment, and offseason
- duplicate recruit-name prevention
- unresolved ID/template/capitalization checks for primary UI copy
- screenshot review for major screens

Full regression verification should include:

- `python -m pytest -q`
- focused lineup, manager GUI, recruitment, playoffs, and persistence tests
- GUI screenshot capture for the rebuilt major screens when possible

## Milestone Deliverables

1. Active-starter enforcement and roster UI clarity.
2. Rebuilt match/replay surface.
3. Post-match recap/report presentation pass.
4. Hub simulation controls and digest view.
5. Visual-system pass across key manager screens.
6. Copy/name/flavor audit with deterministic name uniqueness.
7. Updated tests and screenshot evidence.

