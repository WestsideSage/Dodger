"""Discipline domain records and deterministic effects (Section 34-35).

This module implements the warnings, blue cards, and discipline state machines
for V11, including escalation from warnings to blue cards and placeholder
yellow cards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any

from .catch_queue import CatchQueueState
from .official_events import OfficialEvent, OfficialEventKind, RuleReference
from .match_lifecycle import OfficialGameResult
from .player_state import OfficialPlayerState, OfficialPlayerStatus


@dataclass
class WarningRecord:
    """Represents a verbal warning issued to a player."""
    player_id: str
    team_id: str
    offense: str
    match_id: str
    game_id: str | None = None
    timestamp_ms: int = 0


@dataclass
class BlueCardRecord:
    """Represents a blue card issued to a player."""
    player_id: str
    team_id: str
    offense: str
    match_id: str
    prior_warning_count: int = 0


@dataclass
class DisciplineState:
    """Per-match mutable disciplinary state."""
    warnings_by_player: Dict[str, List[WarningRecord]] = field(default_factory=dict)
    warnings_by_team: Dict[str, List[WarningRecord]] = field(default_factory=dict)
    blue_cards_by_player: Dict[str, List[BlueCardRecord]] = field(default_factory=dict)
    yellow_card_placeholder_emitted: Set[Tuple[str, str]] = field(default_factory=set)

    def to_dict(self) -> dict:
        return {
            "warnings_by_player": {
                pid: [
                    {
                        "player_id": r.player_id,
                        "team_id": r.team_id,
                        "offense": r.offense,
                        "match_id": r.match_id,
                        "game_id": r.game_id,
                        "timestamp_ms": r.timestamp_ms
                    }
                    for r in records
                ]
                for pid, records in self.warnings_by_player.items()
            },
            "warnings_by_team": {
                tid: [
                    {
                        "player_id": r.player_id,
                        "team_id": r.team_id,
                        "offense": r.offense,
                        "match_id": r.match_id,
                        "game_id": r.game_id,
                        "timestamp_ms": r.timestamp_ms
                    }
                    for r in records
                ]
                for tid, records in self.warnings_by_team.items()
            },
            "blue_cards_by_player": {
                pid: [
                    {
                        "player_id": r.player_id,
                        "team_id": r.team_id,
                        "offense": r.offense,
                        "match_id": r.match_id,
                        "prior_warning_count": r.prior_warning_count
                    }
                    for r in records
                ]
                for pid, records in self.blue_cards_by_player.items()
            },
            "yellow_card_placeholder_emitted": [
                [player_id, offense]
                for player_id, offense in self.yellow_card_placeholder_emitted
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> DisciplineState:
        warnings_by_player = {}
        for pid, records in data.get("warnings_by_player", {}).items():
            warnings_by_player[pid] = [
                WarningRecord(
                    player_id=r["player_id"],
                    team_id=r["team_id"],
                    offense=r["offense"],
                    match_id=r["match_id"],
                    game_id=r.get("game_id"),
                    timestamp_ms=r["timestamp_ms"],
                )
                for r in records
            ]

        warnings_by_team = {}
        for tid, records in data.get("warnings_by_team", {}).items():
            warnings_by_team[tid] = [
                WarningRecord(
                    player_id=r["player_id"],
                    team_id=r["team_id"],
                    offense=r["offense"],
                    match_id=r["match_id"],
                    game_id=r.get("game_id"),
                    timestamp_ms=r["timestamp_ms"],
                )
                for r in records
            ]

        blue_cards_by_player = {}
        for pid, records in data.get("blue_cards_by_player", {}).items():
            blue_cards_by_player[pid] = [
                BlueCardRecord(
                    player_id=r["player_id"],
                    team_id=r["team_id"],
                    offense=r["offense"],
                    match_id=r["match_id"],
                    prior_warning_count=r["prior_warning_count"],
                )
                for r in records
            ]

        yellow_card_placeholder_emitted = set(
            (item[0], item[1])
            for item in data.get("yellow_card_placeholder_emitted", [])
        )

        return cls(
            warnings_by_player=warnings_by_player,
            warnings_by_team=warnings_by_team,
            blue_cards_by_player=blue_cards_by_player,
            yellow_card_placeholder_emitted=yellow_card_placeholder_emitted,
        )


def issue_warning(
    state: DisciplineState,
    queue: CatchQueueState | None = None,
    *,
    player_id: str,
    team_id: str,
    offense: str,
    match_id: str,
    game_id: str | None = None,
    timestamp_ms: int = 0,
    players: Dict[str, OfficialPlayerState] | None = None,
    game_state: Any = None,
    team_a_id: str | None = None,
) -> Tuple[Optional[OfficialEvent], Optional[OfficialEvent]]:
    """Issue a verbal warning to a player (Section 34).

    If the same player + offense has been warned before in this match, escalate
    to a blue card by calling issue_blue_card and returning that as the second
    tuple element.
    """
    prior_warnings = [
        w for w in state.warnings_by_player.get(player_id, [])
        if w.offense == offense
    ]

    if prior_warnings and queue is not None:
        # Escalate to blue card
        blue_event, yellow_or_forfeit = issue_blue_card(
            state,
            queue,
            player_id=player_id,
            team_id=team_id,
            offense=offense,
            match_id=match_id,
            game_id=game_id,
            timestamp_ms=timestamp_ms,
            players=players,
            game_state=game_state,
            team_a_id=team_a_id,
        )
        return None, blue_event

    # Record warning
    record = WarningRecord(
        player_id=player_id,
        team_id=team_id,
        offense=offense,
        match_id=match_id,
        game_id=game_id,
        timestamp_ms=timestamp_ms,
    )
    if player_id not in state.warnings_by_player:
        state.warnings_by_player[player_id] = []
    state.warnings_by_player[player_id].append(record)

    if team_id not in state.warnings_by_team:
        state.warnings_by_team[team_id] = []
    state.warnings_by_team[team_id].append(record)

    warn_event = OfficialEvent(
        event_id=f"warn-{player_id}-{offense.replace(' ', '_')}-{len(state.warnings_by_player[player_id])}",
        kind=OfficialEventKind.DISCIPLINE,
        match_id=match_id,
        game_id=game_id,
        rule_refs=(RuleReference("34"),),
        player_ids=(player_id,),
        team_ids=(team_id,),
        replay_summary=f"Verbal warning issued to {player_id} (Team {team_id}) for {offense}.",
        payload={"kind": "warning", "offense": offense},
    )

    return warn_event, None


def issue_blue_card(
    state: DisciplineState,
    queue: CatchQueueState,
    *,
    player_id: str,
    team_id: str,
    offense: str,
    match_id: str,
    game_id: str | None = None,
    timestamp_ms: int = 0,
    players: Dict[str, OfficialPlayerState] | None = None,
    game_state: Any = None,
    team_a_id: str | None = None,
) -> Tuple[OfficialEvent, Optional[OfficialEvent]]:
    """Issue a blue card to a player (Section 35).

    Moves the player to the back of the catch queue and temporarily adds them to
    discipline_blocked_ids.
    """
    # 1. Update player status
    is_live = False
    if players and player_id in players:
        player_state = players[player_id]
        is_live = player_state.is_live_for_hits()
        player_state.status = OfficialPlayerStatus.BLUE_CARD_QUEUE

    # 2. Append to queued_ids and discipline_blocked_ids
    if player_id in queue.queued_ids:
        queue.queued_ids.remove(player_id)
    queue.queued_ids.append(player_id)

    if player_id not in queue.discipline_blocked_ids:
        queue.discipline_blocked_ids.append(player_id)

    # 3. Decrement active count in game_state if they were active
    if is_live and game_state:
        if team_a_id and team_id == team_a_id:
            game_state.active_count_a = max(0, game_state.active_count_a - 1)
        else:
            game_state.active_count_b = max(0, game_state.active_count_b - 1)

    # 4. Check if issuing leaves the team with zero live players
    live_count = 0
    if players:
        live_count = sum(1 for p in players.values() if p.team_id == team_id and p.is_live_for_hits())
    elif game_state and team_a_id:
        live_count = game_state.active_count_a if team_id == team_a_id else game_state.active_count_b
    else:
        # default fallback: if we don't have players, we can't reliably check
        live_count = 1

    # 5. Record blue card
    prior_warnings = [
        w for w in state.warnings_by_player.get(player_id, [])
        if w.offense == offense
    ]
    prior_warning_count = len(prior_warnings)

    blue_record = BlueCardRecord(
        player_id=player_id,
        team_id=team_id,
        offense=offense,
        match_id=match_id,
        prior_warning_count=prior_warning_count,
    )
    if player_id not in state.blue_cards_by_player:
        state.blue_cards_by_player[player_id] = []
    state.blue_cards_by_player[player_id].append(blue_record)

    blue_card_event = OfficialEvent(
        event_id=f"blue-{player_id}-{offense.replace(' ', '_')}-{len(state.blue_cards_by_player[player_id])}",
        kind=OfficialEventKind.DISCIPLINE,
        match_id=match_id,
        game_id=game_id,
        rule_refs=(RuleReference("35"),),
        player_ids=(player_id,),
        team_ids=(team_id,),
        replay_summary=f"Blue Card issued to {player_id} (Team {team_id}) for {offense}.",
        payload={"kind": "blue_card", "offense": offense},
    )

    # 6. Yellow card placeholder check
    same_offense_blue_cards = [
        bc for bc in state.blue_cards_by_player[player_id]
        if bc.offense == offense
    ]

    second_event = None
    if len(same_offense_blue_cards) == 2:
        state.yellow_card_placeholder_emitted.add((player_id, offense))
        second_event = OfficialEvent(
            event_id=f"yellow-placeholder-{player_id}-{offense.replace(' ', '_')}",
            kind=OfficialEventKind.DISCIPLINE,
            match_id=match_id,
            game_id=game_id,
            rule_refs=(RuleReference("35"),),
            player_ids=(player_id,),
            team_ids=(team_id,),
            replay_summary=f"Yellow card placeholder: second Blue Card for {player_id} for {offense}.",
            payload={"kind": "yellow_card_placeholder", "deferred": True, "offense": offense},
        )

    # 7. Forfeit check takes precedence or is returned as second_event if yellow_event is None
    if live_count == 0:
        forfeit_result = OfficialGameResult.FORFEIT_A
        if team_a_id and team_id != team_a_id:
            forfeit_result = OfficialGameResult.FORFEIT_B

        if game_state:
            game_state.result = forfeit_result

        forfeit_event = OfficialEvent(
            event_id=f"forfeit-{team_id}-{match_id}",
            kind=OfficialEventKind.DISCIPLINE,
            match_id=match_id,
            game_id=game_id,
            rule_refs=(RuleReference("35"),),
            team_ids=(team_id,),
            replay_summary=f"Team {team_id} forfeits due to having zero live players after disciplinary action.",
            payload={"kind": "game_forfeit", "forfeit_result": forfeit_result.value},
        )
        # If there's a forfeit, it dominates the second event spot because game is over.
        second_event = forfeit_event

    return blue_card_event, second_event


def clear_discipline_blocked(queue: CatchQueueState, player_id: str) -> None:
    """Remove a player from discipline_blocked_ids so they can be caught back in."""
    if player_id in queue.discipline_blocked_ids:
        queue.discipline_blocked_ids.remove(player_id)
