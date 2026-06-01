"""WT-30 — Scout Opponent reveals REAL derived intel.

These integration tests exercise the command-center scout path end to end:

* cold start (no tape): scouting still reveals derivable, already-player-facing
  facts — program archetype, roster shape, key threat — so the Tactical Diff is
  never empty exactly when the bug bites;
* with tape: scouting exposes the opponent's observed historical tendencies,
  labelled as observed-from-tape; and
* the fog-of-war fence: the reveal is sourced from PAST recorded matches, never
  the opponent's live/upcoming hidden ``coach_policy`` — proven by making the
  tape say X while the live club says a deliberately different Y.
"""
from __future__ import annotations

import dataclasses
import json
import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.command_center import aggregate_opponent_tape
from dodgeball_sim.command_week_service import (
    command_center_payload,
    mark_opponent_scouted,
)
from dodgeball_sim.persistence import (
    create_schema,
    load_clubs,
    save_club,
)
from dodgeball_sim.use_cases import simulate_week


def _career_conn(seed: int = 20260426) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=seed)
    conn.commit()
    return conn


def _diff(conn: sqlite3.Connection) -> dict:
    payload = command_center_payload(conn)
    return payload["plan"]["matchup_details"]["tactical_diff"]


def _current_opponent_id(conn: sqlite3.Connection) -> str:
    payload = command_center_payload(conn)
    return payload["plan"]["opponent"]["club_id"]


def _insert_tape_match(
    conn: sqlite3.Connection,
    *,
    opponent_id: str,
    other_id: str,
    opponent_policy: dict[str, str],
    seed: int,
) -> None:
    """Insert one synthetic recorded match so ``opponent_id`` has tape.

    Mirrors what ``record_match`` writes: a ``matches`` row whose ``setup_json``
    carries each side's ``coach_policy``. We only need the opponent's side to be
    well-formed for tape aggregation.
    """
    setup = {
        "config_version": "phase1.v1",
        "team_a": {
            "id": opponent_id,
            "name": opponent_id.title(),
            "chemistry": 50,
            "coach_policy": dict(opponent_policy),
            "players": [],
        },
        "team_b": {
            "id": other_id,
            "name": other_id.title(),
            "chemistry": 50,
            "coach_policy": {
                "approach": "mixed",
                "target_focus": "spread",
                "catch_posture": "opportunistic",
                "rush_commit": "balanced",
                "rush_target": "nearest",
            },
            "players": [],
        },
    }
    box = {"teams": {opponent_id: {}, other_id: {}}, "winner": opponent_id}
    conn.execute(
        """
        INSERT INTO matches (
            seed, config_version, winner_team_id, team_a_id, team_b_id,
            difficulty, setup_json, box_score_json, final_tick
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            seed,
            "phase1.v1",
            opponent_id,
            opponent_id,
            other_id,
            "pro",
            json.dumps(setup),
            json.dumps(box),
            100,
        ),
    )
    conn.commit()


def test_cold_start_scout_reveals_nonempty_derivable_facts():
    """Week 1, no tape: scouting flips the diff and reveals real facts."""
    conn = _career_conn()

    before = _diff(conn)
    assert before["scouted"] is False
    assert before["intel_revealed"] is False
    assert all(row["opponent_known"] is False for row in before["player_plan"])
    assert before["cold_start"] is None

    opponent_id = _current_opponent_id(conn)
    after = mark_opponent_scouted(conn)["plan"]["matchup_details"]["tactical_diff"]
    assert after["scouted"] is True
    # The diff is NOT empty: cold-start facts are present even with zero tape.
    assert after["intel_revealed"] is True
    cold = after["cold_start"]
    assert cold is not None
    assert cold["roster_shape"]["total"] == 6  # fielded program is six-deep
    assert cold["threat"] is not None and cold["threat"]["name"]

    # Faithfulness (ADR-0002): the program identity the scout shows must be the
    # SAME stored value standings/status display — not a fresh recomputation that
    # could drift. Assert it equals the club's stored program_archetype.
    stored_archetype = load_clubs(conn)[opponent_id].program_archetype
    assert cold["program_archetype"] == stored_archetype


def test_cold_start_archetype_tracks_stored_value_not_a_recompute():
    """If the stored program identity is edited, the scout follows it verbatim.

    Proves the scout reads the canonical stored ``club.program_archetype`` (what
    standings/broadcast show) rather than recomputing from the roster — so the
    two surfaces can never contradict each other.
    """
    from dodgeball_sim.persistence import load_all_rosters

    conn = _career_conn()
    opponent_id = _current_opponent_id(conn)
    opp = load_clubs(conn)[opponent_id]
    # Overwrite the stored identity with a sentinel a recompute would never yield,
    # preserving the real roster so roster_shape stays valid.
    opp = dataclasses.replace(opp, program_archetype="Scout-Source Sentinel")
    save_club(conn, opp, list(load_all_rosters(conn).get(opponent_id, [])))
    conn.commit()

    after = mark_opponent_scouted(conn)["plan"]["matchup_details"]["tactical_diff"]
    assert after["cold_start"]["program_archetype"] == "Scout-Source Sentinel"


def test_scout_with_tape_reveals_observed_tendencies():
    """After games are played, scouting exposes the opponent's tape tendencies."""
    conn = _career_conn()
    # Play three weeks so the whole league (including the next opponent) accrues
    # a public record of how they have played.
    for _ in range(3):
        simulate_week(conn, update=None)

    opponent_id = _current_opponent_id(conn)
    tape = aggregate_opponent_tape(conn, opponent_id)
    assert tape, "expected the next opponent to have accrued tape"

    after = mark_opponent_scouted(conn)["plan"]["matchup_details"]["tactical_diff"]
    assert after["scouted"] is True
    assert after["tape_axes_revealed"] >= 1
    revealed = {row["axis"]: row for row in after["player_plan"] if row["opponent_known"]}
    assert revealed, "scouting with tape must reveal at least one axis"
    for row in revealed.values():
        # Each revealed axis is labelled as observed-from-tape with confidence.
        assert row["opponent_source"] == "tape"
        assert 0.0 < row["confidence"] <= 1.0
        assert row["sample"] >= 1
    assert "tendenc" in after["note"].lower()


def test_scout_reveal_is_sourced_from_tape_not_the_live_hidden_plan():
    """Fog-of-war fence: the reveal must come from PAST tape, never the live plan.

    Construct the discriminating case the static AI normally hides: make the
    opponent's recorded tape say X on every axis, then overwrite their LIVE
    (upcoming, hidden) coach policy with a deliberately different Y. The scout
    reveal must show X (tape) and Y must appear nowhere — proving the source is
    historical tape, not the live club object.
    """
    conn = _career_conn()
    opponent_id = _current_opponent_id(conn)
    clubs = load_clubs(conn)
    other_id = next(cid for cid in clubs if cid != opponent_id)

    tape_policy_X = {
        "approach": "patient",
        "target_focus": "ball_holders",
        "catch_posture": "play_safe",
        "rush_commit": "hold_back",
        "rush_target": "nearest",
    }
    # Distinct on every axis so a leak would be unmistakable.
    live_policy_Y = {
        "approach": "aggressive",
        "target_focus": "their_stars",
        "catch_posture": "go_for_catches",
        "rush_commit": "all_in",
        "rush_target": "center",
    }
    assert all(tape_policy_X[a] != live_policy_Y[a] for a in tape_policy_X)

    # Several recorded games all showing X → a strong observed tendency.
    for i in range(4):
        _insert_tape_match(
            conn,
            opponent_id=opponent_id,
            other_id=other_id,
            opponent_policy=tape_policy_X,
            seed=1000 + i,
        )

    # Overwrite the opponent's LIVE coach policy with Y (the hidden upcoming plan).
    opp_club = clubs[opponent_id]
    opp_club = dataclasses.replace(
        opp_club, coach_policy=type(opp_club.coach_policy).from_dict(live_policy_Y)
    )
    save_club(conn, opp_club, [])
    conn.commit()

    # Sanity: the live plan really is Y now.
    assert load_clubs(conn)[opponent_id].coach_policy.as_dict() == live_policy_Y

    after = mark_opponent_scouted(conn)["plan"]["matchup_details"]["tactical_diff"]
    revealed = {row["axis"]: row for row in after["player_plan"] if row["opponent_known"]}
    assert revealed, "tape should have revealed axes"
    for axis, row in revealed.items():
        # Shows the TAPE value (X), humanized.
        assert row["opponent_value"] == tape_policy_X[axis].replace("_", " ").capitalize()

    # The live hidden plan Y must not appear ANYWHERE in the serialized diff,
    # except on axes where Y happens to equal the player's own value (those are
    # the player's plan, not a leak).
    player_values = {row["axis"]: row["player_value"].lower() for row in after["player_plan"]}
    serialized = json.dumps(after).lower()
    leaks = {
        axis: value
        for axis, value in live_policy_Y.items()
        if value.replace("_", " ") in serialized
        and value.replace("_", " ") != player_values.get(axis)
        and value != tape_policy_X[axis]  # X==Y impossible here, but be explicit
    }
    assert not leaks, f"live hidden plan leaked into the scout reveal: {leaks}"
