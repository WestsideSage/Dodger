"""Signing Day payload builder.

Turns the raw `recruitment_signing` rows into card-ready records that
surface the user's recruiting interaction history per prospect, plus a
one-line reason that ties the outcome to those interactions.

The reason classifier and outcome-kind logic are pure functions so they
are easy to unit test in isolation (`tests/test_signing_day_payload.py`).
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional


# ---- Pure classifiers (no I/O) ---------------------------------------------


def classify_outcome_kind(
    *,
    signing_club_id: str,
    player_club_id: str,
    actions: Mapping[str, Any] | None,
    user_bid: bool = False,
) -> str:
    """Return one of: "my_signing", "rival_signing", "surprise".

    A surprise is a rival signing of a prospect the user invested in
    (contacted or visited) — or one the user actually BID on at Signing Day
    and lost (a snipe). Pure-info rival signings are "rival_signing".
    """
    is_user_signing = signing_club_id == player_club_id and bool(player_club_id)
    if is_user_signing:
        return "my_signing"
    actions = actions or {}
    if user_bid or actions.get("contacted") or actions.get("visited"):
        return "surprise"
    return "rival_signing"


def reason_line(
    *,
    outcome_kind: str,
    actions: Mapping[str, Any] | None,
    signing_club_name: str,
    user_bid: bool = False,
) -> str:
    """Return a single-line reason tying the outcome to user interactions.

    Reasons reflect the boolean action flags only (scouted/contacted/visited)
    — the underlying schema is bool-per-action, not counts.
    """
    actions = actions or {}
    scouted = bool(actions.get("scouted"))
    contacted = bool(actions.get("contacted"))
    visited = bool(actions.get("visited"))
    locked_out = bool(actions.get("locked_out"))

    def _investment_phrase() -> str:
        parts = []
        if visited:
            parts.append("a campus visit")
        if contacted:
            parts.append("a contact call")
        if scouted and not (contacted or visited):
            parts.append("a scout report")
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0]
        if len(parts) == 2:
            return f"{parts[0]} and {parts[1]}"
        return ", ".join(parts[:-1]) + f", and {parts[-1]}"

    if outcome_kind == "my_signing":
        investment = _investment_phrase()
        if visited:
            return f"Signed with you after {investment}."
        if contacted:
            return f"Signed with you after {investment}."
        if scouted:
            return "Signed with you off the strength of your scout report."
        return "Signed with you despite no prior contact."

    if outcome_kind == "surprise":
        investment = _investment_phrase()
        if locked_out:
            return f"Locked out before signing day — went to {signing_club_name} despite {investment}."
        if user_bid:
            if investment:
                return (
                    f"{signing_club_name}'s offer beat yours on Signing Day "
                    f"despite {investment}."
                )
            return f"{signing_club_name}'s offer beat yours on Signing Day."
        if investment:
            return f"Lost to {signing_club_name} despite {investment}."
        return f"Signed with {signing_club_name} — a surprise destination."

    # rival_signing
    if scouted:
        return f"Signed with {signing_club_name} — you scouted but never made contact."
    return f"Signed with {signing_club_name} — never on your board."


# ---- Card assembly ---------------------------------------------------------


def build_signing_card(
    *,
    signing,
    player,
    prospect,
    club_name: str,
    player_club_id: str,
    actions: Mapping[str, Any] | None,
    user_bid: bool = False,
) -> dict[str, Any]:
    """Assemble a single signing-day card record.

    `player` is the Player object (from any roster) if it exists, else None.
    `prospect` is the Prospect object from the pool, used as fallback for
    OVR estimate when no Player record exists.
    """
    actions = dict(actions or {})
    outcome_kind = classify_outcome_kind(
        signing_club_id=signing.club_id,
        player_club_id=player_club_id,
        actions=actions,
        user_bid=user_bid,
    )
    name = None
    ovr: Optional[int] = None
    role = ""
    if player is not None:
        name = player.name
        try:
            ovr = player.overall_skill()
        except Exception:
            ovr = None
        role = getattr(player, "archetype", "") or ""
    if name is None and prospect is not None:
        name = prospect.name
    if ovr is None and prospect is not None:
        low, high = prospect.public_ratings_band.get("ovr", (0, 0))
        ovr = int(round((low + high) / 2))
    if not role and prospect is not None:
        role = getattr(prospect, "public_archetype_guess", "") or ""
    # PT4-07: archetypes reach the class report as display names, never raw
    # enum keys ("dodger_anchor" leaked verbatim onto the cards).
    from .models import archetype_display_name

    role = archetype_display_name(str(getattr(role, "value", role) or ""))

    return {
        "player_id": signing.player_id,
        "name": name or signing.player_id,
        "ovr": int(ovr or 0),
        "role": role,
        "club_id": signing.club_id,
        "club_name": club_name,
        "user_interaction": {
            "scouted": bool(actions.get("scouted")),
            "contacted": bool(actions.get("contacted")),
            "visited": bool(actions.get("visited")),
            "locked_out": bool(actions.get("locked_out")),
        },
        "outcome_kind": outcome_kind,
        "reason": reason_line(
            outcome_kind=outcome_kind,
            actions=actions,
            signing_club_name=club_name,
            user_bid=user_bid,
        ),
        "round_number": int(getattr(signing, "round_number", 0) or 0),
    }


def build_signing_cards(
    *,
    signings: Iterable,
    rosters: Mapping[str, list],
    prospects_by_id: Mapping[str, Any],
    clubs: Mapping[str, Any],
    player_club_id: str,
    actions_by_player: Mapping[str, Mapping[str, Any]] | None,
    user_bid_player_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Build the full list of signing cards for the signing-day beat.

    ``user_bid_player_ids``: prospects the user made a Signing Day offer on
    (V16 contested rounds) — a rival signing of one of these is a snipe and
    must say so, not "never on your board".
    """
    actions_by_player = actions_by_player or {}
    user_bid_player_ids = user_bid_player_ids or set()

    def _find_player(player_id: str):
        for roster in rosters.values():
            for p in roster:
                if p.id == player_id:
                    return p
        return None

    def _club_name(club_id: str) -> str:
        club = clubs.get(club_id)
        return getattr(club, "name", None) or club_id

    cards = []
    for signing in signings:
        player = _find_player(signing.player_id)
        prospect = prospects_by_id.get(signing.player_id)
        card = build_signing_card(
            signing=signing,
            player=player,
            prospect=prospect,
            club_name=_club_name(signing.club_id),
            player_club_id=player_club_id,
            actions=actions_by_player.get(signing.player_id),
            user_bid=signing.player_id in user_bid_player_ids,
        )
        cards.append(card)
    return cards


__all__ = [
    "classify_outcome_kind",
    "reason_line",
    "build_signing_card",
    "build_signing_cards",
]
