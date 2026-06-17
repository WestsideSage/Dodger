# V26 — The Crowd: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the program a living crowd — revived treasury-gated facilities, two append-only receipted fan ledgers, matchday + merch income, bench roles that make depth and the identity traits matter, and offseason media beats — all from real logged events, behind `pyramid_world_active` so legacy saves are byte-identical.

**Architecture:** Two dormant systems are revived and modernized to the V22–V25 idiom: facilities (web path fed `()`) become **permanent, user-owned, treasury-bought buildings** stored cleanly (the legacy per-season CLI `club_facilities` path is left untouched); prestige growth (CLI-only) is ported to a shared web offseason event-rollup that also drives the new club-fan ledger. New `fan_ledger.py` (append-only receipts) and `facilities_office.py` (treasury buy + catalog) carry the new logic; income lines join `economy.apply_season_finances`; bench roles ride `dynasty_state` JSON; media is a new offseason beat.

**Tech Stack:** Python 3 (frozen dataclasses, SQLite, `dynasty_state` KV + a `_migrate_v19` for the fan tables, `rng.derive_seed`), pytest; React + TypeScript (no test runner — build/lint + data-flow + Python guards).

**Spec:** `docs/specs/2026-06-17-v26-the-crowd-spec.md`. **Era authority:** `docs/specs/2026-06-12-climb-era-vision.md` § V26. **Build-state truth:** `docs/STATUS.md`. **Branch:** `feature/v24-the-board`.

**Standing rules (AGENTS.md / hard-won this arc):**
- Run `python -m pytest -q` to a real exit code; **never pipe pytest to `tail`** (it masks the exit code AND truncates the FAILED list — bit us in V25).
- New `derive_seed` namespace `v26_media` only; fan gains are pure functions of logged events.
- New JSON fields read via `.get()` defaults; new `EconomyConfig` fields default so legacy ledgers are byte-identical.
- `OFFSEASON_CEREMONY_BEATS` + active-beats + `persistence._MAX_OFFSEASON_BEAT_INDEX` change together (the V25 clamp bug).
- Intentional development-outcome changes (the facility revival) update golden logs in the same pass.
- Pyramid-gate every income line + fan accrual; verify legacy byte-identical.

---

## File Structure

**New files:**
- `src/dodgeball_sim/fan_ledger.py` — append-only fan ledger: `add_fans`/`add_followers` (write a receipt + bump the running total), `club_fans`/`player_followers`, `load_fan_receipts`. The single mutation home (never bump a total without a receipt).
- `src/dodgeball_sim/facilities_office.py` — web facilities: `owned_facilities(conn)`, `facility_catalog()`, `buy_facility(conn, facility_type)` (treasury sink), `facilities_state(conn)` (panel payload).
- `src/dodgeball_sim/fan_economy.py` — pure fan-gain + income formulas (the `staff_effects.py`/`contracts.py` single-formula-home pattern): `club_fans_for_event`, `followers_for_event`, `matchday_income_k`, `merch_income_k`, `stadium_capacity`.
- `src/dodgeball_sim/bench_roles.py` — role model: `assign_role`/`assigned_roles`, `mentor_bonus_for`, `analyst_targeting_bonus`, `ambassador_income_k`.
- `tests/test_v26_facilities.py`, `test_v26_club_fans.py`, `test_v26_player_fans.py`, `test_v26_fan_income.py`, `test_v26_bench_roles.py`, `test_v26_media.py`, `test_v26_offseason_integration.py`.
- `tools/fan_income_probe.py`, `tools/facility_effect_probe.py`, `tools/bench_role_probe.py`.
- `frontend/src/components/dynasty/FacilitiesUpgradePanel.tsx`, `frontend/src/components/ceremonies/MediaEvent.tsx`, fan-ledger display in the History tab.

**Modified files:**
- `src/dodgeball_sim/facilities.py` — add `TRAINING_HALL`/`STADIUM`/`MERCH_CENTER` types + a Training-Hall `DevelopmentModifiers` effect; consume-or-remove the dead `scouting_*_bonus` fields.
- `src/dodgeball_sim/development.py` — `_facility_bonus` covers the Training-Hall stats; `apply_season_development` gains a `mentor_dev_bonus` param.
- `src/dodgeball_sim/offseason_ceremony.py` — the `facilities=()` site (773) feeds the user's owned facilities; the offseason event-rollup (prestige + club fans + player followers); the Mentor wiring; the `media_event` beat.
- `src/dodgeball_sim/economy.py` — `apply_season_finances` matchday + merch lines.
- `src/dodgeball_sim/config.py` — `ContractConfig`-style `FanConfig` / `EconomyConfig` fields + facility costs.
- `src/dodgeball_sim/persistence.py` — `_migrate_v19` (fan tables) + `CURRENT_SCHEMA_VERSION` 18→19 + `_MAX_OFFSEASON_BEAT_INDEX` if `media_event` lands.
- `src/dodgeball_sim/offseason_presentation.py`, `offseason_service.py`, `server.py` — facilities/media/fan endpoints + beat payloads.
- `src/dodgeball_sim/{official_engine,rec_engine}.py` (read-only hook) — the Analyst `targeting_read_bonus` into the preps dict (no resolution change).
- `frontend/src/{types.ts, components/DynastyOffice.tsx, components/Offseason.tsx, components/ceremonies/RecapStandings.tsx, api/client.ts}`.

---

## Phase 1 — Facilities revival + modernization

*The dormant `facilities=()` fix + treasury-gated permanent buildings. Fully concrete.*

### Task 1.1: New facility types + Training-Hall effect + treasury costs

**Files:**
- Modify: `src/dodgeball_sim/facilities.py`
- Modify: `src/dodgeball_sim/config.py`
- Test: `tests/test_v26_facilities.py`

- [ ] **Step 1: Failing test.**
```python
# tests/test_v26_facilities.py
from dodgeball_sim.facilities import FacilityType, FACILITY_DEFINITIONS, apply_facility_effects
from dodgeball_sim.config import DEFAULT_FACILITIES as F


def test_new_facility_types_exist_with_treasury_costs():
    for t in (FacilityType.TRAINING_HALL, FacilityType.STADIUM, FacilityType.MERCH_CENTER):
        assert t in FACILITY_DEFINITIONS
        assert F.treasury_cost_k[t.value] > 0


def test_training_hall_lifts_general_development():
    mods = apply_facility_effects(None, None, [FacilityType.TRAINING_HALL])
    # Training Hall raises the general growth multiplier above the neutral 1.0.
    assert mods.general_growth_multiplier > 1.0


def test_stadium_and_merch_have_no_development_effect():
    for t in (FacilityType.STADIUM, FacilityType.MERCH_CENTER):
        mods = apply_facility_effects(None, None, [t])
        assert mods.general_growth_multiplier == 1.0 and mods.power_growth_multiplier == 1.0
```

- [ ] **Step 2: Run, verify fail.** `python -m pytest tests/test_v26_facilities.py -q` → FAIL (types/field missing).

- [ ] **Step 3: Add the types + a `general_growth_multiplier` field.** In `facilities.py`: add `TRAINING_HALL = "training_hall"`, `STADIUM = "stadium"`, `MERCH_CENTER = "merch_center"` to `FacilityType`; add `general_growth_multiplier: float = 1.0` to `DevelopmentModifiers`; add the three `FacilityDefinition` rows to `FACILITY_DEFINITIONS` (keep `prestige_cost` for the CLI; the web cost lives in config); in `apply_facility_effects` set `general_growth_multiplier=1.10 if TRAINING_HALL in selected else 1.0`; extend `_normalize_facility_type` aliases for the three new strings.

- [ ] **Step 4: Add `FacilityConfig`** to `config.py` (after `DEFAULT_CONTRACTS`):
```python
@dataclass(frozen=True)
class FacilityConfig:
    # Treasury cost to build each facility (permanent, one-time).
    treasury_cost_k: Mapping[str, int] = field(default_factory=lambda: {
        "training_hall": 160, "stadium": 200, "merch_center": 140,
        "velocity_lab": 120, "reaction_wall": 120, "recovery_suite": 90,
        "film_room": 90, "analytics_dept": 180, "chemistry_lounge": 90,
    })

DEFAULT_FACILITIES = FacilityConfig()
```
Export `"FacilityConfig"`, `"DEFAULT_FACILITIES"`.

- [ ] **Step 5: Wire the Training-Hall bonus** in `development.py:_facility_bonus` — return `(general_growth_multiplier - 1.0) * 1.3` added to EVERY stat's delta (a broad lift), keeping the existing per-stat facility bonuses.

- [ ] **Step 6: Consume-or-remove dead fields.** The `scouting_budget_tier_bonus`/`scouting_precision_bonus` `DevelopmentModifiers` fields are computed but never read in the web path. Per current standards, remove them from `DevelopmentModifiers` + `apply_facility_effects` (the CLI `_scouting_budget_level` re-checks the facility strings inline, so nothing depends on these fields). Update `tests/` that pin them.

- [ ] **Step 7: Run + full suite.** `python -m pytest tests/test_v26_facilities.py -q` → PASS; `python -m pytest -q` green. **Commit.**

### Task 1.2: Permanent user-owned facilities store + treasury buy (TDD)

**Files:**
- Create: `src/dodgeball_sim/facilities_office.py`
- Test: `tests/test_v26_facilities.py`

- [ ] **Step 1: Failing tests** — `owned_facilities` empty by default; `buy_facility` deducts treasury + adds the facility; refuses when the treasury is short; refuses a duplicate; pyramid-gated (legacy raises/no-ops):
```python
def test_buy_facility_spends_treasury_and_persists(pyramid_conn):  # helper builds a pyramid career
    from dodgeball_sim.economy import set_treasury_k, treasury_k
    from dodgeball_sim import facilities_office as fo
    set_treasury_k(pyramid_conn, 1000); pyramid_conn.commit()
    res = fo.buy_facility(pyramid_conn, "training_hall")
    assert res["owned"] and "training_hall" in fo.owned_facilities(pyramid_conn)
    assert treasury_k(pyramid_conn) == 1000 - res["cost_k"]

def test_buy_facility_refuses_when_short(pyramid_conn):
    from dodgeball_sim.economy import set_treasury_k
    from dodgeball_sim import facilities_office as fo
    set_treasury_k(pyramid_conn, 5); pyramid_conn.commit()
    import pytest
    with pytest.raises(ValueError):
        fo.buy_facility(pyramid_conn, "stadium")
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement `facilities_office.py`** — owned facilities are a permanent per-user-club list in `dynasty_state` (`v26_owned_facilities_json`); `buy_facility` mirrors `recruiting_office.upgrade_scouting_network` (treasury check + `set_treasury_k` + append, MAX 6 owned, refuse duplicate/short/non-pyramid); `facility_catalog()` returns each `FacilityDefinition` + `treasury_cost_k` + `owned`/`can_afford`; `facilities_state(conn)` is the panel payload.

- [ ] **Step 4: Run, verify pass + full suite.** **Commit.**

### Task 1.3: Revive facilities in the web development pass (TDD — intentional outcome change)

**Files:**
- Modify: `src/dodgeball_sim/offseason_ceremony.py:773` (the `facilities=()` site)
- Test: `tests/test_v26_facilities.py`

- [ ] **Step 1: Failing test** — a user club that OWNS a Training Hall develops a young player MORE than the same seed without it (the effect is real):
```python
def test_owned_training_hall_lifts_user_development(pyramid_conn):
    # Run one offseason with vs without an owned Training Hall; the owning run's
    # user-roster OVR delta is strictly larger. (Build two identical-seed careers.)
    ...
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Feed owned facilities for the user club** in the dev loop. Replace `facilities=()` with `facilities=_user_facilities if is_player_club else ()` where `_user_facilities = tuple(facilities_office.owned_facilities(conn)) if pyramid_world_active(conn) else ()` is computed once before the loop. AI clubs stay `()` (abstracted — user-program feature).

- [ ] **Step 4: Run, verify pass.**

- [ ] **Step 5: Full suite + golden logs.** `python -m pytest -q`. Any development witness for a facility-OWNING user club shifts (intentional) — re-derive + note. Fresh saves own nothing → byte-identical. Green. **Commit** `feat(v26): revive facilities in the web dev path (user-owned, treasury-bought)`.

### Task 1.4: Facilities endpoint + DynastyOffice panel (frontend)

**Files:** `server.py` (`POST /api/dynasty-office/facilities/upgrade` + `facilities_state` on the office payload), `dynasty_office.py` (attach `facilities_upgrade`), `types.ts`, `frontend/src/components/dynasty/FacilitiesUpgradePanel.tsx` (clone `ScoutingNetworkPanel`), `DynastyOffice.tsx` (render it in the Staff tab), `api/client.ts` (`upgradeFacility`).
- [ ] Backend Pydantic field added BEFORE the FE reads it (response_model strip trap). Python guard test on the rendered `facilities_upgrade` payload.
- [ ] `npm run build` + `npm run lint` clean. **Commit.**

### Task 1.5: Phase 1 gate
- [ ] `python -m pytest -q` green (real exit code); legacy/non-pyramid + no-facilities byte-identical; `tools/facility_effect_probe.py` shows BEFORE/AFTER development delta. Commit any golden re-pins.

---

## Phase 2 — Club fan ledger (+ prestige growth ported to web)

### Task 2.1: `_migrate_v19` fan tables (TDD)
**Files:** `persistence.py` (`CURRENT_SCHEMA_VERSION` 18→19, `_migrate_v19` creating `club_fans`, `player_fans`, `fan_ledger`); Test `tests/test_v26_club_fans.py`.
- [ ] Failing test: a fresh schema is v19 with the three tables; a v18 save migrates idempotently (column-existence guards, the v18 `division_membership` precedent).
- [ ] Implement + commit. Add a guard test pinning `CURRENT_SCHEMA_VERSION == 19`.

### Task 2.2: `fan_ledger.py` append-only ledger (TDD)
**Files:** Create `fan_ledger.py`; Test `tests/test_v26_club_fans.py`.
- [ ] Failing tests: `add_fans(conn, club_id, delta, season_id, event_type, receipt)` bumps `club_fans` AND writes a `fan_ledger` row with the running total; `club_fans(conn, club_id)` reads it; never bump without a receipt. Mirror `add_followers` for players.
- [ ] Implement (the single mutation home). Commit.

### Task 2.3: `fan_economy.py` fan-gain formulas + offseason rollup (TDD)
**Files:** Create `fan_economy.py`; Modify `offseason_ceremony.py` (a shared `_award_prestige_and_fans` rollup in the offseason, guarded by `v26_fans_awarded_for`); Test `tests/test_v26_club_fans.py`.
- [ ] **Failing receipt-audit test:** after an offseason, a club that won the division / promoted / won Worlds has a `fan_ledger` whose deltas sum to its `club_fans`, each receipt naming the event ("+N after the promotion final"). Sources: `pyramid_postseason` ledger, `worlds_history_json`, `club_trophies`, `rivalry_records` (weighted by `compute_rivalry_score`), per-win from standings.
- [ ] **Port prestige to web:** the same rollup also grows prestige (the dormant `_award_prestige_for_season` + cup/title `+6` logic), so V24 Contender + credibility grow on web. Idempotent.
- [ ] Implement `fan_economy.club_fans_for_event(...)` (pure) + the rollup. Commit `feat(v26): club fan ledger + web prestige growth from real events`.

---

## Phase 3 — Player followings

### Task 3.1: Player-following gains from MVPs/records/milestones/district (TDD)
**Files:** `fan_economy.py` (`followers_for_event`), `offseason_ceremony.py` (extend the rollup); Test `tests/test_v26_player_fans.py`.
- [ ] Failing test: a player who won MVP (`signature_moments` `moment_type='mvp'`) / set a record / hit a milestone (`RatifiedRecord.is_new_holder`/`milestone_label`) / has a district tie (`Club.home_region`) accrues followers a benchwarmer does not; each delta a receipt. (In-game `MomentKind` events are replay-only → not used; disclosed.)
- [ ] Implement + commit. Determinism fence.

---

## Phase 4 — Fan income (matchday + merch)

### Task 4.1: Income formulas (TDD)
**Files:** `fan_economy.py` (`stadium_capacity`, `matchday_income_k`, `merch_income_k`); `config.py` (`EconomyConfig` fan fields, default 0); Test `tests/test_v26_fan_income.py`.
- [ ] Failing tests: `matchday = min(club_fans, stadium_capacity) × per-fan rate`; `merch = (club_fans + Σ star followings) × merch rate`; stadium capacity rises with the Stadium facility + tier; all `0` when the knobs default (legacy).
- [ ] Implement (pure). Commit.

### Task 4.2: Wire into `apply_season_finances` (TDD)
**Files:** `economy.py` (`apply_season_finances` matchday + merch lines + ledger keys + honest rules line); Test `tests/test_v26_fan_income.py`.
- [ ] Failing tests: pyramid save with fans → ledger has `matchday_income_k`/`merch_income_k` and `net_k` adds them; legacy save → both 0, net unchanged (byte-identical). Mirror the V25 `player_wage_bill_k` wiring.
- [ ] Implement; pyramid-gate; re-pin economy witnesses (additive 0 on legacy). Commit.

### Task 4.3: Recap finances rows (frontend)
**Files:** `types.ts` (`finances.matchday_income_k?`/`merch_income_k?`), `RecapStandings.tsx` (green income spans, optional-guarded like `player_wage_bill_k`). `npm run build`+`lint`. Commit.

---

## Phase 5 — Bench roles

### Task 5.1: Role model + assignment (TDD)
**Files:** Create `bench_roles.py`; Test `tests/test_v26_bench_roles.py`.
- [ ] Failing tests: `assign_role(conn, player_id, 'mentor'|'analyst'|'ambassador')` persists in `dynasty_state` (`v26_bench_roles_json`); only a non-starter (lineup position ≥ `STARTERS_COUNT`) may hold a role; one role per player; `assigned_roles(conn)` round-trips.
- [ ] Implement + commit.

### Task 5.2: Mentor dev modifier (TDD — identity-traits consumer)
**Files:** `development.py` (`apply_season_development` gains `mentor_dev_bonus: float = 0.0` applied only to young targets), `offseason_ceremony.py` (compute the mentor bonus per youngster from the assigned Mentor's identity trait); Test `tests/test_v26_bench_roles.py`.
- [ ] Failing test: a youngster paired with a Mentor gains a strictly larger OVR delta than an unmentored control at the same seed; the bonus scales with the mentor's relevant identity trait (its first honest consumer).
- [ ] Implement (new param — do NOT reuse the club-wide `staff_development_modifier`). Commit.

### Task 5.3: Analyst targeting-read + Ambassador income (TDD)
**Files:** `bench_roles.py` (`analyst_targeting_bonus`, `ambassador_income_k`), the preps-dict hook in `offseason_ceremony`/match-prep where `targeting_read_bonus` is set (both engines already read it), `fan_economy`/`economy` for the Ambassador income; Tests in `test_v26_bench_roles.py`.
- [ ] Failing tests: an Analyst raises the team's `targeting_read_bonus` (scales with his `tactical_iq`) — assert the prep value, NOT a match outcome; an Ambassador adds his following's income to the merch/matchday line.
- [ ] Implement + commit. `tools/bench_role_probe.py` (each role measurably matters).

### Task 5.4: Bench-role assignment UI (frontend)
**Files:** `types.ts` (`bench_role?` on the roster row — a SEPARATE field, never overwrite archetype `role`), a role dropdown on `LineupEditor.tsx`, `api/client.ts` (`POST /api/dynasty-office/bench-role`), `server.py` route. Build+lint. Commit.

---

## Phase 6 — Media mini-events

### Task 6.1: `media_event` offseason beat (TDD)
**Files:** `offseason_ceremony.py` (`OFFSEASON_CEREMONY_BEATS` insert `media_event` between `rookie_class_preview` and `recruitment`; `compute_active_beats` conditional — only when an event fires on the `v26_media` stream; `_MAX_OFFSEASON_BEAT_INDEX` 10→11 + guard test), `offseason_presentation.py` (payload branch + text branch), `offseason_service.py` (choice handler + commit), `server.py` (`POST /api/offseason/media`); Test `tests/test_v26_media.py`.
- [ ] **Failing isolation test (the load-bearing fence):** a media choice changes ONLY fans/prestige/credibility — never a match result, standings, roster, development, or treasury beyond the disclosed fan/prestige effect. Assert before/after equality on standings + a played match outcome.
- [ ] Implement; effects route to `fan_ledger`/`save_club_prestige`/a one-season credibility bonus in `dynasty_state` read inside `recruiting_office._credibility`. Commit.

### Task 6.2: Media event card (frontend)
**Files:** `frontend/src/components/ceremonies/MediaEvent.tsx`, `Offseason.tsx` dispatch, `types.ts` variant. Build+lint. Commit.

---

## Phase 7 — Balance pass + probes + verification

### Task 7.1: Tune + pin constants
- [ ] Run `tools/fan_income_probe.py` (combined fan income 15–25% of competitive prize money, NEVER exceeds it at any tier), `facility_effect_probe.py`, `bench_role_probe.py`. Tune `FanConfig`/`FacilityConfig`/`EconomyConfig`. Record BEFORE/AFTER in the retro.
- [ ] Permanent invariant: `test_v26_fan_income_never_rivals_prize_money`.

### Task 7.2: Golden-log re-derivation
- [ ] Re-derive development witnesses for facility-owning + mentored clubs; update golden logs in the same commit.

### Task 7.3: Full verification + docs
- [ ] `python -m pytest -q` green (real exit code, NOT `| tail`).
- [ ] `npm run build` + `npm run lint` clean.
- [ ] Live prod-server walk (port 8010): buy a facility, watch fans accrue with receipts across a season, see matchday/merch in the Recap, assign a bench role, resolve a media beat. Zero console errors; purge the walk save.
- [ ] Update `docs/STATUS.md` + `docs/specs/MILESTONES.md`; write `docs/retrospectives/2026-XX-XX-v26-the-crowd-retrospective.md`.
- [ ] Commit.

---

## Self-Review (spec coverage)

| Spec requirement | Task(s) |
|---|---|
| Revive facilities in the web dev path (the `()` fix) | 1.3 |
| Facilities → treasury sink + new types, modernized | 1.1, 1.2, 1.4 |
| Dead computed modifier fields consumed/removed | 1.1 (step 6) |
| Club fan ledger from real events, receipted | 2.2, 2.3 |
| Prestige growth ported to web | 2.3 |
| Player followings (MVP/records/milestones/district) | 3.1 |
| Matchday + merch income, meaningful margin | 4.1, 4.2, 7.1 |
| Bench roles (Mentor/Analyst/Ambassador), identity-traits consumer | 5.1–5.4 |
| Media mini-events, effects isolated to fans/prestige/credibility | 6.1, 6.2 |
| `_migrate_v19` fan tables (first Climb-Era migration) | 2.1 |
| Append-only fan ledger (no opaque scalar) | 2.2 |
| Pyramid-gated, legacy byte-identical | 1.3, 2.3, 4.2, 1.5 |
| Beat tuple + active-beats + `_MAX_OFFSEASON_BEAT_INDEX` together | 6.1 |
| Fan-income-margin invariant + facility/role probes | 7.1, 4.1, 5.3 |
| Golden-log updates on intentional dev changes | 1.5, 7.2 |

No placeholder steps remain in Phase 1 (fully concrete); Phases 2–7 name exact files, test targets, and signatures, with internal edits finalized against source at execution per phase (the large functions touched there — `apply_season_development`, `apply_season_finances`, `initialize_manager_offseason` — are read live per the repo's verify-before-editing rule).
