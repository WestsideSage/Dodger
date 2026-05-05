from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RivalryMatchResult:
    match_id: str
    season_id: str
    club_a_id: str
    club_b_id: str
    winner_club_id: str | None
    score_margin: int
    was_playoff: bool = False
    was_championship: bool = False
    notable_moment: str = ""


@dataclass(frozen=True)
class RivalryRecord:
    club_a_id: str
    club_b_id: str
    a_wins: int = 0
    b_wins: int = 0
    draws: int = 0
    total_meetings: int = 0
    total_margin: int = 0
    playoff_meetings: int = 0
    championship_meetings: int = 0
    last_winner_club_id: str | None = None
    last_meeting_season: str = ""
    defining_moments: tuple[str, ...] = ()


def compute_rivalry_score(record: RivalryRecord) -> float:
    if record.total_meetings == 0:
        return 0.0
    balance_ratio = 1.0 - (
        abs(record.a_wins - record.b_wins) / max(1, record.total_meetings)
    )
    average_margin = record.total_margin / record.total_meetings
    closeness_ratio = 1.0 - min(average_margin, 8.0) / 8.0
    frequency_score = min(record.total_meetings, 10) * 4.0
    balance_score = balance_ratio * 35.0
    closeness_score = closeness_ratio * 20.0
    stage_score = record.playoff_meetings * 6.0 + record.championship_meetings * 10.0
    moment_score = min(len(record.defining_moments), 4) * 2.5
    return round(
        frequency_score + balance_score + closeness_score + stage_score + moment_score,
        2,
    )


def update_rivalry(
    record: RivalryRecord,
    match_result: RivalryMatchResult,
) -> RivalryRecord:
    canonical = _canonicalize(record, match_result)
    a_wins = canonical.a_wins
    b_wins = canonical.b_wins
    draws = canonical.draws
    last_winner = None

    if match_result.winner_club_id is None:
        draws += 1
    elif match_result.winner_club_id == canonical.club_a_id:
        a_wins += 1
        last_winner = canonical.club_a_id
    else:
        b_wins += 1
        last_winner = canonical.club_b_id

    moments = canonical.defining_moments
    if match_result.notable_moment.strip():
        moments = moments + (match_result.notable_moment.strip(),)

    return RivalryRecord(
        club_a_id=canonical.club_a_id,
        club_b_id=canonical.club_b_id,
        a_wins=a_wins,
        b_wins=b_wins,
        draws=draws,
        total_meetings=canonical.total_meetings + 1,
        total_margin=canonical.total_margin + abs(int(match_result.score_margin)),
        playoff_meetings=canonical.playoff_meetings + int(match_result.was_playoff),
        championship_meetings=canonical.championship_meetings
        + int(match_result.was_championship),
        last_winner_club_id=last_winner,
        last_meeting_season=match_result.season_id,
        defining_moments=moments,
    )


def _canonicalize(
    record: RivalryRecord,
    match_result: RivalryMatchResult,
) -> RivalryRecord:
    if {
        record.club_a_id,
        record.club_b_id,
    } != {match_result.club_a_id, match_result.club_b_id}:
        raise ValueError("Match result clubs do not match rivalry record clubs")
    if (
        record.club_a_id == match_result.club_a_id
        and record.club_b_id == match_result.club_b_id
    ):
        return record
    return RivalryRecord(
        club_a_id=record.club_a_id,
        club_b_id=record.club_b_id,
        a_wins=record.a_wins,
        b_wins=record.b_wins,
        draws=record.draws,
        total_meetings=record.total_meetings,
        total_margin=record.total_margin,
        playoff_meetings=record.playoff_meetings,
        championship_meetings=record.championship_meetings,
        last_winner_club_id=record.last_winner_club_id,
        last_meeting_season=record.last_meeting_season,
        defining_moments=record.defining_moments,
    )


__all__ = [
    "RivalryMatchResult",
    "RivalryRecord",
    "compute_rivalry_score",
    "update_rivalry",
]
