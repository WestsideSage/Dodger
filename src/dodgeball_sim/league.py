from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from .models import CoachPolicy


@dataclass(frozen=True)
class Club:
    """Persistent franchise entity. Distinct from Team (match snapshot)."""
    club_id: str
    name: str
    colors: str          # legacy e.g. "red/black"; kept for backward compat
    home_region: str
    founded_year: int
    coach_policy: CoachPolicy = field(default_factory=CoachPolicy)
    primary_color: str = ""
    secondary_color: str = ""
    venue_name: str = ""
    tagline: str = ""
    program_archetype: str = "Balanced Rebuild"


@dataclass(frozen=True)
class Division:
    """V23: one rung of the pyramid (or the International Circuit).

    ``tier`` orders the domestic climb (1 = Premier). The Circuit carries
    tier 1 strength but ``kind="international"`` — key logic on
    ``division_id``, never on tier alone.
    """
    division_id: str
    name: str
    tier: int
    kind: str            # "domestic" | "international"
    short_name: str      # "D1" / "D2" / "D3" / "INT"


@dataclass(frozen=True)
class DivisionMembership:
    """A club's seat in a division for one season (persisted per season)."""
    season_id: str
    club_id: str
    division_id: str
    division_name: str
    tier: int
    kind: str


@dataclass(frozen=True)
class Conference:
    conference_id: str
    name: str
    club_ids: Tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "club_ids", tuple(self.club_ids))


@dataclass(frozen=True)
class League:
    league_id: str
    name: str
    conferences: Tuple[Conference, ...]
    season_ids: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "conferences", tuple(self.conferences))
        object.__setattr__(self, "season_ids", tuple(self.season_ids))

    def all_club_ids(self) -> List[str]:
        ids: List[str] = []
        for conf in self.conferences:
            ids.extend(conf.club_ids)
        return ids


__all__ = ["Club", "Conference", "Division", "DivisionMembership", "League"]
