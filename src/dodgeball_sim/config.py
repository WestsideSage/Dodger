from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class DifficultyProfile:
    """Describes how AI decision noise behaves at a given difficulty."""

    name: str
    decision_noise: float  # 0=no noise, 1=fully random
    scouting_blur: float  # reserved for future scouting systems


@dataclass(frozen=True)
class BalanceConfig:
    version: str
    accuracy_scale: float
    catch_scale: float
    power_to_catch_scale: float
    fatigue_hit_modifier: float
    fatigue_dodge_modifier: float
    fatigue_catch_modifier: float
    chemistry_influence: float
    tempo_tick_bonus: int
    max_ticks: int
    max_events: int
    base_seed_offset: int
    rush_accuracy_modifier_max: float
    rush_fatigue_cost_max: float
    difficulty_profiles: Dict[str, DifficultyProfile]


@dataclass(frozen=True)
class ScoutingBalanceConfig:
    """Tunable balance parameters for the V2-A scouting model."""

    tier_thresholds: Dict[str, int]
    weekly_scout_point_base: int
    archetype_affinity_multiplier: float
    archetype_weakness_multiplier: float
    archetype_neutral_multiplier: float
    trait_sense_multipliers: Dict[str, float]
    jitter_min: float
    jitter_max: float
    trajectory_rates: Dict[str, float]
    public_archetype_mislabel_rate: float
    public_baseline_band_half_width: int
    prospect_class_size: int
    hidden_gem_ovr_floor: int


_DEFAULT_DIFFICULTIES: Dict[str, DifficultyProfile] = {
    "rookie": DifficultyProfile(name="rookie", decision_noise=0.4, scouting_blur=0.2),
    "pro": DifficultyProfile(name="pro", decision_noise=0.15, scouting_blur=0.05),
    "elite": DifficultyProfile(name="elite", decision_noise=0.05, scouting_blur=0.0),
}

CONFIG_REGISTRY: Dict[str, BalanceConfig] = {
    "phase1.v1": BalanceConfig(
        version="phase1.v1",
        accuracy_scale=12.0,
        catch_scale=11.0,
        power_to_catch_scale=0.75,
        fatigue_hit_modifier=0.1,
        fatigue_dodge_modifier=0.1,
        fatigue_catch_modifier=0.07,
        chemistry_influence=0.02,
        tempo_tick_bonus=2,
        max_ticks=240,
        max_events=800,
        base_seed_offset=17,
        rush_accuracy_modifier_max=0.15,
        rush_fatigue_cost_max=0.20,
        difficulty_profiles=_DEFAULT_DIFFICULTIES,
    )
}

DEFAULT_CONFIG = CONFIG_REGISTRY["phase1.v1"]

DEFAULT_SCOUTING_CONFIG = ScoutingBalanceConfig(
    tier_thresholds={"GLIMPSED": 10, "KNOWN": 35, "VERIFIED": 70},
    weekly_scout_point_base=5,
    archetype_affinity_multiplier=1.20,
    archetype_weakness_multiplier=0.80,
    archetype_neutral_multiplier=1.00,
    trait_sense_multipliers={"LOW": 0.70, "MEDIUM": 1.00, "HIGH": 1.30},
    jitter_min=0.90,
    jitter_max=1.10,
    trajectory_rates={
        "NORMAL": 0.70,
        "IMPACT": 0.22,
        "STAR": 0.07,
        "GENERATIONAL": 0.01,
    },
    public_archetype_mislabel_rate=0.15,
    public_baseline_band_half_width=25,
    prospect_class_size=25,
    hidden_gem_ovr_floor=8,
)


def get_config(version: str | None = None) -> BalanceConfig:
    """Return the requested config, defaulting to the latest entry."""

    if version is None:
        return DEFAULT_CONFIG
    if version not in CONFIG_REGISTRY:
        raise KeyError(f"Unknown config version: {version}")
    return CONFIG_REGISTRY[version]


__all__ = [
    "BalanceConfig",
    "DifficultyProfile",
    "ScoutingBalanceConfig",
    "CONFIG_REGISTRY",
    "DEFAULT_CONFIG",
    "DEFAULT_SCOUTING_CONFIG",
    "get_config",
]
