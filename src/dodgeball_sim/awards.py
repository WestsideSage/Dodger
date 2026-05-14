from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .stats import PlayerMatchStats


@dataclass(frozen=True)
class SeasonAward:
    season_id: str
    award_type: str   # "mvp", "best_thrower", "best_catcher", "best_newcomer"
    player_id: str
    club_id: str
    award_score: float


# ---------------------------------------------------------------------------
# MVP formula — versioned via config in future; hardcoded coefficients for now
# ---------------------------------------------------------------------------

_MVP_WEIGHTS = {
    "eliminations_by_throw": 3.0,
    "catches_made": 4.0,
    "dodges_successful": 1.5,
    "revivals_caused": 2.0,
    "times_eliminated": -2.0,
    "clutch_events": 3.0,
}

_CHAMPIONSHIP_BONUS = 20.0


def _mvp_score(stats: PlayerMatchStats) -> float:
    return (
        _MVP_WEIGHTS["eliminations_by_throw"] * stats.eliminations_by_throw
        + _MVP_WEIGHTS["catches_made"] * stats.catches_made
        + _MVP_WEIGHTS["dodges_successful"] * stats.dodges_successful
        + _MVP_WEIGHTS["revivals_caused"] * stats.revivals_caused
        + _MVP_WEIGHTS["times_eliminated"] * stats.times_eliminated
        + _MVP_WEIGHTS["clutch_events"] * stats.clutch_events
    )


def compute_season_awards(
    season_id: str,
    player_season_stats: Dict[str, PlayerMatchStats],
    player_club_map: Dict[str, str],
    newcomer_player_ids: frozenset,
    champion_club_id: Optional[str] = None,
) -> List[SeasonAward]:
    """Compute all season awards from aggregated per-player stats. Pure.

    Args:
        season_id: identifier for the season.
        player_season_stats: player_id → summed PlayerMatchStats across all matches.
        player_club_map: player_id → club_id (their club at season end).
        newcomer_player_ids: set of player_ids flagged as newcomers this season.
        champion_club_id: club_id of the season champion, or None if no champion.
    """
    if not player_season_stats:
        return []

    def _award(award_type: str, player_id: str, score: float) -> SeasonAward:
        return SeasonAward(
            season_id=season_id,
            award_type=award_type,
            player_id=player_id,
            club_id=player_club_map.get(player_id, "unknown"),
            award_score=round(score, 4),
        )

    awards: List[SeasonAward] = []

    base_scored = {pid: _mvp_score(stats) for pid, stats in player_season_stats.items()}
    # Championship bonus: players on the title-winning club get a flat boost.
    # Stats remain the primary driver; the bonus only tips a close race.
    scored = {
        pid: score + (
            _CHAMPIONSHIP_BONUS
            if champion_club_id and player_club_map.get(pid) == champion_club_id
            else 0.0
        )
        for pid, score in base_scored.items()
    }

    # MVP — highest mvp_score overall (with optional championship bonus)
    mvp_id = max(scored, key=lambda pid: (scored[pid], pid))
    awards.append(_award("mvp", mvp_id, scored[mvp_id]))

    # Best Thrower — most eliminations_by_throw
    best_thrower_id = max(
        player_season_stats,
        key=lambda pid: (player_season_stats[pid].eliminations_by_throw, pid),
    )
    awards.append(
        _award(
            "best_thrower",
            best_thrower_id,
            float(player_season_stats[best_thrower_id].eliminations_by_throw),
        )
    )

    # Best Catcher — most catches_made
    best_catcher_id = max(
        player_season_stats,
        key=lambda pid: (player_season_stats[pid].catches_made, pid),
    )
    awards.append(
        _award(
            "best_catcher",
            best_catcher_id,
            float(player_season_stats[best_catcher_id].catches_made),
        )
    )

    # Best Newcomer — highest mvp_score among newcomer_player_ids
    newcomers_present = newcomer_player_ids & player_season_stats.keys()
    if newcomers_present:
        best_newcomer_id = max(newcomers_present, key=lambda pid: (scored[pid], pid))
        awards.append(_award("best_newcomer", best_newcomer_id, scored[best_newcomer_id]))

    return awards


def compute_match_mvp(player_match_stats: Dict[str, PlayerMatchStats]) -> Optional[str]:
    """Return the match MVP player_id, or None when no stats are available."""
    if not player_match_stats:
        return None
    return max(
        player_match_stats,
        key=lambda player_id: (_mvp_score(player_match_stats[player_id]), player_id),
    )


def aggregate_season_stats(
    per_match_stats: Dict[str, List[PlayerMatchStats]],
) -> Dict[str, PlayerMatchStats]:
    """Sum per-match stats into one PlayerMatchStats per player. Pure."""
    result: Dict[str, PlayerMatchStats] = {}
    for player_id, match_list in per_match_stats.items():
        result[player_id] = PlayerMatchStats(
            throws_attempted=sum(s.throws_attempted for s in match_list),
            throws_on_target=sum(s.throws_on_target for s in match_list),
            eliminations_by_throw=sum(s.eliminations_by_throw for s in match_list),
            catches_attempted=sum(s.catches_attempted for s in match_list),
            catches_made=sum(s.catches_made for s in match_list),
            times_targeted=sum(s.times_targeted for s in match_list),
            dodges_successful=sum(s.dodges_successful for s in match_list),
            times_hit=sum(s.times_hit for s in match_list),
            times_eliminated=sum(s.times_eliminated for s in match_list),
            revivals_caused=sum(s.revivals_caused for s in match_list),
            clutch_events=sum(s.clutch_events for s in match_list),
            elimination_plus_minus=sum(s.elimination_plus_minus for s in match_list),
            minutes_played=sum(s.minutes_played for s in match_list),
        )
    return result


__all__ = [
    "SeasonAward",
    "compute_match_mvp",
    "compute_season_awards",
    "aggregate_season_stats",
]
