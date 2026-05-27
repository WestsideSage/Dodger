"""Structural validator: confirms a postgame payload is consistent with its source MatchResult.

Complements `_assert_postgame_copy_truthful` in use_cases.py, which is a string-level
guard. This module checks *structural* fields (scores, winner, survivor counts, catches)
of the assembled aftermath payload against the resolved ``MatchResult``.

If the payload's match_card claims a winner that doesn't match
``result.winner_team_id``, or its survivor counts diverge from the box score,
or any top-performer reports more catches than the team's box-score totals,
``validate_postgame_payload`` raises :class:`PostgameTruthError`.

The caller (``_build_aftermath``) catches that and falls back to a degraded
but truthful payload rather than ship the contradiction.
"""
from __future__ import annotations

from typing import Any, Mapping


class PostgameTruthError(AssertionError):
    """Raised when a postgame payload contradicts its source MatchResult."""


def _box_living(result, club_id: str) -> int | None:
    teams = (result.box_score or {}).get("teams") or {}
    team = teams.get(club_id)
    if not isinstance(team, Mapping):
        return None
    totals = team.get("totals") or {}
    living = totals.get("living")
    try:
        return int(living)
    except (TypeError, ValueError):
        return None


def _box_catches(result, club_id: str) -> int | None:
    teams = (result.box_score or {}).get("teams") or {}
    team = teams.get(club_id)
    if not isinstance(team, Mapping):
        return None
    totals = team.get("totals") or {}
    catches = totals.get("catches")
    try:
        return int(catches)
    except (TypeError, ValueError):
        return None


def validate_postgame_payload(payload: Mapping[str, Any], result) -> None:
    """Raise :class:`PostgameTruthError` if ``payload`` contradicts ``result``.

    Checks (only those that map to real payload fields produced by
    ``_build_aftermath``):

    - ``match_card.winner_club_id`` matches ``result.winner_team_id``
    - ``match_card.home_survivors`` / ``away_survivors`` match the
      ``living`` totals in ``result.box_score["teams"]``
    - For each entry in ``top_performers``, ``catches_made`` does not
      exceed the total ``catches`` for that player's team in the box score
      (when team totals are available for both teams)
    """
    if not isinstance(payload, Mapping):
        raise PostgameTruthError(f"payload is not a mapping: {type(payload).__name__}")

    match_card = payload.get("match_card")
    if not isinstance(match_card, Mapping):
        # No match_card => nothing structural to validate (e.g. bye week).
        return

    home_club_id = match_card.get("home_club_id")
    away_club_id = match_card.get("away_club_id")
    expected_winner = result.winner_team_id
    actual_winner = match_card.get("winner_club_id")
    if actual_winner != expected_winner:
        raise PostgameTruthError(
            f"winner mismatch: payload winner_club_id={actual_winner!r} "
            f"but result.winner_team_id={expected_winner!r}"
        )

    if home_club_id is not None:
        expected_home = _box_living(result, str(home_club_id))
        actual_home = match_card.get("home_survivors")
        if expected_home is not None and int(actual_home) != expected_home:
            raise PostgameTruthError(
                f"home survivor score mismatch for {home_club_id!r}: "
                f"payload={actual_home} but box_score living={expected_home}"
            )
    if away_club_id is not None:
        expected_away = _box_living(result, str(away_club_id))
        actual_away = match_card.get("away_survivors")
        if expected_away is not None and int(actual_away) != expected_away:
            raise PostgameTruthError(
                f"away survivor score mismatch for {away_club_id!r}: "
                f"payload={actual_away} but box_score living={expected_away}"
            )

    # top_performers per-player catches must not exceed their team's total
    # catches. We can only check players whose team appears in the box score.
    top_performers = payload.get("top_performers") or []
    team_catch_totals: dict[str, int] = {}
    for club_id in (home_club_id, away_club_id):
        if club_id is None:
            continue
        total = _box_catches(result, str(club_id))
        if total is not None:
            team_catch_totals[str(club_id)] = total
    # Sum reported catches per team and compare.
    reported_per_team: dict[str, int] = {}
    for entry in top_performers:
        if not isinstance(entry, Mapping):
            continue
        # top_performers carries club_name, not club_id, so we can't
        # group by club id directly. Instead enforce the per-player
        # bound: no single player can have more catches than either
        # team's total — that's a weaker but still real invariant.
        catches = entry.get("catches_made")
        if catches is None:
            continue
        try:
            catches_int = int(catches)
        except (TypeError, ValueError):
            continue
        if team_catch_totals and catches_int > max(team_catch_totals.values()):
            player_name = entry.get("player_name") or entry.get("player_id") or "?"
            raise PostgameTruthError(
                f"top_performer catches_made for {player_name!r}={catches_int} "
                f"exceeds max team catches total={max(team_catch_totals.values())}"
            )

    # Sanity: when both teams' totals are known, the sum of reported
    # catches across all top_performers cannot exceed the sum of team
    # catches. (Top performers is a subset of all players, so this is a
    # legitimate upper bound.)
    if len(team_catch_totals) >= 1:
        total_reported = 0
        for entry in top_performers:
            if not isinstance(entry, Mapping):
                continue
            c = entry.get("catches_made")
            try:
                total_reported += int(c)
            except (TypeError, ValueError):
                continue
        team_sum = sum(team_catch_totals.values())
        if total_reported > team_sum:
            raise PostgameTruthError(
                f"top_performers report {total_reported} total catches "
                f"but box_score teams sum to {team_sum}"
            )


__all__ = ["PostgameTruthError", "validate_postgame_payload"]
