from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping


@dataclass(frozen=True)
class CareerStats:
    player_id: str
    player_name: str
    club_id: str | None = None
    career_eliminations: int = 0
    career_catches: int = 0
    career_dodges: int = 0
    seasons_at_one_club: int = 0
    championships: int = 0


@dataclass(frozen=True)
class TeamRecordStats:
    club_id: str
    club_name: str
    titles: int = 0
    unbeaten_run: int = 0


@dataclass(frozen=True)
class UpsetResult:
    match_id: str
    season_id: str
    winner_club_id: str
    winner_club_name: str
    loser_club_id: str
    loser_club_name: str
    winner_overall: float
    loser_overall: float

    @property
    def overall_gap(self) -> float:
        return round(self.loser_overall - self.winner_overall, 2)


@dataclass(frozen=True)
class LeagueRecord:
    record_type: str
    holder_id: str
    holder_type: str
    holder_name: str
    value: float
    set_in_season: str
    detail: str = ""


@dataclass(frozen=True)
class RecordBroken:
    record_type: str
    holder_id: str
    holder_type: str
    holder_name: str
    previous_holder_id: str | None
    previous_value: float
    new_value: float
    set_in_season: str
    detail: str = ""


_INDIVIDUAL_RECORD_TYPES = {
    "career_eliminations": "career_eliminations",
    "career_catches": "career_catches",
    "career_dodges": "career_dodges",
    "most_seasons_at_one_club": "seasons_at_one_club",
    "most_championships": "championships",
}


def build_individual_records(
    career_stats: Iterable[CareerStats],
    season_id: str,
) -> dict[str, LeagueRecord]:
    stats = list(career_stats)
    if not stats:
        return {}
    return {
        record_type: _best_player_record(record_type, stats, attribute_name, season_id)
        for record_type, attribute_name in _INDIVIDUAL_RECORD_TYPES.items()
    }


def build_team_records(
    team_stats: Iterable[TeamRecordStats],
    upset_results: Iterable[UpsetResult],
    season_id: str,
) -> dict[str, LeagueRecord]:
    clubs = list(team_stats)
    upsets = list(upset_results)
    records: dict[str, LeagueRecord] = {}
    if clubs:
        records["most_titles"] = _best_team_record("most_titles", clubs, "titles", season_id)
        records["longest_unbeaten_run"] = _best_team_record(
            "longest_unbeaten_run",
            clubs,
            "unbeaten_run",
            season_id,
        )
    if upsets:
        best_upset = max(
            upsets,
            key=lambda item: (item.overall_gap, item.season_id, item.match_id),
        )
        records["biggest_upset_win"] = LeagueRecord(
            record_type="biggest_upset_win",
            holder_id=best_upset.winner_club_id,
            holder_type="club",
            holder_name=best_upset.winner_club_name,
            value=best_upset.overall_gap,
            set_in_season=best_upset.season_id,
            detail=(
                f"beat {best_upset.loser_club_name} as a "
                f"{best_upset.overall_gap:.1f} OVR underdog"
            ),
        )
    return records


def check_records_broken(
    match_stats: Mapping[str, object] | None,
    career_stats: Iterable[CareerStats],
    current_records: Mapping[str, LeagueRecord],
) -> list[RecordBroken]:
    payload = dict(match_stats or {})
    season_id = str(payload.get("season_id", "unknown_season"))
    team_stats = list(payload.get("team_stats", ()))
    upset_results = list(payload.get("upset_results", ()))
    next_records: dict[str, LeagueRecord] = {}
    next_records.update(build_individual_records(career_stats, season_id))
    next_records.update(build_team_records(team_stats, upset_results, season_id))

    broken: list[RecordBroken] = []
    for record_type, next_record in sorted(next_records.items()):
        current = current_records.get(record_type)
        current_value = current.value if current is not None else float("-inf")
        if next_record.value <= current_value:
            continue
        broken.append(
            RecordBroken(
                record_type=record_type,
                holder_id=next_record.holder_id,
                holder_type=next_record.holder_type,
                holder_name=next_record.holder_name,
                previous_holder_id=current.holder_id if current is not None else None,
                previous_value=0.0 if current is None else current.value,
                new_value=next_record.value,
                set_in_season=next_record.set_in_season,
                detail=next_record.detail,
            )
        )
    return broken


def _best_player_record(
    record_type: str,
    career_stats: list[CareerStats],
    attribute_name: str,
    season_id: str,
) -> LeagueRecord:
    leader = max(
        career_stats,
        key=lambda item: (
            getattr(item, attribute_name),
            item.player_name,
            item.player_id,
        ),
    )
    value = float(getattr(leader, attribute_name))
    return LeagueRecord(
        record_type=record_type,
        holder_id=leader.player_id,
        holder_type="player",
        holder_name=leader.player_name,
        value=value,
        set_in_season=season_id,
        detail=_record_detail(record_type, leader.player_name, value),
    )


def _best_team_record(
    record_type: str,
    team_stats: list[TeamRecordStats],
    attribute_name: str,
    season_id: str,
) -> LeagueRecord:
    leader = max(
        team_stats,
        key=lambda item: (
            getattr(item, attribute_name),
            item.club_name,
            item.club_id,
        ),
    )
    value = float(getattr(leader, attribute_name))
    return LeagueRecord(
        record_type=record_type,
        holder_id=leader.club_id,
        holder_type="club",
        holder_name=leader.club_name,
        value=value,
        set_in_season=season_id,
        detail=_record_detail(record_type, leader.club_name, value),
    )


def _record_detail(record_type: str, holder_name: str, value: float) -> str:
    labels = {
        "career_eliminations": "career eliminations",
        "career_catches": "career catches",
        "career_dodges": "career dodges",
        "most_seasons_at_one_club": "seasons with one club",
        "most_championships": "championships",
        "most_titles": "titles",
        "longest_unbeaten_run": "match unbeaten run",
    }
    label = labels.get(record_type, record_type.replace("_", " "))
    numeric_value = float(value)
    if numeric_value.is_integer():
        rendered_value = str(int(value))
    else:
        rendered_value = f"{value:.1f}"
    return f"{holder_name} now leads with {rendered_value} {label}"


__all__ = [
    "CareerStats",
    "LeagueRecord",
    "RecordBroken",
    "TeamRecordStats",
    "UpsetResult",
    "build_individual_records",
    "build_team_records",
    "check_records_broken",
]
