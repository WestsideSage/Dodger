import dataclasses
import sqlite3
from fastapi.testclient import TestClient
from dodgeball_sim.server import app, get_db
from dodgeball_sim.persistence import (
    create_schema,
    load_all_rosters,
    load_clubs,
    save_club,
)
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.web_status_service import build_standings_payload

def test_standings_includes_recent_matches():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        # Advance the week to generate matches
        client.post("/api/sim", json={"mode": "week"})
        client.post("/api/sim", json={"mode": "week"})
        
        res = client.get('/api/standings')
        data = res.json()
        assert 'recent_matches' in data
        assert type(data['recent_matches']) == list
    finally:
        app.dependency_overrides.clear()


def test_standings_exposes_user_games_remaining():
    """The standings table must report the same games-remaining count the
    command center uses, so the two surfaces never contradict each other."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        before = client.get('/api/standings').json()['user_games_remaining']
        assert isinstance(before, int)
        assert before > 0
        client.post("/api/sim", json={"mode": "week"})
        after = client.get('/api/standings').json()['user_games_remaining']
        # Playing a user match must decrement the count (byes excluded).
        assert after < before
    finally:
        app.dependency_overrides.clear()


def test_standings_identity_label_equals_mechanical_program_archetype():
    """WT-24 (ADR 0002): the standings identity label must NAME each club's real
    mechanical ``program_archetype`` — the value the AI actually plays as — for
    every club, with no divergent hand-maintained per-club flavor mapping.

    The label is ``f"Yr {n} · {identity}"``; the identity segment after the
    separator must equal the club's stored ``program_archetype`` exactly, and
    that stored value must match what ``load_clubs`` reports. Asserting over the
    whole standings payload covers each club / each archetype value present.
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()

    clubs = load_clubs(conn)
    payload = build_standings_payload(conn)
    assert payload["standings"]  # non-empty, so the loop actually asserts

    for row in payload["standings"]:
        club_id = row["club_id"]
        stored_archetype = clubs[club_id].program_archetype
        # The exposed archetype field is already faithful; the historic lie was
        # the label diverging from it.
        assert row["program_archetype"] == stored_archetype
        identity = row["program_trajectory_label"].split(" · ", 1)[1]
        assert identity == stored_archetype, (
            f"{club_id}: standings label identity {identity!r} must equal the "
            f"mechanical program_archetype {stored_archetype!r}"
        )


def test_standings_identity_label_is_a_pure_function_not_a_hardcoded_map():
    """If the stored ``program_archetype`` is edited to a value no per-club
    mapping would ever yield, the standings label must follow it verbatim.

    Proves the label is DERIVED FROM ``club.program_archetype`` (a faithful
    function) rather than a separate club-id keyed table that can drift — the
    same fence ``test_scout_reveal.py`` puts around the scout reveal.
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()

    sentinel = "Drift-Sentinel Identity"
    rosters = load_all_rosters(conn)
    target_club = dataclasses.replace(
        load_clubs(conn)["lunar"], program_archetype=sentinel
    )
    save_club(conn, target_club, list(rosters.get("lunar", [])))
    conn.commit()

    payload = build_standings_payload(conn)
    lunar_row = next(r for r in payload["standings"] if r["club_id"] == "lunar")
    assert lunar_row["program_archetype"] == sentinel
    assert lunar_row["program_trajectory_label"].endswith(f"· {sentinel}")
