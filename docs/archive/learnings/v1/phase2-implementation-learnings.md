# Phase 2 Implementation Learnings

Technical lessons from building the Phase 2 dynasty spine. These are the non-obvious decisions and gotchas that are worth preserving.

---

## SQLite Signed Int64 Constraint

`derive_seed()` returns an unsigned 64-bit integer (up to 2^64 - 1). SQLite's INTEGER column is signed 64-bit (max 2^63 - 1). This causes an `OverflowError: Python int too large to convert to SQLite INTEGER` when storing large seeds.

**Fix:** `return int.from_bytes(digest[:8], "big") % (2 ** 63)` in `rng.py`.

**Implication:** Seed values are always positive and fit within signed int64. No effect on simulation outcomes — `random.Random(seed)` uses the full hash of whatever integer is passed.

---

## DeterministicRNG Needs `gauss()`

`DeterministicRNG` only had `unit()`, `roll()`, `choice()`, `shuffle()`. The dynasty roster generation needs Gaussian distributions for ratings and ages. Used `self._random.gauss(mu, sigma)` internally since `DeterministicRNG` wraps `random.Random`.

**Pattern:** Any time a new generation function needs shaped distributions, add the method to `DeterministicRNG` rather than bypassing it. Bypassing breaks the "all randomness is explicit and auditable" invariant.

---

## Circular Import Avoidance

The import chain that matters:
```
persistence.py ← can import from → league.py, season.py, scheduler.py, awards.py, stats.py
franchise.py   ← can import from → all of the above (including persistence.py in future)
dynasty_cli.py ← can import from → all of the above
```

`persistence.py` must NOT import from `franchise.py`. If it did, and `franchise.py` later imports from `persistence.py` (as planned), you get a circular import. The safe rule: persistence.py only imports from pure, leaf-level modules that have no dependency on persistence.

**Tested:** `franchise.py` currently has zero imports from `persistence.py`. All I/O in Phase 2 goes through `dynasty_cli.py` calling both directly. In Phase 3+, `franchise.py` will gain persistence calls — that stays safe as long as `persistence.py` never imports from `franchise.py`.

---

## Winner Must Be Persisted Directly

Early approach: re-derive the winner from player stats after the fact (who had `times_eliminated=0`). Problem: this logic diverges from the engine's actual `winner_team_id` for edge cases (e.g., time-limit draws, simultaneous final eliminations).

**Fix:** Added `winner_club_id`, `home_survivors`, `away_survivors` to the `match_records` table and `save_match_result()`. The engine's truth is captured at persist time, not re-derived from stats.

**Why it matters:** `compute_standings()` uses `winner_club_id` to assign W/L/D. If re-derived incorrectly, a match the engine called a draw gets scored as a win, corrupting the standings.

---

## `Player` Model Extension — Defaults Required

`Player` is a frozen dataclass used throughout the existing engine. Adding `age`, `club_id`, `newcomer` required default values (`age=18`, `club_id=None`, `newcomer=True`) so the existing `tests/factories.py` and all call sites that don't pass these fields continue to work without modification.

**Pattern for future additions:** Always add new `Player` fields with defaults. Never add required fields to existing dataclasses that have widespread instantiation sites.

---

## `_player_to_dict` / `_player_from_dict` Symmetry

The `_player_to_dict` function in `persistence.py` was originally used only for Phase 1 match setup serialization. It was extended to include `age`, `club_id`, `newcomer`. A matching `_player_from_dict` was added.

Both must stay in sync. If a new Player field is added in Phase 3 (e.g., `nickname`, `archetype`), update both functions. The DB round-trip test catches this: save a club roster, load it back, verify field equality.

---

## Season Schedule — Match ID Format

Match IDs use the format `{season_id}_w{week:02d}_{home_club_id}_vs_{away_club_id}`. The season ID is embedded in the match ID. This means:

- `season_id` can be extracted from `match_id` via `match_id.split("_w")[0]` — but this is fragile if `season_id` itself contains `_w`.
- Phase 2 uses `season_2025` which avoids this. Phase 3+ should ensure season IDs never contain `_w` in the middle, or change the extraction to pass `season_id` explicitly through `ScheduledMatch`.

**Recommendation for Phase 3:** Add `season_id` as a field on `ScheduledMatch` to eliminate the string-parse dependency.

---

## Standings Computation Is Pure and Re-Runnable

`compute_standings(results: List[SeasonResult])` in `season.py` is a pure function. It re-runs cleanly from any list of `SeasonResult`. After each matchday, `_recompute_and_save_standings` rebuilds the full standings from `match_records` — this is intentionally idempotent (running it twice produces the same result).

This design means standings are always derivable from the event log, consistent with the "no hidden state" principle.

---

## `CoachPolicy` Field Deserialization

`load_clubs()` in `persistence.py` deserializes `coach_policy_json` using:
```python
CoachPolicy(**{k: v for k, v in cp_dict.items() if k in CoachPolicy.__dataclass_fields__})
```

The filter on `__dataclass_fields__` future-proofs against JSON blobs containing old field names after a `CoachPolicy` refactor. This avoids `TypeError: unexpected keyword argument` when loading old save data.

**Phase 5B adds 4 new CoachPolicy fields.** When those are added, old save data won't have them — the filter + defaults handle this gracefully.

---

## `best_newcomer` Award Requires Explicit Opt-In

`compute_season_awards()` takes a `newcomer_player_ids: frozenset` argument. Phase 2 passes `frozenset()` (empty) since all players are new but we're not tracking the newcomer flag in stats yet. The award simply isn't generated when the set is empty.

Phase 3 will set `newcomer=True` on roster generation and clear it after season 1. The `newcomer_player_ids` set gets populated from players where `newcomer=True` at season start.

---

## Schema Version Bootstrapping

`create_schema()` reads the current version from `schema_version` table before `schema_version` exists (chicken-and-egg). The fix: `get_schema_version()` wraps the query in `try/except sqlite3.OperationalError` and returns 0 if the table doesn't exist yet. Version 0 means "never migrated" — all migrations run.

This must be preserved. If `get_schema_version()` is ever changed to not catch `OperationalError`, fresh DB creation will break.
