from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .engine import MatchResult
from .models import CoachPolicy
from .moment_events import (
    Comeback,
    DramaticCatch,
    FloodThrow,
    GassedCollapse,
    LateGameEscape,
    MomentEvent,
    MomentKind,
    OneVOneFinale,
)


@dataclass(frozen=True)
class AftermathContext:
    match_result: MatchResult
    moment_events: tuple[MomentEvent, ...]
    policy_team: CoachPolicy
    policy_opponent: CoachPolicy
    tier: int
    # The player team's club id. When supplied, postgame copy is rendered
    # from the player's perspective (their survivors first, win/loss
    # branched against this id). When None, the legacy behaviour is used:
    # the first key in box_score["teams"] is treated as "mine" — fine for
    # writer-side tests that don't care about player perspective.
    player_club_id: str | None = None
    # Selected coach Intent at match start. When supplied (alongside
    # ``player_club_id``) the lazy ``narrative_beats`` property derives
    # ``selected_plan_label`` from this intent.
    selected_intent: str | None = None

    @property
    def narrative_beats(self):
        """Lazily derive ``NarrativeBeats`` from the resolved MatchResult.

        Every aftermath copy generator (headline, body, verdict, frontend
        gates) consults this struct instead of recomputing comeback /
        deficit / plan-label state from pre-resolution inputs. See
        ``replay_proof.derive_narrative_beats`` for the contract.
        """
        # Imported lazily to avoid a circular import with replay_proof,
        # which itself pulls voice_verdict for the approach-label helper.
        from .replay_proof import derive_narrative_beats

        return derive_narrative_beats(
            self.match_result,
            player_club_id=self.player_club_id,
            moment_events=self.moment_events,
            selected_intent=self.selected_intent,
        )

    def player_name(self, player_id: str | None) -> str:
        if not player_id:
            return "Unknown player"
        for team in self.match_result.box_score.get("teams", {}).values():
            players = team.get("players", {})
            if player_id in players:
                return str(players[player_id].get("name", player_id))
        return player_id

    def team_name(self, team_id: str | None) -> str:
        if not team_id:
            return "Unknown team"
        team = self.match_result.box_score.get("teams", {}).get(team_id)
        if isinstance(team, Mapping):
            return str(team.get("name", team_id))
        return team_id

    def survivors_for(self, team_id: str | None) -> int | None:
        if not team_id:
            return None
        team = self.match_result.box_score.get("teams", {}).get(team_id)
        if not isinstance(team, Mapping):
            return None
        totals = team.get("totals", {})
        if not isinstance(totals, Mapping):
            return None
        living = totals.get("living")
        return int(living) if living is not None else None


def moment_events_from_payload(payload: Any) -> tuple[MomentEvent, ...]:
    if not isinstance(payload, list):
        return ()
    parsed: list[MomentEvent] = []
    for item in payload:
        if not isinstance(item, Mapping):
            continue
        kind = item.get("kind")
        clean_item = {key: value for key, value in item.items() if key != "kind"}
        if kind == MomentKind.DRAMATIC_CATCH.value:
            parsed.append(DramaticCatch(**clean_item))
        elif kind == MomentKind.LATE_GAME_ESCAPE.value:
            parsed.append(LateGameEscape(**clean_item))
        elif kind == MomentKind.ONE_V_ONE_FINALE.value:
            parsed.append(OneVOneFinale(**clean_item))
        elif kind == MomentKind.GASSED_COLLAPSE.value:
            parsed.append(GassedCollapse(**clean_item))
        elif kind == MomentKind.FLOOD_THROW.value:
            parsed.append(FloodThrow(**clean_item))
        elif kind == MomentKind.COMEBACK.value:
            parsed.append(Comeback(**clean_item))
    return tuple(parsed)


__all__ = ["AftermathContext", "moment_events_from_payload"]
