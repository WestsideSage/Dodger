"""V16 Tasks 2+3 — the contested offseason.

The user's prospect pick resolves through the dormant V2-B round system
(interest + credibility buy real signing odds; snipes are honest outcomes,
not errors), and AI clubs sign real prospects so the league moves.
"""

import dataclasses
import json
import sqlite3

import pytest

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.career_state import CareerState, CareerStateCursor
from dodgeball_sim.config import AI_OFFSEASON_SIGNINGS_PER_CLUB
from dodgeball_sim.offseason_ceremony import (
    available_recruitment_choices,
    ensure_ai_offseason_signings,
    finalize_season,
    initialize_manager_offseason,
    sign_chosen_rookie_contested,
)
from dodgeball_sim.offseason_presentation import load_active_beats
from dodgeball_sim.offseason_service import recruit_offseason_payload
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_all_rosters,
    load_clubs,
    load_lineup_default,
    load_prospect_pool,
    load_recruitment_signings,
    load_season,
    save_career_state_cursor,
    save_lineup_default,
    set_state,
)

# Seeds where the TOP prospect (by public estimate) is contested hard enough
# that the uncourted user offer loses the round, while the courted offer wins
# it. Found by tools/contested_offer_probe.py (witness list, 2026-06-10
# post-V18 re-derivation: the vet-mix seeding moved club profiles, so BASE was
# re-tuned 90.0 -> 85.0; probe now reads uncourted 43% sniped, courted +32
# 12%, interest-100 0%); pinned here as the cause->effect proof that interest
# is a real consumer. If these fail after an RNG-stream or balance change,
# re-run the probe and pick fresh witnesses from its printed list.
WITNESS_SEED = 7
WITNESS_SEEDS = (7, 13)
_REDERIVE = "re-derive witnesses with tools/contested_offer_probe.py"


def _career_in_recruitment(root_seed: int) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=root_seed)
    season_id = get_state(conn, "active_season_id")
    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    finalize_season(conn, season, rosters)
    initialize_manager_offseason(conn, season, clubs, rosters, root_seed=root_seed)
    recruitment_index = load_active_beats(conn).index("recruitment")
    save_career_state_cursor(
        conn,
        CareerStateCursor(
            state=CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING,
            season_number=1,
            week=0,
            offseason_beat_index=recruitment_index,
        ),
    )
    conn.commit()
    return conn


def _top_prospect_id(conn: sqlite3.Connection) -> str:
    choices = available_recruitment_choices(conn, 1)
    return next(c["prospect_id"] for c in choices if c["kind"] == "prospect")


def _court(conn: sqlite3.Connection, prospect_id: str, interest: int) -> None:
    set_state(
        conn,
        "prospect_recruitment_actions_json",
        json.dumps(
            {
                prospect_id: {
                    "scouted": True,
                    "contacted": True,
                    "visited": True,
                    "interest": interest,
                }
            }
        ),
    )
    conn.commit()


def _signing_rows(conn: sqlite3.Connection) -> list[tuple]:
    season_id = get_state(conn, "active_season_id")
    return sorted(
        (s.player_id, s.club_id, s.source, round(s.offer_strength, 4))
        for s in load_recruitment_signings(conn, season_id)
    )


def test_same_seed_contested_pick_is_deterministic():
    # Scope note: this compares two runs in ONE process (fixed hash seed), so
    # it cannot catch nondeterminism driven by set/dict iteration order across
    # interpreter launches. The live code orders via sorted() everywhere
    # (eligibility sets are membership-only); keep it that way.
    outcomes = []
    for _ in range(2):
        conn = _career_in_recruitment(4242)
        target = _top_prospect_id(conn)
        signed, outcome = sign_chosen_rookie_contested(conn, "aurora", 1, target)
        outcomes.append(
            (
                target,
                signed.id if signed else None,
                outcome["kind"],
                outcome.get("winning_club_id"),
                _signing_rows(conn),
            )
        )
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize("witness_seed", WITNESS_SEEDS)
def test_courtship_flips_a_snipe_into_a_signing(witness_seed):
    # Control: uncourted pick of the top prospect loses the contested round.
    control = _career_in_recruitment(witness_seed)
    target = _top_prospect_id(control)
    control_signed, control_outcome = sign_chosen_rookie_contested(control, "aurora", 1, target)
    assert control_signed is None
    assert control_outcome["kind"] == "sniped", (
        f"seed {witness_seed}: uncourted control was not sniped — {_REDERIVE}"
    )
    assert control_outcome["prospect_id"] == target
    assert control_outcome["winning_club_id"] != "aurora"

    # Variant: identical seed, but the user courted the prospect all season.
    courted = _career_in_recruitment(witness_seed)
    assert _top_prospect_id(courted) == target
    _court(courted, target, interest=95)
    courted_signed, courted_outcome = sign_chosen_rookie_contested(courted, "aurora", 1, target)
    assert courted_outcome["kind"] == "signed", (
        f"seed {witness_seed}: courted pick did not win — {_REDERIVE}"
    )
    assert courted_signed is not None
    # The signed roster player carries the prospect identity.
    roster_ids = {p.id for p in load_all_rosters(courted)["aurora"]}
    assert courted_signed.id in roster_ids


def test_snipe_is_a_legitimate_outcome_not_an_error():
    conn = _career_in_recruitment(WITNESS_SEED)
    target = _top_prospect_id(conn)
    payload = recruit_offseason_payload(conn, target)

    assert payload["signed_player"] is None
    outcome = payload["signing_outcome"]
    assert outcome["kind"] == "sniped"
    assert outcome["prospect_id"] == target
    assert outcome["winning_club_name"]
    assert "interest" in outcome["explanation"].lower()
    # A snipe consumes no signing slot and keeps the player in the beat.
    assert payload["payload"]["signed_count"] == 0
    assert payload["can_recruit"] is True
    # The sniped prospect is gone from the remainder.
    remaining = {c["prospect_id"] for c in payload["payload"]["available_prospects"]}
    assert target not in remaining


def test_contested_win_returns_signed_outcome():
    conn = _career_in_recruitment(WITNESS_SEED)
    choices = available_recruitment_choices(conn, 1)
    top = next(c for c in choices if c["kind"] == "prospect")
    target = top["prospect_id"]
    _court(conn, target, interest=95)
    # Re-read: courting (scouted=True) narrows the band the picker shows.
    choices = available_recruitment_choices(conn, 1)
    top = next(c for c in choices if c["prospect_id"] == target)
    payload = recruit_offseason_payload(conn, target)

    assert payload["signed_player"] is not None
    outcome = payload["signing_outcome"]
    assert outcome["kind"] == "signed", f"courted top pick lost — {_REDERIVE}"
    assert payload["payload"]["signed_count"] == 1
    # The post-signing honesty surface (plan acceptance criterion 2): the
    # outcome carries the pre-signing scouted band and the verified reveal.
    assert outcome["your_interest"] == 95
    assert outcome["scouted_band"] == top["public_ovr_band"]
    assert outcome["reveal"].startswith("Scouted ")
    assert f"verified OVR {payload['signed_player']['overall']}" in outcome["reveal"]


def test_ai_clubs_sign_prospects_when_user_skips():
    conn = _career_in_recruitment(4242)
    pool_before = {
        p.player_id for p in load_prospect_pool(conn, class_year=1)
    }
    assert pool_before
    rosters_before = {cid: {p.id for p in r} for cid, r in load_all_rosters(conn).items()}

    recruit_offseason_payload(conn, "skip")

    season_id = get_state(conn, "active_season_id")
    signings = load_recruitment_signings(conn, season_id)
    ai_signings = [s for s in signings if s.source == "ai"]
    assert ai_signings, "the league must move even when the user skips"

    per_club: dict[str, int] = {}
    rosters_after = load_all_rosters(conn)
    for signing in ai_signings:
        assert signing.club_id != "aurora"
        per_club[signing.club_id] = per_club.get(signing.club_id, 0) + 1
        roster_ids = {p.id for p in rosters_after[signing.club_id]}
        assert signing.player_id in roster_ids
        assert signing.player_id not in rosters_before[signing.club_id]
    assert all(count <= AI_OFFSEASON_SIGNINGS_PER_CLUB for count in per_club.values())


def test_ai_club_at_roster_ceiling_sits_out_signing_day():
    conn = _career_in_recruitment(4242)
    from dodgeball_sim.config import AI_OFFSEASON_MAX_ROSTER
    from dodgeball_sim.persistence import save_club

    clubs = load_clubs(conn)
    padded_club = next(cid for cid in sorted(clubs) if cid != "aurora")
    roster = list(load_all_rosters(conn)[padded_club])
    i = 0
    while len(roster) < AI_OFFSEASON_MAX_ROSTER:
        base = roster[i % len(roster)]
        roster.append(
            dataclasses.replace(base, id=f"{base.id}_pad{i}", name=f"Depth {i}")
        )
        i += 1
    save_club(conn, clubs[padded_club], roster)
    conn.commit()

    recruit_offseason_payload(conn, "skip")

    season_id = get_state(conn, "active_season_id")
    ceiling_signings = [
        s
        for s in load_recruitment_signings(conn, season_id)
        if s.club_id == padded_club
    ]
    assert ceiling_signings == [], (
        f"{padded_club} is at the {AI_OFFSEASON_MAX_ROSTER}-player ceiling and "
        "must sit out Signing Day"
    )


def test_ai_signings_run_once_per_offseason():
    conn = _career_in_recruitment(4242)
    recruit_offseason_payload(conn, "skip")
    season_id = get_state(conn, "active_season_id")
    first = _signing_rows(conn)
    ensure_ai_offseason_signings(conn)
    ensure_ai_offseason_signings(conn)
    assert _signing_rows(conn) == first
    assert get_state(conn, "offseason_ai_signings_done_for") == season_id


def test_user_lineup_default_preserved_on_contested_win():
    conn = _career_in_recruitment(WITNESS_SEED)
    target = _top_prospect_id(conn)
    _court(conn, target, interest=95)
    prior_default = list(load_lineup_default(conn, "aurora"))
    custom = list(reversed(prior_default))
    save_lineup_default(conn, "aurora", custom)
    conn.commit()

    signed, outcome = sign_chosen_rookie_contested(conn, "aurora", 1, target)
    assert outcome["kind"] == "signed" and signed is not None

    after = list(load_lineup_default(conn, "aurora"))
    # The manual order must survive (the raw sign_prospect_to_club path would
    # have rewritten it to roster order); the recruit slots in like the
    # uncontested path does.
    assert after[:5] == custom[:5]
    assert signed.id in after


def test_free_agent_pick_is_direct_and_uncontested():
    conn = _career_in_recruitment(4242)
    choices = available_recruitment_choices(conn, 1)
    fa = next(c for c in choices if c["kind"] == "free_agent")

    payload = recruit_offseason_payload(conn, fa["prospect_id"])
    assert payload["signed_player"] is not None
    assert payload["signing_outcome"]["kind"] == "free_agent_signed"

    season_id = get_state(conn, "active_season_id")
    contested_rows = [
        s for s in load_recruitment_signings(conn, season_id) if s.club_id == "aurora"
    ]
    assert contested_rows == []


def test_ai_cap_holds_across_user_picks_and_close():
    conn = _career_in_recruitment(4242)
    for _ in range(3):
        choices = available_recruitment_choices(conn, 1)
        prospect = next((c for c in choices if c["kind"] == "prospect"), None)
        if prospect is None:
            break
        recruit_offseason_payload(conn, prospect["prospect_id"])
    cursor_state = get_state(conn, "offseason_ai_signings_done_for")
    if cursor_state is None:
        ensure_ai_offseason_signings(conn)

    season_id = get_state(conn, "active_season_id")
    per_club: dict[str, int] = {}
    for signing in load_recruitment_signings(conn, season_id):
        if signing.source == "ai":
            per_club[signing.club_id] = per_club.get(signing.club_id, 0) + 1
    assert per_club, "AI clubs should have signed during the offseason"
    assert all(count <= AI_OFFSEASON_SIGNINGS_PER_CLUB for count in per_club.values())
