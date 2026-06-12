"""V22 Phase 1 — the shared wide name pools and the founding-pool seed.

Owner: "We need a much wider breadth of recruit names… many of these older
systems have not been touched literally since the game was first
brainstormed." One module (names.py) now feeds prospects, rookies and staff;
the founding draft pool is seeded per creation instead of being the same 25
prospects forever; founders carry natural ceilings + growth arcs.
"""
from __future__ import annotations

from dodgeball_sim.names import FIRST_NAMES, LAST_NAMES, unique_full_name
from dodgeball_sim.rng import DeterministicRNG


def test_pools_are_wide_and_duplicate_free():
    assert len(FIRST_NAMES) >= 160, "first-name pool must stay wide"
    assert len(LAST_NAMES) >= 280, "last-name pool must stay wide"
    assert len(set(FIRST_NAMES)) == len(FIRST_NAMES)
    assert len(set(LAST_NAMES)) == len(LAST_NAMES)


def test_unique_full_name_consumes_exactly_two_draws():
    """Determinism contract: two RNG draws per name regardless of collisions,
    so downstream rating rolls never shift based on how many names were
    already taken."""
    seed = 99
    crowded = DeterministicRNG(seed)
    used = {f"{first} {LAST_NAMES[0]}" for first in FIRST_NAMES}  # force skips
    unique_full_name(rng=crowded, used_names=set(used), fallback_tag="x")

    reference = DeterministicRNG(seed)
    reference.unit()
    reference.unit()
    assert crowded.unit() == reference.unit(), (
        "collision handling consumed RNG — downstream draws would shift"
    )


def test_unique_full_name_never_repeats_and_spreads_surnames():
    rng = DeterministicRNG(20260611)
    used: set[str] = set()
    used_last: set[str] = set()
    names = [
        unique_full_name(
            rng=rng, used_names=used, used_last_names=used_last, fallback_tag=f"#{i}"
        )
        for i in range(120)
    ]
    assert len(set(names)) == 120
    surnames = [name.rsplit(" ", 1)[-1] for name in names]
    assert len(set(surnames)) == 120, "surnames must not repeat while the pool lasts"


def test_founding_pool_follows_the_creation_seed():
    """V22 Phase 1: the pool was hardcoded to one seed — every created club
    drafted the same 25 prospects. Different creation seeds must now produce
    different founding classes, and the same seed must reproduce its class
    (the picker and the builder fetch with the same number)."""
    from dodgeball_sim.save_service import starting_prospects_payload

    a1 = starting_prospects_payload(101)["prospects"]
    a2 = starting_prospects_payload(101)["prospects"]
    b = starting_prospects_payload(202)["prospects"]
    assert [p["name"] for p in a1] == [p["name"] for p in a2]
    assert [p["name"] for p in a1] != [p["name"] for p in b]


def test_founding_prospects_expose_full_sheet_with_natural_ceilings():
    """The founding draft is the player's own class — the payload carries the
    full sheet (age, ratings, ceiling, tier, arc) and ceilings follow the V19
    natural rule (best hidden rating + 8, no 70 floor), so a dregs class no
    longer reads as a wall of identical 'Ceil 70' cards."""
    from dodgeball_sim.save_service import starting_prospects_payload

    prospects = starting_prospects_payload(7)["prospects"]
    assert len(prospects) >= 20
    ceilings = set()
    for p in prospects:
        assert p["age"] >= 18
        assert set(p["ratings"]) == {
            "accuracy", "power", "dodge", "catch", "stamina", "tactical_iq"
        }
        assert p["potential_tier"]
        assert p["ceiling_label"] in {"HIGH_CEILING", "SOLID", "STANDARD"}
        ceilings.add(p["potential_ceiling"])
    assert len(ceilings) >= 8, (
        f"founding ceilings should vary naturally, got only {sorted(ceilings)}"
    )


def test_build_from_scratch_persists_founder_growth_arcs(tmp_path):
    """Founders' hidden trajectories persist exactly like Signing Day
    signings — the development engine and roster ceiling display read them."""
    import sqlite3

    from dodgeball_sim.save_service import (
        build_from_scratch_save,
        starting_prospects_payload,
    )

    seed = 31337
    ids = [p["player_id"] for p in starting_prospects_payload(seed)["prospects"]][:6]
    result = build_from_scratch_save(tmp_path, {
        "save_name": "arcs",
        "club_name": "Arc FC",
        "city": "Arcadia",
        "colors": "red/black",
        "coach_name": "Coach",
        "coach_backstory": "Builder",
        "roster_player_ids": ids,
        "root_seed": seed,
    })
    conn = sqlite3.connect(result["path"])
    conn.row_factory = sqlite3.Row
    try:
        rows = {
            row["player_id"]: row["trajectory"]
            for row in conn.execute("SELECT player_id, trajectory FROM player_trajectory")
        }
    finally:
        conn.close()
    for player_id in ids:
        assert rows.get(player_id) in {"NORMAL", "IMPACT", "STAR", "GENERATIONAL"}
