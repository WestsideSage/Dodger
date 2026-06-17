# V25 — The Market: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every player a salary + contract term, settle a club wage bill each offseason, and add an offseason Transfer Period (re-sign / uphill poaching / buyouts) played symmetrically by the AI — money finally enters a player's story.

**Architecture:** A new pure-formula module (`contracts.py`) prices entry/second deals, wage budgets, buyout fees, and dev-comp from config knobs. A new orchestration module (`transfer_market.py`) builds the Transfer Period state by *reusing* the V24 motivation grades (`motivations.club_fit`) and the contested resolver (`recruitment_domain.resolve_recruitment_round`). `Player` gains two fields that ride the existing JSON-blob persistence with safe defaults (no player-field migration). A new gating offseason beat (`transfer_period`) hosts the interactive decisions. The entire layer is gated behind `world.pyramid_world_active()`; legacy/non-pyramid saves stay byte-identical.

**Tech Stack:** Python 3 (frozen dataclasses, SQLite KV via `persistence.get_state`/`set_state`, `rng.derive_seed` namespaced determinism), pytest; React + TypeScript frontend (no test runner — build/lint + data-flow + Python string guards).

**Spec:** `docs/specs/2026-06-17-v25-the-market-spec.md`. **Era authority:** `docs/specs/2026-06-12-climb-era-vision.md` § V25. **Build-state truth:** `docs/STATUS.md`.

**Branch:** `feature/v24-the-board` (Climb-Era arc merges to main as a unit).

**Standing rules (from AGENTS.md / repo law):**
- Run `python -m pytest -q` green before each commit; never `pytest | tail` (masks failures).
- New `derive_seed` namespaces only (`v25_contract`, `v25_transfer`, `v25_poach`); never touch `derive_seed(0, 'v24_motivation', id)` (root_seed is the literal `0`).
- New Player JSON fields read via `.get(..., default)` — never `d[...]` (legacy saves raise otherwise).
- Intentional outcome changes (player-blob fields, finances ledger) update golden logs in the same pass.
- Pyramid-gate everything; verify legacy single-league byte-identical.

---

## File Structure

**New files:**
- `src/dodgeball_sim/contracts.py` — pure salary/term/budget/fee formulas (the single formula home, `staff_effects.py` pattern). No DB, no RNG side effects.
- `src/dodgeball_sim/transfer_market.py` — Transfer Period orchestration: expiring-cohort detection, re-sign offers, poach resolution, buyouts, AI re-signing, the transfer ledger. Reads `contracts.py` + `motivations.py` + `recruitment_domain.py`.
- `tests/test_v25_contracts.py`, `tests/test_v25_retention.py`, `tests/test_v25_poaching.py`, `tests/test_v25_buyouts.py`, `tests/test_v25_transfer_beat.py`, `tests/test_v25_ai_symmetry.py`.
- `tools/poach_retention_probe.py`, `tools/roster_fortress_probe.py`.
- `frontend/src/components/ceremonies/TransferPeriod.tsx` — the new beat UI.

**Modified files:**
- `src/dodgeball_sim/models.py` — `Player` + `salary_k`, `contract_term`.
- `src/dodgeball_sim/persistence.py` — `_player_to_dict` / `_player_from_dict` (the only serialization boundary).
- `src/dodgeball_sim/config.py` — new `ContractConfig` + `DEFAULT_CONTRACTS`.
- `src/dodgeball_sim/economy.py` — `apply_season_finances` wage-bill outflow + `player_wage_bill_k` helper.
- `src/dodgeball_sim/offseason_ceremony.py` — term decrement (all-clubs loop), `OFFSEASON_CEREMONY_BEATS` insert, transfer-state compute + backfill in `initialize_manager_offseason`, AI re-sign + poach sweep, `compute_active_beats` conditional.
- `src/dodgeball_sim/offseason_presentation.py` — `build_beat_payload` `transfer_period` branch + finances wages line.
- `src/dodgeball_sim/offseason_service.py` — transfer action handlers + state transitions.
- `src/dodgeball_sim/career_state.py` — `SEASON_COMPLETE_TRANSFER_PENDING` + `_ALLOWED` edges.
- `src/dodgeball_sim/server.py` — transfer POST endpoints + Pydantic response fields.
- `frontend/src/components/Offseason.tsx`, `frontend/src/components/ceremonies/RecapStandings.tsx`, `frontend/src/components/Roster*.tsx` (salary surfacing), `frontend/src/api/client.ts`, `frontend/src/types.ts`.

---

## Phase 1 — Contracts foundation (data, entry deals, wage settlement)

*Everything downstream depends on these fields + the formula home. Fully concrete.*

### Task 1.1: `ContractConfig` knobs

**Files:**
- Modify: `src/dodgeball_sim/config.py` (after `DEFAULT_ECONOMY`, ~line 254)

- [ ] **Step 1: Add the config dataclass.** Insert after `DEFAULT_ECONOMY = EconomyConfig()`:

```python
@dataclass(frozen=True)
class ContractConfig:
    """V25 The Market — player contract knobs. Proposed sim-design; tuned in
    Phase 7 against the squeeze-never-spiral invariant and the poach/retention
    probe. Amounts are integer thousands; never claimed as real-world fidelity."""
    entry_term: int = 3
    # STANDARD entry deals: tier-standardized, ABILITY-BLIND (money enters at
    # the second contract). Keyed by tier (1=Premier, 2=Challenger, 3=District/Circuit default).
    entry_salary_by_tier: Mapping[int, int] = field(
        default_factory=lambda: {1: 22, 2: 14, 3: 8}
    )
    # Second contracts price ability: floor + per_ovr*(OVR - pivot), x tier mult.
    second_base_k: int = 8
    second_per_ovr_k: float = 0.8
    second_ovr_pivot: int = 60
    second_tier_multiplier: Mapping[int, float] = field(
        default_factory=lambda: {1: 1.8, 2: 1.35, 3: 1.0}
    )
    second_term_default: int = 3
    # AI wage BUDGET caps (no balance tracked) — gate poach/re-sign aggression.
    wage_budget_by_tier: Mapping[int, int] = field(
        default_factory=lambda: {1: 420, 2: 240, 3: 140}
    )
    # Buyout fee / AI asking price = factor * salary * term_remaining.
    buyout_fee_factor: float = 2.0
    # Dev-compensation credit when a homegrown player is poached (fraction of fee).
    dev_compensation_fraction: float = 0.5


DEFAULT_CONTRACTS = ContractConfig()
```

- [ ] **Step 2: Ensure imports.** Confirm `from dataclasses import dataclass, field` and `from typing import Mapping` are present at the top of `config.py`; add `field` / `Mapping` to the existing import lines if missing.

- [ ] **Step 3: Export.** Add `"ContractConfig"` and `"DEFAULT_CONTRACTS"` to `config.py`'s `__all__`.

- [ ] **Step 4: Commit.**
```bash
git add src/dodgeball_sim/config.py
git commit -m "feat(v25): ContractConfig knobs (entry/second salaries, wage budgets, buyout fee)"
```

### Task 1.2: `contracts.py` pure formulas (TDD)

**Files:**
- Create: `src/dodgeball_sim/contracts.py`
- Test: `tests/test_v25_contracts.py`

- [ ] **Step 1: Write failing tests.**
```python
# tests/test_v25_contracts.py
from dodgeball_sim import contracts
from dodgeball_sim.config import DEFAULT_CONTRACTS as C


def test_entry_salary_is_ability_blind_and_tier_standard():
    # Two prospects of very different OVR sign IDENTICAL entry salaries at a tier.
    assert contracts.entry_salary_k(tier=3) == C.entry_salary_by_tier[3]
    assert contracts.entry_salary_k(tier=1) == C.entry_salary_by_tier[1]
    # entry deal does not take an OVR argument at all — courtship, not money.


def test_entry_term_is_the_standard_default():
    assert contracts.entry_term() == C.entry_term


def test_second_contract_prices_ability_and_tier():
    low = contracts.second_contract_salary_k(ovr=70, tier=3)
    high = contracts.second_contract_salary_k(ovr=90, tier=1)
    assert high > low > 0
    # tier multiplier applies: same OVR costs more in a higher tier.
    assert contracts.second_contract_salary_k(ovr=80, tier=1) > \
           contracts.second_contract_salary_k(ovr=80, tier=3)


def test_wage_bill_sums_active_roster_salaries():
    roster = [_player(salary_k=10), _player(salary_k=14), _player(salary_k=0)]
    assert contracts.wage_bill_k(roster) == 24


def test_wage_budget_is_tier_derived():
    assert contracts.wage_budget_for_tier(1) > contracts.wage_budget_for_tier(3)


def test_buyout_fee_scales_with_salary_term_and_factor():
    fee = contracts.buyout_fee_k(salary_k=20, term_remaining=2)
    assert fee == round(C.buyout_fee_factor * 20 * 2)


def test_dev_compensation_is_a_modest_fraction_of_fee():
    fee = contracts.buyout_fee_k(salary_k=20, term_remaining=2)
    comp = contracts.dev_compensation_k(salary_k=20, term_remaining=2)
    assert comp == round(C.dev_compensation_fraction * fee)
    assert comp < fee


def _player(salary_k):
    from dodgeball_sim.models import Player, PlayerRatings, PlayerArchetype
    return Player(
        id=f"p{salary_k}", name="x",
        ratings=PlayerRatings(accuracy=60, power=60, dodge=60, catch=60),
        archetype=PlayerArchetype.BALANCED, salary_k=salary_k,
    )
```

- [ ] **Step 2: Run, verify fail.** `python -m pytest tests/test_v25_contracts.py -q` → FAIL (module/fields not defined). (Player `salary_k` arrives in Task 1.3 — these will also drive that; if collection errors on the field, complete Task 1.3 first, then return. The two tasks are a pair.)

- [ ] **Step 3: Implement `contracts.py`.**
```python
"""V25 The Market — the single formula home for player contracts.

Pure functions only: no DB, no RNG side effects, config-driven (the
``staff_effects.py`` pattern). Amounts are integer thousands. Proposed
sim-design, tuned in Phase 7; never claimed as real-world fidelity.
"""
from __future__ import annotations

from typing import Iterable

from .config import DEFAULT_CONTRACTS, ContractConfig


def entry_salary_k(tier: int, config: ContractConfig = DEFAULT_CONTRACTS) -> int:
    """STANDARD entry deal: tier-standardized, ability-blind."""
    return int(config.entry_salary_by_tier.get(tier, config.entry_salary_by_tier[3]))


def entry_term(config: ContractConfig = DEFAULT_CONTRACTS) -> int:
    return int(config.entry_term)


def second_contract_salary_k(
    ovr: int, tier: int, config: ContractConfig = DEFAULT_CONTRACTS
) -> int:
    """Second deals price ability: floor + per_ovr*(OVR - pivot), x tier mult."""
    base = config.second_base_k + config.second_per_ovr_k * max(0, ovr - config.second_ovr_pivot)
    mult = config.second_tier_multiplier.get(tier, 1.0)
    return max(config.second_base_k, round(base * mult))


def wage_bill_k(roster: Iterable, config: ContractConfig = DEFAULT_CONTRACTS) -> int:
    """Sum of active-player salaries (every Player carries salary_k)."""
    return sum(int(getattr(p, "salary_k", 0)) for p in roster)


def wage_budget_for_tier(tier: int, config: ContractConfig = DEFAULT_CONTRACTS) -> int:
    return int(config.wage_budget_by_tier.get(tier, config.wage_budget_by_tier[3]))


def buyout_fee_k(
    salary_k: int, term_remaining: int, config: ContractConfig = DEFAULT_CONTRACTS
) -> int:
    return round(config.buyout_fee_factor * int(salary_k) * max(1, int(term_remaining)))


def dev_compensation_k(
    salary_k: int, term_remaining: int, config: ContractConfig = DEFAULT_CONTRACTS
) -> int:
    return round(config.dev_compensation_fraction * buyout_fee_k(salary_k, term_remaining, config))
```

- [ ] **Step 4: Run, verify pass.** `python -m pytest tests/test_v25_contracts.py -q` → PASS (after Task 1.3 lands the `salary_k` field).

- [ ] **Step 5: Commit.**
```bash
git add src/dodgeball_sim/contracts.py tests/test_v25_contracts.py
git commit -m "feat(v25): contracts.py pure formula home + tests"
```

### Task 1.3: `Player` gains `salary_k` + `contract_term` (TDD)

**Files:**
- Modify: `src/dodgeball_sim/models.py:150-159` (the `Player` dataclass)
- Modify: `src/dodgeball_sim/persistence.py:91-117` (`_player_to_dict`) and `:154-...` (`_player_from_dict` Player construction)
- Test: `tests/test_v25_contracts.py` (add round-trip cases)

- [ ] **Step 1: Write failing round-trip test.**
```python
# add to tests/test_v25_contracts.py
def test_player_contract_fields_roundtrip_and_default():
    from dodgeball_sim.persistence import _player_to_dict, _player_from_dict
    from dodgeball_sim.models import Player, PlayerRatings, PlayerArchetype
    p = Player(id="z", name="Z",
               ratings=PlayerRatings(accuracy=60, power=60, dodge=60, catch=60),
               archetype=PlayerArchetype.BALANCED, salary_k=18, contract_term=2)
    back = _player_from_dict(_player_to_dict(p))
    assert back.salary_k == 18 and back.contract_term == 2


def test_legacy_player_dict_without_contract_fields_defaults():
    # A pre-V25 blob (no salary_k/contract_term keys) must load, not raise.
    from dodgeball_sim.persistence import _player_from_dict, _player_to_dict
    from dodgeball_sim.models import Player, PlayerRatings, PlayerArchetype
    p = Player(id="z", name="Z",
               ratings=PlayerRatings(accuracy=60, power=60, dodge=60, catch=60),
               archetype=PlayerArchetype.BALANCED)
    blob = _player_to_dict(p)
    del blob["salary_k"]; del blob["contract_term"]
    back = _player_from_dict(blob)
    assert back.salary_k == 0 and back.contract_term == 1
```

- [ ] **Step 2: Run, verify fail.** `python -m pytest tests/test_v25_contracts.py::test_player_contract_fields_roundtrip_and_default -q` → FAIL (`unexpected keyword argument 'salary_k'`).

- [ ] **Step 3: Add fields to `Player`** (`models.py`, after `newcomer: bool = True`):
```python
    salary_k: int = 0
    contract_term: int = 1
```

- [ ] **Step 4: Extend `_player_to_dict`** (`persistence.py`, in the returned dict, after `"newcomer": ...`):
```python
        "salary_k": player.salary_k,
        "contract_term": player.contract_term,
```

- [ ] **Step 5: Extend `_player_from_dict`** Player construction (after `newcomer=d.get("newcomer", True),`):
```python
        salary_k=d.get("salary_k", 0),
        contract_term=d.get("contract_term", 1),
```

- [ ] **Step 6: Run, verify pass.** `python -m pytest tests/test_v25_contracts.py -q` → PASS (all, including Task 1.2).

- [ ] **Step 7: Full-suite guard (witness check).** `python -m pytest -q`. Adding JSON keys may shift player-blob fixture witnesses. If any fail on the new keys, they are an **intentional outcome change** — re-derive the golden values and note in the Phase 7 retro. Fix and re-run green.

- [ ] **Step 8: Commit.**
```bash
git add src/dodgeball_sim/models.py src/dodgeball_sim/persistence.py tests/test_v25_contracts.py
git commit -m "feat(v25): Player.salary_k + contract_term (JSON blob, legacy-default safe)"
```

### Task 1.4: Wage bill in `apply_season_finances` (TDD)

**Files:**
- Modify: `src/dodgeball_sim/economy.py` (add `player_wage_bill_k` helper + wage line in `apply_season_finances:152-248`)
- Test: `tests/test_v25_contracts.py`

- [ ] **Step 1: Write failing test** (uses an in-memory pyramid save helper from the existing test utils — mirror an existing `test_economy.py` fixture that builds a pyramid career, sets a user roster with salaries, runs `apply_season_finances`, and asserts the ledger):
```python
def test_wage_bill_is_a_settlement_outflow_on_pyramid_saves(pyramid_conn_with_user_roster):
    conn, season_id, club_id, standings = pyramid_conn_with_user_roster(
        salaries=[10, 14, 8, 8, 8, 8]  # wage bill 56
    )
    from dodgeball_sim import economy
    ledger = economy.apply_season_finances(
        conn, season_id=season_id, club_id=club_id, standings=standings
    )
    assert ledger["player_wage_bill_k"] == 56
    # net subtracts wages alongside staff payroll
    assert ledger["net_k"] == (
        ledger["league_payout_k"] + ledger["playoff_bonus_k"]
        - ledger["staff_payroll_k"] - ledger["player_wage_bill_k"]
    )


def test_legacy_nonpyramid_save_has_no_wage_bill(flat_conn_with_user_roster):
    # Non-pyramid save: byte-identical, no wage line.
    conn, season_id, club_id, standings = flat_conn_with_user_roster()
    from dodgeball_sim import economy
    ledger = economy.apply_season_finances(
        conn, season_id=season_id, club_id=club_id, standings=standings
    )
    assert ledger.get("player_wage_bill_k", 0) == 0
```
*(If `test_economy.py` lacks reusable fixtures, add `pyramid_conn_with_user_roster` / `flat_conn_with_user_roster` to `tests/conftest.py` building on the existing pyramid-career test helpers — reuse, do not reinvent, the V23 `tests/test_v23_world.py` career-builder.)*

- [ ] **Step 2: Run, verify fail.** → FAIL (`KeyError: 'player_wage_bill_k'`).

- [ ] **Step 3: Add helper** to `economy.py`:
```python
def player_wage_bill_k(conn: sqlite3.Connection, club_id: str) -> int:
    """Sum of the club's active-roster salaries (0 on non-pyramid saves)."""
    from .world import pyramid_world_active
    if not pyramid_world_active(conn):
        return 0
    from .persistence import load_club_roster
    from .contracts import wage_bill_k
    roster = load_club_roster(conn, club_id) or []
    return wage_bill_k(roster)
```
*(Confirm the real roster loader name via `persistence.py`; the map cites `club_rosters` — use the existing `load_club_roster`/equivalent, do not add a new one.)*

- [ ] **Step 4: Wire into `apply_season_finances`** — after `payroll = staff_payroll_k(conn, config)` (line 206):
```python
    wage_bill = player_wage_bill_k(conn, club_id)
```
change `net` (line 208) to:
```python
    net = league_payout_k + playoff_bonus_k - payroll - wage_bill
```
and add to the `ledger` dict (after `"staff_payroll_k": payroll,`):
```python
        "player_wage_bill_k": wage_bill,
```

- [ ] **Step 5: Run, verify pass.** `python -m pytest tests/test_v25_contracts.py -q` → PASS.

- [ ] **Step 6: Full suite + economy witnesses.** `python -m pytest -q`. `test_economy.py` ledger witnesses now carry `player_wage_bill_k=0` for non-pyramid fixtures (additive, should pass); any pyramid finance witness is an intentional change — re-pin. Green before commit.

- [ ] **Step 7: Commit.**
```bash
git add src/dodgeball_sim/economy.py tests/test_v25_contracts.py tests/conftest.py
git commit -m "feat(v25): player wage bill as apply_season_finances outflow (pyramid-gated)"
```

### Task 1.5: Entry deals at signing + one-time backfill

**Files:**
- Modify: `src/dodgeball_sim/recruitment.py` (`sign_prospect_to_club` — assign entry deal as the prospect becomes a Player)
- Modify: `src/dodgeball_sim/offseason_ceremony.py` (`initialize_manager_offseason` — backfill pass guarded by `v25_contracts_seeded_for`)
- Test: `tests/test_v25_contracts.py`

- [ ] **Step 1: Failing test — new signings get the tier-standard entry deal:**
```python
def test_new_signing_gets_tier_standard_entry_deal(pyramid_career_d3):
    conn, ... = pyramid_career_d3
    # sign a prospect via the real commit path; assert the rostered Player:
    signed = ...  # locate via roster after sign_prospect_to_club
    from dodgeball_sim.contracts import entry_salary_k, entry_term
    assert signed.salary_k == entry_salary_k(tier=3)
    assert signed.contract_term == entry_term()
```

- [ ] **Step 2: Failing test — backfill prices existing roster once, deterministically:**
```python
def test_backfill_prices_existing_roster_once(pyramid_career_midsave):
    conn, club_id = pyramid_career_midsave  # roster with salary_k==0
    from dodgeball_sim.offseason_ceremony import _seed_v25_contracts  # new helper
    _seed_v25_contracts(conn, season_id="season_3")
    roster = load_club_roster(conn, club_id)
    assert all(p.salary_k > 0 for p in roster)        # priced
    assert len(set(p.contract_term for p in roster)) > 1   # terms spread, not all equal
    before = [p.salary_k for p in roster]
    _seed_v25_contracts(conn, season_id="season_3")   # idempotent
    assert [p.salary_k for p in load_club_roster(conn, club_id)] == before
```

- [ ] **Step 3: Run, verify fail.**

- [ ] **Step 4: Implement entry-deal assignment in `sign_prospect_to_club`** — at the point the `Player` is constructed from `hidden_ratings`, set `salary_k=contracts.entry_salary_k(tier)` and `contract_term=contracts.entry_term()` (resolve the signing club's tier via `load_division_map`). Use `dataclasses.replace` if the Player is built first. Gate on `pyramid_world_active` (legacy signings stay term=1/salary=0 default).

- [ ] **Step 5: Implement `_seed_v25_contracts(conn, season_id)`** in `offseason_ceremony.py`: guarded by `get_state(conn, "v25_contracts_seeded_for")`; for every club's every player with `salary_k == 0`, price via `contracts.second_contract_salary_k(p.overall_skill(), tier)` and assign a spread `contract_term` from a `derive_seed(root_seed, "v25_contract", player_id)` draw in `[1..entry_term]`; persist rosters; set the sentinel. Call it inside `initialize_manager_offseason` **before** `offseason_initialized_for` is written, only when `pyramid_world_active`.

- [ ] **Step 6: Run, verify pass.**

- [ ] **Step 7: Full suite.** `python -m pytest -q` green.

- [ ] **Step 8: Commit.**
```bash
git add -A
git commit -m "feat(v25): tier-standard entry deals at signing + one-time roster backfill"
```

### Task 1.6: Phase 1 verification gate

- [ ] Run `python -m pytest -q` → all green.
- [ ] Confirm a non-pyramid (legacy) career save is byte-identical (no wage line; player blobs default). Add `tests/test_v25_contracts.py::test_legacy_world_unchanged` asserting a flat-world finances ledger has no `player_wage_bill_k` effect and players load with defaults.
- [ ] Commit any witness re-pins with message `test(v25): re-pin player-blob/finances witnesses for contract fields (intentional)`.

---

## Phase 2 — Contract aging, expiry, retention (re-sign), user side

### Task 2.1: Term decrement in the all-clubs offseason loop (TDD)
**Files:** Modify `offseason_ceremony.py` (`initialize_manager_offseason` all-clubs loop); Test `tests/test_v25_retention.py`.
- [ ] Failing test: after one offseason init, every active player's `contract_term` decreased by 1 (floored at 0); keyed on numeric season order (`game_loop.season_sort_key`), not lexical.
- [ ] Implement: in the existing per-club/per-player loop (where development+aging already iterate), decrement `contract_term` via `dataclasses.replace`, gated by `pyramid_world_active`, on a season-scoped idempotency guard `v25_term_decremented_for` (do NOT reuse the dev/finances guards). Persist rosters.
- [ ] Full suite green. Commit `feat(v25): contract term decrements each offseason (pyramid-gated, idempotent)`.

### Task 2.2: Expiring-cohort detection in `transfer_market.py` (TDD)
**Files:** Create `transfer_market.py`; Test `tests/test_v25_retention.py`.
- [ ] Failing test for `transfer_market.expiring_players(conn, club_id) -> list[Player]` returning players with `contract_term <= 0`.
- [ ] Implement the pure-ish reader (loads roster, filters). Commit.

### Task 2.3: Retention offer priced by motivation grades (TDD)
**Files:** `transfer_market.py`; Test `tests/test_v25_retention.py`.
- [ ] **Failing traceability test** (the load-bearing proof): two identical players, one whose own club grades **A on Contender/Court-Time** and one graded **D**, at equal re-sign money — the A-grade player re-signs (willingness ≥ threshold) and the D-grade one does not. Build the context with `motivations.build_club_context(conn, club_id, season_id)` and grade with `motivations.club_fit(ctx, player)`.
- [ ] Implement `transfer_market.resign_willingness(conn, club_id, player, offer_salary_k, offer_term) -> ResignOutcome` reusing `club_fit` (the same dealbreaker veto applies) and a `_user_offer_strength`-analog (loyalty interest from fit + the offer). Second-contract salary floor from `contracts.second_contract_salary_k`.
- [ ] Full suite green. Commit `feat(v25): retention re-sign willingness via V24 motivation grades`.

### Task 2.4: Retention state cached in offseason init
**Files:** `offseason_ceremony.py`, `transfer_market.py`; Test `tests/test_v25_transfer_beat.py`.
- [ ] Compute the user's expiring cohort + per-player re-sign context and cache `v25_transfer_state_json` in `dynasty_state` inside `initialize_manager_offseason` (first-call path, before the sentinel). Test the round-trip + idempotency.
- [ ] Commit.

---

## Phase 3 — Uphill poaching (AI hunts the user's expiring stars)

### Task 3.1: Uphill poach eligibility + interest (TDD)
**Files:** `transfer_market.py` (`poach_suitors(conn, season_id, player)`); Test `tests/test_v25_poaching.py`.
- [ ] Failing tests: only **higher-tier** AI clubs **with wage headroom** (`contracts.wage_budget_for_tier(tier) - current_bill >= estimated_wage`) appear as suitors; lower/equal-tier clubs never poach up; suitor interest reuses `prospect_market.derive_club_pursuit` on the `v25_poach` stream (substituting player OVR). Deterministic per `(player, club)`.
- [ ] Implement; reuse the `_eligible_ai_offer_clubs` shape (extended with the headroom check). Commit.

### Task 3.2: Poach vs retention resolution + receipts (TDD)
**Files:** `transfer_market.py`; Test `tests/test_v25_poaching.py`.
- [ ] **Failing traceability test:** a player with a strong Contender grade for the user's club **stays** even when a rival's raw bid is higher (motivations break ties); a weak-grade player **leaves** even when the user's bid is competitive. Resolution via `recruitment_domain.resolve_recruitment_round` (user retention offer vs poach offers on the same offer-strength field).
- [ ] **Failing receipt test:** a departure produces a receipt string derivable from data — the outbid ratio + the losing grade ("outbid ×2.1, your Contender grade is D").
- [ ] Implement `transfer_market.resolve_poaching(...)`. Commit.

### Task 3.3: Dev-compensation credit on homegrown departures (TDD)
**Files:** `transfer_market.py`, treasury via `economy.set_treasury_k`; Test `tests/test_v25_poaching.py`.
- [ ] Failing test: when a homegrown player leaves, treasury gains `contracts.dev_compensation_k(...)` (income, < buyout fee). Newcomer/homegrown flag derivation: signed by the user club (track via a `signed_by` tag or `newcomer`+roster history — resolve at implementation against the real signing record).
- [ ] Implement + commit.

---

## Phase 4 — Buyouts (incoming refusable, outgoing bids)

### Task 4.1: Incoming buyout offers you can refuse (TDD)
**Files:** `transfer_market.py`; Test `tests/test_v25_buyouts.py`.
- [ ] Failing tests: an AI club generates a buyout offer on a user's **contracted** (non-expiring) player (deterministic, `v25_transfer` stream); **refuse** keeps player + wage unchanged; **accept** removes the player, credits `contracts.buyout_fee_k` to treasury, frees the wage. No mid-season path (only callable in the transfer beat).
- [ ] Implement `incoming_buyout_offers(...)`, `accept_buyout(...)`, `refuse_buyout(...)`. Commit.

### Task 4.2: Outgoing buyout bids vs AI asking prices (TDD)
**Files:** `transfer_market.py`; Test `tests/test_v25_buyouts.py`.
- [ ] Failing tests: user bid ≥ AI asking price (`contracts.buyout_fee_k` on the target) **and** treasury covers it **and** resulting wage bill within reason → transfer succeeds (player joins user roster at his contract, treasury debited); under-price/under-funded → refused. Rich-club privilege: a broke club cannot bid.
- [ ] Implement `outgoing_bid(...)`. Commit.

---

## Phase 5 — AI symmetry + news fodder

### Task 5.1: AI re-signs its own expiring players (TDD)
**Files:** `offseason_ceremony.py` (new AI transfer sweep, guarded by `v25_poach_done_for`), `transfer_market.py`; Test `tests/test_v25_ai_symmetry.py`.
- [ ] Failing tests: AI clubs re-sign expiring players they grade well + can afford; let walk those they can't afford or grade poorly (wage budget binds). Real roster deltas, deterministic. Runs after Signing Day equivalents without double-firing (own idempotency guard, not `offseason_ai_signings_done_for`).
- [ ] Implement `transfer_market.run_ai_transfer_period(conn, season_id)`; call it from the offseason sweep alongside `ensure_ai_offseason_signings`. Commit.

### Task 5.2: Roster-fortress invariant + transfer ledger (TDD)
**Files:** `transfer_market.py` (`v25_transfers_json` ledger), `tools/roster_fortress_probe.py`; Test `tests/test_v25_ai_symmetry.py`.
- [ ] Failing test: across an offseason, total league veteran movement (re-signs that changed terms + poaches + buyouts) > 0; the ledger records each move with a data-derived receipt.
- [ ] Implement the ledger write at each resolution chokepoint. Commit.

### Task 5.3: Class-wire-style news line on notable transfers
**Files:** reuse the V24 `news_headlines` chokepoint; Test `tests/test_v25_ai_symmetry.py`.
- [ ] Failing test: a notable poach/transfer emits a league-wide news line derivable from the ledger. Implement + commit.

### Task 5.4: `tools/poach_retention_probe.py`
- [ ] Build the probe: across seeds, show grades flip poach/retention outcomes (the spec's headline proof). Record BEFORE/AFTER in the retro. Commit.

---

## Phase 6 — Frontend Transfer Period UI + contract surfacing

### Task 6.1: Beat plumbing (backend → payload → state)
**Files:** `offseason_ceremony.py` (`OFFSEASON_CEREMONY_BEATS` insert `transfer_period` after `retirements`; `compute_active_beats` conditional — suppress when no actionable contracts), `career_state.py` (`SEASON_COMPLETE_TRANSFER_PENDING` + `_ALLOWED` edges modeled on `recruitment`), `offseason_presentation.py` (`build_beat_payload` branch + `build_offseason_ceremony_beat` text branch), `offseason_service.py` (action handlers + transitions), `server.py` (POST endpoints + Pydantic fields), `types.ts` (new beat variant + payload).
- [ ] Backend tests in `tests/test_v25_transfer_beat.py`: beat appears in the active sequence at the right index on a pyramid save with expiring players; absent on legacy; the `resolve all / auto` path advances the state; mandatory decisions gate advancement (recruitment-style). Add the Pydantic response fields **before** the FE reads them (response_model strip trap).
- [ ] Commit.

### Task 6.2: `TransferPeriod.tsx` + Offseason wiring
**Files:** `frontend/src/components/ceremonies/TransferPeriod.tsx` (new), `Offseason.tsx` (beat dispatch), `frontend/src/api/client.ts` (typed POST methods following `hireStaff`/`recruit`), `types.ts`.
- [ ] Render re-sign cards, incoming-buyout accept/refuse, outgoing-bid action, departures-with-receipts strip; optimistic-revert pattern from `ProspectCard`; `setBeat` on server response (never local mutation of ceremony beats).
- [ ] `npm run build` + `npm run lint` clean. Commit.

### Task 6.3: Salary/term on roster + cards; wages line in Finances
**Files:** `RecapStandings.tsx` (wages line from `finances.player_wage_bill_k`), roster/player card components, `money.ts` (`formatK`, integer-thousands).
- [ ] Surface `salary_k` / `contract_term` (guard optional fields like `treasury_k` is guarded). Backend Pydantic fields added first.
- [ ] `npm run build` + `npm run lint` clean. Python guard test asserting the rendered finances payload carries the wages key. Commit.

---

## Phase 7 — Balance pass + probes + verification

### Task 7.1: Tune + pin constants
- [ ] Run `tools/poach_retention_probe.py`, `tools/roster_fortress_probe.py`, and a squeeze-never-spiral run over ~8 seasons (founded D3 → promotion). Tune `ContractConfig` so: entry deals stay cheap, second contracts bite, promotion inflates payroll **without** a multi-season negative spiral (the V23 −217k precedent), and league veteran movement > 0/offseason. Record BEFORE/AFTER in the retro.
- [ ] Add permanent invariant tests: `test_v25_squeeze_never_spirals` (no save goes negative for ≥3 consecutive offseasons from wages alone), `test_v25_roster_fortress` (movement > 0).

### Task 7.2: Golden-log re-derivation
- [ ] Re-derive any witnesses moved by the player-blob fields + finances ledger; update golden logs in the same commit with a note.

### Task 7.3: Full verification + docs
- [ ] `python -m pytest -q` green (real exit code, not `| tail`).
- [ ] `npm run build` + `npm run lint` clean.
- [ ] Live prod-server browser walk (port 8010, not 8000 — the owner's game): founded D3 career across several seasons — re-sign a star, lose one to an uphill poach (verify the receipt), refuse an incoming buyout, see the wages line in Finances. Zero console errors; purge the walk save.
- [ ] Update `docs/STATUS.md` + `docs/specs/MILESTONES.md`; write `docs/retrospectives/2026-XX-XX-v25-the-market-retrospective.md` with measurements + disclosed deferrals.
- [ ] Commit.

---

## Self-Review (spec coverage)

| Spec requirement | Task(s) |
|---|---|
| `salary_k` + `contract_term` on Player, no migration | 1.3 |
| STANDARD ability-blind entry deals | 1.2 (formula), 1.5 (assignment) |
| Wage bill as settlement outflow, MODERATE squeeze | 1.4, 7.1 |
| One-time deterministic backfill | 1.5 |
| Term decrement / expiry (numeric season order) | 2.1 |
| Retention = recruiting's mirror (reuse `club_fit`) | 2.3 |
| Second-contract salaries price ability | 1.2, 2.3 |
| Uphill poaching, motivations break ties, receipts | 3.1, 3.2 |
| Dev-compensation credit | 3.3 |
| Incoming refusable buyouts / outgoing bids | 4.1, 4.2 |
| AI symmetry (re-sign, wage-budget churn) | 5.1 |
| Roster-fortress invariant + ledger | 5.2, 7.1 |
| News line on notable moves | 5.3 |
| Gating `transfer_period` beat (new CareerState) | 6.1 |
| Transfer Period UI + contract surfacing | 6.2, 6.3 |
| poach/retention + squeeze-never-spiral probes | 5.4, 7.1 |
| AI wage-budget cap (not full treasuries) | 1.1, 3.1, 5.1 |
| Behind `pyramid_world_active`, legacy byte-identical | 1.3–1.5, 2.1, 1.6 |
| Golden-log updates on intentional changes | 1.3, 1.4, 7.2 |

No placeholder steps remain in Phase 1 (fully concrete); Phases 2–7 name exact files, test targets, and signatures, with internal edits finalized against source at execution per phase (the functions modified there — `initialize_manager_offseason`, `resolve_recruitment_round`, `build_beat_payload` — are large and must be read live, per the repo's "verify current names before editing" rule).
