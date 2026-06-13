from __future__ import annotations

from dataclasses import dataclass, replace
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
    # V19 ceiling scarcity (owner philosophy 2026-06-10: "OVR should be a
    # reward and monument to the effort it took to build the roster").
    # Elite ceilings are trajectory-gated: STAR (floor 90) ~0.75/class —
    # very rare but findable if you scout hard; GENERATIONAL (floor 96, a
    # guaranteed future Hall of Famer arc) ~1 per 4 classes. IMPACT (floor
    # 82) is the scarce "High" tier; NORMAL promises nothing beyond the
    # prospect's own rolled ceiling. Pre-V19 rates (0.70/0.22/0.07/0.01)
    # put ~7.5 prospects/class at an effective 82+ ceiling and converged
    # the whole league to high-80s OVR once V18 made development deliver.
    trajectory_rates={
        "NORMAL": 0.86,
        "IMPACT": 0.10,
        "STAR": 0.03,
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
# The user's Signing Day offer = BASE + interest * WEIGHT. Re-measured after
# the V19 ceiling-scarcity tune moved the prospect pool
# (tools/contested_offer_probe.py, 60 seeds, 2026-06-10 post-scarcity run):
# rival max offers on the TOP prospect min 76.1 / median 87.0 / max 98.0,
# uncourted interest ~38-52. BASE re-tuned 90.0 -> 85.0 (V18 vet mix) ->
# 79.0 (V19 scarcity) to keep the V16 design targets: the uncourted star
# pick sits at the rival median (genuinely losable, ~half the time),
# contact+visit (~+32 interest) clearly ahead, and full courtship
# (interest 100 -> 97.0) near-safe.
CONTESTED_USER_OFFER_BASE = 79.0
CONTESTED_USER_OFFER_INTEREST_WEIGHT = 0.18
# D3 (owner-confirmed 2026-06-10, V18): AI clubs get the SAME Signing Day
# plays as the user — up to 3 prospect signings per offseason (the user
# picker's cap in offseason_service.recruit_offseason_payload) against the
# same 12-player ceiling (offseason_presentation.MAX_USER_ROSTER). Signing
# fewer is a board decision, not a rule. The V16 launch default (1 signing,
# ceiling 10) let the engaged user's recruiting volume snowball into a 41%
# title share once V18 made development deliver ceilings — measured in the
# V18 sprint plan's Task 2 section.
AI_OFFSEASON_SIGNINGS_PER_CLUB = 3
# AI clubs at or above this roster size sit out Signing Day offers entirely
# (the offseason trim-to-9 then frees slots, mirroring the user's 12-cap).
AI_OFFSEASON_MAX_ROSTER = 12


# --- V24 The Board (config layer) -------------------------------------------
# The pyramid world's recruiting class feeds all 28 clubs, not one 7-club
# division. tools/ai_board_coverage_probe.py measured the single 25-class fully
# consumed every offseason (25.0 signings) with the International Circuit
# starved (65% coverage); a wider class restocks the whole world. Legacy
# single-league saves keep the historical 25 (no witness churn). Probe-tuned.
PYRAMID_PROSPECT_CLASS_SIZE = 56


def scouting_config_for_world(pyramid: bool) -> "ScoutingBalanceConfig":
    """Scouting config sized for the world: the 28-club pyramid gets the wide
    class; legacy single-league keeps the historical 25-prospect class."""
    if pyramid:
        return replace(DEFAULT_SCOUTING_CONFIG, prospect_class_size=PYRAMID_PROSPECT_CLASS_SIZE)
    return DEFAULT_SCOUTING_CONFIG


# Higher-tier AI clubs chase upside so the Worlds feeders (Premier + the
# International Circuit, both tier 1) build toward a compounding user's level
# instead of treading water on ready-now depth; lower tiers favor ready-now.
# The weight multiplies (public ceiling band - AI_TIER_CEILING_BASELINE),
# clamped at zero so it rewards upside, never raw signing. Probe-tuned against
# the D1/INT OVR trajectory (tools/climb_resistance_probe.py).
AI_TIER_CEILING_BASELINE = 60.0
AI_TIER_CEILING_PREFERENCE: Dict[int, float] = {
    1: 0.55,  # Premier + Circuit: chase ceiling hard
    2: 0.30,  # Challenger: balanced
    3: 0.12,  # District: mostly ready-now
}

# V24 Phase 3 motivations: the user's Signing Day offer becomes
# BASE + interest*INTEREST_WEIGHT + fit*MOTIVATION_FIT_WEIGHT, where fit is the
# 0-1 blend of the club's grades in the motivations the prospect cares about. A
# dealbreaker veto floors the offer to CONTESTED_VETO_OFFER_FLOOR (he never
# verbals). Pyramid-only; legacy offers pass fit=0 -> the exact V16 formula.
# Probe-tuned against tools/contested_offer_probe.py.
MOTIVATION_FIT_WEIGHT = 18.0
CONTESTED_VETO_OFFER_FLOOR = 25.0

# V24 Phase 4 funnel: a focus-listed prospect at/above this interest (and with no
# dealbreaker veto) has effectively verballed — your strongest pre-Signing-Day
# commitment signal.
VERBAL_INTEREST_THRESHOLD = 80


# --- V22 Club Economy (config layer) ----------------------------------------
# Owner (2026-06-11): "add a budget component… a financial management aspect"
# (Teamfight Manager cited), deliberately light — one treasury number, annual
# staff payroll, league payouts by finish. USER club only; AI club finances
# stay abstracted. All amounts are integer THOUSANDS (displayed "$340k").
#
# Calibration (7-club league, default staff payroll ≈ 276k/season):
#   champion  340 + 140 = 480  → ~+200k surplus funds upgrades
#   mid-table 280        →  ~break-even on default staff
#   basement  220        →  ~-56k/season squeeze (pressure, no death spiral —
#                            hiring freezes while negative, payroll still owed)
@dataclass(frozen=True)
class EconomyConfig:
    # Treasury seeds.
    starting_budget_k: int = 600          # create-a-club wizard budget
    takeover_treasury_k: int = 150        # curated takeover careers
    # Season income: base + (total_clubs - rank) * step, plus ONE playoff
    # bonus for the furthest stage reached.
    base_payout_k: int = 220
    per_rank_step_k: int = 20
    champion_bonus_k: int = 140
    runner_up_bonus_k: int = 80
    semifinalist_bonus_k: int = 40
    # Staff salaries: quality-priced from the head's visible ratings.
    # salary = max(floor, round(0.75*primary + 0.25*secondary) - offset)
    salary_floor_k: int = 20
    salary_rating_offset_k: int = 25


DEFAULT_ECONOMY = EconomyConfig()


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
    "AI_TIER_CEILING_BASELINE",
    "AI_TIER_CEILING_PREFERENCE",
    "PYRAMID_PROSPECT_CLASS_SIZE",
    "scouting_config_for_world",
    "BalanceConfig",
    "CONTESTED_USER_OFFER_BASE",
    "CONTESTED_USER_OFFER_INTEREST_WEIGHT",
    "CONTESTED_VETO_OFFER_FLOOR",
    "MOTIVATION_FIT_WEIGHT",
    "DEFAULT_ECONOMY",
    "DifficultyProfile",
    "EconomyConfig",
    "ScoutingBalanceConfig",
    "CONFIG_REGISTRY",
    "DEFAULT_CONFIG",
    "DEFAULT_SCOUTING_CONFIG",
    "get_config",
]
