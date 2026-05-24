from __future__ import annotations

from dodgeball_sim.highlights import build_highlight_package


def _event(event_id: int, tick: int, resolution: str, thrower: str, target: str) -> dict:
    state_diff = {}
    if resolution in {"hit", "failed_catch", "catch"}:
        state_diff = {
            "player_out": {
                "team": "away" if target.startswith("away") else "home",
                "player_id": target if resolution != "catch" else thrower,
            }
        }
    return {
        "event_id": event_id,
        "tick": tick,
        "event_type": "throw",
        "phase": "live",
        "actors": {"thrower": thrower, "target": target},
        "outcome": {"resolution": resolution},
        "state_diff": state_diff,
        "label": f"{thrower} {resolution} {target}",
        "detail": f"Tick {tick}",
    }


def _proof(sequence_index: int, tick: int, event_id: int, resolution: str, home_living: int, away_living: int) -> dict:
    return {
        "sequence_index": sequence_index,
        "tick": tick,
        "event_id": event_id,
        "thrower_id": "home_1" if tick < 20 else "away_1",
        "target_id": "away_1" if tick < 20 else "home_1",
        "resolution": resolution,
        "summary": f"proof-{event_id}",
        "detail": f"detail-{event_id}",
        "score_state": {
            "home_living": home_living,
            "away_living": away_living,
            "home_eliminated_player_ids": [],
            "away_eliminated_player_ids": [],
        },
    }


def test_build_highlight_package_selects_real_beats_with_valid_sources() -> None:
    events = [
        _event(1, 1, "miss", "home_1", "away_1"),
        _event(2, 2, "hit", "home_1", "away_1"),
        _event(3, 5, "hit", "home_2", "away_2"),
        _event(4, 9, "catch", "away_1", "home_1"),
        _event(5, 12, "failed_catch", "home_3", "away_3"),
        _event(6, 20, "hit", "away_1", "home_2"),
    ]
    proof_events = [
        _proof(0, 1, 1, "miss", 6, 6),
        _proof(1, 2, 2, "hit", 6, 5),
        _proof(2, 5, 3, "hit", 6, 4),
        _proof(3, 9, 4, "catch", 5, 4),
        _proof(4, 12, 5, "failed_catch", 5, 3),
        _proof(5, 20, 6, "hit", 4, 3),
    ]
    moment_events = [
        {
            "kind": "dramatic_catch",
            "match_id": "m1",
            "tick": 9,
            "catcher_id": "away_1",
            "returning_player_id": "away_4",
            "display_text": "Away 1 flips the match with a catch.",
        },
        {
            "kind": "comeback",
            "match_id": "m1",
            "tick": 20,
            "team_id": "away",
            "deficit_at_low_point": 2,
            "catches_during_comeback": 1,
            "display_text": "Away claw back into it.",
        },
    ]
    name_map = {
        "home_1": "Home One",
        "home_2": "Home Two",
        "home_3": "Home Three",
        "away_1": "Away One",
        "away_2": "Away Two",
        "away_3": "Away Three",
    }

    beats = build_highlight_package(
        events=events,
        proof_events=proof_events,
        moment_events=moment_events,
        name_map=name_map,
    )

    assert 4 <= len(beats) <= 6
    assert beats[0].kind == "opening"
    assert beats[0].source_event_id == 2
    assert beats[-1].kind == "finish"
    assert beats[-1].source_event_id == 6
    assert any(beat.kind == "moment" and beat.source_event_id == 4 for beat in beats)
    assert any(beat.source_event_id == 6 for beat in beats)
    assert len({beat.source_event_id for beat in beats}) == len(beats)
    assert all(beat.proof_source.startswith("event:") for beat in beats)


def test_build_highlight_package_is_deterministic_and_deduplicates_event_ids() -> None:
    events = [
        _event(7, 3, "hit", "home_1", "away_1"),
        _event(8, 7, "catch", "away_1", "home_1"),
        _event(9, 11, "hit", "home_2", "away_2"),
    ]
    proof_events = [
        _proof(0, 3, 7, "hit", 6, 5),
        _proof(1, 7, 8, "catch", 5, 5),
        _proof(2, 11, 9, "hit", 5, 4),
    ]
    moment_events = [
        {
            "kind": "dramatic_catch",
            "match_id": "m2",
            "tick": 7,
            "catcher_id": "away_1",
            "returning_player_id": "away_4",
            "display_text": "A huge catch.",
        },
        {
            "kind": "late_game_escape",
            "match_id": "m2",
            "tick": 11,
            "survivor_id": "home_2",
            "attacker_count": 3,
            "display_text": "Late-game survival.",
        },
    ]

    first = build_highlight_package(
        events=events,
        proof_events=proof_events,
        moment_events=moment_events,
        name_map={},
    )
    second = build_highlight_package(
        events=events,
        proof_events=proof_events,
        moment_events=moment_events,
        name_map={},
    )

    assert first == second
    assert len({beat.source_event_id for beat in first}) == len(first)
