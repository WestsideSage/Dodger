"""Unit tests for V14 lineup-liability replay tags.

"Liability Exploited" must only appear when the saved event log proves the
liability was directly punished. Anything short of full proof degrades to
"involved" or no tag at all — never an unsupported exploitation claim.
"""

from __future__ import annotations

from dodgeball_sim.replay_proof import build_replay_proof


def _throw(resolution: str, *, thrower: str, target: str, player_out: dict | None = None) -> dict:
    return {
        "event_id": 1,
        "tick": 10,
        "event_type": "throw",
        "phase": "live",
        "actors": {
            "offense_team": "home",
            "defense_team": "away",
            "thrower": thrower,
            "target": target,
        },
        "context": {},
        "probabilities": {},
        "rolls": {},
        "outcome": {"resolution": resolution},
        "state_diff": {"player_out": player_out} if player_out else {},
    }


# Slot 0 prefers DODGER_ANCHOR/CATCHER (so a "thrower" there is a liability);
# slot 1 prefers DODGER_ANCHOR/BALL_HAWK (so "dodger_anchor" there is fine).
def _snapshots() -> dict:
    return {
        "home": [
            {"id": "home_1", "name": "Home Cap", "archetype": "thrower", "match_role": "active"},
            {"id": "home_2", "name": "Home Two", "archetype": "dodger_anchor", "match_role": "active"},
        ],
        "away": [
            {"id": "away_1", "name": "Away Cap", "archetype": "thrower", "match_role": "active"},
            {"id": "away_2", "name": "Away Two", "archetype": "dodger_anchor", "match_role": "active"},
        ],
    }


def _proof(event: dict) -> dict:
    result = build_replay_proof(
        [event],
        name_map={"home_1": "Home Cap", "home_2": "Home Two", "away_1": "Away Cap", "away_2": "Away Two"},
        roster_snapshots=_snapshots(),
        home_club_id="home",
        away_club_id="away",
    )
    return result["proof_events"][0]


def test_liability_target_eliminated_is_exploited():
    # away_1 is a mismatched Captain (thrower at slot 0) and is eliminated by the
    # hit -> directly punished -> exploited.
    event = _proof(_throw("hit", thrower="home_2", target="away_1", player_out={"team": "away", "player_id": "away_1"}))
    assert event["liability_context"]["tag"] == "exploited"
    assert "LIABILITY EXPLOITED" in event["proof_tags"]
    # 2026-06-09 audit: the note states the saved fact (an out-of-role starter
    # went out) without claiming the mismatch caused it — no shipping engine
    # applies a role penalty.
    assert any(
        "Out-of-role starter eliminated" in item
        for item in event["liability_context"]["items"]
    )
    assert not any("penalty as a mismatched" in item for item in event["liability_context"]["items"])


def test_liability_thrower_caught_is_exploited():
    # home_1 is a mismatched Captain; the throw is caught and home_1 goes out.
    event = _proof(_throw("catch", thrower="home_1", target="away_2", player_out={"team": "home", "player_id": "home_1"}))
    assert event["liability_context"]["tag"] == "exploited"
    assert "LIABILITY EXPLOITED" in event["proof_tags"]


def test_liability_present_but_not_punished_is_involved():
    # home_1 (liability) throws and the target dodges; nobody is eliminated.
    event = _proof(_throw("dodged", thrower="home_1", target="away_2"))
    assert event["liability_context"]["tag"] == "involved"
    assert "LIABILITY" in event["proof_tags"]
    assert "LIABILITY EXPLOITED" not in event["proof_tags"]


def test_liability_succeeds_is_not_exploited():
    # home_1 (liability) hits the non-liability away_2 -> the liability was NOT
    # punished; the other side was. Must not claim exploitation.
    event = _proof(_throw("hit", thrower="home_1", target="away_2", player_out={"team": "away", "player_id": "away_2"}))
    assert event["liability_context"]["tag"] == "involved"
    assert "LIABILITY EXPLOITED" not in event["proof_tags"]


def test_no_liability_participant_yields_no_tag():
    # home_2 and away_2 are dodger_anchors in accepting slots -> not liabilities.
    event = _proof(_throw("hit", thrower="home_2", target="away_2", player_out={"team": "away", "player_id": "away_2"}))
    assert event["liability_context"]["tag"] is None
    assert "LIABILITY" not in event["proof_tags"]
    assert "LIABILITY EXPLOITED" not in event["proof_tags"]


def test_exploitation_requires_elimination_proof():
    # Liability target on a hit, but NO player_out recorded -> punishment is not
    # proven, so it must degrade to "involved", never "exploited".
    event = _proof(_throw("hit", thrower="home_2", target="away_1"))
    assert event["liability_context"]["tag"] == "involved"
    assert "LIABILITY EXPLOITED" not in event["proof_tags"]
