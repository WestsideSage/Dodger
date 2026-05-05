from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .scheduler import ScheduledMatch


@dataclass(frozen=True)
class SimRequest:
    mode: str
    current_week: int | None = None
    weeks: int = 1
    include_user_matches: bool = False
    milestone: str | None = None
    milestone_week: int | None = None


@dataclass(frozen=True)
class SimStop:
    reason: str
    match_id: str | None = None
    week: int | None = None


def choose_matches_to_sim(
    schedule: Sequence[ScheduledMatch],
    completed_match_ids: set[str],
    player_club_id: str,
    request: SimRequest,
) -> tuple[list[ScheduledMatch], SimStop]:
    """Choose pending matches for a bulk-sim request without crossing stop points."""
    pending = sorted(
        [match for match in schedule if match.match_id not in completed_match_ids],
        key=lambda m: (m.week, m.match_id),
    )
    chosen: list[ScheduledMatch] = []
    start_week = request.current_week if request.current_week is not None else (pending[0].week if pending else None)

    for match in pending:
        if request.mode == "week" and start_week is not None and match.week != start_week:
            continue
        if request.mode == "multiple_weeks" and start_week is not None and match.week >= start_week + request.weeks:
            break
        if request.mode == "milestone":
            stop = _milestone_stop(match, request)
            if stop is not None:
                return chosen, stop
        if _is_user_match(match, player_club_id) and not request.include_user_matches:
            return chosen, SimStop(reason="user_match", match_id=match.match_id, week=match.week)
        chosen.append(match)

    reason = "season_complete" if not pending or len(chosen) == len(pending) else "request_complete"
    return chosen, SimStop(reason=reason)


def summarize_sim_digest(
    *,
    matches_simmed: int,
    user_record_delta: str,
    standings_note: str,
    notable_lines: Iterable[str],
    scouting_note: str = "No scouting updates.",
    recruitment_note: str = "No recruitment updates.",
    next_action: str,
) -> dict[str, object]:
    return {
        "matches_simmed": matches_simmed,
        "user_record_delta": user_record_delta,
        "standings_note": standings_note,
        "notable_lines": list(notable_lines),
        "scouting_note": scouting_note,
        "recruitment_note": recruitment_note,
        "next_action": next_action,
    }


def _milestone_stop(match: ScheduledMatch, request: SimRequest) -> SimStop | None:
    milestone = (request.milestone or "").lower()
    milestone_week = request.milestone_week
    if milestone in {"recruitment_day", "offseason", "offseason_ceremony", "development", "retirement"}:
        if milestone_week is not None and match.week >= milestone_week:
            return SimStop(reason=milestone, week=milestone_week)
    if milestone == "playoffs" and "_p_" in match.match_id:
        return SimStop(reason="playoffs", match_id=match.match_id, week=match.week)
    if milestone in {"season_end", "champion", "hall_of_fame", "record", "signature_event"}:
        if milestone_week is not None and match.week >= milestone_week:
            return SimStop(reason=milestone, week=milestone_week)
    return None


def _is_user_match(match: ScheduledMatch, player_club_id: str) -> bool:
    return player_club_id in (match.home_club_id, match.away_club_id)


__all__ = ["SimRequest", "SimStop", "choose_matches_to_sim", "summarize_sim_digest"]
