"""Tier 1 (Local Rec League) rule contract — encoded from brief §3.5.

This is config, not behavior. The rec driver consumes it; B/C consume
it indirectly via driver outputs. Higher tiers will add their own
``tier_N_rules.py`` modules in their respective sub-projects.
"""

from __future__ import annotations

from dataclasses import dataclass

from .stall_timer import STALL_CAP_SECONDS


@dataclass(frozen=True)
class TierRules:
    tier_id: str
    display_name: str
    team_size: int
    ball_count: int
    balls_per_side_at_rush: int
    headshot_thrower_out: bool
    refs_present: bool
    discipline_modeled: bool
    burden_modeled: bool
    no_blocking_mode_enabled: bool
    designated_retriever: bool
    stall_cap_seconds: float
    time_cap_seconds: int
    match_format: str  # "single_game" | "best_of_3" | ...
    substitutions_allowed: bool


TIER_1_RULES = TierRules(
    tier_id="local_rec_league",
    display_name="Local Rec League",
    team_size=6,
    ball_count=6,
    balls_per_side_at_rush=3,
    headshot_thrower_out=True,
    refs_present=False,
    discipline_modeled=False,
    burden_modeled=False,
    no_blocking_mode_enabled=False,
    designated_retriever=False,
    stall_cap_seconds=STALL_CAP_SECONDS,
    time_cap_seconds=300,
    match_format="single_game",
    substitutions_allowed=False,
)


__all__ = ["TierRules", "TIER_1_RULES"]
