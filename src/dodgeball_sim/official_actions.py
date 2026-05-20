"""Proactive and reactive action modeling for the official engine.

This module exists so :mod:`official_engine` does NOT become a god object
mixing rules, tactics, timing, and randomness. The engine asks for a
:class:`ProactiveAction` on each tick; the sequence/live-ball resolver asks
for :class:`ReactiveAction` instances during resolution.

V11 design constraints:
- No hidden RNG. The selector takes a seeded :class:`random.Random` so the
  same state + seed yields the same choice.
- No hidden rating boosts. Ratings and ``CoachPolicy`` shift probabilities,
  not absolute outcomes.
- Legal-action filtering is rules-aware: queued, suspended, inactive, or
  not-yet-live entering players are excluded.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple

from .ball_state import BallState, OfficialBall
from .burden import BurdenState, ThrowClockStatus
from .player_state import OfficialPlayerState, OfficialPlayerStatus


class ProactiveKind(str, Enum):
    THROW = "throw"
    RETRIEVE = "retrieve"
    ENTER_COURT = "enter_court"
    WAIT = "wait"


class ReactiveKind(str, Enum):
    CATCH_ATTEMPT = "catch_attempt"
    DODGE = "dodge"
    BLOCK = "block"


@dataclass(frozen=True)
class ProactiveAction:
    kind: ProactiveKind
    actor_id: str


@dataclass(frozen=True)
class ThrowAction(ProactiveAction):
    ball_id: str = ""
    target_player_id: Optional[str] = None


@dataclass(frozen=True)
class RetrieveAction(ProactiveAction):
    ball_id: str = ""


@dataclass(frozen=True)
class EnterCourtAction(ProactiveAction):
    pass


@dataclass(frozen=True)
class WaitAction(ProactiveAction):
    pass


@dataclass(frozen=True)
class ReactiveAction:
    kind: ReactiveKind
    actor_id: str


@dataclass(frozen=True)
class CatchAttemptAction(ReactiveAction):
    ball_id: str = ""


@dataclass(frozen=True)
class DodgeAction(ReactiveAction):
    pass


@dataclass(frozen=True)
class BlockAction(ReactiveAction):
    held_ball_id: str = ""


# Alias used by some specs.
OfficialAction = ProactiveAction


def _player_can_act_proactively(player: OfficialPlayerState) -> bool:
    return player.status == OfficialPlayerStatus.ACTIVE


class LegalActionGenerator:
    """Generates the set of legal proactive actions for a given state."""

    def __init__(
        self,
        *,
        players: Mapping[str, OfficialPlayerState],
        balls: Sequence[OfficialBall],
        burden: BurdenState | None = None,
    ) -> None:
        self._players = players
        self._balls = balls
        self._burden = burden

    def for_player(self, player_id: str) -> List[ProactiveAction]:
        player = self._players[player_id]
        # Entering players have a separate action available; once live they
        # become ACTIVE through the catch_queue lifecycle.
        if player.status == OfficialPlayerStatus.ENTERING:
            return [EnterCourtAction(kind=ProactiveKind.ENTER_COURT, actor_id=player_id)]
        if not _player_can_act_proactively(player):
            return []

        actions: List[ProactiveAction] = [WaitAction(kind=ProactiveKind.WAIT, actor_id=player_id)]

        # Throws: only balls this player controls, and only if the burden /
        # throw clock allow it. ZERO_CALLED forbids waiting on burden team.
        held_balls = [b for b in self._balls if b.controller_player_id == player_id and b.activated]
        on_burden = self._burden is not None and self._burden.team_id == player.team_id
        clock_zero = (
            self._burden is not None
            and self._burden.clock_status == ThrowClockStatus.ZERO_CALLED
        )
        for ball in held_balls:
            actions.append(ThrowAction(
                kind=ProactiveKind.THROW, actor_id=player_id, ball_id=ball.ball_id,
            ))

        # If the throw clock has hit zero on this player's team, WAIT is no
        # longer legal -- they must throw or face the penalty.
        if on_burden and clock_zero and held_balls:
            actions = [a for a in actions if a.kind != ProactiveKind.WAIT]

        # Retrieve: any free ball on this team's side.
        for ball in self._balls:
            if ball.state == BallState.ACTIVATED_FREE and ball.side == player.team_id:
                actions.append(RetrieveAction(
                    kind=ProactiveKind.RETRIEVE, actor_id=player_id, ball_id=ball.ball_id,
                ))

        return actions

    def all_legal(self) -> List[ProactiveAction]:
        out: List[ProactiveAction] = []
        for pid in self._players:
            out.extend(self.for_player(pid))
        return out


class ActionSelector:
    """Chooses a proactive action deterministically from a seeded RNG.

    The selector weights actions by player ratings, ``CoachPolicy``, burden
    pressure, and clock pressure. It does *not* fabricate outcomes; weights
    feed the random draw only.
    """

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def select(
        self,
        actions: Sequence[ProactiveAction],
        *,
        weights: Iterable[float] | None = None,
    ) -> ProactiveAction:
        if not actions:
            raise ValueError("No legal actions to select from")
        if weights is None:
            weights_list = [1.0] * len(actions)
        else:
            weights_list = list(weights)
        if len(weights_list) != len(actions):
            raise ValueError("weights length must match actions length")
        return self._rng.choices(list(actions), weights=weights_list, k=1)[0]


def request_reactive_action(
    *,
    actor: OfficialPlayerState,
    kind: ReactiveKind,
    ball_id: str | None = None,
    held_ball_id: str | None = None,
) -> ReactiveAction:
    """Sequence/live-ball modules call this to build the reactive action the
    actor would take. Only live (ACTIVE) players can produce reactive actions.
    """

    if actor.status != OfficialPlayerStatus.ACTIVE:
        raise ValueError(
            f"Reactive action requested for non-active player {actor.player_id} "
            f"(status={actor.status.value})"
        )
    if kind == ReactiveKind.CATCH_ATTEMPT:
        return CatchAttemptAction(kind=kind, actor_id=actor.player_id, ball_id=ball_id or "")
    if kind == ReactiveKind.DODGE:
        return DodgeAction(kind=kind, actor_id=actor.player_id)
    if kind == ReactiveKind.BLOCK:
        return BlockAction(kind=kind, actor_id=actor.player_id, held_ball_id=held_ball_id or "")
    raise ValueError(f"Unknown reactive kind {kind!r}")
