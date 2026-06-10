from __future__ import annotations

"""Lineup resolution for Manager Mode.

A lineup is an ordered list of player IDs. The UI may show the full ordered
roster, but match simulation activates only the first STARTERS_COUNT valid
players. Bench players remain rostered and visible outside the match.
"""

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .models import Player, PlayerArchetype

STARTERS_COUNT = 6

_ROLE_NAMES = ["Captain", "Striker", "Anchor", "Runner", "Rookie", "Utility"]

COURT_SLOT_PREFERENCES: dict[int, set[PlayerArchetype]] = {
    0: {PlayerArchetype.DODGER_ANCHOR, PlayerArchetype.CATCHER},
    1: {PlayerArchetype.DODGER_ANCHOR, PlayerArchetype.BALL_HAWK},
    2: {PlayerArchetype.THROWER, PlayerArchetype.BALL_HAWK},
    3: {PlayerArchetype.THROWER, PlayerArchetype.CATCHER},
}

_HYBRID_DECOMPOSITION: dict[PlayerArchetype, tuple[PlayerArchetype, PlayerArchetype]] = {
    PlayerArchetype.THROWER_CATCHER: (PlayerArchetype.THROWER, PlayerArchetype.CATCHER),
    PlayerArchetype.THROWER_DODGER: (PlayerArchetype.THROWER, PlayerArchetype.DODGER_ANCHOR),
    PlayerArchetype.CATCHER_HAWK: (PlayerArchetype.CATCHER, PlayerArchetype.BALL_HAWK),
    PlayerArchetype.HAWK_DODGER: (PlayerArchetype.BALL_HAWK, PlayerArchetype.DODGER_ANCHOR),
}


def slot_accepts(archetype: PlayerArchetype, slot_prefs: set[PlayerArchetype]) -> bool:
    if archetype in slot_prefs:
        return True
    if archetype in _HYBRID_DECOMPOSITION:
        primary, secondary = _HYBRID_DECOMPOSITION[archetype]
        return primary in slot_prefs or secondary in slot_prefs
    return False


_ROLE_LIABILITIES = {
    slot: {archetype for archetype in PlayerArchetype if not slot_accepts(archetype, prefs)}
    for slot, prefs in COURT_SLOT_PREFERENCES.items()
}


def check_lineup_liabilities(roster: Sequence[Player], lineup_ids: Sequence[str]) -> List[str]:
    """Advisory role-fit notes for the first six slots.

    HONESTY (2026-06-09 audit): no shipping engine consumes slot-role fit —
    only the retired legacy ``MatchEngine`` applied liability penalties. These
    strings are advisory composition notes, and every surface that renders
    them must keep that framing (no claimed in-match penalty).
    """
    players_by_id = {player.id: player for player in roster}
    starters = [players_by_id[pid] for pid in lineup_ids[:STARTERS_COUNT] if pid in players_by_id]
    warnings = []
    for idx, player in enumerate(starters):
        role_name = _ROLE_NAMES[idx] if idx < len(_ROLE_NAMES) else "Utility"
        prefs = COURT_SLOT_PREFERENCES.get(idx, set())
        if prefs and not slot_accepts(player.archetype, prefs):
            warnings.append(
                f"{player.name} is a mismatched {role_name}: the role label prefers a different archetype (advisory fit note)."
            )
    return warnings


def is_liability(team_players: Sequence[Player], player: Player) -> bool:
    try:
        idx = list(team_players).index(player)
        prefs = COURT_SLOT_PREFERENCES.get(idx, set())
        return bool(prefs) and not slot_accepts(player.archetype, prefs)
    except ValueError:
        return False


def optimize_ai_lineup(roster: Sequence[Player]) -> List[str]:
    """Greedy heuristic: assign highest OVR players to non-liability slots."""
    sorted_roster = sorted(roster, key=lambda p: -p.overall_skill())
    lineup: List[Player | None] = [None] * STARTERS_COUNT
    remaining = list(sorted_roster)

    for i in range(STARTERS_COUNT):
        prefs = COURT_SLOT_PREFERENCES.get(i, set())
        for player in remaining:
            if not prefs or slot_accepts(player.archetype, prefs):
                lineup[i] = player
                remaining.remove(player)
                break

    for i in range(STARTERS_COUNT):
        if lineup[i] is None and remaining:
            lineup[i] = remaining.pop(0)

    final_ids = [player.id for player in lineup if player is not None]
    final_ids.extend(player.id for player in remaining)
    return final_ids


class LineupViolation(ValueError):
    """Raised when a manual lineup submission fails structural validation.

    ``reason`` is a stable machine-readable tag the API surface and frontend
    can branch on. Human-facing copy is built at the boundary, not here.
    """

    _VALID_REASONS = frozenset({"not_on_roster", "duplicate", "position_count"})

    def __init__(self, reason: str, message: str = "") -> None:
        if reason not in self._VALID_REASONS:
            raise ValueError(f"Unknown LineupViolation reason: {reason!r}")
        self.reason = reason
        super().__init__(message or reason)


@dataclass(frozen=True)
class ManualLineupResult:
    """Result of ``apply_manual_lineup``.

    ``starters`` is the ordered list of starting players, each carrying its
    ``player_id`` (matching ``Player.id``). ``ordered_player_ids`` is the
    starter ids followed by the remaining roster ordered by OVR — the canonical
    shape ``save_lineup_default`` expects.
    """

    starters: List["_LineupStarter"]
    ordered_player_ids: List[str]


@dataclass(frozen=True)
class _LineupStarter:
    """Thin starter row exposing ``player_id`` for downstream consumers."""

    player_id: str
    player: Player


def apply_manual_lineup(club_with_roster, starters: Sequence[str]) -> ManualLineupResult:
    """Validate and resolve a manual starter override.

    Pure function: no persistence. The caller (web endpoint) is responsible
    for persisting the resulting ``ordered_player_ids`` via
    ``save_lineup_default``.

    ``club_with_roster`` is duck-typed: it must expose a ``roster`` attribute
    that is a sequence of ``Player`` (sample-data fixtures and the web layer
    both wrap the persisted roster this way).

    Validates structurally — does NOT enforce positional fit. Positional
    mismatches surface separately via ``check_lineup_liabilities`` and are
    treated as warnings, not errors.
    """

    roster: Sequence[Player] = tuple(getattr(club_with_roster, "roster", ()))
    starter_ids = list(starters)

    if len(starter_ids) != STARTERS_COUNT:
        raise LineupViolation(
            "position_count",
            f"Expected {STARTERS_COUNT} starters, got {len(starter_ids)}.",
        )

    if len(set(starter_ids)) != len(starter_ids):
        raise LineupViolation("duplicate", "Starter list contains duplicates.")

    roster_by_id = {player.id: player for player in roster}
    missing = [pid for pid in starter_ids if pid not in roster_by_id]
    if missing:
        raise LineupViolation(
            "not_on_roster",
            f"Players not on roster: {', '.join(missing)}",
        )

    # Reuse the resolver to backfill the bench in canonical OVR order.
    resolved = LineupResolver().resolve_with_diagnostics(
        roster, default=None, override=starter_ids,
    )
    starter_rows = [
        _LineupStarter(player_id=pid, player=roster_by_id[pid])
        for pid in resolved.lineup[:STARTERS_COUNT]
    ]
    return ManualLineupResult(
        starters=starter_rows,
        ordered_player_ids=list(resolved.lineup),
    )


@dataclass(frozen=True)
class ResolvedLineup:
    """Lineup with diagnostics about IDs dropped during resolution."""

    lineup: List[str]
    dropped_ids: List[str]


class LineupResolver:
    """Resolve override -> default -> roster order, then backfill by OVR."""

    def resolve(
        self,
        roster: Sequence[Player],
        default: Optional[Sequence[str]],
        override: Optional[Sequence[str]],
    ) -> List[str]:
        return self.resolve_with_diagnostics(roster, default, override).lineup

    def resolve_with_diagnostics(
        self,
        roster: Sequence[Player],
        default: Optional[Sequence[str]],
        override: Optional[Sequence[str]],
    ) -> ResolvedLineup:
        roster_ids = {player.id for player in roster}
        chosen: Sequence[str]
        if override is not None:
            chosen = override
        elif default is not None:
            chosen = default
        else:
            chosen = [player.id for player in roster]

        kept: List[str] = []
        dropped: List[str] = []
        seen: set[str] = set()
        for player_id in chosen:
            if player_id in roster_ids and player_id not in seen:
                kept.append(player_id)
                seen.add(player_id)
            elif player_id not in roster_ids:
                dropped.append(player_id)

        remaining = [player for player in roster if player.id not in seen]
        remaining.sort(key=lambda player: (-player.overall_skill(), player.id))
        kept.extend(player.id for player in remaining)

        return ResolvedLineup(lineup=kept, dropped_ids=dropped)

    def active_starters(self, resolved_lineup: Sequence[str]) -> List[str]:
        """Return the legal active match participants from a resolved lineup."""
        return list(resolved_lineup[:STARTERS_COUNT])


__all__ = [
    "COURT_SLOT_PREFERENCES",
    "STARTERS_COUNT",
    "LineupResolver",
    "LineupViolation",
    "ManualLineupResult",
    "ResolvedLineup",
    "apply_manual_lineup",
    "check_lineup_liabilities",
    "is_liability",
    "optimize_ai_lineup",
    "slot_accepts",
]
