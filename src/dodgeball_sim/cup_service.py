"""V27 The Calendar — Phase 2: the web home for the Domestic Cup.

The dormant pure-bracket model in ``cup.py`` (kept import-pure per
``test_cup_module_has_no_db_boundary_imports``) gets a web home here. All
DB + sim wiring lives in this module; ``cup.py`` stays pure. The CLI's
``_simulate_next_cup_round`` / ``_award_cup_champion_if_ready`` /
``_pick_cup_winner`` (in ``dynasty_cli.py``) are the reference implementation —
their logic is MIRRORED here, never imported (the CLI carries print deps).

Architecture guardrails (non-negotiable):
- Foam engine only (the standard ``simulate_match`` path; no cloth/no-sting).
- New seed namespace ``v27_cup``: ``derive_seed(root_seed, 'v27_cup', season_id)``.
- ``cup_id = f"{season_id}_domestic_cup"`` (distinct from the legacy CLI cup).
- ``meta_patch=None`` (MetaPatch is retired; do not revive it).
- Pyramid-gated by the caller; legacy single-league saves never reach this.
- Purses + fans idempotent via per-event guards (the V26 pattern).
"""
from __future__ import annotations

import sqlite3
from typing import Dict, List

from .cup import CupBracket, generate_cup_bracket
from .rng import DeterministicRNG, derive_seed


_DOMESTIC_CUP_EVENT_KEY = "domestic_cup"
_DOMESTIC_CUP_NAME = "Domestic Cup"
_CUP_ID_SUFFIX = "_domestic_cup"
_RESOLVED_GUARD = "v27_domestic_cup_resolved_for"
_FANS_GUARD = "v27_domestic_cup_fans_for"


def _cup_id(season_id: str) -> str:
    return f"{season_id}{_CUP_ID_SUFFIX}"


def _cup_bracket_to_payload(bracket: CupBracket) -> dict:
    """Serialize a ``CupBracket`` to the dict shape ``load_cup_bracket`` returns.

    Mirrors ``dynasty_cli._cup_bracket_to_payload`` (the CLI private helper) —
    replicated here so ``cup_service`` never imports the CLI.
    """
    return {
        "club_ids": list(bracket.club_ids),
        "rounds": [
            {
                "round_number": round_.round_number,
                "matches": [
                    {
                        "match_id": match.match_id,
                        "round_number": match.round_number,
                        "slot_number": match.slot_number,
                        "side_a": {
                            "club_id": match.side_a.club_id,
                            "source_match_id": match.side_a.source_match_id,
                        },
                        "side_b": None
                        if match.side_b is None
                        else {
                            "club_id": match.side_b.club_id,
                            "source_match_id": match.side_b.source_match_id,
                        },
                        "auto_advance_club_id": match.auto_advance_club_id,
                    }
                    for match in round_.matches
                ],
            }
            for round_ in bracket.rounds
        ],
    }


def _division_club_ids(conn: sqlite3.Connection, season_id: str) -> List[str]:
    """All club ids with a division seat this season (the 28-club pyramid)."""
    from .persistence import load_division_memberships

    return [m.club_id for m in load_division_memberships(conn, season_id)]


def ensure_domestic_cup(
    conn: sqlite3.Connection, season_id: str, root_seed: int
) -> dict:
    """Generate + persist the cross-division Domestic Cup bracket, once.

    Idempotent: if a bracket already exists for this season it is returned
    as-is (never regenerated/overwritten). The bracket covers ALL division
    clubs (the 28-club pyramid), seeded deterministically via the ``v27_cup``
    namespace. Bye matches have their auto-advance winners persisted as cup
    results so the resolver can walk the bracket without special-casing byes.

    Returns the persisted bracket row (``{"cup_id", "season_id", "bracket"}``).
    """
    from .persistence import (
        load_cup_bracket,
        save_cup_bracket,
        save_cup_result,
    )

    existing = load_cup_bracket(conn, season_id)
    if existing is not None:
        return existing

    club_ids = _division_club_ids(conn, season_id)
    bracket = generate_cup_bracket(
        sorted(club_ids),
        DeterministicRNG(derive_seed(root_seed, "v27_cup", season_id)),
    )
    cup_id = _cup_id(season_id)
    payload = _cup_bracket_to_payload(bracket)
    save_cup_bracket(conn, cup_id, season_id, payload)

    # Persist bye (auto-advance) results up front so the resolver walks a
    # uniformly-populated results map (mirrors the CLI's _ensure_season_artifacts).
    for round_payload in payload["rounds"]:
        for match in round_payload["matches"]:
            if match["auto_advance_club_id"]:
                save_cup_result(
                    conn,
                    cup_id,
                    int(round_payload["round_number"]),
                    str(match["match_id"]),
                    str(match["auto_advance_club_id"]),
                )
    conn.commit()
    return load_cup_bracket(conn, season_id)


__all__ = [
    "ensure_domestic_cup",
]
