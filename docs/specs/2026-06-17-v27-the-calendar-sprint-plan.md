# V27 — The Calendar: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the season a calendar of real competitions — a revived cross-division Domestic Cup, cloth/no-sting ruleset invitationals (behind balance gates), Midseason International, the fan-invited Founders' Exhibition, and an elevated Worlds crowning ceremony — each a deterministic auto-simmed real-engine knockout with a trophy, purse, fans, and journalism, behind `pyramid_world_active` so legacy saves are byte-identical.

**Architecture:** Events resolve as deterministic auto-simmed knockouts at their thematic windows (decision 1 in the spec — NOT an in-season weekly-schedule rebuild). The dormant `cup.py` (kept import-pure) gets a web home in `cup_service.py`; a new `events.py` owns the event-result model + idempotent purses + event journalism; cloth/no-sting run through the existing `OfficialEngineAdapter` (no engine changes). New offseason beats (`events`, `worlds_champion`) surface results + the crowning ceremony.

**Tech Stack:** Python 3 (frozen dataclasses, SQLite, `dynasty_state` JSON, `rng.derive_seed`, `OfficialEngineAdapter`/`run_autonomous_match`), pytest; React + TS (no test runner — build/lint + Python guards).

**Spec:** `docs/specs/2026-06-17-v27-the-calendar-spec.md`. **Era authority:** `docs/specs/2026-06-12-climb-era-vision.md` § V27. **Branch:** `feature/v24-the-board`.

**Standing rules (hard-won this arc):**
- `python -m pytest -q` to a real exit code; **never pipe pytest to `tail`**.
- New `derive_seed` namespaces only (`v27_cup`, `v27_msi`, `v27_founders`, `v27_invitational`).
- `OFFSEASON_CEREMONY_BEATS` + active-beats + `persistence._MAX_OFFSEASON_BEAT_INDEX` change together (the V25/V26 clamp bug — now bit twice); update the pinned beat-tuple witness in `test_dispersed_helpers`.
- Pyramid-gate every event; verify legacy byte-identical.
- `cup.py` must stay import-pure (`test_cup_module_has_no_db_boundary_imports`) — DB/sim wiring lives in `cup_service.py`.
- `apply_event_purse` MUST be idempotent (`set_treasury_k` has no guard of its own — replicate the `FINANCES_APPLIED_KEY` pattern).

---

## File Structure

**New files:**
- `src/dodgeball_sim/events.py` — event-result model (`EventResult`, `EventBracketRow`), `apply_event_purse(conn, event_key, purse_k, season_id)` (idempotent), `record_event(conn, season_id, result)` / `load_events(conn, season_id)` (the `v27_events_json` store), `emit_event_news(...)`.
- `src/dodgeball_sim/cup_service.py` — the web cup home (DB + sim): `ensure_domestic_cup(conn, season_id, root_seed)` (generate the cross-division bracket), `resolve_domestic_cup(conn, season_id, root_seed)` (auto-sim to a champion via the real foam engine, award trophy + fans + purse + news). Imports `cup.py` (pure) + `persistence` cup functions; mirrors the CLI `_simulate_next_cup_round`/`_award_cup_champion_if_ready`.
- `src/dodgeball_sim/invitationals.py` — `run_invitational(conn, season_id, ruleset_selection, invitees, root_seed)` (auto-sim a knockout under a non-foam ruleset via `OfficialEngineAdapter`), `msi_invitees(conn, season_id)`, `founders_invitees(conn, season_id, top_n)`.
- `src/dodgeball_sim/config.py` — `EventConfig` / `DEFAULT_EVENTS` (purses, invite counts, fame/fan thresholds, warmth).
- `tools/cup_probe.py`, `tools/ruleset_balance_probe.py`, `tools/event_finance_probe.py`.
- `tests/test_v27_events.py`, `test_v27_cup.py`, `test_v27_ruleset_balance.py`, `test_v27_invitationals.py`, `test_v27_worlds_crowning.py`.
- `frontend/src/components/ceremonies/EventsBeat.tsx`, `WorldsCrowning.tsx`; an invitational/cup bracket display.

**Modified files:**
- `src/dodgeball_sim/offseason_ceremony.py` — `OFFSEASON_CEREMONY_BEATS` insert `events` (after recap-area) + `worlds_champion`; `compute_active_beats` conditionals; resolve the season's events at init (cache `v27_events_json`); the crowning-beat condition.
- `src/dodgeball_sim/persistence.py` — `_MAX_OFFSEASON_BEAT_INDEX` 11→13 (two new beats) + keep the guard test green.
- `src/dodgeball_sim/offseason_presentation.py`, `offseason_service.py`, `server.py` — `events` + `worlds_champion` beat payloads/text; any event endpoints.
- `src/dodgeball_sim/web_status_service.py` — widen `build_news_payload`'s `class_wire`-only category filter to include `event_news`.
- `frontend/src/{types.ts, components/Offseason.tsx}`.

---

## Phase 1 — Event foundation (purses + journalism + the `events` beat)

### Task 1.1: `EventConfig` + `events.py` purse/store/news (TDD)
- [ ] Add `EventConfig`/`DEFAULT_EVENTS` to `config.py` (purses by event tier-scaled, `founders_invite_count=5`, `invitational_fame_min`, prospect-showcase `warmth_credibility`).
- [ ] Failing tests (`tests/test_v27_events.py`): `apply_event_purse` credits the treasury once and is **idempotent** on a second call (its own `v27_<event>_purse_for` guard); `record_event`/`load_events` round-trip the per-season `v27_events_json`.
- [ ] Implement `events.py`; commit.

### Task 1.2: Widen the news filter (TDD)
- [ ] Failing test: a headline with `category='event_news'` is surfaced by `build_news_payload` (today it's dropped — only `class_wire` passes). Mirror existing `web_status_service` tests.
- [ ] Widen the filter (additive — `class_wire` still passes); commit.

### Task 1.3: The `events` offseason beat scaffold (TDD)
- [ ] `OFFSEASON_CEREMONY_BEATS` insert `events` (conditional — only when the season produced events); `compute_active_beats` gains `has_events`; bump `_MAX_OFFSEASON_BEAT_INDEX` 11→12 (this beat) and update the guard + pinned beat-tuple witness; `build_beat_payload`/`build_offseason_ceremony_beat` branches; cache the events state at init.
- [ ] Failing tests (`tests/test_v27_events.py` + the clamp/tuple witnesses): the beat appears when events exist, absent on legacy; clamp == len-1.
- [ ] Implement; full suite green; commit `feat(v27): event foundation — purses, journalism, events beat`.

---

## Phase 2 — Domestic Cup (revive `cup.py` in the web path)

### Task 2.1: `cup_service.ensure_domestic_cup` (TDD)
- [ ] Failing test (`tests/test_v27_cup.py`): on a pyramid career, `ensure_domestic_cup` generates + persists a cross-division bracket over ALL division clubs (`generate_cup_bracket`, `derive_seed(root_seed,'v27_cup',season_id)`, `cup_id='{season_id}_domestic_cup'`); idempotent; `cup.py` stays import-pure (the existing fence test still passes).
- [ ] Implement (reuse `save_cup_bracket`); commit.

### Task 2.2: `cup_service.resolve_domestic_cup` (TDD)
- [ ] Failing tests: auto-sim resolves the bracket to a single champion through the real foam engine (the CLI `_simulate_next_cup_round` is the reference — build `ScheduledMatch`/`simulate_match` per tie, pick winner, no draws); a lower-tier club can beat a higher-tier one (giant-killing happens across seeds); the champion gets a `trophy_type='cup'` trophy + `fans_cup` + a purse (idempotent) + a giant-killing news line. Foam only.
- [ ] Implement; wire `resolve_domestic_cup` into the offseason init events resolution (cache the bracket result in `v27_events_json`).
- [ ] `tools/cup_probe.py` (valid champion every seed; giant-killing rate > 0; determinism). Full suite green; commit `feat(v27): Domestic Cup — cross-division knockout revived in the web path`.

---

## Phase 3 — Ruleset balance gates (the V17 precedent)

### Task 3.1: Cloth + no-sting balance probes (TDD)
- [ ] `tools/ruleset_balance_probe.py`: for cloth and no-sting, run the foam-gate equivalents — archetype-champion parity (matched-OVR shapes, max win-share ≤ ~0.85, ≥3 distinct viable archetypes) + a decision-impact/health pass (displayed core skills are not liabilities; OVR curve has slope) + a full-run stability sweep (no crash across many seeded matches — the V17 `to_official_event` discretion regression).
- [ ] Failing permanent gates (`tests/test_v27_ruleset_balance.py`): cloth + no-sting pass the parity/health bars; record BEFORE and any retune AFTER in the eventual retro.
- [ ] Fix any imbalance found (retune the cloth/no-sting profile constants, with measurement); commit `feat(v27): per-ruleset balance gates (cloth + no-sting) before invitationals`.

---

## Phase 4 — Ruleset Invitationals (Cloth Classic / No-Sting Open)

### Task 4.1: `invitationals.run_invitational` (TDD)
- [ ] Failing tests (`tests/test_v27_invitationals.py`): `run_invitational(conn, season_id, RulesetSelection.OFFICIAL_CLOTH, invitees, root_seed)` auto-sims a knockout under cloth to a valid champion via `OfficialEngineAdapter` (and `OFFICIAL_NO_STING`); match-ids encode the round so the engine clock is right; the foam league/cup is untouched; `decide_cloth_game_by_active_count` is never called on a foam match.
- [ ] Implement; commit.

### Task 4.2: Invitational events wired (invite + purse + warmth) (TDD)
- [ ] Failing tests: the Cloth Classic / No-Sting Open invite by fame (prestige) + standing; champion gets a purse (idempotent) + a small prospect-showcase warmth (`warmth_credibility`, a one-season recruiting/fan bump in the V26 channels); the Phase-3 balance gates are a prerequisite. Resolve at the offseason events pass; cache in `v27_events_json`.
- [ ] Implement; full suite green; commit `feat(v27): ruleset invitationals — Cloth Classic / No-Sting Open`.

---

## Phase 5 — Midseason International + Founders' Exhibition

### Task 5.1: MSI (Premier + Circuit leaders) (TDD)
- [ ] Failing tests (`tests/test_v27_invitationals.py`): `msi_invitees` returns EXACTLY the Premier leader + the Circuit leader (`load_standings` ∩ `load_division_map` by `division_id` — NOT by `tier`, since both are tier 1); MSI runs a small foam knockout to a champion + prestige + purse + a Worlds-seeding note in `v27_events_json`.
- [ ] Implement; commit.

### Task 5.2: Founders' Exhibition (by fan count) (TDD)
- [ ] Failing tests: `founders_invitees(conn, season_id, top_n)` returns the top-N clubs by `fan_ledger.club_fans` (declared no-seeding, money only); a preseason auto-simmed knockout + a purse (idempotent); being beloved is the ticket.
- [ ] Implement; full suite green; commit `feat(v27): MSI + Founders' Exhibition (fan-invited)`.

---

## Phase 6 — Worlds crowning ceremony

### Task 6.1: The `worlds_champion` offseason beat (TDD)
- [ ] `OFFSEASON_CEREMONY_BEATS` insert `worlds_champion` (conditional — only when the user is the Worlds champion in the postseason ledger); bump `_MAX_OFFSEASON_BEAT_INDEX` 12→13 + guard + pinned witness; `build_beat_payload` reads the ledger / `worlds_history_json` (first-ever crown ⇒ `is_first` for the elevated treatment; later ⇒ defending-champion); text branch.
- [ ] Failing tests (`tests/test_v27_worlds_crowning.py`): the beat appears only for the Worlds champion; `is_first` true on the first crown, false after; absent for non-champions / legacy. Post-summit stays legacy play (no NG+/ratchet).
- [ ] Implement; full suite green; commit `feat(v27): Worlds crowning ceremony (first title = the save's crowning beat)`.

---

## Phase 7 — Frontend + verification + docs

### Task 7.1: Events beat + bracket displays + crowning ceremony (frontend)
- [ ] `EventsBeat.tsx` (event result cards: cup champion + giant-killings, invitational winners, MSI, Founders'), a cup/invitational bracket display (extend/clone `PlayoffBracket`), `WorldsCrowning.tsx` (`CeremonyShell` staged reveal, credits-roll energy on `is_first`); `types.ts` beat variants; `Offseason.tsx` dispatch. Pydantic response fields added before the FE reads them (the strip trap).
- [ ] `npm run build` + `npm run lint` clean; Python guards on the rendered event/crowning payloads. Commit.

### Task 7.2: Verification + docs
- [ ] `python -m pytest -q` green (real exit code, NOT `| tail`).
- [ ] `tools/{cup_probe,ruleset_balance_probe,event_finance_probe}.py` pass (event purses a margin of league payout; cup giant-killing; cloth/no-sting parity).
- [ ] Live prod-server walk: a season's events resolve (cup champion + a giant-killing, an invitational, MSI, Founders'), and a Worlds crowning fires on the first title. Zero console errors; purge the walk save.
- [ ] Update `docs/STATUS.md` + `docs/specs/MILESTONES.md`; write `docs/retrospectives/2026-XX-XX-v27-the-calendar-retrospective.md`.
- [ ] Commit.

---

## Self-Review (spec coverage)

| Spec requirement | Task(s) |
|---|---|
| Domestic Cup (cross-division, foam, knockout) revived in web | 2.1, 2.2 |
| `cup.py` stays import-pure; web home in `cup_service` | 2.1 |
| Ruleset Invitationals (cloth/no-sting) | 4.1, 4.2 |
| Balance gates BEFORE invitationals (V17 precedent) | 3.1 |
| MSI (Premier + Circuit leaders, by division_id) | 5.1 |
| Founders' Exhibition (by fan count, no-seeding) | 5.2 |
| Worlds crowning ceremony (first = crowning) | 6.1 |
| Events auto-simmed real-engine at windows (decision 1) | 2.2, 4.1, 5.1, 5.2 |
| Idempotent purses + event journalism (widened filter) | 1.1, 1.2 |
| `events` + `worlds_champion` beats + clamp/tuple updates | 1.3, 6.1 |
| Pyramid-gated, legacy byte-identical | 1.3, 2.2, 6.1, 7.2 |
| Calendar-integrity + declared-stakes + balance probes | 2.2, 3.1, 5.2, 7.2 |

No placeholder steps remain at the phase-task level; per-phase TDD code is finalized against source at execution (the large surfaces — `initialize_manager_offseason`, the CLI cup reference, `OfficialEngineAdapter`, `build_news_payload` — are read live per the verify-before-editing rule).
