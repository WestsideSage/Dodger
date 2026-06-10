"""Adapter that routes a generic ``MatchSetup`` into the Tier 1 rec driver.

The franchise/web pipeline persists and replays ``MatchResult`` objects, while
Plan A's driver architecture produces ``DriverMatchOutput``. This adapter keeps
the current persistence contract intact and stores the emitted moment events in
the terminal ``match_end`` context so replay/aftermath consumers can recover
them without a schema migration.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Iterable

from .engine import MatchResult
from .engine_driver import DriverMatchInput, DriverMatchOutput
from .events import MatchEvent
from .models import MatchSetup
from .moment_events import MomentEvent
from .rec_engine import RecTier1Driver


class RecEngineAdapter:
    tier_id: str = "local_rec_league"

    def run(self, setup: MatchSetup, *, seed: int, match_id: str | None = None) -> DriverMatchOutput:
        team_a = setup.team_a
        team_b = setup.team_b
        starters_a = tuple(player.id for player in team_a.players)
        starters_b = tuple(player.id for player in team_b.players)
        player_lookup = {player.id: player for player in team_a.players} | {player.id: player for player in team_b.players}
        driver_input = DriverMatchInput(
            match_id=match_id or f"{team_a.id}-vs-{team_b.id}",
            team_a_id=team_a.id,
            team_b_id=team_b.id,
            starters_a=starters_a,
            starters_b=starters_b,
            player_lookup=player_lookup,
            policy_a=team_a.coach_policy,
            policy_b=team_b.coach_policy,
            seed=seed,
            config={"config_version": setup.config_version},
        )
        return RecTier1Driver().run(driver_input)

    def run_generic(
        self,
        setup: MatchSetup,
        *,
        seed: int,
        match_id: str | None = None,
        difficulty: str = "pro",
    ) -> MatchResult:
        output = self.run(setup, seed=seed, match_id=match_id)
        events = _translate_events(
            setup=setup,
            output=output,
            seed=seed,
            difficulty=difficulty,
        )
        return MatchResult(
            events=tuple(events),
            winner_team_id=output.winner_team_id,
            box_score=_derive_box_score(
                setup=setup,
                events=events,
                winner_team_id=output.winner_team_id,
            ),
            final_tick=events[-1].tick,
            seed=seed,
            config_version=setup.config_version,
        )


def _translate_events(
    *,
    setup: MatchSetup,
    output: DriverMatchOutput,
    seed: int,
    difficulty: str,
) -> list[MatchEvent]:
    team_a = setup.team_a
    team_b = setup.team_b
    events: list[MatchEvent] = [
        MatchEvent(
            event_id=0,
            tick=0,
            seed=seed,
            event_type="match_start",
            phase="init",
            actors={"team_a": team_a.id, "team_b": team_b.id},
            context={
                "config_version": setup.config_version,
                "difficulty": difficulty,
                "meta_patch": None,
                "team_policies": {
                    team_a.id: team_a.coach_policy.as_dict(),
                    team_b.id: team_b.coach_policy.as_dict(),
                },
            },
            probabilities={},
            rolls={},
            outcome={"message": "Tier 1 match initialized"},
            state_diff={},
        )
    ]

    next_event_id = 1
    for raw in output.events:
        raw_type = str(raw.get("type", "event"))
        if raw_type == "stall_reset":
            events.append(
                MatchEvent(
                    event_id=next_event_id,
                    tick=int(raw.get("tick", 0)),
                    seed=seed,
                    event_type="stall_reset",
                    phase="live",
                    actors={"team": raw.get("from")},
                    context={"reason": "stall reset"},
                    probabilities={},
                    rolls={},
                    outcome={"message": "Balls reset after a stall."},
                    state_diff={},
                )
            )
            next_event_id += 1
            continue
        translated = _translate_throw_event(raw=raw, event_id=next_event_id, seed=seed, difficulty=difficulty)
        events.append(translated)
        next_event_id += 1

    end_tick = events[-1].tick if events else 0
    events.append(
        MatchEvent(
            event_id=next_event_id,
            tick=end_tick,
            seed=seed,
            event_type="match_end",
            phase="complete",
            actors={"winner": output.winner_team_id},
            context={
                "reason": "elimination" if output.winner_team_id is not None else "time_cap",
                "moment_events": [_moment_to_dict(moment) for moment in output.moment_events],
            },
            probabilities={},
            rolls={},
            outcome={"winner": output.winner_team_id},
            state_diff={},
        )
    )
    return events


def _translate_throw_event(*, raw: Dict[str, Any], event_id: int, seed: int, difficulty: str) -> MatchEvent:
    resolution_map = {
        "miss": "miss",
        "hit": "hit",
        "dodge": "dodged",
        "block": "dodged",
        "catch_clean": "catch",
        "catch_return": "catch",
        "catch_failed_hit": "failed_catch",
        "headshot_thrower_out": "miss",
    }
    target = raw.get("target")
    target_team = raw.get("target_team")
    if raw.get("type") == "headshot_thrower_out":
        target = None
        target_team = None
    state_diff = dict(raw.get("state_diff") or {})
    # A catch_return resurrects a queued teammate of the catcher (the target's
    # team). Persist that fact: without it the replay's live survivor state
    # keeps the returned player marked eliminated for the rest of the match.
    returning_player_id = raw.get("returning_player_id")
    if raw.get("type") == "catch_return" and returning_player_id:
        state_diff["player_return"] = {
            "team": target_team,
            "player_id": returning_player_id,
        }
    return MatchEvent(
        event_id=event_id,
        tick=int(raw.get("tick", 0)),
        seed=seed,
        event_type="throw",
        phase="live",
        actors={
            "offense_team": raw.get("thrower_team"),
            "defense_team": target_team,
            "thrower": raw.get("thrower"),
            "target": target,
        },
        context={
            "tick": int(raw.get("tick", 0)),
            "thrower_selection": {},
            "target_selection": dict(raw.get("target_selection") or {}),
            "difficulty": difficulty,
            "policy_snapshot": dict(raw.get("policy_snapshot") or {}),
            "chemistry_delta": 0.0,
            "meta_patch": None,
            "rush_context": dict(raw.get("rush_context") or {}),
            "sync_context": dict(raw.get("sync_context") or {}),
            "calc": {},
            "fatigue": dict(raw.get("fatigue") or {}),
            "pressure_active": False,
            "catch_decision": raw.get("catch_decision"),
        },
        probabilities={},
        rolls={},
        outcome={
            "resolution": resolution_map.get(str(raw.get("type")), "miss"),
        },
        state_diff=state_diff,
    )


def _derive_box_score(
    *,
    setup: MatchSetup,
    events: Iterable[MatchEvent],
    winner_team_id: str | None,
) -> Dict[str, Any]:
    event_list = list(events)
    box = {"teams": {}, "winner": winner_team_id}
    # Final on-court status from the full diff stream: an elimination marks a
    # player out, a catch-return brings them BACK. Treating "was ever out" as
    # "ended the match out" undercounted survivors on every match with a
    # return — and, because franchise.simulate_match derives the recorded
    # winner from these survivor totals, it falsified recorded outcomes (a
    # 2-0 elimination win recorded as a 0-0 draw). The event log is canon.
    final_out_ids: set[str] = set()
    for event in event_list:
        state_diff = event.state_diff or {}
        player_out = state_diff.get("player_out") or {}
        if player_out.get("player_id"):
            final_out_ids.add(str(player_out["player_id"]))
        player_return = state_diff.get("player_return") or {}
        if player_return.get("player_id"):
            final_out_ids.discard(str(player_return["player_id"]))
    for team in (setup.team_a, setup.team_b):
        team_players = {}
        team_events = [event for event in event_list if event.event_type == "throw"]
        outs_recorded = 0
        hits = 0
        catches = 0
        dodges = 0
        for player in team.players:
            throws = 0
            player_hits = 0
            player_catches = 0
            player_dodges = 0
            caught = 0
            for event in team_events:
                actors = event.actors
                resolution = str(event.outcome.get("resolution", "miss"))
                if actors.get("thrower") == player.id:
                    throws += 1
                    if resolution in {"hit", "failed_catch"}:
                        player_hits += 1
                    if resolution == "catch":
                        caught += 1
                if actors.get("target") == player.id:
                    if resolution == "catch":
                        player_catches += 1
                    elif resolution == "dodged":
                        player_dodges += 1
            team_players[player.id] = {
                "name": player.name,
                "throws": throws,
                "hits": player_hits,
                "catches": player_catches,
                "dodges": player_dodges,
                "caught": caught,
                "is_out": player.id in final_out_ids,
            }
            outs_recorded += player_hits
            hits += player_hits
            catches += player_catches
            dodges += player_dodges
        living = len([player for player in team.players if player.id not in final_out_ids])
        box["teams"][team.id] = {
            "name": team.name,
            "totals": {
                "outs_recorded": outs_recorded,
                "hits": hits,
                "catches": catches,
                "dodges": dodges,
                "living": living,
            },
            "players": team_players,
        }
    return box


def _moment_to_dict(moment: MomentEvent) -> dict[str, Any]:
    payload = asdict(moment)
    payload["kind"] = moment.kind.value
    return payload


__all__ = ["RecEngineAdapter"]
