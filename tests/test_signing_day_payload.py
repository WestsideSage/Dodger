"""Tests for the Signing Day card payload (reason lines + outcome kinds).

The reason line MUST tie to the user's interaction history with that
prospect. These tests assert that the classifier reads the action flags
and produces visibly different output for different histories.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from dodgeball_sim.signing_day_payload import (
    build_signing_card,
    build_signing_cards,
    classify_outcome_kind,
    reason_line,
)


# ---- classify_outcome_kind --------------------------------------------------


def test_my_signing_when_clubs_match():
    assert classify_outcome_kind(
        signing_club_id="user",
        player_club_id="user",
        actions={"contacted": True},
    ) == "my_signing"


def test_rival_signing_when_no_investment():
    assert classify_outcome_kind(
        signing_club_id="rival",
        player_club_id="user",
        actions=None,
    ) == "rival_signing"


def test_surprise_when_user_invested_but_rival_won():
    assert classify_outcome_kind(
        signing_club_id="rival",
        player_club_id="user",
        actions={"visited": True},
    ) == "surprise"

    assert classify_outcome_kind(
        signing_club_id="rival",
        player_club_id="user",
        actions={"contacted": True},
    ) == "surprise"


def test_lost_bid_is_a_surprise_even_without_courtship():
    """V16: a rival signing of a prospect the user actually BID on at Signing
    Day is a snipe — never a plain 'never on your board' rival signing."""
    assert classify_outcome_kind(
        signing_club_id="rival",
        player_club_id="user",
        actions=None,
        user_bid=True,
    ) == "surprise"


def test_lost_bid_reason_names_the_beaten_offer():
    line = reason_line(
        outcome_kind="surprise",
        actions=None,
        signing_club_name="Lunar Syndicate",
        user_bid=True,
    )
    assert line == "Lunar Syndicate's offer beat yours on Signing Day."
    courted = reason_line(
        outcome_kind="surprise",
        actions={"visited": True},
        signing_club_name="Lunar Syndicate",
        user_bid=True,
    )
    assert courted == (
        "Lunar Syndicate's offer beat yours on Signing Day despite a campus visit."
    )


def test_scout_only_is_not_a_surprise():
    """Scouting alone is information-gathering, not investment — losing a
    scouted-only prospect to a rival is a plain rival_signing, not a surprise."""
    assert classify_outcome_kind(
        signing_club_id="rival",
        player_club_id="user",
        actions={"scouted": True},
    ) == "rival_signing"


# ---- reason_line ------------------------------------------------------------


def test_reason_mentions_visit_for_my_signing_after_visit():
    text = reason_line(
        outcome_kind="my_signing",
        actions={"visited": True, "contacted": True, "scouted": True},
        signing_club_name="Aurora",
    )
    assert "visit" in text.lower()
    assert text.startswith("Signed with you")


def test_reason_mentions_contact_for_my_signing_after_contact():
    text = reason_line(
        outcome_kind="my_signing",
        actions={"contacted": True, "scouted": True},
        signing_club_name="Aurora",
    )
    assert "contact" in text.lower()


def test_reason_calls_out_rival_for_surprise():
    text = reason_line(
        outcome_kind="surprise",
        actions={"visited": True},
        signing_club_name="Aurora",
    )
    # The surprise line must name the rival club and reference the
    # interaction the user actually had with the prospect.
    assert "Aurora" in text
    assert "visit" in text.lower()


def test_reason_for_rival_signing_with_no_history():
    text = reason_line(
        outcome_kind="rival_signing",
        actions=None,
        signing_club_name="Aurora",
    )
    assert "Aurora" in text
    assert "never" in text.lower()


def test_reason_for_rival_signing_after_scout_only():
    text = reason_line(
        outcome_kind="rival_signing",
        actions={"scouted": True},
        signing_club_name="Aurora",
    )
    assert "Aurora" in text
    assert "scout" in text.lower()


def test_reason_differs_for_different_histories():
    """Sanity: the SAME outcome with different action histories must
    produce different reason strings — this is the gating quality bar."""
    no_history = reason_line(
        outcome_kind="my_signing", actions=None, signing_club_name="Aurora"
    )
    visited = reason_line(
        outcome_kind="my_signing",
        actions={"visited": True},
        signing_club_name="Aurora",
    )
    contacted = reason_line(
        outcome_kind="my_signing",
        actions={"contacted": True},
        signing_club_name="Aurora",
    )
    assert no_history != visited
    assert no_history != contacted
    assert visited != contacted


# ---- build_signing_card -----------------------------------------------------


def _make_signing(player_id="p1", club_id="rival", round_number=1):
    return SimpleNamespace(
        season_id="2026",
        round_number=round_number,
        club_id=club_id,
        player_id=player_id,
        source="ai",
        offer_strength=80.0,
        recap_reason="",
    )


def _make_player(player_id="p1", name="Alex", ovr=72.0, archetype="Sharpshooter"):
    return SimpleNamespace(
        id=player_id,
        name=name,
        archetype=archetype,
        overall_skill=lambda: ovr,
    )


def _make_prospect(player_id="p1", name="Alex", role="Sharpshooter", band=(65, 75)):
    return SimpleNamespace(
        player_id=player_id,
        name=name,
        public_archetype_guess=role,
        public_ratings_band={"ovr": band},
    )


def test_card_uses_player_ovr_when_available():
    card = build_signing_card(
        signing=_make_signing(club_id="user"),
        player=_make_player(ovr=74.0),
        prospect=_make_prospect(band=(60, 65)),
        club_name="User FC",
        player_club_id="user",
        actions={"visited": True},
    )
    assert card["ovr"] == 74
    assert card["outcome_kind"] == "my_signing"
    assert card["user_interaction"]["visited"] is True
    assert "visit" in card["reason"].lower()


def test_card_falls_back_to_prospect_band_midpoint_when_no_player():
    card = build_signing_card(
        signing=_make_signing(club_id="rival"),
        player=None,
        prospect=_make_prospect(band=(60, 70)),
        club_name="Rival FC",
        player_club_id="user",
        actions=None,
    )
    assert card["ovr"] == 65
    assert card["outcome_kind"] == "rival_signing"
    assert card["role"] == "Sharpshooter"


# ---- build_signing_cards (end-to-end shape) --------------------------------


def test_build_signing_cards_joins_actions_by_player_id():
    signings = [
        _make_signing(player_id="p1", club_id="user"),
        _make_signing(player_id="p2", club_id="rival"),
    ]
    rosters = {
        "user": [_make_player(player_id="p1", name="Alex", ovr=70.0)],
        "rival": [_make_player(player_id="p2", name="Sam", ovr=68.0)],
    }
    prospects_by_id = {
        "p1": _make_prospect(player_id="p1", name="Alex"),
        "p2": _make_prospect(player_id="p2", name="Sam"),
    }
    clubs = {
        "user": SimpleNamespace(name="User FC"),
        "rival": SimpleNamespace(name="Aurora"),
    }
    actions_by_player = {
        "p1": {"visited": True, "contacted": True, "scouted": True},
        "p2": {"contacted": True},  # user invested in p2 but rival won
    }
    cards = build_signing_cards(
        signings=signings,
        rosters=rosters,
        prospects_by_id=prospects_by_id,
        clubs=clubs,
        player_club_id="user",
        actions_by_player=actions_by_player,
    )
    assert len(cards) == 2
    by_id = {c["player_id"]: c for c in cards}
    assert by_id["p1"]["outcome_kind"] == "my_signing"
    assert by_id["p2"]["outcome_kind"] == "surprise"
    assert "Aurora" in by_id["p2"]["reason"]
    assert "contact" in by_id["p2"]["reason"].lower()


def test_build_signing_cards_handles_empty_actions_dict():
    cards = build_signing_cards(
        signings=[_make_signing(player_id="p1", club_id="rival")],
        rosters={"rival": [_make_player(player_id="p1", ovr=64.0)]},
        prospects_by_id={"p1": _make_prospect(player_id="p1")},
        clubs={"rival": SimpleNamespace(name="Aurora")},
        player_club_id="user",
        actions_by_player={},
    )
    assert len(cards) == 1
    assert cards[0]["outcome_kind"] == "rival_signing"
    assert cards[0]["user_interaction"] == {
        "scouted": False,
        "contacted": False,
        "visited": False,
        "locked_out": False,
    }
