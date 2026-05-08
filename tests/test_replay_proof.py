from __future__ import annotations

from dodgeball_sim.replay_proof import build_replay_proof
from dodgeball_sim.stats import PlayerMatchStats


def _throw_event(resolution: str, *, player_out: dict | None = None) -> dict:
    return {
        "event_id": 1,
        "tick": 4,
        "event_type": "throw",
        "phase": "live",
        "actors": {
            "offense_team": "home",
            "defense_team": "away",
            "thrower": "home_1",
            "target": "away_1",
        },
        "context": {
            "target_selection": {
                "recent_pressure_player_id": "away_2",
                "scores": [{"player_id": "away_1", "score": 0.62}],
            },
            "catch_decision": {"attempt": True, "threshold": 0.45},
            "policy_snapshot": {
                "target_stars": 0.72,
                "tempo": 0.55,
                "catch_bias": 0.50,
            },
            "rush_context": {
                "active": True,
                "rush_frequency": 0.8,
                "rush_proximity": 0.7,
                "proximity_modifier": 0.03,
                "fatigue_delta": 0.4,
            },
            "sync_context": {"is_synced": True, "sync_modifier": 0.05},
            "fatigue": {
                "thrower_fatigue": 1.25,
                "target_fatigue": 0.5,
                "thrower_consistency_modifier": 1.0,
                "target_consistency_modifier": 1.0,
            },
        },
        "probabilities": {"p_on_target": 0.74, "p_catch": 0.31},
        "rolls": {"on_target": 0.3, "catch": 0.6},
        "outcome": {"resolution": resolution},
        "state_diff": {"player_out": player_out} if player_out else {},
    }


def _snapshots() -> dict:
    return {
        "home": [
            {"id": "home_1", "name": "Power Captain", "archetype": "Power", "match_role": "active"},
            {"id": "home_2", "name": "Home Two", "archetype": "Precision", "match_role": "active"},
        ],
        "away": [
            {"id": "away_1", "name": "Away Target", "archetype": "Defense", "match_role": "active"},
            {"id": "away_2", "name": "Away Two", "archetype": "Precision", "match_role": "active"},
        ],
    }


def test_build_replay_proof_uses_saved_throw_context_without_engine_rerun():
    proof = build_replay_proof(
        [_throw_event("hit", player_out={"team": "away", "player_id": "away_1"})],
        name_map={"home_1": "Power Captain", "away_1": "Away Target", "away_2": "Away Two"},
        roster_snapshots=_snapshots(),
        home_club_id="home",
        away_club_id="away",
        home_survivors=2,
        away_survivors=1,
        player_match_stats={"home_1": PlayerMatchStats(minutes_played=4)},
    )

    event = proof["proof_events"][0]
    assert proof["key_play_indices"] == [0]
    assert event["sequence_index"] == 0
    assert event["thrower_name"] == "Power Captain"
    assert event["target_name"] == "Away Target"
    assert event["resolution"] == "hit"
    assert event["odds"] == {"p_on_target": 0.74, "p_catch": 0.31}
    assert event["rolls"] == {"on_target": 0.3, "catch": 0.6}
    assert "rush arrived" in event["tactic_context"]["items"][0]
    assert "synchronized attack" in event["tactic_context"]["items"][1]
    assert event["fatigue"]["thrower_fatigue"] == 1.25
    assert event["score_state"]["away_living"] == 1
    assert "mismatched Captain" in event["liability_context"]["items"][0]
    assert proof["evidence_report"]["evidence_lanes"][0]["summary"] == "Final survivors were 2-1."


def test_replay_proof_uses_narrative_pack_language_for_saved_context():
    proof = build_replay_proof(
        [_throw_event("hit", player_out={"team": "away", "player_id": "away_1"})],
        name_map={"home_1": "Power Captain", "away_1": "Away Target", "away_2": "Away Two"},
        roster_snapshots=_snapshots(),
        home_club_id="home",
        away_club_id="away",
    )

    event = proof["proof_events"][0]
    assert event["proof_tags"] == ["HIT", "RUSH", "SYNC", "EXHAUSTED", "LIABILITY"]
    assert event["summary"] == "A synced attack connects! Power Captain eliminates Away Target."
    assert "Target selection leaned toward Away Target" in event["decision_context"]["items"][0]
    assert any("rush arrived" in item for item in event["tactic_context"]["items"])
    assert any("synchronized attack triggered" in item.lower() for item in event["tactic_context"]["items"])
    assert any("High fatigue" in item for item in event["fatigue"]["items"])
    assert event["liability_context"]["items"] == [
        "Thrower suffered a liability penalty as a mismatched Captain (Power archetype)."
    ]


def test_replay_proof_does_not_invent_missing_evidence():
    event = _throw_event("dodged")
    event["context"] = {}
    proof = build_replay_proof(
        [event],
        name_map={},
        roster_snapshots={"home": [], "away": []},
        home_club_id="home",
        away_club_id="away",
    )

    assert proof["key_play_indices"] == []
    lanes = {lane["title"]: lane for lane in proof["evidence_report"]["evidence_lanes"]}
    assert lanes["Tactics proof"]["items"] == ["No saved tactic context was present on throw events."]
    assert lanes["Liability proof"]["items"] == ["No lineup liability appeared in the saved throw evidence."]
    assert lanes["Command plan"]["items"] == ["Neutral or direct simulations do not claim department-order effects."]
