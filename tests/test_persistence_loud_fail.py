from __future__ import annotations

import pytest

from dodgeball_sim.persistence import _player_from_dict


def test_loud_fail_on_missing_v2_ratings():
    legacy = {
        "id": "p1",
        "name": "Legacy",
        "ratings": {
            "accuracy": 60,
            "power": 60,
            "dodge": 60,
            "catch": 60,
            "stamina": 60,
            "tactical_iq": 60,
        },
        "archetype": "thrower",
        "traits": {},
        "age": 25,
        "club_id": "c1",
        "newcomer": False,
    }

    with pytest.raises(ValueError) as exc_info:
        _player_from_dict(legacy)

    message = str(exc_info.value)
    for required in ("catch_courage", "throw_selection_iq", "conditioning_curve"):
        assert required in message


def test_loud_fail_on_missing_archetype():
    payload = {
        "id": "p1",
        "name": "P",
        "ratings": {
            "accuracy": 60,
            "power": 60,
            "dodge": 60,
            "catch": 60,
            "stamina": 60,
            "tactical_iq": 60,
            "catch_courage": 50,
            "throw_selection_iq": 50,
            "conditioning_curve": 50,
        },
        "traits": {},
        "age": 25,
        "club_id": "c1",
        "newcomer": False,
    }

    with pytest.raises(ValueError) as exc_info:
        _player_from_dict(payload)

    assert "archetype" in str(exc_info.value)


def test_loud_fail_on_unknown_archetype_value():
    payload = {
        "id": "p1",
        "name": "P",
        "ratings": {
            "accuracy": 60,
            "power": 60,
            "dodge": 60,
            "catch": 60,
            "stamina": 60,
            "tactical_iq": 60,
            "catch_courage": 50,
            "throw_selection_iq": 50,
            "conditioning_curve": 50,
        },
        "archetype": "Tactical",
        "traits": {},
        "age": 25,
        "club_id": "c1",
        "newcomer": False,
    }

    with pytest.raises(ValueError):
        _player_from_dict(payload)


def test_clean_v2_payload_loads():
    payload = {
        "id": "p1",
        "name": "P",
        "ratings": {
            "accuracy": 60,
            "power": 60,
            "dodge": 60,
            "catch": 60,
            "stamina": 60,
            "tactical_iq": 60,
            "catch_courage": 70,
            "throw_selection_iq": 65,
            "conditioning_curve": 55,
        },
        "archetype": "thrower_catcher",
        "traits": {},
        "age": 25,
        "club_id": "c1",
        "newcomer": False,
    }

    player = _player_from_dict(payload)

    assert player.ratings.catch_courage == 70
    assert player.archetype.value == "thrower_catcher"
