"""Official player state and starter / setup validation.

V11 splits player status across more than the generic ``is_out`` boolean so
the catch queue, entering window, discipline, and re-entry restrictions can
all be modeled deterministically.

Phase 1 also includes ``validate_starters`` for mixed-division roster checks.
The validator takes plain ``(player_id, gender)`` pairs to keep the generic
:class:`~dodgeball_sim.models.Player` dataclass untouched in this phase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, Sequence, Tuple

from .rulesets import DivisionType, Gender, RulesetProfile


class OfficialPlayerStatus(str, Enum):
    """Per-player status in an official-rules match.

    The status machine is split out from the generic
    :class:`~dodgeball_sim.models.PlayerState` so V11 catch queues, discipline,
    and re-entry can use proper named states instead of multiple booleans.
    """

    INACTIVE_NONSTARTER = "inactive_nonstarter"
    ACTIVE = "active"
    HIT_PENDING = "hit_pending"
    EXITING = "exiting"
    QUEUED = "queued"
    ENTERING = "entering"
    INJURED = "injured"
    BLUE_CARD_QUEUE = "blue_card_queue"
    YELLOW_CARD_REMOVED = "yellow_card_removed"
    RED_CARD_REMOVED = "red_card_removed"
    SUSPENDED = "suspended"
    EJECTED = "ejected"


@dataclass
class OfficialPlayerState:
    """Mutable per-player state for an in-progress official match."""

    player_id: str
    team_id: str
    gender: Gender | None = None
    status: OfficialPlayerStatus = OfficialPlayerStatus.INACTIVE_NONSTARTER
    is_starter: bool = False
    holding_ball_ids: Tuple[str, ...] = ()
    last_sequence_id: str | None = None

    def is_live_for_hits(self) -> bool:
        return self.status == OfficialPlayerStatus.ACTIVE

    def is_eligible_for_catch(self) -> bool:
        # Only live players can attempt a catch (they may catch a ball that
        # was thrown at them or at a teammate, but not while queued/entering).
        return self.status == OfficialPlayerStatus.ACTIVE

    def is_in_queue(self) -> bool:
        return self.status in (
            OfficialPlayerStatus.QUEUED,
            OfficialPlayerStatus.BLUE_CARD_QUEUE,
            OfficialPlayerStatus.ENTERING,
        )


class OfficialSetupValidationError(ValueError):
    """Raised when a roster/starter selection violates the ruleset profile."""


def validate_starters(
    profile: RulesetProfile,
    starters: Sequence[Tuple[str, Gender | None]],
    *,
    roster_genders: Sequence[Gender | None] | None = None,
) -> None:
    """Validate a starting lineup against the ruleset profile.

    ``starters`` is the proposed starting lineup as ``(player_id, gender)``
    tuples. For mixed-division play, ``roster_genders`` is the full roster's
    gender list so we can apply the "3-2 when only two of one gender are
    available" allowance from the audit (USAD 2026.1 section 4).

    Rules enforced:

    - Starter count matches ``profile.roster_rule.starters``.
    - No duplicate player ids.
    - For mixed division: no more than 3 starters of one gender, unless the
      roster contains fewer than 3 players of the other gender, in which
      case 3-2 / 4-2 is allowed only if more of that gender simply do not
      exist on the roster.
    """

    required = profile.roster_rule.starters
    if len(starters) != required:
        raise OfficialSetupValidationError(
            f"Expected {required} starters, got {len(starters)}"
        )
    ids = [pid for pid, _ in starters]
    if len(set(ids)) != len(ids):
        raise OfficialSetupValidationError("Duplicate player ids in starters")

    if profile.division != DivisionType.MIXED:
        return

    cap = profile.roster_rule.mixed_max_one_gender
    males = sum(1 for _, g in starters if g == Gender.MALE)
    females = sum(1 for _, g in starters if g == Gender.FEMALE)

    def _check_over_cap(over_count: int, other_in_starters: int,
                        other_in_roster: int | None, label: str) -> None:
        if over_count <= cap:
            return
        # Over the cap is only legal when the other gender has fewer than
        # ``cap`` players available on the roster AND every available player
        # of the other gender is in the starting lineup.
        if other_in_roster is None:
            raise OfficialSetupValidationError(
                f"Mixed division: too many {label} starters "
                f"({over_count} > {cap}); rule 4 audit"
            )
        if other_in_roster >= cap:
            raise OfficialSetupValidationError(
                f"Mixed division: too many {label} starters "
                f"({over_count} > {cap}); other gender had {other_in_roster}"
            )
        if other_in_starters < other_in_roster:
            raise OfficialSetupValidationError(
                f"Mixed division: must start every available player of the "
                f"other gender before exceeding the {cap}-cap"
            )

    other_m = (
        sum(1 for g in roster_genders if g == Gender.FEMALE)
        if roster_genders is not None
        else None
    )
    other_f = (
        sum(1 for g in roster_genders if g == Gender.MALE)
        if roster_genders is not None
        else None
    )
    _check_over_cap(males, females, other_m, "male")
    _check_over_cap(females, males, other_f, "female")


def initial_states(
    starters: Iterable[Tuple[str, str, Gender | None]],
    nonstarters: Iterable[Tuple[str, str, Gender | None]] = (),
) -> List[OfficialPlayerState]:
    """Build initial :class:`OfficialPlayerState` records.

    ``starters`` and ``nonstarters`` are ``(player_id, team_id, gender)``
    tuples. Starters begin ACTIVE; non-starters begin INACTIVE_NONSTARTER and
    are not eligible for catch-driven re-entry per section 23.
    """

    states: List[OfficialPlayerState] = []
    for pid, tid, gender in starters:
        states.append(
            OfficialPlayerState(
                player_id=pid,
                team_id=tid,
                gender=gender,
                status=OfficialPlayerStatus.ACTIVE,
                is_starter=True,
            )
        )
    for pid, tid, gender in nonstarters:
        states.append(
            OfficialPlayerState(
                player_id=pid,
                team_id=tid,
                gender=gender,
                status=OfficialPlayerStatus.INACTIVE_NONSTARTER,
                is_starter=False,
            )
        )
    return states
