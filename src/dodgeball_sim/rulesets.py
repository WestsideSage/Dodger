"""Immutable official ruleset profiles for V11.

A :class:`RulesetProfile` is a pure configuration object: it tells the rules
modules how many balls each side starts with, what the burden majority
threshold is, how many starters take the court, what gender mix is legal, and
which match/game timing applies. It must not contain mutable state or random
seeds.

Source precedence (see V11 design):

1. USA Dodgeball 2026.1 PDF
2. ``docs/rules/usad-2026.1-rule-matrix-audit.md`` corrections
3. ``docs/specs/usa_dodgeball_2026_extraction_matrix.md`` (traceability)
4. V11 design + implementation plan
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class BallMaterial(str, Enum):
    FOAM = "foam"
    NO_STING = "no_sting"
    CLOTH = "cloth"


class DivisionType(str, Enum):
    OPEN = "open"
    WOMEN = "women"
    MIXED = "mixed"


class Gender(str, Enum):
    """Gender for mixed-division starter validation.

    USA Dodgeball mixed games may not be played with four starters of one
    gender. Gender on non-mixed rosters is informational only.
    """

    MALE = "M"
    FEMALE = "F"


@dataclass(frozen=True)
class CourtProfile:
    """Court dimensions and lane references.

    V11 does not yet use full spatial coordinates; the profile stores symbolic
    references so future spatial rules can plug in without reshaping the
    ruleset.
    """

    length_feet: float = 60.0
    width_feet: float = 30.0
    attack_line_offset_feet: float = 0.0


@dataclass(frozen=True)
class OfficialRosterRule:
    """Starter / roster legality rules for the chosen division."""

    starters: int = 6
    max_roster: int = 12
    division: DivisionType = DivisionType.OPEN
    # Mixed: no more than 3 starters of one gender unless only 2 of that
    # gender are available on the roster.
    mixed_max_one_gender: int = 3


@dataclass(frozen=True)
class RulesetProfile:
    """Immutable configuration for an official-rules match."""

    name: str
    material: BallMaterial
    division: DivisionType
    ball_count: int
    burden_majority_threshold: int
    roster_rule: OfficialRosterRule
    court: CourtProfile = CourtProfile()
    # Game/Match timing (seconds). Sentinel 0 means "untimed".
    game_clock_seconds: int = 180
    match_clock_seconds: int = 0
    # Throw-clock seconds before a "play n balls" call (foam/no-sting use the
    # same 5-second window; cloth uses the same window but with the play-n
    # follow-up handled in burden.py).
    throw_clock_seconds: int = 5
    # No-blocking trigger (seconds of game elapsed). 0 disables.
    no_blocking_trigger_seconds: int = 0


_FOAM_ROSTER = OfficialRosterRule(starters=6, max_roster=12, division=DivisionType.OPEN)
_NO_STING_ROSTER = OfficialRosterRule(starters=6, max_roster=12, division=DivisionType.OPEN)
_CLOTH_ROSTER = OfficialRosterRule(starters=6, max_roster=12, division=DivisionType.OPEN)


FOAM_OPEN = RulesetProfile(
    name="foam-open",
    material=BallMaterial.FOAM,
    division=DivisionType.OPEN,
    ball_count=6,
    burden_majority_threshold=4,
    roster_rule=_FOAM_ROSTER,
    game_clock_seconds=180,
    no_blocking_trigger_seconds=180,
)

NO_STING_OPEN = RulesetProfile(
    name="no-sting-open",
    material=BallMaterial.NO_STING,
    division=DivisionType.OPEN,
    ball_count=6,
    burden_majority_threshold=4,
    roster_rule=_NO_STING_ROSTER,
    game_clock_seconds=180,
    no_blocking_trigger_seconds=180,
)

CLOTH_OPEN = RulesetProfile(
    name="cloth-open",
    material=BallMaterial.CLOTH,
    division=DivisionType.OPEN,
    # Cloth uses 5 balls (2 per side + 1 neutral center per spec).
    ball_count=5,
    burden_majority_threshold=3,
    roster_rule=_CLOTH_ROSTER,
    game_clock_seconds=180,
    no_blocking_trigger_seconds=0,
)


def mixed_division(profile: RulesetProfile) -> RulesetProfile:
    """Return a mixed-division variant of an open-division profile."""

    mixed_rule = OfficialRosterRule(
        starters=profile.roster_rule.starters,
        max_roster=profile.roster_rule.max_roster,
        division=DivisionType.MIXED,
        mixed_max_one_gender=profile.roster_rule.mixed_max_one_gender,
    )
    return RulesetProfile(
        name=f"{profile.name}-mixed",
        material=profile.material,
        division=DivisionType.MIXED,
        ball_count=profile.ball_count,
        burden_majority_threshold=profile.burden_majority_threshold,
        roster_rule=mixed_rule,
        court=profile.court,
        game_clock_seconds=profile.game_clock_seconds,
        match_clock_seconds=profile.match_clock_seconds,
        throw_clock_seconds=profile.throw_clock_seconds,
        no_blocking_trigger_seconds=profile.no_blocking_trigger_seconds,
    )


def women_division(profile: RulesetProfile) -> RulesetProfile:
    women_rule = OfficialRosterRule(
        starters=profile.roster_rule.starters,
        max_roster=profile.roster_rule.max_roster,
        division=DivisionType.WOMEN,
        mixed_max_one_gender=profile.roster_rule.mixed_max_one_gender,
    )
    return RulesetProfile(
        name=f"{profile.name}-women",
        material=profile.material,
        division=DivisionType.WOMEN,
        ball_count=profile.ball_count,
        burden_majority_threshold=profile.burden_majority_threshold,
        roster_rule=women_rule,
        court=profile.court,
        game_clock_seconds=profile.game_clock_seconds,
        match_clock_seconds=profile.match_clock_seconds,
        throw_clock_seconds=profile.throw_clock_seconds,
        no_blocking_trigger_seconds=profile.no_blocking_trigger_seconds,
    )


PROFILES: Tuple[RulesetProfile, ...] = (
    FOAM_OPEN,
    NO_STING_OPEN,
    CLOTH_OPEN,
    mixed_division(FOAM_OPEN),
    mixed_division(NO_STING_OPEN),
    mixed_division(CLOTH_OPEN),
    women_division(FOAM_OPEN),
    women_division(NO_STING_OPEN),
    women_division(CLOTH_OPEN),
)


def profile_by_name(name: str) -> RulesetProfile:
    for profile in PROFILES:
        if profile.name == name:
            return profile
    raise KeyError(f"Unknown ruleset profile: {name!r}")


class RulesetSelection(str, Enum):
    """Top-level ruleset selector for a career.

    Set at career creation only; persists for the lifetime of that career.
    Existing V1-V10 careers default to :attr:`GENERIC` and cannot opt in
    mid-career (the official rules constitute a different patch).
    """

    GENERIC = "generic"
    OFFICIAL_FOAM = "official_foam"
    OFFICIAL_NO_STING = "official_no_sting"
    OFFICIAL_CLOTH = "official_cloth"

    def is_official(self) -> bool:
        return self != RulesetSelection.GENERIC

    def to_profile(self) -> RulesetProfile:
        if self == RulesetSelection.OFFICIAL_FOAM:
            return FOAM_OPEN
        if self == RulesetSelection.OFFICIAL_NO_STING:
            return NO_STING_OPEN
        if self == RulesetSelection.OFFICIAL_CLOTH:
            return CLOTH_OPEN
        raise ValueError(f"Generic ruleset has no official profile: {self}")
