from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .scheduler import ScheduledMatch
from .season import StandingsRow


PLAYOFF_FORMAT = "top4_single_elimination"


@dataclass(frozen=True)
class PlayoffBracket:
    season_id: str
    format: str
    seeds: tuple[str, ...]
    rounds: tuple[Mapping[str, Any], ...]
    status: str


@dataclass(frozen=True)
class SeasonOutcome:
    season_id: str
    champion_club_id: str
    champion_source: str
    final_match_id: str | None
    runner_up_club_id: str | None
    payload: Mapping[str, Any]


def playoff_match_id_prefix(season_id: str) -> str:
    return f"{season_id}_p_"


def is_playoff_match_id(season_id: str, match_id: str) -> bool:
    return match_id.startswith(playoff_match_id_prefix(season_id))


def top_four_seeds(standings: Sequence[StandingsRow]) -> tuple[str, ...]:
    ordered = sorted(standings, key=lambda row: (-row.points, -row.elimination_differential, row.club_id))
    return tuple(row.club_id for row in ordered[:4])


def create_semifinal_bracket(
    season_id: str,
    standings: Sequence[StandingsRow],
    week: int,
) -> tuple[PlayoffBracket, tuple[ScheduledMatch, ...]]:
    seeds = top_four_seeds(standings)
    if len(seeds) < 4:
        raise ValueError("Top-4 playoffs require at least four seeded clubs")
    matchups = (
        ("semifinal_1", f"{season_id}_p_r1_m1", seeds[0], seeds[3]),
        ("semifinal_2", f"{season_id}_p_r1_m2", seeds[1], seeds[2]),
    )
    matches = tuple(
        ScheduledMatch(
            match_id=match_id,
            season_id=season_id,
            week=week,
            home_club_id=higher_seed,
            away_club_id=lower_seed,
        )
        for _round_name, match_id, higher_seed, lower_seed in matchups
    )
    bracket = PlayoffBracket(
        season_id=season_id,
        format=PLAYOFF_FORMAT,
        seeds=seeds,
        rounds=(
            {
                "round": "semifinal",
                "matches": [
                    {"match_id": match.match_id, "home": match.home_club_id, "away": match.away_club_id}
                    for match in matches
                ],
            },
        ),
        status="semifinals_scheduled",
    )
    return bracket, matches


def create_final_match(
    bracket: PlayoffBracket,
    winners_by_match_id: Mapping[str, str],
    week: int,
) -> tuple[PlayoffBracket, ScheduledMatch]:
    semi_round = next((round_info for round_info in bracket.rounds if round_info.get("round") == "semifinal"), None)
    if semi_round is None:
        raise ValueError("Bracket has no semifinal round")
    semi_matches = list(semi_round.get("matches", ()))
    if len(semi_matches) != 2:
        raise ValueError("Bracket must have two semifinal matches")
    finalists = tuple(winners_by_match_id.get(match["match_id"]) for match in semi_matches)
    if any(finalist is None for finalist in finalists):
        raise ValueError("Both semifinal winners are required")
    seed_rank = {club_id: index for index, club_id in enumerate(bracket.seeds)}
    first, second = finalists
    home, away = sorted((str(first), str(second)), key=lambda club_id: seed_rank[club_id])
    final = ScheduledMatch(
        match_id=f"{bracket.season_id}_p_final",
        season_id=bracket.season_id,
        week=week,
        home_club_id=home,
        away_club_id=away,
    )
    rounds = tuple(bracket.rounds) + (
        {"round": "final", "matches": [{"match_id": final.match_id, "home": home, "away": away}]},
    )
    return (
        PlayoffBracket(
            season_id=bracket.season_id,
            format=bracket.format,
            seeds=bracket.seeds,
            rounds=rounds,
            status="final_scheduled",
        ),
        final,
    )


def outcome_from_final(
    bracket: PlayoffBracket,
    *,
    final_match_id: str,
    home_club_id: str,
    away_club_id: str,
    winner_club_id: str,
) -> SeasonOutcome:
    runner_up = away_club_id if winner_club_id == home_club_id else home_club_id
    return SeasonOutcome(
        season_id=bracket.season_id,
        champion_club_id=winner_club_id,
        champion_source="playoff_final",
        final_match_id=final_match_id,
        runner_up_club_id=runner_up,
        payload={"format": bracket.format, "seeds": list(bracket.seeds)},
    )


def playoff_stage_label(season_id: str, match_id: str) -> str:
    if match_id == f"{season_id}_p_r1_m1" or match_id == f"{season_id}_p_r1_m2":
        return "Playoff Semifinal"
    if match_id == f"{season_id}_p_final":
        return "Playoff Final"
    return "Regular Season"


__all__ = [
    "PLAYOFF_FORMAT",
    "PlayoffBracket",
    "SeasonOutcome",
    "create_final_match",
    "create_semifinal_bracket",
    "is_playoff_match_id",
    "outcome_from_final",
    "playoff_match_id_prefix",
    "playoff_stage_label",
    "top_four_seeds",
]
