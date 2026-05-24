from __future__ import annotations

from dodgeball_sim.broadcast import build_broadcast_frame, build_commentary_inserts


def test_build_broadcast_frame_tags_playoff_rivalry_and_degrades_without_trajectory() -> None:
    frame = build_broadcast_frame(
        season_id="season_1",
        match_id="season_1_p_final",
        week=6,
        player_club_id="aurora",
        opponent_club_id="blaze",
        rivalry_summary={
            "club_a_id": "aurora",
            "club_b_id": "blaze",
            "rivalry": {
                "rivalry_score": 71.0,
                "total_meetings": 5,
                "playoff_meetings": 2,
                "championship_meetings": 1,
            },
        },
        last_meeting={
            "week": 5,
            "winner_club_id": "blaze",
            "home_survivors": 2,
            "away_survivors": 1,
        },
        trajectory_row=None,
    )

    assert frame.stakes_tag is not None
    assert frame.stakes_tag.label == "Playoff Final"
    assert frame.rivalry_tag is not None
    assert frame.rivalry_tag.label == "Rivalry Game"
    assert frame.archetype_tag is None
    assert frame.historical_hook is not None
    assert "championship" in frame.historical_hook.text.lower()
    assert frame.voice_slot == "broadcast.playoff_final"


def test_build_broadcast_frame_is_deterministic_for_same_inputs() -> None:
    kwargs = {
        "season_id": "season_1",
        "match_id": "season_1_p_r1_m1",
        "week": 5,
        "player_club_id": "aurora",
        "opponent_club_id": "comets",
        "rivalry_summary": {
            "club_a_id": "aurora",
            "club_b_id": "comets",
            "rivalry": {"rivalry_score": 44.0, "total_meetings": 2},
        },
        "last_meeting": None,
        "trajectory_row": None,
    }

    first = build_broadcast_frame(**kwargs)
    second = build_broadcast_frame(**kwargs)

    assert first == second


def test_commentary_inserts_only_render_when_record_claim_is_still_true() -> None:
    events = [
        {
            "event_id": 14,
            "tick": 14,
            "event_type": "throw",
            "actors": {"thrower": "ace", "target": "target"},
            "outcome": {"resolution": "hit"},
            "state_diff": {"player_out": {"team": "away", "player_id": "target"}},
        }
    ]
    name_map = {"ace": "Avery Cross", "target": "Tala Hart"}
    record_items = [
        {
            "record_type": "most_career_eliminations",
            "holder_id": "ace",
            "holder_type": "player",
            "record_value": 218,
            "set_in_season": "season_1",
            "record": {
                "holder_name": "Avery Cross",
                "detail": "Career elimination leader.",
            },
        }
    ]

    inserts = build_commentary_inserts(events, record_items=record_items, name_map=name_map)

    assert len(inserts) == 1
    assert inserts[0].source_event_id == 14
    assert inserts[0].source_record_id == "most_career_eliminations"
    assert "Avery Cross" in inserts[0].text

    stale_records = [
        {
            **record_items[0],
            "holder_id": "someone_else",
            "record": {
                "holder_name": "Someone Else",
                "detail": "Career elimination leader.",
            },
        }
    ]
    assert build_commentary_inserts(events, record_items=stale_records, name_map=name_map) == []
