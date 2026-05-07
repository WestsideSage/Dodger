# E2E Integration Pass Design

**Date:** 2026-05-06
**Type:** Integration pass — not a new milestone
**Goal:** Wire all V8–V10 thin stubs into existing progression owners so a full season playthrough (new game → season end → offseason → draft → season 2) is complete and honest.

## Relation to Prior Work

Extends `docs/retrospectives/v8-v10/2026-05-06-dynasty-office-blitz-handoff.md`. Does not supersede any milestone spec. Closes the four documented thin spots using only existing modules.

## Approach: Playthrough-Driven Integration

Changes are delivered in game-flow order. Each seam is wired mechanically and its UI evidence updated in the same pass, so every fix is immediately testable. No new tabs, no new modules, no new persistence tables.

---

## Seam 1 — Promise Fulfillment at Season End

### Where it lives

`src/dodgeball_sim/dynasty_office.py`, `src/dodgeball_sim/offseason_ceremony.py`

`offseason_beats.py` owns ceremony payload helpers and beat-completion state only. The actual mutation point — where rosters, dev ticks, and season state are live — is `offseason_ceremony.initialize_manager_offseason()`, called before `offseason_beats` finalizes each beat. Promise evaluation runs here, immediately before the `development` beat is marked complete, so roster state from `load_all_rosters()` is valid and pre-retirement.

### What's missing

Promises are persisted in `dynasty_state` under key `program_promises_json` but never evaluated. The `result` field on each promise stays `None` indefinitely.

### Promise schema change

Each promise record stored in `program_promises_json` must include `player_id` (the promised player). The `save_recruiting_promise(conn, player_id, promise_type)` function signature already takes `player_id` — it must be persisted in the record. Currently it is not. Add `player_id` as a stored field — without it, fulfillment evidence can't be queried. The API endpoint `POST /api/dynasty-office/promises` already receives `player_id` in the request body; no API change needed.

Schema after change:
```json
{
  "player_id": "player_abc",
  "promise_type": "early_playing_time",
  "status": "open",
  "result": null,
  "result_season_id": null,
  "evidence": "Will be checked against future command history and player match stats."
}
```

### Fulfillment evidence per promise type

| Promise type | Fulfilled when | Evidence source |
|---|---|---|
| `early_playing_time` | Player has ≥ 6 rows in `player_match_stats` for the current season's match IDs | `player_match_stats` joined to `match_records` by season. No start marker exists — participation (having a stats row) is the explicit model. Spec records this explicitly so implementors do not infer starts from appearances. |
| `development_priority` | Club applied a non-`BALANCED` `dev_focus` for ≥ 3 weeks this season AND player is on the active roster at the pre-retirement evaluation moment | `command_history.plan_json → department_orders.dev_focus != "BALANCED"` (count weeks); roster presence from `load_all_rosters(conn)[cursor.club_id]` at evaluation time — not from match participation. Note: `dev_focus` is a club-level command, not per-player. This is the correct evidence model — the promise means "I'll run a development-focused program while you're here," not a targeted player regimen. |
| `contender_path` | The manager's club (from `CareerStateCursor.club_id`) appears in `playoff_brackets.seeds_json` for the current season | `load_playoff_bracket(conn, season_id)` — if the bracket exists and `cursor.club_id` is in seeds, fulfilled |

### Evaluation timing and idempotency

Evaluation runs as a sub-step of the `development` offseason beat in `offseason_beats.py`, before the beat is marked complete. The evaluator checks each open promise:

1. If `result_season_id == current_season_id`, skip — result already set.
2. Else: query evidence, set `result` to `"fulfilled"` or `"broken"`, set `result_season_id = current_season_id`, write `evidence_text` explaining why.
3. Persist the updated promise list via `set_state` before the beat progresses.

This makes the evaluator safe to replay through ceremony state: repeated calls produce the same outcome without accumulating results.

### Save compatibility

`load_json_state(conn, PROMISE_STATE_KEY, [])` already returns `[]` for missing keys. Older promises without `player_id` are treated as unresolvable: they stay `status: open`, `result: null`, with `evidence_text: "Legacy promise — player identity not recorded."` No migration, no reset.

---

## Seam 2 — Staff → Development Math

### Where it lives

`src/dodgeball_sim/development.py`, `src/dodgeball_sim/offseason_ceremony.py`, `src/dodgeball_sim/config.py`

### What's missing

`apply_season_development` does not consult department heads. Staff hires have no mechanical effect on development outcomes.

### Integration point

`apply_season_development(player, season_stats, facilities, rng, trajectory, dev_focus)` currently returns a `Player` with modified ratings. Add one new optional parameter:

```python
staff_development_modifier: float = 0.0
```

Applied after base growth is computed, before facilities:

```python
effective_growth = base_growth * (1.0 + staff_development_modifier)
```

### Modifier formula

```python
staff_development_modifier = max(0.0, (rating - 50) / 50.0 * config.max_staff_development_modifier)
```

- Positive-only for this pass. Staff is a program-building lever, not a punishment.
- `rating` is `department_heads.rating_primary` for the development department.
- If no development department head exists, modifier is `0.0` — baseline behavior unchanged.
- `config.max_staff_development_modifier` is a new field on `BalanceConfig`, default `0.15` (15% max boost at rating 100).

### Config change

Add to `BalanceConfig` in `config.py`:
```python
max_staff_development_modifier: float = 0.15
```

Follows existing `max_` naming convention. Default preserves current behavior when department head is absent.

### Baseline invariants (required tests)

Three tests must ship alongside this seam:

1. `test_staff_dev_modifier_zero_when_no_department_head` — `apply_season_development` called without a staff modifier produces identical output to current behavior.
2. `test_staff_dev_modifier_bounded_at_max` — a hired department head at rating 100 produces a modifier of exactly `max_staff_development_modifier`, not more.
3. `test_offseason_dev_path_loads_department_head_and_passes_modifier` — run `offseason_ceremony.initialize_manager_offseason()` (or the relevant caller) against an in-memory save with a hired development department head; assert the returned player ratings reflect a non-zero bounded modifier. This test proves the path from department head persistence → modifier calculation → `apply_season_development` is actually connected, not just that the math formula is correct in isolation.

### UI evidence

`DynastyOffice.tsx` effect lanes for the development department head must show:

- Department name
- `rating_primary` value
- Computed modifier as a percentage (e.g., `+8%`)
- Last-applied season/week (from `staff_market_actions_json` recent actions)

Replace the current "future hook" placeholder text with real values once the modifier is wired.

### Save compatibility

`load_department_heads(conn)` already returns an empty list for saves without any hires. `staff_development_modifier` defaults to `0.0` in all callers — no migration needed.

---

## Seam 3 — Prospect Pool Source of Truth

### Where it lives

`src/dodgeball_sim/dynasty_office.py`

### What's missing

Dynasty Office generates prospects with a different RNG seed namespace (`"v8_recruiting_preview"`) than the scouting center (`"prospect_gen"`). This means the Dynasty Office preview shows different prospects than Recruitment Day will use.

### Fix

In `dynasty_office._prospect_rows()`:

1. Call `load_prospect_pool(conn, class_year)` first.
2. If the pool is non-empty (scouting center has run), use it — Dynasty Office is a read-only preview.
3. If empty (early career, scouting not yet run), fall back to `generate_prospect_pool(class_year, rng, config)` using the **same seed** the scouting center will use: `derive_seed(root_seed, "prospect_gen", str(class_year))`.

This means Dynasty Office either shows the exact persisted pool, or the exact deterministic pool that will be persisted later. No divergence.

### Acceptance tests

1. `test_dynasty_office_prospect_pool_matches_recruitment_day_pool` — given the same conn with a saved prospect pool (via `save_prospect_pool`), Dynasty Office `build_dynasty_office_state` must return prospects whose `player_id` values exactly match `load_prospect_pool` output. At least one prospect identity verified by `player_id`.

2. `test_dynasty_office_fallback_pool_matches_scouting_center_seed` — given a conn with no saved prospect pool, Dynasty Office `build_dynasty_office_state` generates prospects using `derive_seed(root_seed, "prospect_gen", str(class_year))`. Assert that the returned `player_id` values exactly match what `generate_prospect_pool` produces when called with the same seed — i.e., the same pool that `scouting_center.py` line 664 will later persist. This ensures pre-scouting and post-scouting previews are identical.

### Save compatibility

`load_prospect_pool(conn, class_year)` returns `[]` for saves without a persisted pool. The fallback path generates deterministically. No migration needed.

---

## Seam 4 — `_ensure_dynasty_keys` Robustness

### Where it lives

`src/dodgeball_sim/dynasty_office.py`

### What's needed

A helper called at the top of `build_dynasty_office_state` and both POST handlers. Behavior:

- If key is absent from `dynasty_state`, initialize to `[]` via `set_state`.
- If key is present but JSON is malformed (parse fails), raise `ValueError("Corrupted dynasty state key: {key}")` — surface a controlled error, do not silently overwrite.

This protects older saves (clean empty-list initialization) without hiding data loss from corruption.

---

## UI Evidence Pass

After the three mechanical seams are wired, a UI evidence pass updates `DynastyOffice.tsx`:

1. **Promise cards:** Show `result` badge (`FULFILLED` / `BROKEN` / `OPEN`) and `evidence_text` when result is set.
2. **Staff effect lanes:** Show real modifier percentage and last-applied date, replacing "future hook" copy.
3. **Prospect cards:** No change — pool alignment is a backend fix; the displayed fields stay the same.

---

## Playthrough Verification Sequence

After implementation, verify in this order against a running save:

1. Start new game → complete week 1 → match resolves.
2. Open replay proof from command center → proof events load, key plays navigable.
3. Open Dynasty Office → save a promise with a known player_id → confirm player_id stored.
4. Complete season → trigger offseason ceremony → development beat runs.
5. Reload Dynasty Office → promise shows `fulfilled` or `broken` with evidence text.
6. Hire a staff member (development dept) → run offseason dev tick → verify player rating change is within bounded range.
7. Open Dynasty Office → prospect list matches `load_prospect_pool` for this season.
8. Complete offseason ceremony all 10 beats → draft → advance to season 2 → confirm clean load.
9. Open an old save with no dynasty state → Dynasty Office loads with empty promises and empty staff history.

---

## What This Does Not Change

- No new tabs or routes.
- No new SQLite tables or schema migrations.
- `apply_season_development` signature change is additive (default parameter — all existing callers unchanged).
- No engine behavior changes. No golden log updates needed.
- V9 living memory depth is out of scope for this pass (dedicated future task).
- Negative staff modifiers are out of scope — balance milestone with AI staff competition.
