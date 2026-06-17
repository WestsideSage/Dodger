"""V25 The Market — Phase 1 contract foundation tests.

Pure-formula + Player-serialization round-trip coverage. DB-backed settlement /
entry-deal / backfill tests live alongside the later Phase 1 tasks once the
career fixtures are in place.
"""
from dodgeball_sim import contracts
from dodgeball_sim.config import DEFAULT_CONTRACTS as C
from dodgeball_sim.models import Player, PlayerRatings, PlayerArchetype


def _player(salary_k: int = 0, contract_term: int = 1) -> Player:
    return Player(
        id=f"p{salary_k}-{contract_term}",
        name="x",
        ratings=PlayerRatings(accuracy=60, power=60, dodge=60, catch=60),
        archetype=PlayerArchetype.THROWER,
        salary_k=salary_k,
        contract_term=contract_term,
    )


# --- contracts.py pure formulas -------------------------------------------------

def test_entry_salary_is_ability_blind_and_tier_standard():
    assert contracts.entry_salary_k(tier=3) == C.entry_salary_by_tier[3]
    assert contracts.entry_salary_k(tier=1) == C.entry_salary_by_tier[1]
    # entry deal takes no OVR argument at all — courtship, not money.


def test_entry_term_is_the_standard_default():
    assert contracts.entry_term() == C.entry_term


def test_second_contract_prices_ability_and_tier():
    low = contracts.second_contract_salary_k(ovr=70, tier=3)
    high = contracts.second_contract_salary_k(ovr=90, tier=1)
    assert high > low > 0
    # same OVR costs more in a higher tier.
    assert contracts.second_contract_salary_k(ovr=80, tier=1) > \
        contracts.second_contract_salary_k(ovr=80, tier=3)


def test_second_contract_floors_at_base_for_low_ovr():
    # below the pivot, the per-OVR term is clamped to 0 -> base * tier mult.
    assert contracts.second_contract_salary_k(ovr=40, tier=3) == C.second_base_k


def test_wage_bill_sums_active_roster_salaries():
    roster = [_player(salary_k=10), _player(salary_k=14), _player(salary_k=0)]
    assert contracts.wage_bill_k(roster) == 24


def test_wage_budget_is_tier_derived():
    assert contracts.wage_budget_for_tier(1) > contracts.wage_budget_for_tier(3)


def test_buyout_fee_scales_with_salary_term_and_factor():
    assert contracts.buyout_fee_k(salary_k=20, term_remaining=2) == round(
        C.buyout_fee_factor * 20 * 2
    )


def test_dev_compensation_is_a_modest_fraction_of_fee():
    fee = contracts.buyout_fee_k(salary_k=20, term_remaining=2)
    comp = contracts.dev_compensation_k(salary_k=20, term_remaining=2)
    assert comp == round(C.dev_compensation_fraction * fee)
    assert comp < fee


# --- Player serialization round-trip --------------------------------------------

def test_player_contract_fields_roundtrip_and_default():
    from dodgeball_sim.persistence import _player_to_dict, _player_from_dict

    p = _player(salary_k=18, contract_term=2)
    back = _player_from_dict(_player_to_dict(p))
    assert back.salary_k == 18 and back.contract_term == 2


def test_legacy_player_dict_without_contract_fields_defaults():
    # A pre-V25 blob (no salary_k/contract_term keys) must load, not raise.
    from dodgeball_sim.persistence import _player_from_dict, _player_to_dict

    blob = _player_to_dict(_player())
    del blob["salary_k"]
    del blob["contract_term"]
    back = _player_from_dict(blob)
    assert back.salary_k == 0 and back.contract_term == 1
