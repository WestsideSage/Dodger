"""V25 The Market — the single formula home for player contracts.

Pure functions only: no DB, no RNG side effects, config-driven (the
``staff_effects.py`` pattern). Amounts are integer thousands. Proposed
sim-design, tuned in Phase 7 against the squeeze-never-spiral invariant and the
poach/retention probe; never claimed as real-world fidelity.
"""
from __future__ import annotations

from typing import Iterable

from .config import DEFAULT_CONTRACTS, ContractConfig


def entry_salary_k(tier: int, config: ContractConfig = DEFAULT_CONTRACTS) -> int:
    """STANDARD entry deal: tier-standardized, ABILITY-BLIND.

    Takes no OVR by design — recruiting stays a courtship game; money enters a
    player's story at his second contract.
    """
    table = config.entry_salary_by_tier
    return int(table.get(tier, table[3]))


def entry_term(config: ContractConfig = DEFAULT_CONTRACTS) -> int:
    return int(config.entry_term)


def second_contract_salary_k(
    ovr: int, tier: int, config: ContractConfig = DEFAULT_CONTRACTS
) -> int:
    """Second deals price ability: floor + per_ovr*(OVR - pivot), x tier mult."""
    base = config.second_base_k + config.second_per_ovr_k * max(0, int(ovr) - config.second_ovr_pivot)
    mult = config.second_tier_multiplier.get(tier, 1.0)
    return max(config.second_base_k, round(base * mult))


def wage_bill_k(roster: Iterable, config: ContractConfig = DEFAULT_CONTRACTS) -> int:
    """Sum of active-player salaries (every Player carries salary_k)."""
    return sum(int(getattr(p, "salary_k", 0)) for p in roster)


def wage_budget_for_tier(tier: int, config: ContractConfig = DEFAULT_CONTRACTS) -> int:
    table = config.wage_budget_by_tier
    return int(table.get(tier, table[3]))


def buyout_fee_k(
    salary_k: int, term_remaining: int, config: ContractConfig = DEFAULT_CONTRACTS
) -> int:
    return round(config.buyout_fee_factor * int(salary_k) * max(1, int(term_remaining)))


def dev_compensation_k(
    salary_k: int, term_remaining: int, config: ContractConfig = DEFAULT_CONTRACTS
) -> int:
    return round(
        config.dev_compensation_fraction * buyout_fee_k(salary_k, term_remaining, config)
    )


__all__ = [
    "entry_salary_k",
    "entry_term",
    "second_contract_salary_k",
    "wage_bill_k",
    "wage_budget_for_tier",
    "buyout_fee_k",
    "dev_compensation_k",
]
