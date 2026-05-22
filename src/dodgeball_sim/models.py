from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, Tuple


_RATING_MIN = 0.0
_RATING_MAX = 100.0


class PlayerArchetype(str, Enum):
    THROWER = "thrower"
    CATCHER = "catcher"
    BALL_HAWK = "ball_hawk"
    DODGER_ANCHOR = "dodger_anchor"
    THROWER_CATCHER = "thrower_catcher"
    THROWER_DODGER = "thrower_dodger"
    CATCHER_HAWK = "catcher_hawk"
    HAWK_DODGER = "hawk_dodger"

    @property
    def display_name(self) -> str:
        return _ARCHETYPE_DISPLAY_NAMES[self]


def _clamp_rating(value: float) -> float:
    return max(_RATING_MIN, min(_RATING_MAX, float(value)))


@dataclass(frozen=True)
class PlayerRatings:
    accuracy: float
    power: float
    dodge: float
    catch: float
    stamina: float = 50.0
    tactical_iq: float = 50.0
    catch_courage: float = 50.0
    throw_selection_iq: float = 50.0
    conditioning_curve: float = 50.0

    def normalized_accuracy(self) -> float:
        return self.accuracy / _RATING_MAX

    def normalized_power(self) -> float:
        return self.power / _RATING_MAX

    def normalized_dodge(self) -> float:
        return self.dodge / _RATING_MAX

    def normalized_catch(self) -> float:
        return self.catch / _RATING_MAX

    def normalized_tactical_iq(self) -> float:
        return self.tactical_iq / _RATING_MAX

    def normalized_catch_courage(self) -> float:
        return self.catch_courage / _RATING_MAX

    def normalized_throw_selection_iq(self) -> float:
        return self.throw_selection_iq / _RATING_MAX

    def normalized_conditioning_curve(self) -> float:
        return self.conditioning_curve / _RATING_MAX

    def fatigue_ceiling(self) -> float:
        return max(10.0, self.stamina)

    def overall_skill(self) -> float:
        stats = [
            self.accuracy,
            self.power,
            self.dodge,
            self.catch,
            self.stamina,
        ]
        return sum(stats) / len(stats)

    def identity_profile(self) -> "IdentityProfile":
        return IdentityProfile(
            catch_courage=self.catch_courage,
            throw_selection_iq=self.throw_selection_iq,
            conditioning_curve=self.conditioning_curve,
            tactical_iq=self.tactical_iq,
        )

    def apply_bounds(self) -> "PlayerRatings":
        return PlayerRatings(
            accuracy=_clamp_rating(self.accuracy),
            power=_clamp_rating(self.power),
            dodge=_clamp_rating(self.dodge),
            catch=_clamp_rating(self.catch),
            stamina=_clamp_rating(self.stamina),
            tactical_iq=_clamp_rating(self.tactical_iq),
            catch_courage=_clamp_rating(self.catch_courage),
            throw_selection_iq=_clamp_rating(self.throw_selection_iq),
            conditioning_curve=_clamp_rating(self.conditioning_curve),
        )


@dataclass(frozen=True)
class IdentityProfile:
    """Behavioral identity traits surfaced as text, never averaged into skill OVR."""

    catch_courage: float
    throw_selection_iq: float
    conditioning_curve: float
    tactical_iq: float


@dataclass(frozen=True)
class PlayerTraits:
    potential: float = 50.0
    growth_curve: float = 50.0
    consistency: float = 50.0
    pressure: float = 50.0


@dataclass(frozen=True)
class Player:
    id: str
    name: str
    ratings: PlayerRatings
    archetype: PlayerArchetype | None = None
    traits: PlayerTraits = PlayerTraits()
    age: int = 18
    club_id: str | None = None
    newcomer: bool = True

    def __post_init__(self) -> None:
        if self.archetype is None:
            raise ValueError("Player archetype is required and cannot be None.")
        if not isinstance(self.archetype, PlayerArchetype):
            try:
                object.__setattr__(self, "archetype", PlayerArchetype(str(self.archetype)))
            except ValueError as e:
                raise ValueError(f"Invalid archetype: {self.archetype}") from e

    def overall_skill(self) -> float:
        return self.ratings.overall_skill()

    def identity_profile(self) -> IdentityProfile:
        return self.ratings.identity_profile()


@dataclass(frozen=True)
class CoachPolicy:
    target_stars: float = 0.7
    target_ball_holder: float = 0.5
    risk_tolerance: float = 0.5
    sync_throws: float = 0.2
    rush_frequency: float = 0.5
    rush_proximity: float = 0.5
    tempo: float = 0.5
    catch_bias: float = 0.5

    def normalized(self) -> "CoachPolicy":
        return CoachPolicy(
            target_stars=_clamp_rating(self.target_stars * 100.0) / _RATING_MAX,
            target_ball_holder=_clamp_rating(self.target_ball_holder * 100.0) / _RATING_MAX,
            risk_tolerance=_clamp_rating(self.risk_tolerance * 100.0) / _RATING_MAX,
            sync_throws=_clamp_rating(self.sync_throws * 100.0) / _RATING_MAX,
            rush_frequency=_clamp_rating(self.rush_frequency * 100.0) / _RATING_MAX,
            rush_proximity=_clamp_rating(self.rush_proximity * 100.0) / _RATING_MAX,
            tempo=_clamp_rating(self.tempo * 100.0) / _RATING_MAX,
            catch_bias=_clamp_rating(self.catch_bias * 100.0) / _RATING_MAX,
        )

    def as_dict(self) -> dict:
        normalized = self.normalized()
        return {
            "target_stars": normalized.target_stars,
            "target_ball_holder": normalized.target_ball_holder,
            "risk_tolerance": normalized.risk_tolerance,
            "sync_throws": normalized.sync_throws,
            "rush_frequency": normalized.rush_frequency,
            "rush_proximity": normalized.rush_proximity,
            "tempo": normalized.tempo,
            "catch_bias": normalized.catch_bias,
        }


@dataclass(frozen=True)
class Team:
    id: str
    name: str
    players: Tuple[Player, ...]
    coach_policy: CoachPolicy = CoachPolicy()
    chemistry: float = 0.5  # 0..1

    def __post_init__(self) -> None:
        object.__setattr__(self, "players", tuple(self.players))


_ARCHETYPE_DISPLAY_NAMES: dict[PlayerArchetype, str] = {
    PlayerArchetype.THROWER: "Thrower",
    PlayerArchetype.CATCHER: "Catcher",
    PlayerArchetype.BALL_HAWK: "Ball Hawk",
    PlayerArchetype.DODGER_ANCHOR: "Dodger Anchor",
    PlayerArchetype.THROWER_CATCHER: "Thrower / Catcher",
    PlayerArchetype.THROWER_DODGER: "Thrower / Dodger",
    PlayerArchetype.CATCHER_HAWK: "Catcher / Ball Hawk",
    PlayerArchetype.HAWK_DODGER: "Ball Hawk / Dodger",
}


@dataclass(frozen=True)
class MatchSetup:
    team_a: Team
    team_b: Team
    config_version: str = "phase1.v1"


@dataclass
class PlayerState:
    player: Player
    fatigue: float = 0.0
    is_out: bool = False
    throws_attempted: int = 0
    hits_landed: int = 0
    catches_made: int = 0
    dodges_made: int = 0
    caught_throws: int = 0


@dataclass
class TeamState:
    team: Team
    roster: List[PlayerState] = field(default_factory=list)
    outs_recorded: int = 0
    hits_landed: int = 0
    catches_made: int = 0
    dodges_made: int = 0

    def living_players(self) -> List[PlayerState]:
        return [p for p in self.roster if not p.is_out]


__all__ = [
    "CoachPolicy",
    "IdentityProfile",
    "MatchSetup",
    "Player",
    "PlayerArchetype",
    "PlayerRatings",
    "PlayerState",
    "PlayerTraits",
    "Team",
    "TeamState",
]
