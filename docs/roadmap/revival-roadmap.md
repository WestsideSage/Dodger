# Dodgeball Manager — Revival Roadmap (v2.1)

> Historical archive: this roadmap predates the current V1-V10 milestone state and contains stale details such as old test counts, future modules that now exist, earlier CoachPolicy assumptions, and obsolete process guidance. Use root `AGENTS.md`, `docs/README.md`, `docs/specs/MILESTONES.md`, and the active plan named there as current authority. Keep this file for product history and long-range inspiration, not implementation instructions.

> v2 established the dynasty spine, Club/Team boundary, stat schema, seed namespaces, event taxonomy, migrations, UI gates, and typed meta patch schema. v2.1 is a cleanup pass: six infrastructure items corrected, Phase 5 split into two milestones, and all cross-phase references normalized.

## Context

Dodgeball Manager is an integrity-first sports management sim built in Python. The core match engine (Phase 1) is ~90% complete: deterministic seeded simulation, event sourcing, sigmoid probability model, coach policy system, SQLite persistence, CLI + Tkinter GUI, and a full invariant/Monte Carlo/regression test harness. All 22 tests pass.

The game is being revived as a passion project (no shipping target) to build the full "dynasty manager" experience the project always intended — where sim integrity, fictional player attachment, and long-term historical memory combine into something genuinely addictive.

Each phase ends with something the player can actually sit down and navigate. Backend-only "playable" is not playable.

**Prime directive (unchanged from docs/specs/AGENTS.md):** The game must never feel like it lied. Every outcome explainable via visible inputs + logged RNG + uniform rules. Difficulty adjusts AI decision quality, never on-court stat boosts.

---

## Current Foundation (Do Not Break)

**Core modules (all working):**
- `src/dodgeball_sim/engine.py` — `MatchEngine.run()`, `compute_throw_probabilities()`
- `src/dodgeball_sim/models.py` — `Player`, `PlayerRatings`, `PlayerTraits` (partially unused), `CoachPolicy`, `Team`, `MatchSetup`
- `src/dodgeball_sim/events.py` — `MatchEvent` (immutable, append-only)
- `src/dodgeball_sim/config.py` — `BalanceConfig`, versioned registry
- `src/dodgeball_sim/rng.py` — `DeterministicRNG`
- `src/dodgeball_sim/persistence.py` — SQLite, `connect()`, `record_match()`, `fetch_match()`
- `src/dodgeball_sim/analysis.py` — `analyze_match()`, momentum + hero detection
- `src/dodgeball_sim/narration.py` — `narrate_event()`
- `src/dodgeball_sim/randomizer.py` — Random team/roster generation
- `src/dodgeball_sim/cli.py` — CLI entry point
- `src/dodgeball_sim/gui.py` — Tkinter GUI

**Test harness (must remain green):** `tests/` — 22 tests across invariants, Monte Carlo, regression, narration, persistence, randomizer, setup loader.

**Definition of done for any change:** invariants still pass, golden logs updated if outcomes change, all 22 tests green.

---

## Pre-Phase Infrastructure: The Dynasty Spine

Before any new feature module is written, these six contracts must be established. Every future system depends on them.

### 1. Club vs Team Boundary

The existing engine has `Team`. The dynasty layer will add `Club`. These must never blur.

```
Club    = persistent franchise entity (name, colors, region, history, roster)
Roster  = list of Players currently contracted to a Club
Team    = match-specific squad snapshot passed into MatchEngine (immutable)
```

The conversion layer is the only place that touches both:

```python
build_match_team_snapshot(
    club: Club,
    roster: list[Player],
    lineup: list[player_id],
    coach_policy: CoachPolicy,
    season_context: SeasonContext,
) -> Team
```

The engine stays dumb, pure, and ignorant of Club, Season, and everything outside the match. It receives a `Team` and returns events. The dynasty layer does everything else.

### 2. Canonical Stat Schema — `stats.py`

All awards, records, news, development, hall of fame, and career pages derive from one source. This module must exist before `awards.py`, `records.py`, or `career.py`.

```python
PlayerMatchStats:
    throws_attempted: int
    throws_on_target: int               # thrower accuracy, not target dodge
    eliminations_by_throw: int
    catches_attempted: int
    catches_made: int
    times_targeted: int
    dodges_successful: int              # active dodge vs a throw that was on-target
    times_hit: int                      # on-target throws not caught or dodged
    times_eliminated: int               # times removed from play
    revivals_caused: int                # catch revivals triggered (RuleSet-gated)
    clutch_events: int                  # populated by analysis layer, not engine
    elimination_plus_minus: int         # team eliminations minus opponent eliminations
                                        # while this player was alive (before their own out)
```

**Key distinctions:**
- `throws_on_target` ≠ elimination. A throw can be on-target and caught.
- `dodges_successful` only counts active dodges vs on-target throws. A throw that missed is a thrower miss, not a defender dodge.
- `times_hit` and `times_eliminated` are equal in the default ruleset — every hit eliminates. They diverge only when `catch_revival_enabled = True` in the active RuleSet, which allows a teammate's catch to revive a hit player. Do not imply this divergence is possible without an explicit ruleset flag.
- `elimination_plus_minus`: measures whether the team did better or worse while this player was on court. Positive = team out-eliminated the opponent during that player's time alive.
- "Newcomer" status is a flag set at roster generation time, not derived from age alone.

**Award formulas are versioned config, not hardcoded:**
```python
mvp_score =
    3.0 * eliminations_by_throw
  + 4.0 * catches_made
  + 1.5 * dodges_successful
  + 2.0 * revivals_caused
  - 2.0 * times_eliminated
  + clutch_bonus
```

### 3. Seed Derivation Policy

Adding any new feature must not change existing match outcomes. This is a new invariant.

All randomness uses namespaced seeds derived from a root:

```python
derive_seed(root_seed: int, namespace: str, *ids: str) -> int
```

Seed namespace map:
```
root_seed
├── schedule_seed      derive_seed(root, "schedule", league_id, season_id)
├── match_seed         derive_seed(root, "match", match_id)
├── development_seed   derive_seed(root, "development", season_id, player_id)
├── scouting_seed      derive_seed(root, "scouting", season_id, player_id, club_id)
├── nickname_seed      derive_seed(root, "nickname", player_id)
├── draft_seed         derive_seed(root, "draft", season_id)
├── cup_seed           derive_seed(root, "cup", season_id)
└── news_seed          derive_seed(root, "news", season_id, week)
```

Rule: each namespace gets an independent RNG stream. Adding any new namespace must not shift any `match_seed` consumption. This is verified by a new invariant test: introduce a new seed namespace, confirm golden log match outcomes are unchanged.

### 4. Event Type Taxonomy

`MatchEvent` is the engine's on-court event log. It is the replay source. It must not be overloaded with off-court history.

```
MatchEvent          on-court sim events (throw, hit, dodge, catch, elimination)
SeasonEvent         standings finalized, champion crowned, awards given
CareerEvent         development applied, retirement, hall of fame induction
LeagueHistoryEvent  record broken, rivalry score updated, news generated
TransactionEvent    player signed, released, drafted, facility upgraded
```

All non-match event types share the `DomainEvents` table (introduced in Phase 2, since SeasonEvents and TransactionEvents are needed immediately). The constraint is: replaying a match requires only `MatchEvents` + `MatchRecord` + `MatchRosterSnapshots`. No other table should be required for replay.

### 5. DB Migration Strategy

Before adding any new tables, implement:

```python
SchemaVersion          table tracking current schema version
create_schema()        idempotent; creates all tables at latest version
migrate(from_v, to_v)  applies incremental migrations
backup_before_migration()  copies DB file before destructive changes
```

Migration test: create a v1 DB, insert match data, run migration to v2, verify old match fetch still works and new tables exist.

History is the product. Save compatibility cannot be an afterthought.

### 6. Dynasty Lifecycle Orchestrator — `franchise.py`

The season loop is a state machine. `franchise.py` owns the transitions. Every other module is called by it, not the other way around. `persistence.py` is the only I/O boundary — `franchise.py` calls persistence to load data in, passes it to pure functions, and calls persistence to write results out.

```python
# Preseason
generate_schedule(league, seed) -> Schedule
open_offseason_transactions() -> TransactionWindow

# During season
simulate_matchday(schedule, week) -> list[MatchRecord]
aggregate_matchday_stats(match_records) -> StandingsUpdate

# End of regular season
finalize_regular_season(standings) -> PlayoffBracket | SeasonSummary
simulate_playoffs(bracket) -> Champion

# Offseason
apply_development(players, season_stats, facilities, rng) -> list[Player]
process_retirements(players) -> list[RetiredPlayer]
generate_rookie_class(season_id, rng) -> list[Player]
advance_player_ages(players) -> list[Player]
archive_season(season_data) -> SeasonHistoryRecord
start_next_season() -> Season
```

Each function declares what it reads, writes, whether it uses RNG, and what events it emits. No hidden state mutations. No functions that span two lifecycle stages.

### `MatchRecord` Contract

```python
MatchRecord:
    match_id: str
    season_id: str
    week: int
    home_club_id: str
    away_club_id: str
    home_roster_snapshot_hash: str   # SHA of snapshot stored in MatchRosterSnapshots
    away_roster_snapshot_hash: str
    config_version: str
    ruleset_version: str
    meta_patch_id: str | None
    seed: int
    event_log_hash: str              # detects corruption of the MatchEvent log
    final_state_hash: str
```

The hashes verify integrity. Actual replay is enabled by `MatchRosterSnapshots`, which stores the complete player state at match time.

---

## Phase 2: First Season + Historical Archive

**Milestone:** Generate a league, choose your club, sim a full season matchday by matchday, see standings update in real time, get a season summary with champion and awards, and be able to view any past match report. The archive is there from day one.

### Phase 1 Cleanup (do first)
1. Formalize golden-log pipeline documentation + change-notes template
2. Add automated sanity sweeps comparing GUI/CLI output to canonical log
3. Capture 2-3 additional canonical matchups beyond the single baseline

### New Modules

**`src/dodgeball_sim/stats.py`** *(build first — everything else derives from it)*
- `PlayerMatchStats` dataclass (see canonical schema above)
- `extract_player_stats(event_log: list[MatchEvent], player_id: str) -> PlayerMatchStats` — pure
- `aggregate_club_stats(match_stats: list[PlayerMatchStats]) -> ClubMatchStats` — pure

**`src/dodgeball_sim/franchise.py`**
- Season lifecycle orchestrator (see state machine above)
- Owns all state transitions; calls pure modules for computation, persistence.py for I/O
- No module other than franchise.py and persistence.py touches the DB

**`src/dodgeball_sim/league.py`**
- `Club` dataclass: `club_id`, `name`, `colors`, `home_region`, `founded_year`, `coach_policy`
- `Conference` dataclass: `conference_id`, `name`, `club_ids`
- `League` dataclass: `league_id`, `name`, `conferences`, `season_ids`
- Pure, no I/O

**`src/dodgeball_sim/scheduler.py`**
- `generate_round_robin(club_ids, seed) -> list[ScheduledMatch]` — pure, seeded via `schedule_seed` namespace
- `ScheduledMatch` dataclass: `match_id`, `week`, `home_club_id`, `away_club_id`

**`src/dodgeball_sim/season.py`**
- `Season` dataclass: `season_id`, `year`, `league_id`, `config_version`, `ruleset_version`
- `compute_standings(match_records: list[MatchRecord]) -> list[StandingsRow]` — pure
- `StandingsRow`: `club_id`, `wins`, `losses`, `elimination_differential`, `points`
  - Use `elimination_differential`, not "player diff" — language matches the sport

**`src/dodgeball_sim/awards.py`**
- `compute_season_awards(player_season_stats: dict[str, PlayerMatchStats]) -> list[SeasonAward]`
- Awards: MVP (formula-scored), Best Thrower (eliminations_by_throw), Best Catcher (catches_made), Best Newcomer (newcomer_flag=True, highest mvp_score)
- Award formula is versioned config, not hardcoded
- Pure function — no I/O

### Models.py Changes
- Add `age: int` field to `Player` (default 18)
- Add `club_id: str | None` field to `Player`
- Add `newcomer: bool` field to `Player` (set at generation time, cleared after first season)
- Age increments handled in `franchise.py`, not engine

### DB Extensions
```
SchemaVersion      (version, applied_at)
DomainEvents       (event_id, event_type, scope, entity_ids_json, payload_json, seed, created_at)
Clubs              (club_id, name, colors, home_region, founded_year)
Seasons            (season_id, year, league_id, config_version, ruleset_version)
ScheduledMatches   (match_id, season_id, week, home_club_id, away_club_id)
MatchRecords       (match_id, season_id, week, home_club_id, away_club_id,
                    home_roster_hash, away_roster_hash, config_version,
                    ruleset_version, meta_patch_id, seed, event_log_hash, final_state_hash)
MatchRosterSnapshots (match_id, club_id, players_json)
                    -- players_json: array of full player state at match time
                    -- enables deterministic replay; hash in MatchRecords verifies integrity
PlayerMatchStats   (match_id, player_id, club_id, throws_attempted, throws_on_target,
                    eliminations_by_throw, catches_attempted, catches_made,
                    times_targeted, dodges_successful, times_hit, times_eliminated,
                    revivals_caused, clutch_events, elimination_plus_minus)
SeasonStandings    (season_id, club_id, wins, losses, elimination_differential, points)
SeasonAwards       (season_id, award_type, player_id, club_id, award_score)
```

### Minimum Playable UI (Phase 2)
```
Main menu
  → Create league (generate clubs, choose yours)
  → View schedule
  → Sim next match → match report
  → Sim full matchday
  → View standings
  → View past match report (any match in history)
  → View season summary (champion, awards)
```

### Verification
- Start an 8-club league, sim full season: total wins = total losses (round-robin check)
- Sim same season twice with same root seed → identical `MatchRecord` list
- Player stats extracted from event log match box score totals
- Awards match expected winner from raw `PlayerMatchStats`
- Replay: load `MatchRosterSnapshots` + `MatchRecord.seed`, re-run engine → identical event log hash
- DB migration: create v1, insert match, migrate, old fetch still works
- All 22 existing tests green

---

## Phase 3: Offseason + Roster Continuity

**Milestone:** Seasons now chain together. Players age, develop, and retire. Rookies are generated. You can sign and release players between seasons. Running multiple seasons feels like time passing, not just replaying the same match setup.

*Identity (nicknames, archetypes, signature moments) comes in Phase 4 — after the roster continuity that makes identity meaningful.*

### New Modules

**`src/dodgeball_sim/development.py`**
- Activates existing (unused) `PlayerTraits` fields with precise contracts:
  - `potential` (0–100): hard ceiling for any rating
  - `growth_curve` (early/late/steady): determines peak age range
  - `consistency` (0–1): fatigue resistance modifier. High consistency = smaller absolute rating penalty under fatigue. Logged in `MatchEvent.context` as `consistency_modifier` on fatigue-tick events. Not a general variance multiplier — only affects the fatigue degradation path.
  - `pressure` (0–1): applied only when an explicit high-stakes trigger fires:
    ```
    pressure applies if:
      championship/cup elimination match, OR
      player is last 2 alive, OR
      final elimination opportunity of the match, OR
      rivalry match with rivalry_score > threshold
    ```
    Logged as: `"pressure_active": true, "pressure_reason": "last_player_alive", "pressure_modifier": 0.04`
- `apply_season_development(player, season_stats, facilities, rng) -> Player` — pure, seeded via `development_seed` namespace
  - Players grow toward `potential` before peak age, plateau, then decline
  - Archetypes (assigned in Phase 4) modulate growth rates; until then, growth is archetype-neutral
- `should_retire(player, career_stats) -> bool` — age + performance decline threshold; called by `franchise.py`

**`src/dodgeball_sim/recruitment.py`**
- `FreeAgent` dataclass: player available for signing
- `generate_rookie_class(season_id, rng) -> list[Player]` — pure, seeded via `draft_seed` namespace
- `build_transaction_event(action, player_id, club_id) -> TransactionEvent` — pure; returns event for franchise.py to persist via persistence.py
- No DB access. `franchise.py` calls `recruitment.py` for data, then passes results to `persistence.py`.

### Extensions to Existing Modules

**`engine.py`** — Wire `consistency` and `pressure` into probability computation:
- `consistency`: modifies fatigue degradation rate in `PlayerState`, not the base probability formula
- `pressure`: adds a context modifier to `compute_throw_probabilities()` only when a pressure trigger fires
- Both logged in `MatchEvent.context` — no invisible effects

### New DB Tables
```
FreeAgents        (player_id, available_since_season)
PlayerSeasonStats (player_id, season_id, club_id, matches,
                   total_throws_attempted, total_eliminations,
                   total_catches_made, total_dodges_successful,
                   total_times_eliminated, newcomer)
RetiredPlayers    (player_id, final_season, retirement_reason, age_at_retirement)
```

### Minimum Playable UI (Phase 3)
```
Offseason screen
  → View roster (ages, ratings, development status)
  → Release player
  → Browse free agents + rookie class
  → Sign player
  → Advance to next season
Season-over screen
  → Development report (who grew, who declined)
  → Retirement announcements
  → Rookie class preview
```

### Verification
- Sim 5 seasons: player ages increment correctly, retirements trigger, rookies fill the pool
- `consistency` invariant: high-consistency players take a measurably smaller absolute rating penalty under high-fatigue conditions than low-consistency players (tested at fixed fatigue level, not via variance)
- `pressure` modifier appears in `MatchEvent.context` for all qualifying trigger events and nowhere else
- sign/release cycle persists correctly across save/load
- Seed invariant: `development_seed` usage does not shift any `match_seed` golden log outcome

---

## Phase 4: Identity + Story Layer

**Milestone:** Players are now characters. Each has a nickname and archetype derived from their ratings. Signature moments appear on player pages. The hall of fame grows. Records are chased. The League Wire reports it all. Roster continuity from Phase 3 makes all of this feel earned.

### New Modules

**`src/dodgeball_sim/identity.py`**
- `classify_archetype(ratings: PlayerRatings) -> Archetype` — pure, derived from rating combinations:
  - High power + low catch → Power Arm
  - High catch + high dodge → Ironwall Catcher
  - High accuracy + low stamina → Glass Cannon
  - High dodge + high consistency → Ironman
  - High catch + high pressure → Clutch Catcher
  - Balanced → All-Rounder
- `generate_nickname(player_id, archetype, rng) -> str` — template-based, seeded via `nickname_seed` namespace. Deterministic: same player always gets the same nickname regardless of when called.
- Archetypes assigned at player creation (or first season appearance). They influence development trajectory in `development.py` and narration templates in `narration.py`.

**`src/dodgeball_sim/career.py`**
- `CareerStats`: lifetime aggregation
- `accumulate_career_stats(season_stats: list[PlayerSeasonStats]) -> CareerStats` — pure; `franchise.py` fetches the data from DB and passes it in
- `check_hall_of_fame_eligibility(career_stats: CareerStats) -> bool` — pure; criteria: min seasons + (career eliminations OR championships)
- `SignatureMoment` dataclass: `moment_id`, `player_id`, `season_id`, `match_id`, `moment_type`, `description`
- No DB access. All I/O flows through `franchise.py` → `persistence.py`.

**`src/dodgeball_sim/records.py`**
- Individual records: career eliminations, career catches, career dodges, most seasons at one club, most championships
- Team records: most titles, longest unbeaten run, biggest upset win (OVR gap at time of upset)
- `check_records_broken(match_stats, career_stats, current_records) -> list[RecordBroken]` — pure
- Record breaks returned as structured data; `franchise.py` persists them as `LeagueHistoryEvent`, not `MatchEvent`

**`src/dodgeball_sim/news.py`**
- League Wire: template-based, data-driven (no AI generation)
- `generate_matchday_news(matchday_results, records_broken, rivalries) -> list[Headline]` — pure
- 2-3 headlines per matchday, full recap at season end
- Categories: big upset, record broken, player milestone, retirement, rivalry flashpoint, rookie debut
- All output stored as `LeagueHistoryEvent` via `franchise.py` → `persistence.py`

**`src/dodgeball_sim/rivalries.py`**
- `RivalryRecord`: head-to-head results across all seasons
- `compute_rivalry_score(record: RivalryRecord) -> float` — pure; frequency + result closeness + championship meetings
- `update_rivalry(record, match_result) -> RivalryRecord` — pure; returns updated record
- Top rivalries surface in `narration.py` pre-match and in League Wire
- No DB access.

### Extensions to Existing Modules

**`analysis.py`** — Extend `analyze_match()` with signature moment detection:
- Personal record: career 100th elimination, first career 1v5 hold
- Clutch performer: final elimination to win championship
- Comeback win: 1v3+ deficit held and won
- Rivalry-defining: key moment in match with rivalry_score above threshold
- Detection is post-match derivation; results returned as `list[SignatureMoment]`, not stored in `MatchEvent`

**`narration.py`** — Add archetype-aware templates:
- "Power Arm [name] connects with a devastating throw"
- "Ironwall [name] snatches it out of the air"
- Pre-match: "Club X's top rival. [X] leads the all-time series 14–11."

### New DB Tables
```
PlayerCareerStats  (player_id, career_eliminations, career_catches,
                    career_dodges, seasons_played, championships, clubs_served)
SignatureMoments   (moment_id, player_id, season_id, match_id, moment_type, description)
HallOfFame         (player_id, induction_season, career_summary_json)
RivalryRecords     (club_a_id, club_b_id, a_wins, b_wins, draws,
                    rivalry_score, last_meeting_season)
LeagueRecords      (record_type, holder_id, holder_type, record_value, set_in_season)
NewsHeadlines      (headline_id, season_id, week, category, headline_text, entity_ids_json)
```

### Minimum Playable UI (Phase 4)
```
Player page
  → Career stats tab
  → Season history tab
  → Signature moments tab
  → Nickname + archetype display
Hall of fame screen
  → Inductees by season, career summary
Record book
  → Individual records + leaders
  → Team records
League Wire feed
  → Matchday news
  → Season-end recap
Rivalry page
  → Head-to-head history, rivalry score, defining moments
```

### Verification
- Every generated player has a nickname and archetype; same player always gets the same nickname
- Career stats accumulate correctly across 5+ seasons
- At least one HOF induction occurs after sufficient seasons
- Record breaks stored as `LeagueHistoryEvent`, never appear in `MatchEvent` table
- League Wire generates no unfilled template blanks
- `career.py` and `rivalries.py` contain no DB calls (verified by grep for persistence imports)
- Seed invariant: `nickname_seed` usage does not shift any `match_seed` golden log outcome

---

## Phase 5A: Scouting + Facilities

**Milestone:** Pre-season decisions now exist. Scout the rookie class and free agents with budget-appropriate information. Choose which 3 of 6 facilities to build or maintain, each shaping your club's development identity.

### New Modules

**`src/dodgeball_sim/scouting.py`**
- `ScoutingReport`: `player_id`, `revealed_archetype`, `rating_ranges` (stat → (low, high)), `exact_ratings` (populated only at high budget)
- `generate_scout_report(player, budget_level, rng) -> ScoutingReport` — pure, seeded via `scouting_seed` namespace
  - low: archetype only
  - medium: ±15 rating ranges
  - high: ±3 (near-exact)
- Difficulty controls default budget level — not on-court stat boosts (AGENTS.md guardrail preserved)
- No DB access.

**`src/dodgeball_sim/facilities.py`**

Facility effects are classified strictly. Only development, recovery, information, and tactical-unlock effects allowed. Direct match stat modifiers are excluded from scope.

```
Velocity Lab:       power growth rate +15%, overuse injury risk +5%      [development]
Reaction Wall:      dodge/catch growth rate +15%                          [development]
Recovery Suite:     stamina recovery between matches +20%                [recovery]
Film Room:          scouting budget_level promoted one tier              [information]
Analytics Dept:     scouting near-exact; probability previews pre-match  [information]
Chemistry Lounge:   unlocks sync_throw option in CoachPolicy             [tactical unlock]
```

- Max 3 active facilities per club (meaningful exclusion)
- Facilities cost prestige (earned from wins and championships)
- `apply_facility_effects(player, season_stats, facilities) -> DevelopmentModifiers` — pure; feeds into `development.py`
- Chemistry Lounge unlocks a tactic option the player must explicitly enable in `CoachPolicy` — it does not silently alter match probabilities

### New DB Tables
```
ClubFacilities  (club_id, season_id, facility_type)
ClubPrestige    (club_id, prestige_score)
```

### Minimum Playable UI (Phase 5A)
```
Pre-season screen
  → Scouting board (free agents + rookies, budget-appropriate info)
  → Facility selection (pick 3 of 6, see costs + mechanical effects)
  → Confirm pre-season choices → advance to schedule
```

### Verification
- Scout same player at low/medium/high budget: revealed info widens correctly, same player always gets same report for same seed
- Facility development effects appear in `apply_season_development` output, not in engine probability calculations
- `scouting.py` and `facilities.py` contain no DB calls
- Seed invariant: `scouting_seed` usage does not shift any `match_seed` golden log outcome

---

## Phase 5B: Meta Patches + Cup

**Milestone:** Each season now opens with a meta patch that shifts the strategic landscape. A cup tournament runs alongside the league. Every season feels like a fresh challenge.

### New Modules

**`src/dodgeball_sim/meta.py`**

Meta patches use a typed schema. `RuleSetOverrides` uses all-optional fields so only explicitly set values override the active `RuleSet` — no accidental default overrides.

```python
@dataclass(frozen=True)
class RuleSetOverrides:
    catch_revival_enabled: bool | None = None
    balls_in_play: int | None = None
    shot_clock_seconds: int | None = None  # None = no shot clock

@dataclass(frozen=True)
class MetaPatch:
    patch_id: str
    season_id: str
    name: str
    description: str                           # player-readable, shown before season starts
    power_stamina_cost_modifier: float = 0.0   # +0.15 = 15% more stamina per power throw
    dodge_penalty_modifier: float = 0.0        # +0.05 = harder to dodge
    fatigue_rate_modifier: float = 0.0         # +0.10 = 10% faster stamina drain
    ruleset_overrides: RuleSetOverrides = field(default_factory=RuleSetOverrides)
```

If a player cannot read all active effects before the season starts, the effect cannot exist. Every patch ships with a player-readable description, a new golden log covering affected match types, and a full invariant suite run.

**`src/dodgeball_sim/cup.py`**
- `CupBracket`: single-elimination tournament alongside the league
- `generate_cup_bracket(club_ids, rng) -> CupBracket` — pure, seeded via `cup_seed` namespace
- Separate matchday schedule from league fixtures
- Cup winner stored as `ClubTrophy` via `franchise.py` → `persistence.py`

### Extensions to Existing Modules

**`engine.py`**
- Accept optional `MetaPatch` as input to `MatchEngine.run()`
- Patch modifiers applied as logged multipliers to existing probability formulas
- Every `MatchEvent.context` includes `meta_patch_id` when a patch is active
- No hardcoded patch conditionals — all effects flow through typed fields

**`models.py` — `CoachPolicy` expansion**
Four new tendencies (5 → 9 total):
```python
target_ball_holder: float = 0.5    # prioritize the player currently holding the ball
stall_before_throw: float = 0.3    # hold time before releasing
catch_attempt_bias: float = 0.5    # willingness to risk a catch attempt
rush_proximity: float = 0.4        # how close before committing to a rush throw
```
Pre-match opponent scouting report: "Coach X: High tempo, targets ball-holders, rarely rushes. Sync throws: high."

### New DB Tables
```
MetaPatches    (patch_id, season_id, name, description, modifiers_json, ruleset_overrides_json)
CupBrackets    (cup_id, season_id, bracket_json)
CupResults     (cup_id, round_number, match_id, winner_club_id)
ClubTrophies   (club_id, trophy_type, season_id)
```

### Minimum Playable UI (Phase 5B)
```
Pre-season screen (extended from 5A)
  → Meta patch reveal (name, all visible effects listed explicitly)
Cup bracket screen
  → Cup draw reveal
  → Cup progress during season
  → Cup final + winner
Trophy case
  → League titles + Cup titles by season
Patch history
  → All past meta patches with their effects
```

### Verification
- Apply `heavy_ball` patch, run full invariant suite — monotonicity and symmetry still pass
- Patch modifiers appear in `MatchEvent.context` for every affected throw event
- A patch with no `ruleset_overrides` set does not accidentally enable catch revival (null fields don't override)
- Cup bracket is deterministic from same `cup_seed`
- New `CoachPolicy` tendencies shift AI behavior measurably in event log (AI legibility test)
- Seed invariant: `cup_seed` usage does not shift any `match_seed` golden log outcome

---

## Architecture Principles

- **`persistence.py` is the only I/O boundary.** No module other than `franchise.py` calls `persistence.py`. Pure modules (`career.py`, `recruitment.py`, `scouting.py`, `rivalries.py`, etc.) receive data as arguments and return results — they do not query or write the DB.
- **Pure engine core** — no I/O, fully testable in isolation
- **Immutable dataclasses** with `frozen=True` where state must not mutate
- **Event sourcing extended** — `MatchEvent` for on-court, `DomainEvents` for everything else
- **Versioned config** for all tunable constants — facility effects, patch modifiers, award formulas, development curves
- **Seeded determinism** everywhere — `derive_seed(root, namespace, *ids)` for all randomness
- **Typed contracts** — no arbitrary modifier dicts, no vague "variance multipliers"

Every new system that introduces randomness must:
1. Use `derive_seed` with an explicit namespace from the map above
2. Log its randomness source in the relevant event or report
3. Ship with a seed-invariant test confirming it does not shift existing match outcomes

---

## New Module Summary

| Module | Phase | Purpose |
|--------|-------|---------|
| `stats.py` | 2 | Canonical stat schema — built first, all else derives from it |
| `franchise.py` | 2 | Dynasty lifecycle orchestrator; sole caller of persistence.py |
| `league.py` | 2 | Club, Conference, League models |
| `scheduler.py` | 2 | Round-robin schedule generation |
| `season.py` | 2 | Season state + standings computation |
| `awards.py` | 2 | Season award computation |
| `development.py` | 3 | Player growth/regression, precise trait contracts |
| `recruitment.py` | 3 | Free agents, rookie class, sign/release events |
| `identity.py` | 4 | Nickname + archetype classification |
| `career.py` | 4 | Career stat aggregation, HOF eligibility — pure |
| `records.py` | 4 | Individual + team records, LeagueHistoryEvents |
| `news.py` | 4 | League Wire news generation |
| `rivalries.py` | 4 | Head-to-head rivalry tracking and scoring — pure |
| `scouting.py` | 5A | Scouting uncertainty layer |
| `facilities.py` | 5A | Non-linear facility system (dev/info/tactical only) |
| `meta.py` | 5B | Typed seasonal rule/meta patches |
| `cup.py` | 5B | Knockout cup tournament |

---

## Verification: End-to-End Test for Each Phase

**Phase 2:** 8-club league, full season — standings sum correctly, same seed → identical results, stats from event log match box score, replay via `MatchRosterSnapshots` + seed produces identical event log hash, awards match raw stats, DB migration preserves old match fetches, all 22 existing tests green.

**Phase 3:** 5 seasons — ages increment, retirements trigger, rookies fill pool, high-consistency players take measurably smaller absolute fatigue penalty than low-consistency at fixed fatigue level, `pressure` modifier appears only in qualifying trigger events, no DB imports in `recruitment.py`, seed invariant confirmed for `development_seed`.

**Phase 4:** 5+ seasons — every player has nickname + archetype, same nickname every time, career stats accumulate correctly, HOF induction occurs, record breaks stored as `LeagueHistoryEvent` not `MatchEvent`, League Wire has no unfilled blanks, no DB imports in `career.py` or `rivalries.py`, seed invariant confirmed for `nickname_seed`.

**Phase 5A:** Scouting budget levels produce correct info widths, same player always gets same report for same seed, facility effects appear in dev output not engine probabilities, no DB imports in `scouting.py` or `facilities.py`, seed invariant confirmed for `scouting_seed`.

**Phase 5B:** Invariant suite passes after each of 3 patches, patch modifiers in every affected `MatchEvent.context`, null `ruleset_overrides` fields do not override base ruleset, cup bracket deterministic, new `CoachPolicy` tendencies shift AI behavior measurably, seed invariant confirmed for `cup_seed`.
