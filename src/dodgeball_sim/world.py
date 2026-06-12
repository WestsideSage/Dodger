"""V23 — The World: the 28-club pyramid.

Pure domain module (no I/O): division definitions, the fixed club identities
for the three generated divisions plus the seventh Premier club, per-tier
roster strength shifts, and the pyramid schedule/membership builders.
``career_setup`` composes these into a save at creation;
``pyramid_postseason`` consumes the memberships at season end.

Spec: docs/specs/2026-06-12-v23-the-world-spec.md (vision authority:
docs/specs/2026-06-12-climb-era-vision.md).

World shape (owner-confirmed 2026-06-12):
  D1 Premier League (the curated cast + Ridgeline) — tier 1
  D2 Challenger League (generated)               — tier 2
  D3 District League (generated; founding home)  — tier 3
  International Circuit (generated, strongest)   — closed, "the world"

Like the curated six, every generated club is a FIXED identity — the same
recurring cast in every save — while its roster is seeded per save. The user
founds at the bottom of D3 (TFM1 start) or takes over a curated Premier club
(TFM2 start).
"""
from __future__ import annotations

from typing import Dict, List, Mapping, Sequence

from .league import Club, Division, DivisionMembership
from .models import CoachPolicy
from .scheduler import ScheduledMatch, generate_round_robin
from .season import Season

WORLD_MODEL_STATE_KEY = "world_model"
WORLD_MODEL_PYRAMID = "pyramid"

PYRAMID_LEAGUE_ID = "pyramid"
DIVISION_SIZE = 7

PREMIER = Division("premier", "Premier League", 1, "domestic", "D1")
CHALLENGER = Division("challenger", "Challenger League", 2, "domestic", "D2")
DISTRICT = Division("district", "District League", 3, "domestic", "D3")
CIRCUIT = Division("circuit", "International Circuit", 1, "international", "INT")

DIVISIONS: tuple[Division, ...] = (PREMIER, CHALLENGER, DISTRICT, CIRCUIT)
DOMESTIC_DIVISIONS: tuple[Division, ...] = (PREMIER, CHALLENGER, DISTRICT)

# Roster strength by division, applied to the curated role base stats before
# per-player noise (career_setup.build_curated_roster(base_shift=...)). The
# Circuit is the strongest field in the world; D3 is the founding squeeze's
# honest habitat. Exact values are V23 balance constants — re-derivation of
# the dynasty witnesses on the 28-club world is the milestone's disclosed
# open cost until the verification pass closes it.
ROSTER_SHIFT_BY_DIVISION: Dict[str, float] = {
    PREMIER.division_id: 0.0,
    CHALLENGER.division_id: -6.0,
    DISTRICT.division_id: -11.0,
    CIRCUIT.division_id: 6.0,
}


def division_by_id(division_id: str) -> Division:
    for division in DIVISIONS:
        if division.division_id == division_id:
            return division
    raise KeyError(f"Unknown division: {division_id}")


def pyramid_world_active(conn) -> bool:
    """True when this save was created as a pyramid world (V23+)."""
    from .persistence import get_state

    return get_state(conn, WORLD_MODEL_STATE_KEY) == WORLD_MODEL_PYRAMID


def _club(
    club_id: str,
    name: str,
    *,
    region: str,
    founded: int,
    colors: str,
    primary: str,
    secondary: str,
    venue: str,
    tagline: str,
    approach: str,
    target_focus: str,
    catch_posture: str,
    rush_commit: str,
    rush_target: str,
) -> Club:
    return Club(
        club_id=club_id,
        name=name,
        colors=colors,
        home_region=region,
        founded_year=founded,
        coach_policy=CoachPolicy(
            approach=approach,
            target_focus=target_focus,
            catch_posture=catch_posture,
            rush_commit=rush_commit,
            rush_target=rush_target,
        ),
        primary_color=primary,
        secondary_color=secondary,
        venue_name=venue,
        tagline=tagline,
    )


# The seventh Premier identity (the curated cast is six; a seven-club tier is
# the pyramid's structural unit — scheduler byes, top-4 cut, and promotion
# math all assume it).
RIDGELINE = _club(
    "ridgeline", "Ridgeline Vanguard",
    region="Highlands", founded=1994, colors="slate/orange",
    primary="#475569", secondary="#EA7317", venue="The Summit Hall",
    tagline="Altitude training and a conveyor belt of two-way athletes",
    approach="mixed", target_focus="spread", catch_posture="go_for_catches",
    rush_commit="balanced", rush_target="nearest",
)

CHALLENGER_CLUBS: tuple[Club, ...] = (
    _club("copperline", "Copperline Foxes",
          region="Copper Valley", founded=2001, colors="copper/cream",
          primary="#B87333", secondary="#F4F1EA", venue="The Den",
          tagline="Opportunists who punish every loose ball",
          approach="mixed", target_focus="ball_holders", catch_posture="opportunistic",
          rush_commit="balanced", rush_target="nearest"),
    _club("riverton", "Riverton Current",
          region="Riverlands", founded=1997, colors="blue/white",
          primary="#2C6E91", secondary="#F8FAFC", venue="Floodgate Gym",
          tagline="Wave after wave of tempo throwing",
          approach="aggressive", target_focus="spread", catch_posture="opportunistic",
          rush_commit="all_in", rush_target="center"),
    _club("bellmare", "Bellmare Chargers",
          region="Bellmare", founded=2008, colors="yellow/navy",
          primary="#EAB308", secondary="#1E3A5F", venue="The Bell Tower",
          tagline="A storied bell that only rings for home wins",
          approach="aggressive", target_focus="their_stars", catch_posture="play_safe",
          rush_commit="balanced", rush_target="strongest_side"),
    _club("stillwater", "Stillwater Herons",
          region="Stillwater", founded=1989, colors="grey/teal",
          primary="#6B7F87", secondary="#2E5E5C", venue="Marsh Pavilion",
          tagline="Patient, long-armed, and infuriating to finish off",
          approach="patient", target_focus="spread", catch_posture="go_for_catches",
          rush_commit="hold_back", rush_target="center"),
    _club("foundry", "Foundry Pistons",
          region="Ironworks", founded=1993, colors="black/red",
          primary="#1C1917", secondary="#B91C1C", venue="The Press Floor",
          tagline="Industrial power throwing, zero apologies",
          approach="aggressive", target_focus="ball_holders", catch_posture="play_safe",
          rush_commit="all_in", rush_target="strongest_side"),
    _club("meadowbrook", "Meadowbrook Hornets",
          region="Meadowbrook", founded=2012, colors="gold/black",
          primary="#D6A23A", secondary="#191919", venue="The Nest",
          tagline="Small, fast, and they sting in swarms",
          approach="mixed", target_focus="spread", catch_posture="opportunistic",
          rush_commit="balanced", rush_target="nearest"),
    _club("kestrel", "Kestrel Bay Gulls",
          region="Kestrel Bay", founded=2004, colors="white/sky",
          primary="#E2E8F0", secondary="#3B82A0", venue="Bayside Court",
          tagline="Coastal pace and fearless catch-hunting",
          approach="patient", target_focus="their_stars", catch_posture="go_for_catches",
          rush_commit="hold_back", rush_target="nearest"),
)

# D3 carries the seven district identities the V24 Hometown motivation will
# mirror. Eastreach fields a club only in takeover worlds — in a founding
# world that seventh seat belongs to the player's new club.
DISTRICT_CLUBS: tuple[Club, ...] = (
    _club("harborside", "Harborside Rovers",
          region="Harborside District", founded=2016, colors="navy/rust",
          primary="#1F3A5F", secondary="#B75A3A", venue="Quay Shed 4",
          tagline="Dockworkers' club with a famous travelling support",
          approach="mixed", target_focus="spread", catch_posture="opportunistic",
          rush_commit="balanced", rush_target="center"),
    _club("oldquarter", "Old Quarter Wanderers",
          region="Old Quarter District", founded=1978, colors="maroon/gold",
          primary="#7F1D2D", secondary="#D6A23A", venue="The Cloisters",
          tagline="The oldest club in the districts, long past its glory",
          approach="patient", target_focus="their_stars", catch_posture="play_safe",
          rush_commit="hold_back", rush_target="center"),
    _club("millfields", "Millfields Athletic",
          region="Millfields District", founded=2010, colors="green/white",
          primary="#3F6B3F", secondary="#F8FAFC", venue="Granary Court",
          tagline="Honest graft and a strong junior pipeline",
          approach="mixed", target_focus="ball_holders", catch_posture="opportunistic",
          rush_commit="balanced", rush_target="nearest"),
    _club("northgate", "Northgate Union",
          region="Northgate District", founded=2019, colors="black/lime",
          primary="#18181B", secondary="#84CC16", venue="The Turnstile",
          tagline="A supporters' co-op that plays angry",
          approach="aggressive", target_focus="spread", catch_posture="opportunistic",
          rush_commit="all_in", rush_target="nearest"),
    _club("southbank", "Southbank Royals",
          region="Southbank District", founded=2014, colors="purple/silver",
          primary="#6D28D9", secondary="#CBD5E1", venue="Palace Lanes",
          tagline="Flashy throwers, allergic to defense",
          approach="aggressive", target_focus="their_stars", catch_posture="play_safe",
          rush_commit="balanced", rush_target="strongest_side"),
    _club("westvale", "Westvale Wolves",
          region="Westvale District", founded=2011, colors="grey/blue",
          primary="#4B5563", secondary="#2563EB", venue="The Hollow",
          tagline="Pack defense and counter-throw discipline",
          approach="patient", target_focus="ball_holders", catch_posture="go_for_catches",
          rush_commit="hold_back", rush_target="strongest_side"),
    _club("eastreach", "Eastreach Rangers",
          region="Eastreach District", founded=2017, colors="orange/black",
          primary="#EA7317", secondary="#191919", venue="Reach Rec Centre",
          tagline="Plucky rangers from the city's far edge",
          approach="mixed", target_focus="spread", catch_posture="opportunistic",
          rush_commit="balanced", rush_target="center"),
)

CIRCUIT_CLUBS: tuple[Club, ...] = (
    _club("osaka", "Osaka Tempo",
          region="Osaka", founded=1996, colors="white/crimson",
          primary="#F8FAFC", secondary="#B91C1C", venue="Namba Dome",
          tagline="Metronome passing and surgical target selection",
          approach="patient", target_focus="their_stars", catch_posture="opportunistic",
          rush_commit="balanced", rush_target="center"),
    _club("rhein", "Rhein Kollektiv",
          region="Rhineland", founded=1991, colors="black/white",
          primary="#18181B", secondary="#F8FAFC", venue="Werkhalle Eins",
          tagline="Systemized pressing dodgeball, decades of doctrine",
          approach="mixed", target_focus="ball_holders", catch_posture="go_for_catches",
          rush_commit="balanced", rush_target="strongest_side"),
    _club("bahia", "Bahia Cobras",
          region="Bahia", founded=2003, colors="green/yellow",
          primary="#15803D", secondary="#EAB308", venue="Ginásio da Costa",
          tagline="Improvisational genius and venomous counters",
          approach="aggressive", target_focus="spread", catch_posture="opportunistic",
          rush_commit="all_in", rush_target="nearest"),
    _club("stockholm", "Stockholm Norrsken",
          region="Stockholm", founded=1999, colors="ice/midnight",
          primary="#BFDBFE", secondary="#0F1A2E", venue="Polarhallen",
          tagline="Cold-blooded structure under the northern lights",
          approach="patient", target_focus="spread", catch_posture="go_for_catches",
          rush_commit="hold_back", rush_target="center"),
    _club("nairobi", "Nairobi Thunder",
          region="Nairobi", founded=2006, colors="red/black",
          primary="#DC2626", secondary="#191919", venue="Uhuru Arena",
          tagline="Explosive athleticism and a wall of noise behind it",
          approach="aggressive", target_focus="their_stars", catch_posture="opportunistic",
          rush_commit="all_in", rush_target="strongest_side"),
    _club("seoul", "Seoul Dynamo",
          region="Seoul", founded=2001, colors="blue/silver",
          primary="#1D4ED8", secondary="#CBD5E1", venue="Han River Court",
          tagline="Drilled mechanics and the world's best film room",
          approach="mixed", target_focus="ball_holders", catch_posture="play_safe",
          rush_commit="balanced", rush_target="center"),
    _club("marseille", "Marseille Mistral",
          region="Marseille", founded=1988, colors="white/azure",
          primary="#F8FAFC", secondary="#0E7490", venue="Le Vélodrome Couvert",
          tagline="Gale-force opening rushes off the Mediterranean",
          approach="aggressive", target_focus="spread", catch_posture="play_safe",
          rush_commit="all_in", rush_target="center"),
)


def pyramid_generated_clubs(*, founding: bool) -> Dict[str, List[Club]]:
    """The fixed generated cast by division (excludes curated + user clubs).

    ``founding=True`` leaves the seventh D3 seat open for the player's new
    club; takeover worlds field Eastreach instead.
    """
    district = list(DISTRICT_CLUBS[:-1]) if founding else list(DISTRICT_CLUBS)
    return {
        PREMIER.division_id: [RIDGELINE],
        CHALLENGER.division_id: list(CHALLENGER_CLUBS),
        DISTRICT.division_id: district,
        CIRCUIT.division_id: list(CIRCUIT_CLUBS),
    }


def membership_rows(
    season_id: str, assignment: Mapping[str, Sequence[str]]
) -> List[DivisionMembership]:
    """Build persistence rows from a division_id → club_ids assignment."""
    rows: List[DivisionMembership] = []
    for division_id, club_ids in assignment.items():
        division = division_by_id(division_id)
        for club_id in club_ids:
            rows.append(
                DivisionMembership(
                    season_id=season_id,
                    club_id=club_id,
                    division_id=division.division_id,
                    division_name=division.name,
                    tier=division.tier,
                    kind=division.kind,
                )
            )
    return rows


def create_pyramid_season(
    season_id: str,
    year: int,
    assignment: Mapping[str, Sequence[str]],
    root_seed: int,
    config_version: str = "phase1.v1",
    ruleset_version: str = "default.v1",
) -> Season:
    """One Season holding every division's round-robin, weeks aligned.

    Each division schedules independently (its own seeded home/away stream,
    namespaced by division id), then the fixtures merge into the single
    season the weekly loop already knows how to drive. Seven-club divisions
    produce seven aligned weeks with one bye club per division per week.
    """
    schedule: List[ScheduledMatch] = []
    for division_id in sorted(assignment.keys()):
        club_ids = list(assignment[division_id])
        if len(club_ids) < 2:
            raise ValueError(
                f"Division {division_id} needs at least 2 clubs, got {len(club_ids)}"
            )
        schedule.extend(
            generate_round_robin(
                club_ids=club_ids,
                root_seed=root_seed,
                season_id=season_id,
                league_id=f"{PYRAMID_LEAGUE_ID}_{division_id}",
            )
        )
    return Season(
        season_id=season_id,
        year=year,
        league_id=PYRAMID_LEAGUE_ID,
        config_version=config_version,
        ruleset_version=ruleset_version,
        scheduled_matches=tuple(schedule),
    )


__all__ = [
    "CHALLENGER",
    "CHALLENGER_CLUBS",
    "CIRCUIT",
    "CIRCUIT_CLUBS",
    "DISTRICT",
    "DISTRICT_CLUBS",
    "DIVISIONS",
    "DIVISION_SIZE",
    "DOMESTIC_DIVISIONS",
    "PREMIER",
    "PYRAMID_LEAGUE_ID",
    "RIDGELINE",
    "ROSTER_SHIFT_BY_DIVISION",
    "WORLD_MODEL_PYRAMID",
    "WORLD_MODEL_STATE_KEY",
    "create_pyramid_season",
    "division_by_id",
    "membership_rows",
    "pyramid_generated_clubs",
    "pyramid_world_active",
]
