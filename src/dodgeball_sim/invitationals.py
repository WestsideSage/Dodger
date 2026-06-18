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

# The two ruleset invitationals resolve in this fixed order (deterministic).
_INVITATIONAL_RULESETS: Tuple[RulesetSelection, ...] = (
    RulesetSelection.OFFICIAL_CLOTH,
    RulesetSelection.OFFICIAL_NO_STING,
)

# The invitational field size: the top-N fame-qualified clubs by standing. A
# clean 8-team knockout (quarterfinal -> semifinal -> final) is the default;
# smaller qualified fields still form a valid bracket (byes pad to a power of
# two via generate_cup_bracket).
_INVITATIONAL_FIELD_SIZE = 8

# V26 warmth coexistence: the prospect-showcase warmth lives in a SEPARATE state
# key (NOT v26_credibility_bonus) so a media credibility bonus and an
# invitational warmth in the same offseason both reach recruiting (summed, not
# clobbered). ``recruiting_office._credibility`` sums ``media_credibility_bonus``
# + ``invitational_warmth``. Both are one-offseason effects: offseason init
# zeroes BOTH (``reset_credibility_bonus`` + ``reset_invitational_warmth``)
# before this offseason's invitational resolves and before next offseason's
# recruiting runs.
_WARMTH_KEY = "v27_invitational_warmth"


def invitational_warmth(conn: sqlite3.Connection) -> int:
    """The current invitational warmth bonus (summed into recruiting credibility
    alongside the V26 media bonus). 0 when no invitational has been won this
    offseason or after the offseason reset."""
    from .persistence import get_state

    try:
        return int(get_state(conn, _WARMTH_KEY) or 0)
    except (TypeError, ValueError):
        return 0


def reset_invitational_warmth(conn: sqlite3.Connection) -> None:
    """Clear any stale invitational warmth at the start of a new offseason.

    Mirrors ``media_events.reset_credibility_bonus``: the warmth is a ONE-
    offseason effect. Call from offseason init, inside the player_club_id +
    pyramid_world_active gate, so legacy/non-pyramid worlds stay byte-identical.
    """
    from .persistence import set_state

    set_state(conn, _WARMTH_KEY, "0")


def _warmth_guard_key(event_key: str) -> str:
    return f"v27_{event_key}_warmth_for"


def apply_invitational_warmth(
    conn: sqlite3.Connection, event_key: str, warmth: int, season_id: str
) -> None:
    """Add an invitational champion's prospect-showcase warmth to the recruiting
    credibility channel, ONCE per (event, season).

    Idempotent via a per-event guard (``v27_<event>_warmth_for`` holding
    season_id). The warmth ACCUMULATES in ``v27_invitational_warmth`` (a
    separate key from ``v26_credibility_bonus``) so winning both invitationals
    in one offseason stacks, and a media credibility bonus in the same
    offseason coexists without clobbering. Offseason init resets the total to 0
    before next offseason's recruiting runs.
    """
    from .persistence import get_state, set_state

    guard = _warmth_guard_key(event_key)
    if get_state(conn, guard) == season_id:
        return  # already applied this event this season
    current = invitational_warmth(conn)
    set_state(conn, _WARMTH_KEY, str(current + int(warmth)))
    set_state(conn, guard, season_id)
    conn.commit()


def _invitational_invitees(
    conn: sqlite3.Connection, season_id: str, fame_min: int, field_size: int
) -> List[str]:
    """Select the invitational field: clubs with prestige >= fame_min, ordered
    by standing (the standings sort order — wins/points/game-point-diff), taking
    the top ``field_size``. Fame is the gate; standing is the seed/ranking."""
    from .persistence import load_club_prestige, load_clubs, load_standings

    clubs = load_clubs(conn)
    fame_qualified = {
        cid for cid in clubs if load_club_prestige(conn, cid) >= fame_min
    }
    if len(fame_qualified) < 2:
        return []
    # Order the qualified clubs by their standings rank (load_standings returns
    # the league-sorted order). Clubs not in the standings (e.g. a fresh season
    # with no recorded matches) keep a stable fallback: alphabetical by club id.
    standings_order = [row.club_id for row in load_standings(conn, season_id)]
    in_standings = [cid for cid in standings_order if cid in fame_qualified]
    not_in_standings = sorted(cid for cid in fame_qualified if cid not in in_standings)
    ordered = in_standings + not_in_standings
    return ordered[:field_size]


def resolve_ruleset_invitationals(
    conn: sqlite3.Connection, season_id: str, root_seed: int
) -> List[EventResult]:
    """Resolve both ruleset invitationals (Cloth Classic + No-Sting Open) for
    this season: fame-gate the field, auto-sim each knockout to a champion, and
    award the champion's purse + prospect-showcase warmth (USER club only — AI
    treasuries/credibility are abstracted, mirroring the cup), then record the
    events into ``v27_events_json`` + emit event news.

    Pyramid + user only (the caller gates on ``player_club_id`` +
    ``pyramid_world_active``); legacy/non-pyramid worlds never reach this. All
    grants are idempotent (per-event purse + warmth guards). Effects land ONLY
    in treasury / recruiting-credibility warmth — NEVER match outcomes or
    standings (the V26 isolation invariant).

    Returns the list of resolved :class:`EventResult` (empty when no fame-
    qualified field exists).
    """
    from .config import DEFAULT_EVENTS
    from .event_calendar import (
        apply_event_purse,
        emit_event_news,
        record_event,
    )
    from .persistence import get_state

    player_club_id = get_state(conn, "player_club_id") or ""
    invitees = _invitational_invitees(
        conn, season_id, DEFAULT_EVENTS.invitational_fame_min, _INVITATIONAL_FIELD_SIZE
    )
    if len(invitees) < 2:
        return []

    results: List[EventResult] = []
    for ruleset in _INVITATIONAL_RULESETS:
        event_key, _name = _INVITATIONAL_META[ruleset]
        run_result = run_invitational(
            conn, season_id, ruleset, list(invitees), root_seed
        )
        if run_result is None:
            continue
        champion_club_id = run_result.champion_club_id
        purse_k = 0
        if champion_club_id == player_club_id:
            purse_k = int(DEFAULT_EVENTS.invitational_purse_champion_k)
            apply_event_purse(conn, event_key, purse_k, season_id)
            apply_invitational_warmth(
                conn, event_key, int(DEFAULT_EVENTS.warmth_credibility), season_id
            )
        # Record the event with the actual purse paid (0 when an AI club won).
        recorded = EventResult(
            event_key=event_key,
            event_name=run_result.event_name,
            season_id=season_id,
            champion_club_id=champion_club_id,
            champion_club_name=run_result.champion_club_name,
            ruleset=run_result.ruleset,
            purse_k=purse_k,
            bracket=run_result.bracket,
        )
        record_event(conn, season_id, recorded)
        emit_event_news(conn, season_id, recorded)
        results.append(recorded)
    conn.commit()
    return results


__all__ = [
    "run_invitational",
    "resolve_ruleset_invitationals",
    "invitational_warmth",
    "reset_invitational_warmth",
    "apply_invitational_warmth",
]


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
