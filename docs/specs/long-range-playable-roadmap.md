# Long-Range Playable Roadmap

Status: Drafted 2026-05-02.

## Purpose

This roadmap controls scope for the post-V4 web game. It is not a dream board. It exists to keep Dodgeball Manager moving toward a robust simulation game without documentation drift, vague promises, or disconnected backend-only milestones.

The long-term target is a living dodgeball program sim in the spirit of the best dynasty and management games: memorable players, meaningful staff and program choices, honest match outcomes, long-term league history, and a browser UI that can be played by both a human and an automated agent.

## Product Pillars

### 1. Hybrid Athletic Director Fantasy

The player manages a program, not just a lineup. The core responsibility is deciding where limited program attention goes each week:

- winning now
- developing future stars
- protecting health
- scouting opponents or prospects
- refining tactics
- managing staff-driven program strengths and weaknesses

### 2. Week-By-Week Command Loop

The default time unit is the week. The game should not become a day-by-day chores simulator or a season-sim-only spreadsheet.

The durable loop is:

`set intent -> assign departments -> review advice -> simulate -> diagnose -> adjust`

### 3. Simulation Honesty

The game must never lie about why something happened.

- No hidden AI boosts.
- No user aura.
- No comeback code.
- No animation-driven outcomes.
- No fake tactics or decorative department orders.

Thin mechanics are allowed in early milestones. Fake mechanics are not.

### 4. Player Memory

The game should create players the user remembers years later: overlooked prospects, breakout stars, role-player heroes, record holders, captains, rivals, and legends who occasionally re-enter the world as coaches, scouts, alumni, media voices, or opponents.

Player identity should be built in this order:

1. Archetype: what the player naturally does.
2. Ratings: how good the player is at it.
3. Traits: when the player behaves differently from the baseline.

### 5. Program Consequences

Underlooked program choices should translate to on-court success or failure:

- Poor conditioning should show up as fatigue, injury risk, and late-match decline.
- Strong teaching should improve tactical IQ and development.
- Overemphasizing power while ignoring cardio should create visible tradeoffs.
- Burying elite prospects should slow development or create role concerns.
- Playing liabilities should be punished by opponent targeting and match reports.

### 6. Living League

The league should feel alive outside the user program through:

- standings and rivalries
- stars, records, awards, and title histories
- program ecosystems and staff identities
- news/events that explain real simulation movement

The "dodgeball Nick Saban" should be a real coach entity with elite staff attributes, repeated development success, titles, staff-tree influence, and a visible league footprint. Not just a headline.

### 7. Human And AI Playability

Every milestone must be playable in the browser by a human and by an automated browser agent.

Required milestone gates:

1. Functional gate.
2. Playable gate.
3. AI playthrough gate.
4. Simulation honesty gate.
5. Documentation gate.

If the AI cannot understand the loop through visible labels, stable selectors, and readable reports, the UI is probably not clear enough for humans either.

## Roadmap Rules

1. Slice by playable loop, not isolated system.
2. Each milestone needs one playable thesis.
3. Each milestone needs explicit non-goals.
4. Each milestone must preserve data needed by later loops where practical.
5. Each milestone must include browser playthrough verification.
6. Each milestone must document what remains thin.
7. No milestone should add a main-loop decision unless the game can diagnose its consequence.
8. No milestone should expose a tactic, order, or promise that has no mechanical or report-backed truth.

## Milestone Sequence

The version numbers below are planning anchors. They may shift if implementation reality changes, but the playable-loop ordering should remain the default unless a later audit proves a better order.

## V5: Weekly Command Center

Playable thesis: The player can set a weekly program plan, advance the week, read causal consequences, and adjust the next plan.

Primary loop:

`review week -> set intent -> assign departments -> accept/edit recommendations -> simulate -> dashboard diagnosis`

Core scope:

- Weekly intent.
- Department orders.
- Minimal staff entities.
- Staff recommendations and warnings.
- Recommended lineup/tactics summary.
- Tactics honesty fixes for exposed tactics.
- Post-week dashboard.
- Full season command history.
- Automated browser playthrough.

Non-goals:

- Full staff market.
- Deep player personality.
- Full recruiting promise system.
- Full watchable match rebuild.
- Broadcast presentation.

Unlocks:

- Stored command history for reputation/promises.
- Staff foundations for later staff market.
- Weekly UI spine for every later system.

## V6: Player Identity And Development Loop

Playable thesis: Players become tactically distinct assets whose roles, ratings, traits, reps, and development priorities change roster decisions over a season.

Primary loop:

`evaluate roster -> set development priority -> allocate reps -> simulate weeks -> inspect player movement -> adjust depth chart`

Core scope:

- Archetype-first player model.
- Ratings as performance quality within archetype.
- Limited traits/abilities that create behavior differences.
- Program-level development focus.
- Youth reps and buried-talent consequences.
- Liability warnings for weak starters.
- Tactical IQ as execution quality and role flexibility.
- Development reports tied to command history.

Non-goals:

- Full personality/morale sim.
- Deep individual skill trees.
- Transfer portal equivalent unless specifically scoped.
- Former-player legacy system.

Unlocks:

- Memorable player arcs.
- Better lineup recommendations.
- Recruiting fit based on real development history.
- Richer match viewer roles.

Honesty checks:

- Player archetypes must affect match behavior or recommendations.
- Development must depend on visible factors such as reps, staff, intent, and training focus.
- Reports must distinguish deliberate youth development from negligent weak lineups.

## V7: Watchable Match Proof Loop

Playable thesis: The match viewer makes autonomous play legible enough that the user can see tactics, roles, fatigue, and player decisions express themselves.

Primary loop:

`set plan -> watch/skim match -> inspect key plays -> read report -> adjust tactics/lineup`

Core scope:

- Tactical clarity first: possession, targets, pressure, fatigue, eliminations.
- Role expression in match behavior.
- Event context that explains why a player acted or failed.
- Key-play navigation.
- Fast result remains available.
- Report evidence for tactics, matchup fit, fatigue, and liabilities.

Non-goals:

- Mid-match coaching.
- Broadcast commentary.
- Camera-heavy presentation polish.
- Physics-heavy arcade behavior.

Unlocks:

- Better trust in weekly decisions.
- Foundation for later broadcast layer.
- Stronger player memory through visible signature performances.

Honesty checks:

- Viewer never contradicts event log.
- Visuals show simulation truth, not decorative drama.
- Tactics exposed in V5/V6 are visible in match evidence.

## V8: Recruiting, Promises, And Program Credibility Loop

Playable thesis: Recruiting is shaped by program identity, staff, geography, promises, playing-time reality, and development history.

Primary loop:

`scout lightly during season -> make limited promises -> recruit in phase windows -> honor or break commitments -> see credibility effects`

Core scope:

- Season-phase recruiting.
- Program-reputation-driven interest.
- Geography as recruiting relevance: pipelines, local reputation, distance, regional identity.
- Limited key promises.
- Credibility checks against actual history.
- Prospect fit by archetype, staff, development, and playing time.
- Recruiting dashboard tied to command history and player-development results.

Non-goals:

- Weekly recruiting chores every week.
- Dozens of contract-like promises per recruit.
- Full national media or NIL-style economy unless separately designed.

Unlocks:

- "Overlooked prospect becomes legend" stories.
- Program identity as an earned recruiting engine.
- Promise/trust substrate for morale and staff later.

Honesty checks:

- Recruits should respond to what the program actually did, not just selected branding.
- Broken promises must be rare enough to matter and tracked clearly.
- Geography should create texture without becoming a travel simulator.

## V9: Living League Memory Loop

Playable thesis: The league remembers players, coaches, teams, rivalries, records, awards, and historical arcs outside the user's immediate roster.

Primary loop:

`play season -> track league stars/storylines -> hit records/playoffs/awards -> preserve history -> use history in future seasons`

Core scope:

- Player pages and career histories.
- Program histories.
- Awards and records as first-class surfaces.
- Rivalry and title history.
- Weighted legacy events for rare former-player returns.
- News layer that explains real simulation movement.
- League leaderboards and milestone alerts.

Non-goals:

- Full media personality sim.
- Scripted drama director that bends outcomes.
- Universal post-career roles for every player.

Unlocks:

- Long-memory dynasty saves.
- Alumni/staff/event hooks for later systems.
- Stronger league identity and emotional stakes.

Honesty checks:

- Story events should be seeded and weighted by real career history.
- Former-player returns should be rare, meaningful, and grounded in player achievements or traits.
- News should explain real outcomes, not invent unsupported drama.

## V10: Staff Market And Program Arms Race Loop

Playable thesis: Staff quality, philosophy, retention, and movement shape program rise/fall and create league-wide strategic cycles.

Primary loop:

`evaluate staff -> set program priorities -> respond to offers/poaching -> replace or retain staff -> see program effects`

Core scope:

- Staff hiring and replacement.
- Staff ratings and philosophies.
- Staff improvement/decline.
- Rare poaching events.
- Early coaching tree behavior.
- AI programs use simplified same-rule staff decisions.
- Staff effects on development, conditioning, scouting, tactics, recovery, and culture.

Non-goals:

- Annual HR churn.
- Overly detailed salary negotiation.
- Staff micromanagement that overwhelms weekly play.

Unlocks:

- League ecosystem arms race.
- Rival programs that rise because of real staff quality.
- Former-player coach returns from V9.
- Long-term dynasty maintenance pressure.

Honesty checks:

- AI programs must mostly use the same world objects as the user.
- Staff-driven success should be visible through development, health, tactics, recruiting, and outcomes.
- High reputation should increase pressure and poaching risk, not just provide bonuses.

## V11: AI Program Managers And Rival Adaptation Loop

Playable thesis: Opposing programs make believable simplified decisions under mostly the same rules, creating rebuilds, dynasties, counters, and collapses.

Primary loop:

`observe league movement -> identify rival strategies -> adapt program plan -> see AI respond over seasons`

Core scope:

- Simplified AI weekly intent.
- AI department orders.
- AI roster/development priorities.
- AI recruiting/staff strategy.
- Rival adaptation to dominant user or league styles.
- Program archetypes and strategic identities.

Non-goals:

- Full UI-equivalent decision simulation for every AI club.
- Hidden AI rating boosts.
- Scripted league parity.

Unlocks:

- Sustainable dynasty challenge.
- Real arms race against rivals.
- Better league news and historical arcs.

Honesty checks:

- AI teams should rise/fall from visible staff, roster, recruiting, development, health, and tactics.
- Difficulty should improve AI decision quality or reduce player information, not secretly alter match math.

## V12: Broadcast And Presentation Layer

Playable thesis: Once the simulation is already legible, presentation can make matches and league moments feel more dramatic without changing outcomes.

Primary loop:

`watch key match/highlights -> experience context/commentary -> inspect proof -> continue season`

Core scope:

- Broadcast-style match framing.
- Highlight packages.
- Rivalry and playoff presentation.
- Commentary flavor derived from event logs and history.
- More player personality in visual presentation.
- Better season recap and Hall of Fame presentation.

Non-goals:

- Commentary that invents unsupported causes.
- Visual effects that obscure tactical clarity.
- Mid-match user control unless separately designed.

Unlocks:

- Stronger first impression and emotional payoff.
- More satisfying playoffs, records, and rivalry moments.

Honesty checks:

- Broadcast copy must be derived from event log, player history, or league records.
- The raw proof layer remains available.
- Presentation never changes outcomes.

## Deferred Ideas Parking Lot

These ideas are valid but should not jump the queue unless tied to a playable loop:

- Full facilities economy.
- Deep budget accounting.
- Full personality/relationship sim.
- Transfer portal equivalent.
- Deep staff contract negotiation.
- Weather/venue quirks.
- Travel fatigue.
- Media controversies.
- Mid-match coaching.
- Custom league generator.
- Full sandbox rules editor.

## Drift Control Checklist

Before adding any feature to a milestone, answer:

1. What playable loop does this improve?
2. What decision does the player make?
3. What visible consequence proves the decision mattered?
4. What data must be persisted for later systems?
5. Can a browser automation agent play or inspect it?
6. What is explicitly out of scope?
7. Does it preserve the integrity contract?

If the answers are weak, defer the feature.
