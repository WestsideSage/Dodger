"""V25 The Market — Phase 6: the user's interactive Transfer Period beat engine.

Commit-on-advance: the beat caches default decisions (re-sign expiring at the
ask, refuse incoming buyouts); the user adjusts; advancing commits through the
same contested poach logic the AI faces.
"""
from __future__ import annotations

import sqlite3
from dataclasses import replace

from dodgeball_sim.career_setup import (
    build_expansion_club,
    generate_expansion_roster,
    initialize_curated_manager_career,
)
from dodgeball_sim.config import ContractConfig
from dodgeball_sim.economy import treasury_k
from dodgeball_sim.models import PlayerRatings
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_club_roster,
    load_clubs,
    save_club,
)
from dodgeball_sim import transfer_market as tm

_SEED = 20260617
_OPEN = ContractConfig(buyout_interest_threshold=0)


def _id_with_dealbreaker(motivation, n=600):
    from types import SimpleNamespace

    from dodgeball_sim.motivations import prospect_motivation_profile

    for i in range(n):
        pid = f"tb_{i}"
        if prospect_motivation_profile(SimpleNamespace(player_id=pid)).dealbreaker == motivation:
            return pid
    raise AssertionError(motivation)


# Development always grades 0.55 (never a dealbreaker veto), so a re-sign that
# outbids the field is decided by money, not a hidden veto.
_EXP_ID = _id_with_dealbreaker("development")


def _founding_conn(seed: int = _SEED):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    club = build_expansion_club(
        name="Orphanage Athletic", primary_color="#101010", secondary_color="#FAFAFA",
        venue_name="The Yard", home_region="Eastside", tagline="x",
    )
    roster = generate_expansion_roster(club.club_id, seed)
    initialize_curated_manager_career(
        conn, club.club_id, seed, custom_club=club, custom_roster=roster,
        ruleset_selection="official_foam", world="pyramid",
    )
    conn.commit()
    return conn, club.club_id


def _seed_user(conn, user_club, expiring_ovr=80, contracted_ovr=90):
    club = load_clubs(conn)[user_club]
    roster = load_club_roster(conn, user_club)
    seeded = []
    for i, p in enumerate(roster):
        if i == 0:  # the expiring star
            seeded.append(replace(p, id=_EXP_ID, salary_k=20, contract_term=0,
                                  ratings=PlayerRatings(accuracy=expiring_ovr, power=expiring_ovr,
                                                        dodge=expiring_ovr, catch=expiring_ovr)))
        elif i == 1:  # a contracted star (buyout target)
            seeded.append(replace(p, id="keep_star", salary_k=20, contract_term=2,
                                  ratings=PlayerRatings(accuracy=contracted_ovr, power=contracted_ovr,
                                                        dodge=contracted_ovr, catch=contracted_ovr)))
        else:
            seeded.append(replace(p, salary_k=12, contract_term=2))
    # Pad above the roster floor (6) so a single release/poach can actually
    # depart — the commit protects the floor (you can't field fewer than six).
    while len(seeded) < 8:
        src = seeded[len(seeded) % len(roster)]
        seeded.append(replace(src, id=f"pad_{len(seeded)}", salary_k=10, contract_term=2))
    save_club(conn, club, seeded)
    conn.commit()


def _state(conn, user_club, season_id, config=_OPEN):
    state = tm.build_user_transfer_state(conn, season_id, user_club, _SEED, config)
    tm.save_user_transfer_state(conn, state)
    return state


def test_build_state_defaults_resign_and_refuse():
    conn, user_club = _founding_conn()
    _seed_user(conn, user_club)
    season_id = get_state(conn, "active_season_id")
    state = _state(conn, user_club, season_id)
    assert any(r["player_id"] == _EXP_ID for r in state["expiring"])
    assert all(r["decision"] == "resign" for r in state["expiring"])
    assert all(b["decision"] == "refuse" for b in state["buyouts"])


def test_resign_keeps_player_when_outbidding():
    conn, user_club = _founding_conn()
    _seed_user(conn, user_club)
    season_id = get_state(conn, "active_season_id")
    _state(conn, user_club, season_id)
    # Raise the offer sky-high to beat any suitor.
    tm.set_expiring_decision(conn, _EXP_ID, "resign", user_offer_k=100_000)
    results = tm.apply_user_transfer_decisions(conn, season_id, user_club, _SEED, _OPEN)
    assert any(r["name"] for r in results["resigned"])
    survivors = {p.id: p for p in load_club_roster(conn, user_club)}
    assert _EXP_ID in survivors and survivors[_EXP_ID].contract_term > 0


def test_resign_at_default_offer_keeps_low_fit_player(monkeypatch):
    """PT5: clicking 'Re-sign' and accepting the displayed default offer must
    keep a low-fit expiring player when NO rival poaches him — not silently walk
    him to free agency (the Hugo-Reyes symptom). The default offer must meet the
    fit-adjusted ask, not the raw second-contract wage that silently undershot it.
    (A rival suitor outbidding him is a separate, INTENDED outcome.)"""
    from dodgeball_sim.persistence import load_free_agents

    # Isolate the no-suitor case: with a rival suitor he can be legitimately
    # outbid (the intended poach), which is NOT the bug under test.
    monkeypatch.setattr(tm, "poach_suitors", lambda *a, **k: [])

    conn, user_club = _founding_conn()
    _seed_user(conn, user_club)
    season_id = get_state(conn, "active_season_id")
    state = _state(conn, user_club, season_id)
    row = next(r for r in state["expiring"] if r["player_id"] == _EXP_ID)
    # The default decision is a re-sign at the displayed ask (no explicit change).
    assert row["decision"] == "resign" and row["user_offer_k"] == row["ask_k"]
    assert row["fit"] < 0.5556, "fixture must be low-fit so the raw ask undershoots the true ask"
    tm.apply_user_transfer_decisions(conn, season_id, user_club, _SEED, _OPEN)
    survivors = {p.id: p for p in load_club_roster(conn, user_club)}
    assert _EXP_ID in survivors, "re-signed player walked despite 'Re-sign' with no poacher"
    assert survivors[_EXP_ID].contract_term > 0, "re-signed player has no contract"
    assert _EXP_ID not in {p.id for p in load_free_agents(conn)}, (
        "re-signed player leaked into the free-agent pool"
    )


def test_release_departs_with_receipt():
    conn, user_club = _founding_conn()
    _seed_user(conn, user_club)
    season_id = get_state(conn, "active_season_id")
    _state(conn, user_club, season_id)
    tm.set_expiring_decision(conn, _EXP_ID, "release")
    results = tm.apply_user_transfer_decisions(conn, season_id, user_club, _SEED, _OPEN)
    assert results["departed"] and _EXP_ID not in {p.id for p in load_club_roster(conn, user_club)}
    assert results["departed"][0]["receipt"]


def test_accept_buyout_sells_for_treasury_income():
    conn, user_club = _founding_conn()
    _seed_user(conn, user_club)
    season_id = get_state(conn, "active_season_id")
    state = _state(conn, user_club, season_id)
    buyout = next((b for b in state["buyouts"] if b["player_id"] == "keep_star"), None)
    assert buyout is not None, "a contracted star should draw a buyout offer"

    before = treasury_k(conn)
    tm.set_buyout_decision(conn, "keep_star", "accept")
    results = tm.apply_user_transfer_decisions(conn, season_id, user_club, _SEED, _OPEN)
    assert results["sold"] and treasury_k(conn) > before
    assert "keep_star" not in {p.id for p in load_club_roster(conn, user_club)}


def test_max_offseason_beat_index_matches_canonical_tuple():
    # The persistence clamp literal must equal the canonical last-beat index, or
    # the final schedule_reveal beat becomes unreachable (V25 added a beat).
    from dodgeball_sim.offseason_ceremony import OFFSEASON_CEREMONY_BEATS
    from dodgeball_sim.persistence import _MAX_OFFSEASON_BEAT_INDEX

    assert _MAX_OFFSEASON_BEAT_INDEX == len(OFFSEASON_CEREMONY_BEATS) - 1


def test_compute_active_beats_gates_transfer_period():
    from dodgeball_sim.offseason_ceremony import compute_active_beats

    on = compute_active_beats(None, None, [], development_rows=[], player_club_id="x",
                              has_transfer_content=True)
    off = compute_active_beats(None, None, [], development_rows=[], player_club_id="x",
                               has_transfer_content=False)
    assert "transfer_period" in on
    # Placed between retirements and the rookie preview.
    assert on.index("transfer_period") < on.index("rookie_class_preview")
    assert "transfer_period" not in off


def test_build_beat_payload_transfer_branch_renders_cached_state():
    from types import SimpleNamespace

    from dodgeball_sim.offseason_presentation import build_beat_payload

    conn, user_club = _founding_conn()
    _seed_user(conn, user_club)
    season_id = get_state(conn, "active_season_id")
    _state(conn, user_club, season_id)
    payload = build_beat_payload(
        "transfer_period",
        awards=[], clubs=load_clubs(conn), rosters={}, standings=[], ret_rows=[],
        season=SimpleNamespace(season_id=season_id), season_outcome=None,
        next_preview=None, signed_player_id="", player_club_id=user_club, conn=conn,
    )
    assert "expiring" in payload and "buyouts" in payload
    assert payload["committed"] is False
    assert isinstance(payload["treasury_k"], int)


def test_commit_protects_the_roster_floor():
    # A thin squad where every player expires and is released must still field a
    # legal six after the commit (auto-pilot can never strand the roster below 6).
    conn, user_club = _founding_conn()
    club = load_clubs(conn)[user_club]
    roster = load_club_roster(conn, user_club)  # exactly 6 on a fresh founder
    save_club(conn, club, [replace(p, salary_k=15, contract_term=0) for p in roster])
    conn.commit()
    state = tm.build_user_transfer_state(conn, user_club_id=user_club, season_id=get_state(conn, "active_season_id"), root_seed=_SEED, config=_OPEN)
    # Mark them all to walk.
    for r in state["expiring"]:
        r["decision"] = "release"
        r["user_offer_k"] = 0
    tm.save_user_transfer_state(conn, state)
    tm.apply_user_transfer_decisions(conn, get_state(conn, "active_season_id"), user_club, _SEED, _OPEN)
    assert len(load_club_roster(conn, user_club)) >= 6


def test_commit_is_idempotent():
    conn, user_club = _founding_conn()
    _seed_user(conn, user_club)
    season_id = get_state(conn, "active_season_id")
    _state(conn, user_club, season_id)
    first = tm.apply_user_transfer_decisions(conn, season_id, user_club, _SEED, _OPEN)
    roster_after_first = sorted(p.id for p in load_club_roster(conn, user_club))
    second = tm.apply_user_transfer_decisions(conn, season_id, user_club, _SEED, _OPEN)
    assert first == second
    assert sorted(p.id for p in load_club_roster(conn, user_club)) == roster_after_first
