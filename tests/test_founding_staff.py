"""V22 Phase 3 — the founding staff market and the budgeted hiring step.

Owner: pick your initial six department heads from a generated pool under
the starting budget (Teamfight Manager-style stakes), instead of starting
with the same six hardcoded defaults forever.
"""
from __future__ import annotations

import sqlite3

import pytest

from dodgeball_sim.config import DEFAULT_ECONOMY
from dodgeball_sim.economy import staff_salary_k, treasury_k
from dodgeball_sim.save_service import (
    SaveServiceError,
    build_from_scratch_save,
    starting_prospects_payload,
    starting_staff_payload,
)
from dodgeball_sim.staff_market import (
    FOUNDING_DEPARTMENTS,
    generate_founding_staff_pool,
)


def _cheapest_per_department(pool):
    cheapest = {}
    for candidate in pool:
        dept = candidate["department"]
        if dept not in cheapest or candidate["salary_k"] < cheapest[dept]["salary_k"]:
            cheapest[dept] = candidate
    return cheapest


def test_founding_pool_is_deterministic_and_covers_every_department():
    a = generate_founding_staff_pool(123)
    b = generate_founding_staff_pool(123)
    c = generate_founding_staff_pool(456)
    assert a == b
    assert [x["name"] for x in a] != [x["name"] for x in c]
    assert len(a) == len(FOUNDING_DEPARTMENTS) * 3
    for dept in FOUNDING_DEPARTMENTS:
        tiers = {x["tier"] for x in a if x["department"] == dept}
        assert tiers == {"journeyman", "solid", "premium"}
    # Salaries are the economy formula, not invented numbers.
    for candidate in a:
        assert candidate["salary_k"] == staff_salary_k(
            candidate["rating_primary"], candidate["rating_secondary"]
        )


def test_filling_all_six_departments_is_always_affordable():
    """The affordability invariant: every department offers a journeyman, and
    six journeymen always fit the starting budget — the hiring step can never
    soft-lock the wizard."""
    for seed in (1, 7, 99, 20260611, 31337):
        pool = generate_founding_staff_pool(seed)
        cheapest = _cheapest_per_department(pool)
        assert set(cheapest) == set(FOUNDING_DEPARTMENTS)
        total = sum(c["salary_k"] for c in cheapest.values())
        assert total <= DEFAULT_ECONOMY.starting_budget_k, (
            f"seed {seed}: cheapest staff ${total}k exceeds the budget"
        )


def test_starting_staff_payload_carries_budget_and_rules():
    payload = starting_staff_payload(123)
    assert payload["budget_k"] == DEFAULT_ECONOMY.starting_budget_k
    assert payload["departments"] == list(FOUNDING_DEPARTMENTS)
    assert "treasury" in payload["rules"].lower()
    assert payload["mid_table_payout_k"] == 280
    assert len(payload["candidates"]) == 18


def _build_request(seed: int, name: str, staff_choices=None) -> dict:
    ids = [p["player_id"] for p in starting_prospects_payload(seed)["prospects"]][:6]
    request = {
        "save_name": name,
        "club_name": "Founders FC",
        "city": "Foundry",
        "colors": "teal/black",
        "coach_name": "Coach",
        "coach_backstory": "Builder",
        "roster_player_ids": ids,
        "root_seed": seed,
    }
    if staff_choices is not None:
        request["staff_choices"] = staff_choices
    return request


def test_build_writes_chosen_staff_and_prices_the_books(tmp_path):
    seed = 555
    pool = generate_founding_staff_pool(seed)
    # Splurge on tactics, journeyman everywhere else.
    choices = {
        c["department"]: c["candidate_id"]
        for c in _cheapest_per_department(pool).values()
    }
    premium_tactics = next(
        c for c in pool if c["department"] == "tactics" and c["tier"] == "premium"
    )
    choices["tactics"] = premium_tactics["candidate_id"]
    by_id = {c["candidate_id"]: c for c in pool}
    expected_payroll = sum(by_id[cid]["salary_k"] for cid in choices.values())

    result = build_from_scratch_save(
        tmp_path, _build_request(seed, "staffed", staff_choices=choices)
    )

    conn = sqlite3.connect(result["path"])
    conn.row_factory = sqlite3.Row
    try:
        heads = {
            row["department"]: row
            for row in conn.execute("SELECT * FROM department_heads")
        }
        assert heads["tactics"]["name"] == premium_tactics["name"]
        for dept, cid in choices.items():
            assert heads[dept]["name"] == by_id[cid]["name"]
        assert treasury_k(conn) == DEFAULT_ECONOMY.starting_budget_k - expected_payroll
    finally:
        conn.close()


def test_build_without_staff_choices_keeps_the_default_six(tmp_path):
    result = build_from_scratch_save(tmp_path, _build_request(777, "defaults"))
    conn = sqlite3.connect(result["path"])
    conn.row_factory = sqlite3.Row
    try:
        names = {
            row["department"]: row["name"]
            for row in conn.execute("SELECT department, name FROM department_heads")
        }
    finally:
        conn.close()
    assert names["tactics"] == "Mara Ives"  # the seeded default survives


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (lambda c: c.pop("medical"), "missing: medical"),
        (lambda c: c.update(medical="founding_tactics_solid"), "Unknown staff candidate"),
        (lambda c: c.update(janitorial="founding_tactics_solid"), "Unknown staff departments"),
    ],
)
def test_build_rejects_malformed_staff_choices_before_any_file(tmp_path, mutate, fragment):
    seed = 888
    pool = generate_founding_staff_pool(seed)
    choices = {
        c["department"]: c["candidate_id"]
        for c in _cheapest_per_department(pool).values()
    }
    mutate(choices)
    with pytest.raises(SaveServiceError, match=fragment):
        build_from_scratch_save(
            tmp_path, _build_request(seed, "badstaff", staff_choices=choices)
        )
    assert not list(tmp_path.glob("*.db")), "no save file may exist after a rejection"


def test_in_season_hiring_freezes_while_treasury_negative():
    from dodgeball_sim.career_setup import initialize_curated_manager_career
    from dodgeball_sim.dynasty_office import build_dynasty_office_state, hire_staff_candidate
    from dodgeball_sim.economy import set_treasury_k
    from dodgeball_sim.persistence import create_schema

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260611)
    conn.commit()

    candidate_id = build_dynasty_office_state(conn)["staff_market"]["candidates"][0][
        "candidate_id"
    ]
    set_treasury_k(conn, -25)
    with pytest.raises(ValueError, match="frozen"):
        hire_staff_candidate(conn, candidate_id)

    # Books recover -> the same hire goes through.
    set_treasury_k(conn, 60)
    updated = hire_staff_candidate(conn, candidate_id)
    assert updated["staff_market"]["recent_actions"][0]["candidate_id"] == candidate_id
