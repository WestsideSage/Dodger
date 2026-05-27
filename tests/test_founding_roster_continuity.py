"""Founding-draft picks must carry identity unchanged into the roster.

The founding draft (Build a Club) deliberately has no fog-of-war: a coach
committing a founding roster is signing players to their own club this
instant, not scouting strangers from afar. So the archetype and OVR shown
on the draft screen must match the archetype and OVR shown on the roster
screen immediately after commit, byte-for-byte.

Regression for Codex playtest bug #3.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from dodgeball_sim.server import app, SAVES_DIR


def _cleanup(name: str) -> None:
    path = SAVES_DIR / f"{name}.db"
    if path.exists():
        path.unlink()


def test_founding_draft_archetype_and_overall_match_roster() -> None:
    client = TestClient(app)
    save_name = "test_founding_continuity"
    _cleanup(save_name)

    try:
        # 1. Draft screen payload
        res = client.get("/api/saves/starting-prospects")
        assert res.status_code == 200
        prospects = res.json()["prospects"]
        assert len(prospects) >= 10
        # Pick a spread that includes prospects known to expose any
        # archetype-divergence bug under the default seed (indices 11 and 15
        # are mislabeled in the pool).  If those drift to other indices later,
        # the wide spread still gives the test multiple chances to catch
        # any draft <-> roster mismatch.
        chosen_indices = [0, 5, 11, 15, 19, 24]
        chosen = [prospects[i] for i in chosen_indices]
        chosen_by_id = {p["player_id"]: p for p in chosen}

        # 2. Commit the founding roster
        payload = {
            "save_name": save_name,
            "club_name": "Continuity Club",
            "city": "Testville",
            "colors": "#FF0000,#000000",
            "coach_name": "Test Coach",
            "coach_backstory": "Tactical Mastermind",
            "roster_player_ids": list(chosen_by_id.keys()),
        }
        res = client.post("/api/saves/build-from-scratch", json=payload)
        assert res.status_code == 200, res.json()

        # 3. Roster screen payload
        res = client.get("/api/roster")
        assert res.status_code == 200
        roster = res.json()["roster"]
        assert len(roster) == len(chosen)

        roster_by_id = {p["id"]: p for p in roster}
        for prospect_id, prospect in chosen_by_id.items():
            assert prospect_id in roster_by_id, (
                f"prospect {prospect_id} disappeared from roster"
            )
            player = roster_by_id[prospect_id]

            # Identity: name preserved verbatim.
            assert player["name"] == prospect["name"], (
                f"name drift: draft={prospect['name']!r} roster={player['name']!r}"
            )

            # Archetype: the founding draft must show the TRUE archetype label
            # — same label the roster screen will render.
            assert player["role"] == prospect["public_archetype"], (
                f"archetype drift for {prospect['name']}: "
                f"draft={prospect['public_archetype']!r} "
                f"roster={player['role']!r}"
            )

            # Overall: the draft band must contain the roster OVR.
            ovr_low, ovr_high = prospect["public_ovr_band"]
            assert ovr_low <= player["overall"] <= ovr_high, (
                f"overall drift for {prospect['name']}: "
                f"draft band=[{ovr_low},{ovr_high}] roster={player['overall']}"
            )
    finally:
        _cleanup(save_name)
