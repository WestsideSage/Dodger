"""Thin wrapper around V11's autonomous official engine to satisfy
``EngineDriver``. Does not rewrite the engine; just adapts the I/O.
"""

from __future__ import annotations

from typing import Dict

from .engine_driver import DriverMatchInput, DriverMatchOutput
from .official_engine import AutonomousGameResult, run_autonomous_game
from .rulesets import RulesetSelection


_DEFAULT_RULESET = "official_foam"


class OfficialDriver:
    tier_id: str = "official"

    def run(self, match_input: DriverMatchInput) -> DriverMatchOutput:
        ruleset_name: str = match_input.config.get("ruleset", _DEFAULT_RULESET)
        # RulesetSelection is a str-Enum; .to_profile() returns the
        # corresponding RulesetProfile. See src/dodgeball_sim/rulesets.py.
        profile = RulesetSelection(ruleset_name).to_profile()

        result: AutonomousGameResult = run_autonomous_game(
            profile=profile,
            match_id=match_input.match_id,
            team_a_id=match_input.team_a_id,
            team_b_id=match_input.team_b_id,
            starters_a=match_input.starters_a,
            starters_b=match_input.starters_b,
            player_lookup=match_input.player_lookup,
            policy_a=match_input.policy_a,
            policy_b=match_input.policy_b,
            seed=match_input.seed,
        )

        return DriverMatchOutput(
            events=result.events,
            winner_team_id=result.winner_team_id,
            final_active_a=result.final_active_a,
            final_active_b=result.final_active_b,
            moment_events=(),  # V11 does not emit moments; Plan A scope
            replay_state=result.replay_state,
        )


__all__ = ["OfficialDriver"]
