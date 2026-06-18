"""V27 The Calendar — Phase 4: Ruleset Invitationals (Cloth Classic / No-Sting Open).

An invitational is an auto-simmed knockout resolved in ONE pass under a NON-foam
ruleset (``OfficialEngineAdapter(RulesetSelection.OFFICIAL_CLOTH/_NO_STING)``).
The pure bracket structure reuses ``cup.generate_cup_bracket`` (no
``cup_brackets`` table — invitationals resolve in one pass and record into the
shared ``v27_events_json`` store as :class:`EventResult` bracket rows). A single
champion is produced; draws are impossible (game-points -> overall-skill ->
seeded-alphabetical tiebreak, mirroring ``cup_service._pick_cup_winner``).

Architecture guardrails (non-negotiable):
- NON-FOAM engine only. ``run_invitational`` refuses a foam selection (the foam
  league + Domestic Cup are the foam surfaces; the invitational is the
  cloth/no-sting surface). ``decide_cloth_game_by_active_count`` is never
  called on a foam match — the engine guards it on
  ``profile.material == CLOTH`` (pinned by the foam-isolation test).
- Match-ids ENCODE THE ROUND LABEL so the official engine's match-clock
  resolution is correct (the trap): ``run_autonomous_match`` derives the clock
  from match_id substrings ("semifinal" -> 30 min, "final" -> 40 min, else
  24 min). A knockout match-id must carry "quarterfinal"/"semifinal"/"final".
- New seed namespace ``v27_invitational``; deterministic per
  ``(season_id, ruleset)``.
- Pyramid-gated by the caller (the offseason wiring gates on
  ``player_club_id`` + ``pyramid_world_active``); legacy single-league saves
  never reach this module.
- No DB writes here beyond what the shared ``event_calendar`` helpers do — the
  caller awards the purse + warmth + records the event. This module is the pure
  runner; ``resolve_ruleset_invitationals`` (also here) is the wired wrapper.
"""
from __future__ import annotations

import sqlite3
from typing import List, Optional, Tuple

from .cup import CupBracket, CupEntrant, generate_cup_bracket
from .event_calendar import EventBracketRow, EventResult
from .franchise import simulate_match
from .rng import DeterministicRNG, derive_seed
from .rulesets import RulesetSelection
from .scheduler import ScheduledMatch


# Invitational event keys + display names (one per non-foam ruleset).
_INVITATIONAL_META = {
    RulesetSelection.OFFICIAL_CLOTH: ("cloth_classic", "Cloth Classic"),
    RulesetSelection.OFFICIAL_NO_STING: ("no_sting_open", "No-Sting Open"),
}


def _round_label(round_number: int, total_rounds: int) -> str:
    """The round label embedded in the match-id (drives the engine clock) and
    recorded on the bracket row. Mirrors ``cup_service._round_label``."""
    if round_number == total_rounds:
        return "Final"
    if round_number == total_rounds - 1:
        return "Semifinal"
    if round_number == total_rounds - 2:
        return "Quarterfinal"
    return f"Round {round_number}"


def _round_slug(label: str) -> str:
    """The lowercase slug embedded in the match-id (``semifinal``/``final``)."""
    return label.lower().replace(" ", "_")


def _invitational_match_id(
    *, event_key: str, season_id: str, label: str, slot: int,
    home_id: str, away_id: str,
) -> str:
    """Build a knockout match-id that encodes the round label so
    ``run_autonomous_match``'s clock resolution picks the right clock."""
    slug = _round_slug(label)
    return (
        f"inv_{event_key}_{season_id}_{slug}_m{slot}_{home_id}_vs_{away_id}"
    )


def _resolve_side(side: Optional[CupEntrant], results: dict) -> str | None:
    """Resolve one side of a bracket match to a club id (mirrors cup_service)."""
    if side is None:
        return None
    if side.club_id:
        return str(side.club_id)
    if side.source_match_id:
        return results.get(str(side.source_match_id))
    return None


def _pick_invitational_winner(
    record, rosters: dict, home_id: str, away_id: str,
) -> Tuple[str, str]:
    """Deterministic winner pick — NO draws (mirrors ``cup_service._pick_cup_winner``).

    The official engine can return a None winner (match-clock tie on equal game
    points); the invitational must always advance someone. Game points (the
    official scoring economy) decide first, then overall skill, then a seeded
    alphabetical tiebreak.
    """
    if record.result.winner_team_id is not None:
        return record.result.winner_team_id, "regulation"
    meta = record.result.official_metadata or {}
    home_gp = int(meta.get("team_a_game_points", 0))
    away_gp = int(meta.get("team_b_game_points", 0))
    if home_gp != away_gp:
        return (home_id if home_gp > away_gp else away_id), "game-points tiebreak"
    home_ovr = sum(player.overall_skill() for player in rosters[home_id])
    away_ovr = sum(player.overall_skill() for player in rosters[away_id])
    if home_ovr != away_ovr:
        return (home_id if home_ovr > away_ovr else away_id), "overall tiebreak"
    return min(home_id, away_id), "seeded tiebreak"


def run_invitational(
    conn: sqlite3.Connection,
    season_id: str,
    ruleset_selection: RulesetSelection,
    invitees: List[str],
    root_seed: int,
) -> Optional[EventResult]:
    """Auto-sim a single-elimination knockout under a non-foam ruleset to one
    champion, via :class:`OfficialEngineAdapter` (routed through
    ``franchise.simulate_match`` with the given ``ruleset_selection``).

    Returns an :class:`EventResult` (champion + bracket rows), or ``None`` when
    fewer than 2 invitees cannot form a bracket. Pure sim: no match_records are
    persisted (the invitational is not a league fixture); only the caller
    records the returned result into ``v27_events_json``. The foam league and
    Domestic Cup are untouched.

    Deterministic per ``(root_seed, season_id, ruleset_selection, invitees)``.
    """
    if ruleset_selection == RulesetSelection.OFFICIAL_FOAM or not ruleset_selection.is_official():
        raise ValueError(
            "run_invitational is for non-foam rulesets only (cloth / no-sting); "
            f"got {ruleset_selection!r}"
        )
    if len(invitees) < 2:
        return None

    event_key, event_name = _INVITATIONAL_META[ruleset_selection]
    bracket_seed = derive_seed(
        root_seed, "v27_invitational", season_id, ruleset_selection.value
    )
    bracket = generate_cup_bracket(
        sorted(str(cid) for cid in invitees),
        DeterministicRNG(bracket_seed),
    )

    from .persistence import load_club_roster, load_clubs

    clubs = load_clubs(conn)
    rosters = {cid: load_club_roster(conn, cid) for cid in clubs}

    total_rounds = bracket.total_rounds
    results: dict[str, str] = {}
    bracket_rows: List[EventBracketRow] = []

    for round_ in bracket.rounds:
        round_number = round_.round_number
        label = _round_label(round_number, total_rounds)
        for slot_index, match in enumerate(round_.matches, start=1):
            match_id = match.match_id
            if match.is_bye:
                # Bye: the auto-advance club moves on; no row recorded (no
                # match was played), mirroring the cup resolver.
                results[match_id] = str(match.auto_advance_club_id)
                continue
            home_id = _resolve_side(match.side_a, results)
            away_id = _resolve_side(match.side_b, results)
            if home_id is None or away_id is None:
                # Bracket not yet resolvable upstream — should not happen in a
                # sequential walk, but guard regardless.
                continue
            scheduled = ScheduledMatch(
                match_id=_invitational_match_id(
                    event_key=event_key, season_id=season_id, label=label,
                    slot=slot_index, home_id=home_id, away_id=away_id,
                ),
                season_id=season_id,
                week=100 + round_number,
                home_club_id=home_id,
                away_club_id=away_id,
            )
            record, _ = simulate_match(
                scheduled=scheduled,
                home_club=clubs[home_id],
                away_club=clubs[away_id],
                home_roster=rosters[home_id],
                away_roster=rosters[away_id],
                root_seed=derive_seed(
                    root_seed, "v27_invitational_match",
                    season_id, ruleset_selection.value, scheduled.match_id,
                ),
                config_version="phase1.v1",
                difficulty="pro",
                meta_patch=None,
                ruleset_selection=ruleset_selection.value,
            )
            winner_id, _tiebreak = _pick_invitational_winner(
                record, rosters, home_id, away_id
            )
            results[match_id] = winner_id
            bracket_rows.append(EventBracketRow(
                round=label,
                home_club_id=home_id,
                away_club_id=away_id,
                winner_club_id=winner_id,
                home_club_name=clubs[home_id].name,
                away_club_name=clubs[away_id].name,
            ))

    champion_club_id = results[bracket.final_match_id]
    return EventResult(
        event_key=event_key,
        event_name=event_name,
        season_id=season_id,
        champion_club_id=champion_club_id,
        champion_club_name=clubs[champion_club_id].name,
        ruleset=ruleset_selection.value,
        purse_k=0,
        bracket=tuple(bracket_rows),
    )


__all__ = [
    "run_invitational",
]
