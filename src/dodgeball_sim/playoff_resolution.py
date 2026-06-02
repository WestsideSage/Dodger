"""Explicit playoff match resolution.

Before this module existed, a tied playoff match silently advanced the
better-seeded club inside ``playoffs.create_final_match``. The player
was never told whether their club was eliminated or advanced. This is
the single most-cited trust break in the 2026-05 rookie-run playtest
report (see ``docs/superpowers/plans/2026-05-27-rookie-run-playtest-fixes.md``,
Task 1).

The fix moves the decision upstream and surfaces it. Order of resolution:

1. Regulation produced a winner → ``decided_by="regulation"``.
2. Regulation tied → (future) overtime period; today, the existing match
   engine does not expose a clean "simulate one more period from this
   final state" entry point, so we fall straight through to the seed
   tiebreaker. The ``decided_by="overtime"`` literal is retained in the
   type union so a future hook can be added without changing call sites.
3. Still tied → ``decided_by="seed_tiebreaker"``; better seed (lower
   numeric seed) advances and the ``narrative_note`` says so plainly.

``resolve_playoff_match`` is intentionally pure: it takes a
match-shaped object (anything with ``home_club_id``, ``away_club_id``,
``home_seed``, ``away_seed`` and ``regulation_winner_id``) and returns
a ``PlayoffOutcome``. It does not touch the database or the bracket.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


DecidedBy = Literal["regulation", "overtime", "seed_tiebreaker"]


@dataclass(frozen=True)
class PlayoffOutcome:
    """Typed result of resolving a single playoff match.

    ``narrative_note`` is the short player-facing sentence the banner
    renders verbatim (e.g. "Higher seed advances — regulation ended
    tied"). It must be populated whenever ``decided_by`` is anything
    other than ``"regulation"`` so the UI never has to invent text.
    """

    winner_id: str
    loser_id: str
    decided_by: DecidedBy
    narrative_note: str


class _PlayoffMatchLike(Protocol):
    home_club_id: str
    away_club_id: str
    home_seed: int
    away_seed: int
    regulation_winner_id: str | None


def resolve_playoff_match(match: _PlayoffMatchLike) -> PlayoffOutcome:
    """Resolve a finalised-regulation playoff match into a typed outcome.

    The function never returns ``None`` and never guesses silently: a
    tied regulation produces an explicit ``"seed_tiebreaker"`` outcome
    with a populated ``narrative_note`` the UI surfaces to the player.
    """

    home_id = match.home_club_id
    away_id = match.away_club_id
    regulation_winner = match.regulation_winner_id

    if regulation_winner is not None:
        if regulation_winner == home_id:
            return PlayoffOutcome(
                winner_id=home_id,
                loser_id=away_id,
                decided_by="regulation",
                narrative_note="Decided in regulation.",
            )
        if regulation_winner == away_id:
            return PlayoffOutcome(
                winner_id=away_id,
                loser_id=home_id,
                decided_by="regulation",
                narrative_note="Decided in regulation.",
            )
        raise ValueError(
            f"regulation_winner_id {regulation_winner!r} is not a participant"
            f" (home={home_id!r}, away={away_id!r})"
        )

    # Tied regulation. There is no overtime simulator wired in yet
    # (match_lifecycle.py defines an OVERTIME state but no callable
    # entry point), so we fall straight through to the seed tiebreaker.
    # The decision is loud and visible, not silent like the old
    # create_final_match fallback.
    if match.home_seed == match.away_seed:
        # Bracket invariant: distinct seeds. If callers ever violate
        # this, raise — better than picking by coin flip.
        raise ValueError(
            f"Cannot tiebreak: both clubs share seed {match.home_seed!r}"
        )

    if match.home_seed < match.away_seed:
        winner_id, loser_id, winner_seed = home_id, away_id, match.home_seed
    else:
        winner_id, loser_id, winner_seed = away_id, home_id, match.away_seed

    narrative = (
        # winner_seed is the 0-indexed bracket position; players read seeds as
        # 1-based (#1 = top seed), so display it +1. Seeding logic is unchanged.
        f"Higher seed advances — regulation ended tied and the #"
        f"{winner_seed + 1} seed wins the playoff tiebreaker."
    )
    return PlayoffOutcome(
        winner_id=winner_id,
        loser_id=loser_id,
        decided_by="seed_tiebreaker",
        narrative_note=narrative,
    )


__all__ = ["DecidedBy", "PlayoffOutcome", "resolve_playoff_match"]
