"""Locking the weekly plan (an intent-only save) must not wipe tactics.

Regression for the playtest finding: the Policy Editor edits were discarded
when the player locked the plan, because the lock POSTs ``{intent}`` only and
the save path rebuilt the intent-default plan from scratch. The locked plan is
what feeds the sim and the post-match recap, so a wipe silently reverts the
player's tactical decision and mislabels it in the debrief.
"""
import sqlite3

from fastapi.testclient import TestClient

from dodgeball_sim import server
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import create_schema


def _career_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


def test_intent_only_save_preserves_manually_set_tactics():
    conn = _career_conn()

    def override_db():
        yield conn

    # Tactics that deliberately diverge from the Balanced intent default so a
    # rebuild-from-default would be detectable.
    chosen_tactics = {
        "approach": "aggressive",
        "target_focus": "their_stars",
        "catch_posture": "go_for_catches",
        "rush_commit": "all_in",
        "rush_target": "center",
    }

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)

        # 1. Edit Game Plan: save the divergent tactics (intent unchanged).
        edited = client.post(
            "/api/command-center/plan",
            json={"intent": "Balanced", "tactics": chosen_tactics},
        )
        assert edited.status_code == 200
        assert edited.json()["plan"]["tactics"] == chosen_tactics

        # 2. Lock Plan: the lock action POSTs intent only, no tactics.
        locked = client.post(
            "/api/command-center/plan",
            json={"intent": "Balanced"},
        )
        assert locked.status_code == 200

        # 3. The locked plan must still carry the player's chosen tactics.
        assert locked.json()["plan"]["tactics"] == chosen_tactics

        # And a fresh fetch (what the sim/recap read) agrees.
        fetched = client.get("/api/command-center").json()
        assert fetched["plan"]["tactics"] == chosen_tactics
    finally:
        server.app.dependency_overrides.clear()


def test_balanced_intent_maps_to_a_balanced_preset():
    """Balanced should mean a genuinely balanced plan, not a passive default."""
    conn = _career_conn()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)
        # Force a fresh derive from the Balanced preset by switching intent.
        client.post("/api/command-center/plan", json={"intent": "Win Now"})
        balanced = client.post("/api/command-center/plan", json={"intent": "Balanced"})
        tactics = balanced.json()["plan"]["tactics"]
        assert tactics == {
            "approach": "mixed",
            "target_focus": "spread",
            "catch_posture": "opportunistic",
            "rush_commit": "balanced",
            "rush_target": "nearest",
        }
    finally:
        server.app.dependency_overrides.clear()


def test_changing_intent_still_rederives_tactics_preset():
    """Guard rail: changing the intent should still reset tactics to the new
    intent's preset (so this fix doesn't freeze tactics forever)."""
    conn = _career_conn()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)

        # Set a custom plan under Balanced.
        client.post(
            "/api/command-center/plan",
            json={
                "intent": "Balanced",
                "tactics": {
                    "approach": "patient",
                    "target_focus": "spread",
                    "catch_posture": "play_safe",
                    "rush_commit": "hold_back",
                    "rush_target": "nearest",
                },
            },
        )

        # Switch intent to Win Now: tactics should snap to the aggressive preset.
        switched = client.post(
            "/api/command-center/plan",
            json={"intent": "Win Now"},
        )
        assert switched.status_code == 200
        tactics = switched.json()["plan"]["tactics"]
        assert tactics["approach"] == "aggressive"
        assert tactics["rush_commit"] == "all_in"
    finally:
        server.app.dependency_overrides.clear()
