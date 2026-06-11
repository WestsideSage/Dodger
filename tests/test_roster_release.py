"""Playtest 3 F-8: the release control and the Signing Day sign-over-cut.

The journal's top finding: at 12/12 the Signing Day silently became read-only
and no release/cut/waive control existed anywhere, so a successful young core
froze the roster for the rest of the dynasty. These tests pin the new
turnover loop: release to free agency (with honest promise consequences) and
sign-over-cut at a full-roster Signing Day.
"""
import dataclasses
import sqlite3

from fastapi.testclient import TestClient

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_all_rosters,
    load_clubs,
    load_free_agents,
    load_json_state,
    load_lineup_default,
    load_weekly_command_plan,
    save_club,
    save_weekly_command_plan,
)
from dodgeball_sim.recruiting_office import PROMISE_STATE_KEY
from dodgeball_sim.roster_moves import (
    RosterMoveError,
    release_player_to_free_agency,
)
from dodgeball_sim.server import app, get_db


def _career_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


def _user_roster(conn):
    return load_all_rosters(conn)[get_state(conn, "player_club_id")]


def test_release_moves_player_to_free_agency_and_repairs_lineup():
    conn = _career_conn()
    _pad_user_roster_to(conn, 8)  # the curated career starts AT the 6 floor
    roster_before = list(_user_roster(conn))
    target = roster_before[-1]

    outcome = release_player_to_free_agency(conn, target.id)

    roster_after = _user_roster(conn)
    assert len(roster_after) == len(roster_before) - 1
    assert all(p.id != target.id for p in roster_after)
    # The release is real: the player waits in the free-agent pool, not /dev/null.
    assert any(p.id == target.id for p in load_free_agents(conn))
    # Lineup default repaired — no ghost starter.
    lineup = load_lineup_default(conn, get_state(conn, "player_club_id")) or []
    assert target.id not in lineup
    assert outcome["released_player"]["name"] == target.name
    assert outcome["roster_size"] == len(roster_after)
    assert outcome["broken_promise"] is None


def test_release_blocks_below_the_fielded_six():
    conn = _career_conn()  # curated career starts at exactly 6 players
    roster = list(_user_roster(conn))
    assert len(roster) == 6

    try:
        release_player_to_free_agency(conn, roster[0].id)
        raise AssertionError("expected RosterMoveError at the 6-player floor")
    except RosterMoveError as exc:
        assert exc.status_code == 409
        assert "at least 6" in exc.detail
    assert len(_user_roster(conn)) == 6


def test_release_rejects_player_not_on_roster():
    conn = _career_conn()
    try:
        release_player_to_free_agency(conn, "nobody_here")
        raise AssertionError("expected RosterMoveError for unknown player")
    except RosterMoveError as exc:
        assert exc.status_code == 404


def test_release_breaks_an_open_promise_honestly():
    """Cutting a player you promised development to is a BREAK (credibility
    cost), never a quiet void — the manager chose this outcome."""
    import json

    from dodgeball_sim.dynasty_office import save_recruiting_promise

    conn = _career_conn()
    _pad_user_roster_to(conn, 8)
    target = list(_user_roster(conn))[0]
    save_recruiting_promise(conn, target.id, "development_priority")

    outcome = release_player_to_free_agency(conn, target.id)

    assert outcome["broken_promise"] is not None
    assert outcome["broken_promise"]["status"] == "broken"
    promises = load_json_state(conn, PROMISE_STATE_KEY, [])
    match = next(p for p in promises if p["player_id"] == target.id)
    assert match["status"] == "broken"
    assert "released" in match["evidence"].lower()
    assert match["result_season_id"] == get_state(conn, "active_season_id")
    # The break must reach credibility like any other broken promise.
    assert "broken" in json.dumps(promises)


def test_release_scrubs_current_week_plan_lineup():
    conn = _career_conn()
    _pad_user_roster_to(conn, 8)
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    roster = list(_user_roster(conn))
    target = roster[0]
    six = [p.id for p in roster[:6]]
    save_weekly_command_plan(conn, {
        "season_id": season_id,
        "week": 1,
        "player_club_id": player_club_id,
        "intent": "Balanced",
        "department_orders": {},
        "lineup": {
            "player_ids": six,
            "players": [{"id": p.id, "name": p.name, "overall": p.overall_skill()} for p in roster[:6]],
            "summary": "manual six",
        },
    })
    conn.commit()

    release_player_to_free_agency(conn, target.id)

    plan = load_weekly_command_plan(conn, season_id, 1, player_club_id)
    assert target.id not in (plan["lineup"]["player_ids"] or [])
    assert all(entry["id"] != target.id for entry in plan["lineup"]["players"])


def test_release_endpoint_returns_refreshed_roster_and_outcome():
    conn = _career_conn()
    _pad_user_roster_to(conn, 8)
    target = list(_user_roster(conn))[-1]

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        response = client.post("/api/roster/release", json={"player_id": target.id})
        assert response.status_code == 200
        body = response.json()
        assert all(p["id"] != target.id for p in body["roster"])
        assert body["release_outcome"]["released_player"]["id"] == target.id

        missing = client.post("/api/roster/release", json={"player_id": "ghost"})
        assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Sign-over-cut at a full-roster Signing Day
# ---------------------------------------------------------------------------


def _pad_user_roster_to(conn: sqlite3.Connection, target: int) -> None:
    player_club_id = get_state(conn, "player_club_id")
    clubs = load_clubs(conn)
    roster = list(load_all_rosters(conn)[player_club_id])
    i = 0
    while len(roster) < target:
        base = roster[i % len(roster)]
        roster.append(dataclasses.replace(base, id=f"{base.id}_pad{i}", name=f"Depth {i}"))
        i += 1
    save_club(conn, clubs[player_club_id], roster)
    conn.commit()


def _enter_recruitment_state(conn: sqlite3.Connection) -> None:
    from dodgeball_sim.career_state import CareerState, CareerStateCursor
    from dodgeball_sim.offseason_ceremony import finalize_season, initialize_manager_offseason
    from dodgeball_sim.offseason_presentation import load_active_beats
    from dodgeball_sim.persistence import load_season, save_career_state_cursor

    season_id = get_state(conn, "active_season_id")
    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    finalize_season(conn, season, rosters)
    initialize_manager_offseason(conn, season, clubs, rosters, root_seed=20260426)
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


def _disable_rival_bids(monkeypatch) -> None:
    from dodgeball_sim import recruitment

    monkeypatch.setattr(
        recruitment, "_eligible_ai_offer_clubs", lambda *args, **kwargs: set()
    )


def test_full_roster_signing_day_stays_live_and_swaps(monkeypatch):
    """The journal's exact dead-end: 12/12 made Signing Day a read-only
    "Update" with zero churn possible. Now the picker stays live and a pick
    goes through by releasing a named player."""
    conn = _career_conn()
    _pad_user_roster_to(conn, 12)
    _enter_recruitment_state(conn)
    _disable_rival_bids(monkeypatch)
    player_club_id = get_state(conn, "player_club_id")
    release_target = load_all_rosters(conn)[player_club_id][-1]

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        beat = client.get("/api/offseason/beat").json()
        assert beat["can_recruit"] is True, "a full roster must not lock Signing Day"
        assert beat["payload"]["roster_size"] == 12
        # The swap picker has the roster to choose from.
        assert len(beat["payload"]["user_roster"]) == 12

        prospect_id = beat["payload"]["available_prospects"][0]["prospect_id"]

        # No release named -> actionable rejection, not a silent skip.
        blocked = client.post("/api/offseason/recruit", json={"prospect_id": prospect_id})
        assert blocked.status_code == 409
        assert "release" in blocked.json()["detail"].lower()

        # Swap: release a named player, sign the prospect.
        swapped = client.post(
            "/api/offseason/recruit",
            json={"prospect_id": prospect_id, "release_player_id": release_target.id},
        )
        assert swapped.status_code == 200
        body = swapped.json()
        assert body["signed_player"] is not None
        assert body["released_player"]["id"] == release_target.id
        assert body["payload"]["signed_count"] == 1
    finally:
        app.dependency_overrides.clear()

    roster_after = load_all_rosters(conn)[player_club_id]
    assert len(roster_after) == 12  # swap, not growth
    assert all(p.id != release_target.id for p in roster_after)
    assert any(p.id == release_target.id for p in load_free_agents(conn))


def test_swap_release_does_not_happen_on_a_snipe(monkeypatch):
    """Transactional honesty: when a rival snipes the pick, the named release
    must NOT execute — a failed signing cannot cost the released player."""
    from dodgeball_sim import recruitment

    conn = _career_conn()
    _pad_user_roster_to(conn, 12)
    _enter_recruitment_state(conn)
    player_club_id = get_state(conn, "player_club_id")
    release_target = load_all_rosters(conn)[player_club_id][-1]

    # Force the contested round to be LOST: every AI club bids and the user's
    # offer is floored.
    monkeypatch.setattr(
        recruitment,
        "conduct_recruitment_round",
        lambda *args, **kwargs: None,
    )
    # conduct_recruitment_round returning None means nobody signed; emulate a
    # snipe by patching the service-level signer instead.
    import dodgeball_sim.offseason_service as service

    def fake_contested(conn_, club_id, season_number, prospect_id):
        return None, {"kind": "sniped", "prospect_name": "X", "winning_club_name": "Rivals", "explanation": "outbid"}

    monkeypatch.setattr(service, "sign_chosen_rookie_contested", fake_contested)

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        beat = client.get("/api/offseason/beat").json()
        prospect_id = beat["payload"]["available_prospects"][0]["prospect_id"]
        response = client.post(
            "/api/offseason/recruit",
            json={"prospect_id": prospect_id, "release_player_id": release_target.id},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["signed_player"] is None
        assert body["released_player"] is None
    finally:
        app.dependency_overrides.clear()

    roster_after = load_all_rosters(conn)[player_club_id]
    assert len(roster_after) == 12
    assert any(p.id == release_target.id for p in roster_after)
