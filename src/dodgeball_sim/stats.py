from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .events import MatchEvent


@dataclass(frozen=True)
class PlayerMatchStats:
    throws_attempted: int = 0
    throws_on_target: int = 0
    eliminations_by_throw: int = 0
    catches_attempted: int = 0
    catches_made: int = 0
    times_targeted: int = 0
    dodges_successful: int = 0      # throw targeting this player resolved as "dodged" (not on-target)
    times_hit: int = 0              # on-target throws not caught or dodged; == times_eliminated in default ruleset
    times_eliminated: int = 0       # times removed from play (hit as target OR caught as thrower)
    revivals_caused: int = 0        # catch revivals triggered; 0 in default ruleset (no catch_revival)
    clutch_events: int = 0          # populated by analysis layer after extraction
    elimination_plus_minus: int = 0  # team elims minus opp elims while this player was alive
    minutes_played: int = 0


@dataclass(frozen=True)
class ClubMatchStats:
    outs_recorded: int = 0
    catches_made: int = 0
    throws_attempted: int = 0
    surviving_players: int = 0


def extract_player_stats(
    events: List[MatchEvent],
    player_id: str,
    player_team_id: str,
) -> PlayerMatchStats:
    """Derive PlayerMatchStats for one player from an ordered event log. Pure."""
    throws_attempted = 0
    throws_on_target = 0
    eliminations_by_throw = 0
    catches_attempted = 0
    catches_made = 0
    times_targeted = 0
    dodges_successful = 0
    times_hit = 0
    times_eliminated = 0
    team_elims = 0  # opponents eliminated while player alive
    opp_elims = 0   # teammates eliminated while player alive
    player_alive = True
    minutes_played = 0
    last_tick = 0

    for event in events:
        tick = getattr(event, "tick", getattr(event, "_tick", 0))
        if player_alive:
            minutes_played += max(0, tick - last_tick)
        last_tick = tick
        
        if event.event_type != "throw":
            continue

        actors = event.actors
        resolution = event.outcome.get("resolution", "")
        elim_info = event.state_diff.get("player_out")

        is_thrower = actors.get("thrower") == player_id
        is_target = actors.get("target") == player_id

        # Thrower stats
        if is_thrower:
            throws_attempted += 1
            if resolution in ("hit", "failed_catch", "catch"):
                throws_on_target += 1
            if resolution in ("hit", "failed_catch"):
                eliminations_by_throw += 1

        # Target stats
        if is_target:
            times_targeted += 1
            if resolution == "dodged":
                dodges_successful += 1
            elif resolution in ("hit", "failed_catch"):
                times_hit += 1
                if resolution == "failed_catch":
                    catches_attempted += 1
            elif resolution == "catch":
                catches_attempted += 1
                catches_made += 1

        # Plus-minus: count while player is alive, before marking them out
        if player_alive and elim_info:
            eliminated_id = elim_info.get("player_id")
            eliminated_team = elim_info.get("team")
            if eliminated_id and eliminated_id != player_id and eliminated_team:
                if eliminated_team == player_team_id:
                    opp_elims += 1   # teammate went out = opponent scored
                else:
                    team_elims += 1  # opponent went out = we scored

        # Detect when this player is eliminated
        if elim_info and elim_info.get("player_id") == player_id:
            times_eliminated += 1
            player_alive = False

    return PlayerMatchStats(
        throws_attempted=throws_attempted,
        throws_on_target=throws_on_target,
        eliminations_by_throw=eliminations_by_throw,
        catches_attempted=catches_attempted,
        catches_made=catches_made,
        times_targeted=times_targeted,
        dodges_successful=dodges_successful,
        times_hit=times_hit,
        times_eliminated=times_eliminated,
        revivals_caused=0,
        clutch_events=0,
        elimination_plus_minus=team_elims - opp_elims,
        minutes_played=minutes_played,
    )


def extract_all_stats(
    events: List[MatchEvent],
    team_a_id: str,
    team_b_id: str,
    team_a_player_ids: List[str],
    team_b_player_ids: List[str],
) -> Dict[str, PlayerMatchStats]:
    """Extract stats for all players in a match. Returns player_id → stats."""
    result: Dict[str, PlayerMatchStats] = {}
    for pid in team_a_player_ids:
        result[pid] = extract_player_stats(events, pid, team_a_id)
    for pid in team_b_player_ids:
        result[pid] = extract_player_stats(events, pid, team_b_id)
    return result


def aggregate_club_stats(
    player_stats: List[PlayerMatchStats],
    surviving_players: int,
) -> ClubMatchStats:
    """Aggregate per-player stats into club-level match stats. Pure."""
    return ClubMatchStats(
        outs_recorded=sum(s.eliminations_by_throw for s in player_stats),
        catches_made=sum(s.catches_made for s in player_stats),
        throws_attempted=sum(s.throws_attempted for s in player_stats),
        surviving_players=surviving_players,
    )


__all__ = [
    "PlayerMatchStats",
    "ClubMatchStats",
    "extract_player_stats",
    "extract_all_stats",
    "aggregate_club_stats",
]
