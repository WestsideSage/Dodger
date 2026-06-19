from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, Mapping


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

# V24 Phase 5: visible rival suitors + the in-season interest race. Each focused
# prospect surfaces up to RIVAL_SUITORS_SHOWN named AI suitors; rival pursuit is
# a deterministic talent+tier proxy with a per-(prospect, club) jitter of this
# span (prospect_market.derive_club_pursuit). Leading the race compounds: while
# the user's interest leads, courtship lands a bonus of PER_WEEK × weeks-left,
# capped at MAX, so an early lead beats a late entry at equal effort. Sim-design
# with probe evidence (tools/rival_momentum_probe.py), never real-world fidelity.
RIVAL_SUITORS_SHOWN = 3
# Rival pursuit is on the same 0-100 scale as the user's courtship interest, so
# the race is winnable: a rival's pursuit is a DAMPENED read of the talent it can
# see (weight < 1) plus its tier's upside appetite. Without the damping, every
# good prospect's rivals would sit near 100 and no amount of courtship could ever
# lead — the race would be theater. Probe-tuned (tools/rival_momentum_probe.py).
RIVAL_PURSUIT_TALENT_WEIGHT = 0.65
RIVAL_PURSUIT_JITTER_SPAN = 16.0
RIVAL_MOMENTUM_PER_WEEK = 0.8
RIVAL_MOMENTUM_MAX = 12

# V24 Phase 6: the money-gated Scouting Network. A per-club LEVEL (L1/L2/L3) gates
# which prospects render a full sheet vs a bare name. L1 (your district +
# neighbors) is the free founding baseline; upgrades are one-time treasury sinks,
# compressed by the scouting head (staff_effects.scouting_network_cost_compression).
# AI clubs carry a level by division tier (+ a deterministic blind-spot jitter),
# so gems fall through the cracks. Costs are integer $k; probe-tuned vs V22
# payouts (the table's L1=60 is the free founding baseline, not a purchase).
NETWORK_UPGRADE_COSTS: Dict[int, int] = {2: 140, 3: 280}
NETWORK_DEFAULT_LEVEL = 1
NETWORK_MAX_LEVEL = 3
# AI network level by division tier; a deterministic per-(season, club) jitter
# can drop a club one level (a blind spot) so unrecruited gems happen organically.
AI_NETWORK_LEVEL_BY_TIER: Dict[int, int] = {1: 3, 2: 2, 3: 1}
AI_NETWORK_BLINDSPOT_RATE = 0.25


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


# V25 The Market — player contract knobs. Proposed sim-design; tuned in Phase 7
# against the squeeze-never-spiral invariant and the poach/retention probe.
# Amounts are integer thousands; never claimed as real-world fidelity.
@dataclass(frozen=True)
class ContractConfig:
    entry_term: int = 3
    # STANDARD entry deals: tier-standardized, ABILITY-BLIND (money enters at the
    # second contract). Keyed by tier (1=Premier, 2=Challenger, 3=District /
    # Circuit default). Phase 7: tuned so a full squad's wages stay a MODERATE
    # fraction of the tier's prize money (squeeze, never tyranny).
    entry_salary_by_tier: Mapping[int, int] = field(
        default_factory=lambda: {1: 14, 2: 9, 3: 5}
    )
    # Second contracts price ability: floor + per_ovr*(OVR - pivot), x tier mult.
    # Phase 7: a competitive squad's wage bill lands at ~25-40% of tier income.
    second_base_k: int = 6
    second_per_ovr_k: float = 0.35
    second_ovr_pivot: int = 60
    second_tier_multiplier: Mapping[int, float] = field(
        default_factory=lambda: {1: 1.4, 2: 1.2, 3: 1.0}
    )
    second_term_default: int = 3
    # AI wage BUDGET caps (no balance tracked) — gate poach/re-sign aggression.
    # Tuned to bite once a club's squad develops into its cap, not on raw rookies.
    wage_budget_by_tier: Mapping[int, int] = field(
        default_factory=lambda: {1: 230, 2: 140, 3: 75}
    )
    # Buyout fee / AI asking price = factor * salary * term_remaining.
    buyout_fee_factor: float = 2.0
    # Dev-compensation credit when a homegrown player is poached (fraction of fee).
    dev_compensation_fraction: float = 0.5
    # Retention (re-sign): how motivation fit bends a player's salary ask. A
    # perfect-fit player re-signs for ``resign_fit_discount`` below his ask; a
    # zero-fit player demands ``resign_low_fit_premium`` above it.
    resign_fit_discount: float = 0.4
    resign_low_fit_premium: float = 0.5
    resign_term_default: int = 3
    # Poaching: a perfect-fit player will stay for up to this many $k below a
    # rival's offer (loyalty buffer); a zero-fit player leaves for any premium.
    poach_loyalty_money_k: int = 30
    # A poacher offers est-wage scaled up to (1 + interest/100) — money is the
    # uphill pull; a club with no wage headroom for the est wage sits out.
    poach_offer_interest_scale: float = 1.0
    # Buyouts: a higher-tier club only tables an offer for a contracted player
    # whose pursuit interest crosses this bar (so not every squad player draws a
    # bid). Roster floor a buyout may never breach.
    buyout_interest_threshold: int = 70
    min_roster_after_transfer: int = 6
    # AI re-signs get this term; a departing player at/above this OVR is news.
    transfer_news_ovr_threshold: int = 80


DEFAULT_CONTRACTS = ContractConfig()


# V26 The Crowd — facility build costs (treasury, permanent one-time buy). The
# web catalog offers only facilities with real web effects; the legacy CLI
# information/tactical facilities keep their prestige_cost in facilities.py.
@dataclass(frozen=True)
class FacilityConfig:
    treasury_cost_k: Mapping[str, int] = field(default_factory=lambda: {
        "training_hall": 160,
        "stadium": 200,
        "merch_center": 140,
        "velocity_lab": 120,
        "reaction_wall": 120,
        "recovery_suite": 90,
    })
    # The facilities offered in the web Dynasty Office (those with real web
    # effects). Film Room / Analytics / Chemistry Lounge stay CLI-legacy until
    # their web effects are wired.
    web_catalog: tuple = (
        "velocity_lab", "reaction_wall", "recovery_suite",
        "training_hall", "stadium", "merch_center",
    )
    # Training Hall: extra offseason practice-growth OVR for the user club (the
    # V19b practice-credit channel, headroom-capped). The meaningful, visible
    # development effect — the labs add small per-stat passive edges.
    training_hall_dev_ovr: float = 2.0


DEFAULT_FACILITIES = FacilityConfig()


# V26 The Crowd — fan-ledger gains by event + fan-income rates. Proposed
# sim-design tuned in Phase 7; income kept a meaningful margin, never prize
# money's rival. All defaults safe for legacy (no fans → no income).
@dataclass(frozen=True)
class FanConfig:
    # Club fans by event.
    fans_per_win: int = 60
    fans_promotion: int = 1200
    fans_title: int = 1500
    fans_cup: int = 600
    fans_worlds_final: int = 2000
    fans_worlds_win: int = 4000
    # Player followers by event (Phase 3).
    followers_mvp: int = 800
    followers_record: int = 600
    followers_milestone: int = 400
    followers_district_tie: int = 150
    # Fan income (Phase 4): matchday per fan drawn, merch per 1k fans; stadium
    # capacity = base x (1 + owned-stadium) x tier.
    matchday_per_fan_k: float = 0.012
    merch_per_1k_fans_k: float = 0.9
    stadium_base_capacity: int = 4000
    stadium_facility_bonus: int = 6000
    stadium_tier_capacity: Mapping[int, int] = field(
        default_factory=lambda: {1: 9000, 2: 5000, 3: 2500}
    )


DEFAULT_FANS = FanConfig()


# V26 The Crowd — bench roles (one per non-starter, per season). Mentor scales
# with the mentor's identity traits (their first honest consumer); Analyst with
# tactical_iq; Ambassador monetizes his following.
@dataclass(frozen=True)
class BenchRoleConfig:
    mentor_base_dev_ovr: float = 2.5      # max practice-growth bonus to a youngster
    mentor_youth_age_max: int = 23
    analyst_base_targeting: float = 12.0  # max targeting_read_bonus added to user preps
    ambassador_income_per_1k_followers_k: float = 1.4


DEFAULT_BENCH_ROLES = BenchRoleConfig()


# V27 The Calendar — event purses + invite/fame thresholds. Proposed sim-design
# (the spec's "disclosed constants" table); each ships with probe evidence in its
# phase. Purses are integer thousands, tier-scaled so the Domestic Cup pays a
# MODEST margin of league payout (the squeeze invariant — never its rival). All
# defaults safe for legacy (no events -> no purses). Pyramid-only.
@dataclass(frozen=True)
class EventConfig:
    # Domestic Cup champion purse by division tier (1=Premier, 2=Challenger,
    # 3=District). A margin, not a league-payout rival; tuned in Phase 2 against
    # the V22 economy (cup_probe + finances margin).
    cup_purse_champion_k: Mapping[int, int] = field(
        default_factory=lambda: {1: 120, 2: 90, 3: 60}
    )
    # Runner-up + per-round-win purses (tier-scaled anchors). A modest participation
    # margin so a cup run pays something without dwarfing league money.
    cup_purse_runner_up_k: Mapping[int, int] = field(
        default_factory=lambda: {1: 50, 2: 35, 3: 25}
    )
    cup_purse_per_win_k: Mapping[int, int] = field(
        default_factory=lambda: {1: 12, 2: 9, 3: 6}
    )
    # Ruleset Invitational (Cloth Classic / No-Sting Open) champion purse — flat,
    # not tier-scaled (invitationals are cross-tier by fame). Modest.
    invitational_purse_champion_k: int = 70
    invitational_purse_runner_up_k: int = 30
    # MSI (Premier + Circuit leaders) champion purse — prestige + a modest purse.
    msi_purse_champion_k: int = 100
    # Founders' Exhibition (fan-invited, declared no-seeding, money only) purse.
    founders_purse_champion_k: int = 80
    # Founders' invite count: top-N clubs by fan_ledger.club_fans (spec: 4-6).
    founders_invite_count: int = 5
    # Ruleset-invitational fame threshold: a club's prestige must reach this to
    # receive an invitational invite (the fame gate).
    invitational_fame_min: int = 20
    # Prospect-showcase warmth: a one-season credibility bump granted to the
    # invitational champion's club (the V26 recruiting-credibility channel).
    warmth_credibility: int = 4


DEFAULT_EVENTS = EventConfig()


@dataclass(frozen=True)
class WeatherConfig:
    """V28 — The Weather: ecosystem weather tuning (data-derived, no injected dials).

    All constants are proposed sim-design with measured probe evidence; never
    claimed as real-world fidelity. ``meta.py``/MetaPatch stays retired.
    """

    # Meta journalism: minimum absolute delta in a per-division rate for a trend
    # to be reported as "notable" in the league bulletin (keeps the ticker honest
    # — small noise is not narrated as a shift).
    trend_notable_delta: float = 0.04
    # Emergent meta: per-offseason nudge magnitude applied to each AI club's
    # tactic-drift overlay toward the prior season's winning dimensions. Bounded
    # so tactics drift but don't snap in one offseason.
    drift_rate: float = 0.15
    # Emergent meta: deterministic fraction of AI clubs that drift AWAY from the
    # winning trend (the contrarian generation that breaks a permanent solve).
    contrarian_fraction: float = 0.20
    # Officiating emphasis: bounded delta applied to the existing catch/block
    # sigmoid bias before the existing roll (within the rulebook's discretion
    # space; never an invented enforcement). Default 0.0 ⇒ byte-identical.
    emphasis_catch_delta_max: float = 0.08
    emphasis_block_delta_max: float = 0.06


DEFAULT_WEATHER = WeatherConfig()


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
    "ContractConfig",
    "DEFAULT_CONTRACTS",
    "FacilityConfig",
    "DEFAULT_FACILITIES",
    "FanConfig",
    "DEFAULT_FANS",
    "BenchRoleConfig",
    "DEFAULT_BENCH_ROLES",
    "EventConfig",
    "DEFAULT_EVENTS",
    "WeatherConfig",
    "DEFAULT_WEATHER",
    "CONTESTED_USER_OFFER_BASE",
    "CONTESTED_USER_OFFER_INTEREST_WEIGHT",
    "CONTESTED_VETO_OFFER_FLOOR",
    "MOTIVATION_FIT_WEIGHT",
    "VERBAL_INTEREST_THRESHOLD",
    "RIVAL_SUITORS_SHOWN",
    "RIVAL_PURSUIT_TALENT_WEIGHT",
    "RIVAL_PURSUIT_JITTER_SPAN",
    "RIVAL_MOMENTUM_PER_WEEK",
    "RIVAL_MOMENTUM_MAX",
    "NETWORK_UPGRADE_COSTS",
    "NETWORK_DEFAULT_LEVEL",
    "NETWORK_MAX_LEVEL",
    "AI_NETWORK_LEVEL_BY_TIER",
    "AI_NETWORK_BLINDSPOT_RATE",
    "DEFAULT_ECONOMY",
    "DifficultyProfile",
    "EconomyConfig",
    "ScoutingBalanceConfig",
    "CONFIG_REGISTRY",
    "DEFAULT_CONFIG",
    "DEFAULT_SCOUTING_CONFIG",
    "get_config",
]
