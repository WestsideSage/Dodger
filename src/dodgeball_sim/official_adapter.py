"""Adapter that routes a generic ``MatchSetup`` into the official engine.

Used by the use-case layer to simulate a single match under official rules
when the career's :class:`~dodgeball_sim.rulesets.RulesetSelection` is set.
Produces a generic-shaped :class:`~dodgeball_sim.engine.MatchResult` derived
from the official event stream via :mod:`official_translator`, so downstream
stats and persistence don't need to know which engine produced the match.
"""

from __future__ import annotations

from dataclasses import dataclass, replace, asdict
from typing import Any, Dict, Tuple

from .engine import MatchResult
from .models import MatchSetup
from .moment_events import MomentEvent
from .official_engine import run_autonomous_match
from .official_events import OfficialEvent
from .official_persistence import replay_state_to_dict
from .official_stats import derive_box_score
from .official_translator import collect_official_metadata, translate_events
from .replay_contracts import OfficialReplayState
from .rulesets import RulesetSelection
from .season_emphasis import SeasonEmphasis


@dataclass(frozen=True)
class OfficialMatchResult:
    """Raw official outcome (event stream + metadata).

    The :meth:`OfficialEngineAdapter.run_generic` method returns the
    generic-compatible :class:`MatchResult` for pipeline integration;
    callers wanting the raw event stream can use :meth:`run` instead.
    """

    winner_team_id: str | None
    box_score: Dict[str, Any]
    events: Tuple[OfficialEvent, ...]
    ticks: int
    ruleset_selection: str
    official_metadata: Dict[str, Any]
    replay_state: OfficialReplayState
    moment_events: Tuple[MomentEvent, ...] = ()


def _moment_to_dict(moment: MomentEvent) -> Dict[str, Any]:
    payload = asdict(moment)
    payload["kind"] = moment.kind.value
    return payload


class OfficialEngineAdapter:
    """Drives the official engine end to end and returns a generic-shaped
    :class:`MatchResult` so the franchise pipeline keeps its contracts."""

    def __init__(self, selection: RulesetSelection) -> None:
        if not selection.is_official():
            raise ValueError("OfficialEngineAdapter requires an official ruleset")
        self.selection = selection
        self.profile = selection.to_profile()

    def _run_raw(
        self,
        setup: MatchSetup,
        *,
        seed: int,
        match_id: str | None,
        prep_a: dict | None = None,
        prep_b: dict | None = None,
        season_emphasis: SeasonEmphasis | None = None,
    ) -> OfficialMatchResult:
        # Persistence (game_loop.persist_match_record) and aftermath builders
        # assume team_a is the home club; the team_a_id is round-tripped through
        # official_metadata so downstream code can verify. Keep that invariant
        # explicit here so any future caller that flips the order trips fast
        # instead of silently inverting scoreboards.
        team_a = setup.team_a
        team_b = setup.team_b
        starters_a = tuple(p.id for p in team_a.players[: self.profile.roster_rule.starters])
        starters_b = tuple(p.id for p in team_b.players[: self.profile.roster_rule.starters])
        lookup = {p.id: p for p in team_a.players} | {p.id: p for p in team_b.players}
        team_map = (
            {p.id: team_a.id for p in team_a.players}
            | {p.id: team_b.id for p in team_b.players}
        )
        name_map = (
            {p.id: p.name for p in team_a.players}
            | {p.id: p.name for p in team_b.players}
        )
        match_result = run_autonomous_match(
            profile=self.profile,
            match_id=match_id or f"{team_a.id}-vs-{team_b.id}",
            team_a_id=team_a.id, team_b_id=team_b.id,
            starters_a=starters_a, starters_b=starters_b,
            player_lookup=lookup,
            policy_a=team_a.coach_policy, policy_b=team_b.coach_policy,
            seed=seed,
            prep_a=prep_a, prep_b=prep_b,
            season_emphasis=season_emphasis or SeasonEmphasis(),
        )
        box = derive_box_score(
            match_result.events,
            team_a_id=team_a.id, team_b_id=team_b.id,
            team_a_name=team_a.name, team_b_name=team_b.name,
            player_team_map=team_map, player_name_map=name_map,
            starters_a=starters_a, starters_b=starters_b,
            winner_team_id=match_result.winner_team_id,
        )
        # V20 intent context: persist BOTH clubs' locked match policies (the
        # weekly plan's tactics, already applied to the club by
        # _apply_command_plan_to_match) so the replay can show the decision
        # frame the match was actually played under. Post-hoc disclosure of
        # the player's own locked decisions plus the opponent's now-historical
        # plan — by replay time the match is tape, so no fog is broken.
        metadata = asdict(match_result.official_match_score)
        metadata["team_policies"] = {
            team_a.id: dict(team_a.coach_policy.as_dict()),
            team_b.id: dict(team_b.coach_policy.as_dict()),
        }
        return OfficialMatchResult(
            winner_team_id=match_result.winner_team_id,
            box_score=box, events=match_result.events,
            ticks=match_result.ticks,
            ruleset_selection=self.selection.value,
            official_metadata=metadata,
            replay_state=match_result.replay_state,
            moment_events=match_result.moment_events,
        )

    def run(
        self,
        setup: MatchSetup,
        *,
        seed: int,
        match_id: str | None = None,
        season_emphasis: SeasonEmphasis | None = None,
    ) -> OfficialMatchResult:
        return self._run_raw(setup, seed=seed, match_id=match_id, season_emphasis=season_emphasis)

    def run_generic(
        self,
        setup: MatchSetup,
        *,
        seed: int,
        match_id: str | None = None,
        prep_a: dict | None = None,
        prep_b: dict | None = None,
        season_emphasis: SeasonEmphasis | None = None,
    ) -> MatchResult:
        """Run the official engine and return a generic-shaped MatchResult.

        ``prep_a``/``prep_b`` are the V19b staff-focus match preps (tactics
        read sharpening / conditioning stamina relief), derived from each
        club's weekly plan by the caller. ``season_emphasis`` is the V28
        officiating point of emphasis for the season being played (default
        ``SeasonEmphasis()`` ⇒ byte-identical).
        """

        raw = self._run_raw(
            setup, seed=seed, match_id=match_id, prep_a=prep_a, prep_b=prep_b,
            season_emphasis=season_emphasis,
        )
        starters_a = tuple(p.id for p in setup.team_a.players[: self.profile.roster_rule.starters])
        starters_b = tuple(p.id for p in setup.team_b.players[: self.profile.roster_rule.starters])
        match_events = translate_events(
            raw.events, seed=seed,
            team_a_id=setup.team_a.id, team_b_id=setup.team_b.id,
            starters_a=starters_a, starters_b=starters_b,
            winner_team_id=raw.winner_team_id,
        )
        if match_events:
            official_state = replay_state_to_dict(raw.replay_state, include_events=False)
            match_events[0] = replace(
                match_events[0],
                context={**match_events[0].context, "official_state": official_state},
            )
            # Phase 4b: carry the engine's recognition moments on the match_end
            # event context (same shape the rec adapter uses) so the Tier-1
            # moment beats, tier1 voice, and V13 highlights keep working once
            # new careers default to the foam-official engine. Without this the
            # set-scoring default would silently strip the moment layer.
            moment_payload = [_moment_to_dict(moment) for moment in raw.moment_events]
            for index in range(len(match_events) - 1, -1, -1):
                if match_events[index].event_type == "match_end":
                    match_events[index] = replace(
                        match_events[index],
                        context={**match_events[index].context, "moment_events": moment_payload},
                    )
                    break
        return MatchResult(
            events=tuple(match_events),
            winner_team_id=raw.winner_team_id,
            box_score=raw.box_score,
            final_tick=raw.ticks,
            seed=seed,
            config_version=f"official:{self.selection.value}",
            official_metadata=raw.official_metadata,
        )
