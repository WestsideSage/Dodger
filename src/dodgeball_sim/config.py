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
    max_staff_development_modifier: float
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
    # Max distance between the public band's center and the hidden true
    # overall. A symmetric band (jitter 0) would put the truth exactly at the
    # midpoint, making the fog of war invertible (V16 Task 1).
    public_band_center_jitter: float
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
        max_staff_development_modifier=0.15,
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
    public_band_center_jitter=8.0,
    prospect_class_size=25,
    hidden_gem_ovr_floor=8,
)


# --- V16 Contested Offseason (config layer; engine rule: balance constants
# do not live in engine logic) ------------------------------------------------
# The user's Signing Day offer = BASE + interest * WEIGHT. Measured rival
# offers on the TOP prospect (tools/contested_offer_probe.py, 60 seeds):
# min 84.9 / median 99.0 / max 111.7, with uncourted interest ~38-52. These
# values put the uncourted star pick right at the rival median (genuinely
# losable, ~half the time), contact+visit (~+32 interest) clearly ahead
# (~15% risk), and full courtship (interest 100 -> 108.0) near-safe.
CONTESTED_USER_OFFER_BASE = 90.0
CONTESTED_USER_OFFER_INTEREST_WEIGHT = 0.18
# D3: at most this many prospect signings per AI club per offseason.
AI_OFFSEASON_SIGNINGS_PER_CLUB = 1
# AI clubs at or above this roster size sit out Signing Day offers entirely
# (the next offseason's trim-to-9 still creates churn for clubs below it).
AI_OFFSEASON_MAX_ROSTER = 10


def get_config(version: str | None = None) -> BalanceConfig:
    """Return the requested config, defaulting to the latest entry."""

    if version is None:
        return DEFAULT_CONFIG
    if version not in CONFIG_REGISTRY:
        raise KeyError(f"Unknown config version: {version}")
    return CONFIG_REGISTRY[version]


__all__ = [
    "AI_OFFSEASON_MAX_ROSTER",
    "AI_OFFSEASON_SIGNINGS_PER_CLUB",
    "BalanceConfig",
    "CONTESTED_USER_OFFER_BASE",
    "CONTESTED_USER_OFFER_INTEREST_WEIGHT",
    "DifficultyProfile",
    "ScoutingBalanceConfig",
    "CONFIG_REGISTRY",
    "DEFAULT_CONFIG",
    "DEFAULT_SCOUTING_CONFIG",
    "get_config",
]
