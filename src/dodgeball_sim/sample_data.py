from __future__ import annotations

from typing import List

from .league import Club
from .models import CoachPolicy, MatchSetup, Player, PlayerRatings, PlayerTraits, Team
from .setup_loader import describe_matchup


def _player(
    player_id: str,
    name: str,
    *,
    accuracy: float,
    power: float,
    dodge: float,
    catch: float,
    stamina: float = 60.0,
) -> Player:
    ratings = PlayerRatings(
        accuracy=accuracy,
        power=power,
        dodge=dodge,
        catch=catch,
        stamina=stamina,
    ).apply_bounds()
    return Player(id=player_id, name=name, ratings=ratings, traits=PlayerTraits())


def _team(
    team_id: str,
    name: str,
    players: List[Player],
    *,
    policy: CoachPolicy,
    chemistry: float,
) -> Team:
    return Team(id=team_id, name=name, players=tuple(players), coach_policy=policy, chemistry=chemistry)


_AURORA = Club(
    club_id="aurora",
    name="Aurora Sentinels",
    colors="teal/charcoal",
    home_region="Northwest",
    founded_year=1998,
    coach_policy=CoachPolicy(target_stars=0.7, risk_tolerance=0.55, sync_throws=0.25, tempo=0.5, rush_frequency=0.45),
    primary_color="#2E5E5C",
    secondary_color="#1F2933",
    venue_name="Aurora Field House",
    tagline="Calculated aggression and deep scouting tradition",
)

_LUNAR = Club(
    club_id="lunar",
    name="Lunar Syndicate",
    colors="silver/navy",
    home_region="Northeast",
    founded_year=2002,
    coach_policy=CoachPolicy(target_stars=0.65, risk_tolerance=0.45, sync_throws=0.35, tempo=0.42, rush_frequency=0.5),
    primary_color="#5C6F8A",
    secondary_color="#0F1A2E",
    venue_name="Arc Pavilion",
    tagline="Patience, attrition, and an ironclad defensive system",
)

_NORTHWOOD = Club(
    club_id="northwood",
    name="Northwood Ironclads",
    colors="brick/cream",
    home_region="Midwest",
    founded_year=1985,
    coach_policy=CoachPolicy(target_stars=0.8, risk_tolerance=0.7, sync_throws=0.4, tempo=0.65, rush_frequency=0.6),
    primary_color="#B75A3A",
    secondary_color="#F4F1EA",
    venue_name="Wrecker Yard",
    tagline="Relentless tempo and unapologetic power throwing",
)

_HARBOR = Club(
    club_id="harbor",
    name="Harbor Tidebreakers",
    colors="navy/gold",
    home_region="Coastal",
    founded_year=1990,
    coach_policy=CoachPolicy(target_stars=0.55, risk_tolerance=0.4, sync_throws=0.3, tempo=0.4, rush_frequency=0.35),
    primary_color="#1F3A5F",
    secondary_color="#D6A23A",
    venue_name="Anchorage Hall",
    tagline="A punishing defensive grind built on league-best catchers",
)

_GRANITE = Club(
    club_id="granite",
    name="Granite Specters",
    colors="sage/charcoal",
    home_region="Mountain",
    founded_year=2010,
    coach_policy=CoachPolicy(target_stars=0.6, risk_tolerance=0.5, sync_throws=0.5, tempo=0.55, rush_frequency=0.55),
    primary_color="#8FA87E",
    secondary_color="#242428",
    venue_name="Granite Arena",
    tagline="Swarm tactics and deep rotation pressure",
)

_SOLSTICE = Club(
    club_id="solstice",
    name="Solstice Flare",
    colors="mustard/black",
    home_region="South",
    founded_year=2005,
    coach_policy=CoachPolicy(target_stars=0.75, risk_tolerance=0.6, sync_throws=0.45, tempo=0.6, rush_frequency=0.5),
    primary_color="#D6A23A",
    secondary_color="#242428",
    venue_name="Ember Court",
    tagline="Surgical sniper control and accuracy-focused recruitment",
)


def curated_clubs() -> List[Club]:
    """Return the v1 curated cast in display order."""
    return [_AURORA, _LUNAR, _NORTHWOOD, _HARBOR, _GRANITE, _SOLSTICE]


_TEAM_A = _team(
    "aurora",
    "Aurora Sentinels",
    [
        _player("aurora_captain", "Marcus Vance", accuracy=78, power=72, dodge=60, catch=55),
        _player("aurora_scout", "Elena Cross", accuracy=68, power=52, dodge=64, catch=58),
        _player("aurora_rookie", "Jamal Hayes", accuracy=60, power=50, dodge=52, catch=65),
    ],
    policy=_AURORA.coach_policy,
    chemistry=0.58,
)

_TEAM_B = _team(
    "lunar",
    "Lunar Syndicate",
    [
        _player("lunar_captain", "Sarah Ives", accuracy=75, power=70, dodge=57, catch=50),
        _player("lunar_anchor", "David Mercer", accuracy=65, power=60, dodge=62, catch=70),
        _player("lunar_spotter", "Chloe Bridges", accuracy=55, power=48, dodge=58, catch=60),
    ],
    policy=_LUNAR.coach_policy,
    chemistry=0.52,
)


def sample_match_setup() -> MatchSetup:
    """Return the canonical sample matchup for demos/CLI."""

    return MatchSetup(team_a=_TEAM_A, team_b=_TEAM_B, config_version="phase1.v1")


def describe_sample_matchup() -> str:
    return describe_matchup(sample_match_setup())


__all__ = ["curated_clubs", "sample_match_setup", "describe_sample_matchup"]
