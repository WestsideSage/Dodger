# Phase 2 Handoff — April 24, 2026

**From:** Claude (Sonnet 4.6)
**To:** Next implementation agent (Claude or Codex)
**Phase completed:** Phase 2 — First Season + Historical Archive
**Tests:** 22/22 passing

> Historical snapshot: this early handoff predates the current milestone index, git setup, and web-app source of truth. Use root `AGENTS.md`, `docs/README.md`, and `docs/specs/MILESTONES.md` for current orientation.

---

## What Was Built This Session

Phase 2 is fully implemented. All modules are importable and tested end-to-end.

### New Modules

| File | Purpose | Status |
|------|---------|--------|
| `src/dodgeball_sim/stats.py` | Canonical PlayerMatchStats schema + event-log extraction | Done |
| `src/dodgeball_sim/league.py` | Club, Conference, League frozen dataclasses | Done |
| `src/dodgeball_sim/scheduler.py` | Deterministic round-robin schedule generation | Done |
| `src/dodgeball_sim/season.py` | Season, SeasonResult, StandingsRow, compute_standings | Done |
| `src/dodgeball_sim/awards.py` | SeasonAward, compute_season_awards, aggregate_season_stats | Done |
| `src/dodgeball_sim/franchise.py` | Season lifecycle orchestrator — pure computation only | Done |
| `src/dodgeball_sim/dynasty_cli.py` | Interactive dynasty mode CLI | Done |

### Modified Modules

| File | Changes |
|------|---------|
| `src/dodgeball_sim/rng.py` | Added `derive_seed()` (% 2^63 for SQLite) and `gauss()` to DeterministicRNG |
| `src/dodgeball_sim/persistence.py` | Schema v2 migrations, 16 new dynasty functions, updated _player_to/from_dict |
| `src/dodgeball_sim/models.py` | Added `age: int = 18`, `club_id: str | None = None`, `newcomer: bool = True` to Player |
| `src/dodgeball_sim/cli.py` | Added `--dynasty` flag |

### DB Schema (v2)

New tables added in `_migrate_v2`:
- `schema_version` — tracks applied migrations
- `domain_events` — off-court event log (not yet used; scaffolded)
- `clubs` — franchise entities
- `club_rosters` — JSON player lists per club
- `seasons` — season metadata
- `scheduled_matches` — round-robin schedule
- `match_records` — completed match records with winner_club_id, home/away survivors, integrity hashes
- `match_roster_snapshots` — full player state for replay (used via `record_roster_snapshot`)
- `player_match_stats` — per-match stat rows keyed by (match_id, player_id)
- `season_standings` — standings including `draws` column
- `season_awards` — MVP, best_thrower, best_catcher, best_newcomer
- `dynasty_state` — key/value table for active season, player club, root seed

---

## How to Run Dynasty Mode

```bash
cd "C:\GPT5-Projects\Dodgeball Simulator"
python -m dodgeball_sim.cli --dynasty
```

This will:
1. Generate 8 clubs from a themed pool with seeded rosters
2. Prompt you to pick your club
3. Drop you into the season menu (schedule / next match / matchday / standings / summary)

---

## Test Baseline

```bash
python -m pytest tests/ -q
# Expected: 22 passed, 2 warnings (utcnow deprecation — benign)
```

All 22 tests are Phase 1 tests. No Phase 2-specific tests were written this session.

---

## Known Issues and Deferred Work

### 1. No Phase 2 Tests Written

The Phase 2 modules are verified by end-to-end smoke tests run interactively, but not by the `tests/` suite. The incoming agent should add:

- `tests/test_stats.py` — stat extraction matches box score totals
- `tests/test_scheduler.py` — round-robin produces correct match count, all clubs appear equally
- `tests/test_season.py` — standings sum (wins == losses after round-robin)
- `tests/test_awards.py` — award winners match raw PlayerMatchStats
- `tests/test_dynasty_persistence.py` — save/load round-trips for clubs, seasons, standings

This is the highest-priority item before starting Phase 3.

### 2. `best_newcomer` Award Not Issued

`compute_season_awards()` takes `newcomer_player_ids: frozenset`. Phase 2 passes `frozenset()` so the award is never given. Phase 3 sets `newcomer=True` at roster generation and populates this set from players where `newcomer=True` at season start.

### 3. `season_id` Extraction Is Fragile

In `franchise.py`, `record.season_id` is extracted from the match ID via `match_id.split("_w")[0]`. This breaks if a `season_id` itself contains `_w`. Phase 3 should add `season_id: str` as an explicit field on `ScheduledMatch` and pass it directly.

### 4. `domain_events` Table Unused

The table is scaffolded in v2 but nothing writes to it yet. Phase 2 season events (champion crowned, awards computed) should eventually emit `DomainEvent` rows so off-court history is queryable. Not blocking for Phase 3.

### 5. No Multi-Season Support

Dynasty state stores `active_season_id = "season_2025"` and there's no "start next season" flow. When the season completes, the menu tells the user it continues "in a future update." Phase 3 adds the offseason loop.

### 6. Club Name Collision Risk

`_CLUB_POOL` has 12 entries; 8 are picked each dynasty run. If `root_seed` produces the same shuffle across two runs, clubs are identical (by design — deterministic). But if someone edits the pool, existing DBs that stored old club IDs will have orphaned records. Phase 3 should add a migration if the pool changes.

### 7. Standings After Full-Season Sim

`simulate_full_season()` in `franchise.py` returns standings computed from in-memory `SeasonResult` objects. These are NOT persisted automatically — the caller must call `save_standings()`. The `dynasty_cli.py` does this correctly via `_recompute_and_save_standings()`, but a direct call to `simulate_full_season()` + `save_standings()` requires manually constructing the correct `SeasonResult` list. This is addressed by adding `save_match_result(winner_club_id=...)` at persist time.

---

## Architecture Invariants — Do Not Break

1. **`persistence.py` must not import from `franchise.py`** — would create a circular dependency when Phase 3 adds persistence calls inside franchise.py.

2. **`derive_seed` output is always `% (2 ** 63)`** — SQLite signed int64 constraint. Do not remove this modulo.

3. **`DeterministicRNG` is the only RNG source** — no bare `random.random()` calls in any module. Always use `DeterministicRNG` initialized with a `derive_seed` output.

4. **All new seed namespaces must be added to the map in `revival-roadmap.md`** — run the seed-invariant check before merging: add the new namespace, confirm golden log match outcomes are unchanged.

5. **`MatchEvent` is on-court only** — off-court events go to `domain_events`. Do not add dynasty/season data to the `match_events` table.

6. **Player dataclass changes require default values** — `Player` is instantiated in many places. New fields must always have defaults.

---

## Next Steps (Phase 3 — Offseason + Roster Continuity)

See `docs/roadmap/revival-roadmap.md` Phase 3 section for full spec. Priority order:

1. **Write Phase 2 tests first** (see Known Issues §1 above) — green baseline before any Phase 3 code.

2. **Add `season_id` to `ScheduledMatch`** — eliminate the fragile string-split extraction.

3. **Implement `development.py`** — `apply_season_development(player, season_stats, facilities, rng)` with precise `consistency` (fatigue resistance modifier) and `pressure` (high-stakes trigger only) contracts as specified in the roadmap.

4. **Implement `recruitment.py`** — `generate_rookie_class(season_id, rng)` seeded via `draft_seed`, `build_transaction_event()`, free agent pool.

5. **Add offseason loop to `dynasty_cli.py`** — development report screen, retirement announcements, rookie class preview, sign/release menu.

6. **Wire `consistency` and `pressure` into `engine.py`** — these activate the Phase 3 trait fields that are currently defined but unused.

7. **Add multi-season state management** — when season ends, advance to next season, increment ages, run development, process retirements, replenish free agents.

The Phase 3 minimum playable gate: 5 seasons chain correctly — players age, retirements trigger, rookies fill the pool, sign/release persists across save/load.

---

## File Locations Quick Reference

```
src/dodgeball_sim/
  engine.py          Core match engine — do not modify without updating golden logs
  models.py          Player, Team, CoachPolicy, MatchSetup — Player has age/club_id/newcomer
  rng.py             DeterministicRNG + derive_seed — seed map in roadmap doc
  persistence.py     All DB I/O — sole I/O boundary
  franchise.py       Pure computation orchestrator — no DB calls
  dynasty_cli.py     Interactive CLI — calls both franchise.py and persistence.py
  stats.py           PlayerMatchStats + extraction functions
  league.py          Club, Conference, League
  scheduler.py       ScheduledMatch + generate_round_robin
  season.py          Season, SeasonResult, StandingsRow, compute_standings
  awards.py          SeasonAward, compute_season_awards, aggregate_season_stats

docs/
  roadmap/revival-roadmap.md    Full 5-phase plan — source of truth
  specs/AGENTS.md               Design invariants and guardrails
  learnings/                    Technical gotchas per phase
  retrospectives/               This folder — session handoffs

tests/
  (22 Phase 1 tests — all must pass before and after any change)
```
