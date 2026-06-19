from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from .archetype_derivation import derive_archetype
from .config import ScoutingBalanceConfig
from .models import Player, PlayerArchetype, PlayerRatings, PlayerTraits
from .rng import DeterministicRNG, derive_seed
from .scouting_center import Prospect, Trajectory
from typing import Any, Dict, Optional, Sequence, Tuple


@dataclass(frozen=True)
class FreeAgent:
    player: Player
    available_since_season: str


@dataclass(frozen=True)
class TransactionEvent:
    event_type: str
    action: str
    player_id: str
    club_id: str | None


DEFAULT_RECRUITMENT_BUDGET = {
    "scout": [0, 3],
    "contact": [0, 5],
    "visit": [0, 1],
}

def staff_focus_for_week(conn: sqlite3.Connection, season_id: str, week: int) -> str:
    """The user club's V19b staff focus for this week ('' when unset)."""
    from .persistence import get_state, load_weekly_command_plan

    club_id = get_state(conn, "player_club_id")
    if not club_id:
        return ""
    plan = load_weekly_command_plan(conn, season_id, int(week), club_id)
    orders = dict((plan or {}).get("department_orders") or {})
    return str(orders.get("focus_department") or "").strip().lower()


def get_current_recruiting_budget(conn: sqlite3.Connection, season_id: str, week: int) -> dict[str, list[int]]:
    from .persistence import get_state
    budget = {
        "scout": [0, 3],
        "contact": [0, 5],
        "visit": [0, 1],
    }
    # V19b: a "scouting" staff focus week buys one extra Scout action.
    if staff_focus_for_week(conn, season_id, week) == "scouting":
        budget["scout"][1] += 1
    # Load used slots from db
    raw = get_state(conn, f"recruiting_slots_used_{season_id}_{week}")
    if raw:
        used = __import__("json").loads(raw)
        budget["scout"][0] = used.get("scout", 0)
        budget["contact"][0] = used.get("contact", 0)
        budget["visit"][0] = used.get("visit", 0)
    return budget

def deduct_recruiting_slot(conn: sqlite3.Connection, season_id: str, week: int, verb: str) -> None:
    from .persistence import get_state, set_state
    if verb not in DEFAULT_RECRUITMENT_BUDGET:
        raise ValueError(f"Unknown recruiting verb: {verb}")

    key = f"recruiting_slots_used_{season_id}_{week}"
    raw = get_state(conn, key)
    used = __import__("json").loads(raw) if raw else {}
    current_used = used.get(verb, 0)
    max_allowed = DEFAULT_RECRUITMENT_BUDGET[verb][1]
    # V19b: the scouting staff focus raises the Scout cap (mirrors
    # get_current_recruiting_budget so the UI and the guard agree).
    if verb == "scout" and staff_focus_for_week(conn, season_id, week) == "scouting":
        max_allowed += 1

    if current_used >= max_allowed:
        raise ValueError(f"No {verb} slots remaining this week")

    used[verb] = current_used + 1
    set_state(conn, key, __import__("json").dumps(used))
    conn.commit()


# V22 Phase 1: name pools live in names.py (one wide, culturally broad set
# shared by prospects, rookies and staff). The module-level aliases survive
# for callers/tests that reach for recruitment's pools directly.
from .names import FIRST_NAMES as _FIRST_NAMES
from .names import LAST_NAMES as _LAST_NAMES
from .names import unique_full_name as _names_unique_full_name

_GROWTH_CURVES = ("early", "steady", "late")

def _display_name_for_archetype(archetype: PlayerArchetype, ratings: PlayerRatings) -> str:
    # Archetype display names are unified on PlayerArchetype.display_name (the
    # single source of truth). ``ratings`` is retained for signature stability.
    return archetype.display_name


def archetype_for_player(player: Player) -> str:
    return _display_name_for_archetype(player.archetype, player.ratings)


def _unique_name(
    *,
    rng: DeterministicRNG,
    used_names: set[str],
    used_last_names: set[str] | None = None,
    fallback_tag: str,
) -> str:
    # V22 Phase 1: delegate to the shared picker — exactly two RNG draws per
    # name regardless of collisions (the old full-combo shuffle was also
    # fixed-consumption but O(pool²) per draw, unaffordable at the wide pools).
    return _names_unique_full_name(
        rng=rng,
        used_names=used_names,
        used_last_names=used_last_names,
        fallback_tag=fallback_tag,
    )


def generate_rookie_class(
    season_id: str,
    rng: DeterministicRNG,
    size: int = 12,
) -> list[Player]:
    """Generate a deterministic rookie class for one season."""
    rookies: list[Player] = []
    used_names: set[str] = set()
    used_last_names: set[str] = set()
    for index in range(size):
        full_name = _unique_name(
            rng=rng,
            used_names=used_names,
            used_last_names=used_last_names,
            fallback_tag=f"#{index + 1}",
        )
        growth_curve = rng.choice(_GROWTH_CURVES)
        ratings = PlayerRatings(
            accuracy=_rating_roll(rng),
            power=_rating_roll(rng),
            dodge=_rating_roll(rng),
            catch=_rating_roll(rng),
            stamina=_stamina_roll(rng),
            tactical_iq=_rating_roll(rng),
            catch_courage=_rating_roll(rng),
            throw_selection_iq=_rating_roll(rng),
            conditioning_curve=_rating_roll(rng),
        ).apply_bounds()
        rookies.append(
            Player(
                id=f"{season_id}_rookie_{index + 1:02d}",
                name=full_name,
                age=18 + int(rng.roll(0, 4)),
                club_id=None,
                newcomer=True,
                ratings=ratings,
                archetype=derive_archetype(ratings),
                traits=PlayerTraits(
                    potential=_potential_roll(rng),
                    growth_curve=growth_curve,
                    consistency=round(rng.roll(0.3, 0.9), 4),
                    pressure=round(rng.roll(0.3, 0.9), 4),
                ),
            )
        )
    return rookies


def generate_prospect_pool(
    class_year: int,
    rng: DeterministicRNG,
    config: ScoutingBalanceConfig,
    hometown_pool: Optional[Sequence[str]] = None,
) -> list[Prospect]:
    """Generate hidden prospect truths and a wide public baseline.

    ``hometown_pool`` overrides where each prospect's hometown comes from: the
    pyramid world passes its seven districts (V24 Hometown), legacy single-league
    saves keep the surname pool. It is routed through ``rng.choice`` (one draw,
    any list length), so swapping the pool changes only the hometown string and
    never shifts the generation stream — downstream prospects stay byte-identical.
    """
    pool = _LAST_NAMES if hometown_pool is None else hometown_pool
    prospects: list[Prospect] = []
    used_names: set[str] = set()
    used_last_names: set[str] = set()
    # Display-name pool in PlayerArchetype declaration order (identical order to
    # the former _RECRUITMENT_DISPLAY_NAMES dict — preserves RNG determinism).
    archetype_pool = tuple(a.display_name for a in PlayerArchetype)
    trait_pool = ("IRONWALL", "CLUTCH", "QUICK_RELEASE", "GLOVES", "READ_AND_REACT")

    for index in range(config.prospect_class_size):
        full_name = _unique_name(
            rng=rng,
            used_names=used_names,
            used_last_names=used_last_names,
            fallback_tag=f"#{index + 1}",
        )
        # V19 ceiling scarcity: bottom-weighted natural ceilings capped at 88
        # (one rng.unit() draw, same stream position as the old uniform
        # 55-96 roll). Most prospects are honest Low/Mid projects; Elite
        # (90+) and Generational (96+) effective ceilings come almost
        # exclusively from the rare STAR/GENERATIONAL trajectory floors,
        # which scouting reveals — rare, but findable if you do the work.
        potential_ceiling = 55.0 + 33.0 * (rng.unit() ** 2)
        ratings = {
            "accuracy": int(round(rng.roll(35.0, potential_ceiling - 4.0))),
            "power": int(round(rng.roll(35.0, potential_ceiling - 4.0))),
            "dodge": int(round(rng.roll(35.0, potential_ceiling - 4.0))),
            "catch": int(round(rng.roll(35.0, potential_ceiling - 4.0))),
            "stamina": int(round(rng.roll(40.0, min(88.0, potential_ceiling - 2.0)))),
            "tactical_iq": int(round(rng.roll(35.0, potential_ceiling - 4.0))),
            "catch_courage": int(round(rng.roll(35.0, potential_ceiling - 4.0))),
            "throw_selection_iq": int(round(rng.roll(35.0, potential_ceiling - 4.0))),
            "conditioning_curve": int(round(rng.roll(35.0, potential_ceiling - 4.0))),
        }
        trajectory = _draw_trajectory(rng, config)

        trait_count = int(rng.roll(0, 3.999))
        traits: list[str] = []
        for _ in range(trait_count):
            trait = rng.choice(trait_pool)
            if trait not in traits:
                traits.append(trait)

        true_ovr = sum(ratings.values()) / len(ratings)
        half_width = config.public_baseline_band_half_width
        # The public read is an ESTIMATE: jitter the band center so the
        # midpoint does not encode the hidden true overall. Scouting narrows
        # the band around the public estimate; the verified OVR is only
        # revealed at signing (V16 Task 1).
        jitter = config.public_band_center_jitter
        band_center = true_ovr + rng.roll(-jitter, jitter)
        public_low = max(0, int(round(band_center - half_width)))
        public_high = min(100, int(round(band_center + half_width)))
        if public_high - public_low != 2 * half_width:
            public_low = max(0, public_high - 2 * half_width)
            public_high = min(100, public_low + 2 * half_width)

        rating_obj = PlayerRatings(
            accuracy=ratings["accuracy"],
            power=ratings["power"],
            dodge=ratings["dodge"],
            catch=ratings["catch"],
            stamina=ratings["stamina"],
            tactical_iq=ratings["tactical_iq"],
            catch_courage=ratings["catch_courage"],
            throw_selection_iq=ratings["throw_selection_iq"],
            conditioning_curve=ratings["conditioning_curve"],
        ).apply_bounds()
        true_archetype = _display_name_for_archetype(derive_archetype(rating_obj), rating_obj)
        if rng.unit() < config.public_archetype_mislabel_rate:
            public_archetype = rng.choice([a for a in archetype_pool if a != true_archetype])
        else:
            public_archetype = true_archetype

        prospects.append(
            Prospect(
                player_id=f"prospect_{class_year}_{index:03d}",
                class_year=class_year,
                name=full_name,
                age=18 + int(rng.roll(0, 4)),
                hometown=rng.choice(pool),
                hidden_ratings=ratings,
                hidden_trajectory=trajectory,
                hidden_traits=traits,
                public_archetype_guess=public_archetype,
                public_ratings_band={"ovr": (public_low, public_high)},
                pipeline_tier=int(rng.roll(1, 5.999)),
            )
        )
    return prospects


def build_transaction_event(
    action: str,
    player_id: str,
    club_id: str | None,
) -> TransactionEvent:
    return TransactionEvent(
        event_type="transaction",
        action=action,
        player_id=player_id,
        club_id=club_id,
    )


def sign_prospect_to_club(
    conn: sqlite3.Connection,
    prospect: Prospect,
    club_id: str,
    season_num: int,
) -> Player:
    from .persistence import (
        load_all_rosters,
        load_clubs,
        mark_prospect_signed,
        save_club,
        save_lineup_default,
        save_player_trajectory,
    )

    rosters = load_all_rosters(conn)
    clubs = load_clubs(conn)
    if club_id not in clubs:
        raise ValueError(f"Unknown club: {club_id}")
    if _is_prospect_signed(conn, season_num, prospect.player_id):
        raise ValueError(f"Prospect {prospect.player_id} is already signed")
    existing_owner = next(
        (
            existing_club_id
            for existing_club_id, roster in rosters.items()
            if any(existing.id == prospect.player_id for existing in roster)
        ),
        None,
    )
    if existing_owner is not None:
        raise ValueError(f"Prospect {prospect.player_id} is already signed by {existing_owner}")

    mark_prospect_signed(conn, season_num, prospect.player_id)
    ratings = PlayerRatings(
        accuracy=prospect.hidden_ratings["accuracy"],
        power=prospect.hidden_ratings["power"],
        dodge=prospect.hidden_ratings["dodge"],
        catch=prospect.hidden_ratings["catch"],
        stamina=prospect.hidden_ratings["stamina"],
        tactical_iq=prospect.hidden_ratings.get("tactical_iq", 50.0),
        catch_courage=prospect.hidden_ratings.get("catch_courage", 50.0),
        throw_selection_iq=prospect.hidden_ratings.get("throw_selection_iq", 50.0),
        conditioning_curve=prospect.hidden_ratings.get("conditioning_curve", 50.0),
    ).apply_bounds()
    # V25: every signing lands a STANDARD, ability-blind entry deal priced by the
    # signing club's tier (money enters at the second contract). Pyramid-gated so
    # legacy single-league signings keep the byte-identical free 0/1 default.
    entry_salary_k = 0
    entry_contract_term = 1
    from .world import pyramid_world_active

    if pyramid_world_active(conn):
        from . import contracts
        from .persistence import get_state, load_division_map

        season_id = get_state(conn, "active_season_id")
        seat = load_division_map(conn, season_id).get(club_id) if season_id else None
        tier = seat.tier if seat is not None else 3
        entry_salary_k = contracts.entry_salary_k(tier)
        entry_contract_term = contracts.entry_term()
    player = Player(
        id=prospect.player_id,
        name=prospect.name,
        age=prospect.age,
        club_id=club_id,
        newcomer=True,
        salary_k=entry_salary_k,
        contract_term=entry_contract_term,
        ratings=ratings,
        archetype=derive_archetype(ratings),
        traits=PlayerTraits(
            # V19 ceiling scarcity: the signed ceiling is the prospect's own
            # natural headroom (best hidden rating + 8) — the old hard floor
            # of 70 handed every signing a Mid-tier ceiling regardless of
            # talent. Trajectory floors (IMPACT/STAR/GENERATIONAL) still
            # raise the effective ceiling for the labeled tiers.
            potential=min(100.0, max(prospect.hidden_ratings.values()) + 8.0),
            growth_curve=50.0,
            consistency=0.5,
            pressure=0.5,
        ),
    )
    new_roster = list(rosters.get(club_id, [])) + [player]
    save_club(conn, clubs[club_id], new_roster)
    save_lineup_default(conn, club_id, [p.id for p in new_roster])
    save_player_trajectory(conn, player.id, prospect.hidden_trajectory)
    conn.execute("DELETE FROM scouting_state WHERE player_id = ?", (player.id,))
    conn.commit()
    return player


def _is_prospect_signed(conn: sqlite3.Connection, class_year: int, player_id: str) -> bool:
    row = conn.execute(
        "SELECT is_signed FROM prospect_pool WHERE class_year = ? AND player_id = ?",
        (class_year, player_id),
    ).fetchone()
    return bool(row and row["is_signed"])


def _draw_trajectory(rng: DeterministicRNG, config: ScoutingBalanceConfig) -> str:
    roll = rng.unit()
    cumulative = 0.0
    trajectory = Trajectory.NORMAL.value
    for tier_name, rate in config.trajectory_rates.items():
        cumulative += rate
        if roll < cumulative:
            trajectory = tier_name
            break
    return trajectory

def _rating_roll(rng: DeterministicRNG) -> float:
    return round(rng.roll(45.0, 78.0), 2)


def _stamina_roll(rng: DeterministicRNG) -> float:
    return round(rng.roll(50.0, 82.0), 2)


def _potential_roll(rng: DeterministicRNG) -> float:
    # V19 ceiling scarcity: the rookie/free-agent refill pool follows the
    # same bottom-weighted shape as the prospect pool (one rng.unit() draw,
    # same stream position as the old uniform 70-96 roll). Emergency refills
    # are journeymen, not hidden superstars.
    return round(58.0 + 30.0 * (rng.unit() ** 2), 2)


__all__ = [
    "FreeAgent",
    "TransactionEvent",
    "archetype_for_player",
    "build_transaction_event",
    "generate_prospect_pool",
    "generate_rookie_class",
    "sign_prospect_to_club",
]


# ----------------------------------------------------------------------
# Recruitment round helpers (formerly manager_helpers)
# ----------------------------------------------------------------------

def _default_roster_needs() -> Dict[str, float]:
    return {
        "Sharpshooter": 0.5,
        "Net Specialist": 0.5,
        "Ball Hawk": 0.5,
        "Iron Anchor": 0.5,
        "Two-Way Threat": 0.5,
        "Skirmisher": 0.5,
        "Possession Specialist": 0.5,
        "Hit-and-Run": 0.5,
    }

def _next_recruitment_round_number(conn: sqlite3.Connection, season_id: str) -> int:
    prepared = conn.execute(
        """
        SELECT round_number
        FROM recruitment_round
        WHERE season_id = ? AND status = 'prepared'
        ORDER BY round_number
        LIMIT 1
        """,
        (season_id,),
    ).fetchone()
    if prepared is not None:
        return int(prepared["round_number"])

    max_round = conn.execute(
        """
        SELECT MAX(round_number) AS max_round
        FROM (
            SELECT round_number FROM recruitment_round WHERE season_id = ?
            UNION ALL
            SELECT round_number FROM recruitment_signing WHERE season_id = ?
        )
        """,
        (season_id, season_id),
    ).fetchone()
    return int(max_round["max_round"] or 0) + 1

def _eligible_ai_offer_clubs(
    conn: sqlite3.Connection,
    season_id: str,
    user_club_id: Optional[str],
) -> set[str]:
    """AI clubs allowed to bid this round: under the per-offseason signing cap
    (D3) and below the Signing Day roster ceiling. The user club never bids
    through this path.

    V24 (The Board): recruiting is whole-world. Every AI club in the universe
    recruits its own class on merit — not just the user's division — so the
    pyramid's top clubs (Premier + Circuit) get new blood every offseason
    instead of stagnating while the user compounds (this closes the V23
    end-state-dominance gap). Reach/district biases shape WHO each club pursues
    (recruitment_domain.build_recruitment_board); this gate only decides WHO
    may bid. Classic (non-pyramid) saves were never division-scoped and stay
    byte-identical.
    """
    from .config import AI_OFFSEASON_MAX_ROSTER, AI_OFFSEASON_SIGNINGS_PER_CLUB
    from .persistence import load_all_rosters, load_recruitment_signings

    signings_per_club: dict[str, int] = {}
    for signing in load_recruitment_signings(conn, season_id):
        if signing.source == "ai":
            signings_per_club[signing.club_id] = signings_per_club.get(signing.club_id, 0) + 1

    eligible: set[str] = set()
    for club_id, roster in load_all_rosters(conn).items():
        if user_club_id is not None and club_id == user_club_id:
            continue
        if signings_per_club.get(club_id, 0) >= AI_OFFSEASON_SIGNINGS_PER_CLUB:
            continue
        if len(roster) >= AI_OFFSEASON_MAX_ROSTER:
            continue
        eligible.add(club_id)
    return eligible


def _ai_network_visible_prospects(
    club_id: str,
    prospects: list,
    *,
    division_map: dict,
    clubs: dict,
    season_id: str,
) -> list:
    """The prospects an AI club's Scouting Network can see (V24 Phase 6).

    Level by division tier (config.AI_NETWORK_LEVEL_BY_TIER) with a deterministic
    per-(season, club) blind-spot jitter that can drop a club one level. The blind
    spots are the point: they leave gems unrecruited (a national prodigy that no
    L2 club can sign that year, a local kid only his region's clubs see)."""
    from .scouting_network import (
        ai_network_level,
        prospect_fully_visible,
        reach_band_for_trajectory,
    )
    from .world import DISTRICT_REGIONS, district_neighbors

    seat = division_map.get(club_id)
    tier = seat.tier if seat is not None else None
    jitter = DeterministicRNG(derive_seed(0, "ai_network", season_id, club_id)).roll(0.0, 1.0)
    level = ai_network_level(tier, jitter=jitter)
    club = clubs.get(club_id)
    home = getattr(club, "home_region", "") or ""
    neighbors = district_neighbors(home)
    home_recognized = home in DISTRICT_REGIONS
    return [
        p
        for p in prospects
        if prospect_fully_visible(
            reach_band=reach_band_for_trajectory(p.hidden_trajectory),
            hometown=p.hometown,
            level=level,
            home_district=home,
            neighbors=neighbors,
            home_recognized=home_recognized,
        )
    ]


def _user_offer_strength(interest: float, fit_score: float, veto: bool) -> float:
    """The user's contested Signing Day offer strength. ``fit_score=0`` (legacy
    single-league) reproduces the V16 formula exactly. On pyramid saves, fit is
    the 0-1 motivation blend. A dealbreaker veto floors the offer — the prospect
    never verbals, regardless of interest or fit."""
    from .config import (
        CONTESTED_USER_OFFER_BASE,
        CONTESTED_USER_OFFER_INTEREST_WEIGHT,
        CONTESTED_VETO_OFFER_FLOOR,
        MOTIVATION_FIT_WEIGHT,
    )

    if veto:
        return CONTESTED_VETO_OFFER_FLOOR
    return round(
        CONTESTED_USER_OFFER_BASE
        + interest * CONTESTED_USER_OFFER_INTEREST_WEIGHT
        + fit_score * MOTIVATION_FIT_WEIGHT,
        4,
    )


def _tier_ceiling_bonus(tier: int, public_high_band: float) -> float:
    """V24: how much an AI club in a given division TIER weights a prospect's
    upside on its board. Top tiers (Premier + the International Circuit, both
    tier 1) chase ceiling so the Worlds feeders build toward a compounding
    user instead of treading water; bottom tiers favor ready-now. Rewards
    upside above the baseline only — never raw signing."""
    from .config import AI_TIER_CEILING_BASELINE, AI_TIER_CEILING_PREFERENCE

    pref = AI_TIER_CEILING_PREFERENCE.get(tier, 0.0)
    upside = max(0.0, public_high_band - AI_TIER_CEILING_BASELINE)
    return round(upside * pref, 4)


def _ensure_recruitment_prepared(
    conn: sqlite3.Connection,
    root_seed: int,
    season_id: str,
    class_year: int,
    user_club_id: Optional[str] = None,
    round_number: int = 1,
    eligible_club_ids: Optional[set[str]] = None,
) -> Tuple[Any, ...]:
    from .persistence import (
        load_all_rosters,
        load_club_recruitment_profiles,
        load_prospect_pool,
        load_recruitment_signings,
        load_recruitment_board,
        load_recruitment_offers,
        load_recruitment_round,
        save_club_recruitment_profile,
        save_recruitment_board,
        save_recruitment_offers,
        save_recruitment_round,
    )
    from .recruitment_domain import (
        build_recruitment_board,
        build_recruitment_profile,
        prepare_ai_offers,
        RecruitmentBoardRow,
    )

    existing_round = load_recruitment_round(conn, season_id, round_number)
    if existing_round is not None:
        return load_recruitment_offers(conn, season_id, round_number)

    already_signed_ids = {signing.player_id for signing in load_recruitment_signings(conn, season_id)}
    prospects = [
        p
        for p in load_prospect_pool(conn, class_year)
        if p.player_id not in already_signed_ids
        and not _is_already_signed(conn, class_year, p.player_id)
    ]
    profiles = load_club_recruitment_profiles(conn)
    rosters = load_all_rosters(conn)
    active_profiles = []
    for club_id in sorted(rosters):
        if user_club_id is not None and club_id == user_club_id:
            continue
        if eligible_club_ids is not None and club_id not in eligible_club_ids:
            continue
        profile = profiles.get(club_id)
        if profile is None:
            profile = build_recruitment_profile(root_seed, club_id)
            save_club_recruitment_profile(conn, profile)
        active_profiles.append(profile)

    boards = {}
    from .persistence import load_clubs
    from .world import pyramid_world_active
    clubs = load_clubs(conn)
    # V24: in the pyramid, each club's division tier shades how hard it chases
    # upside (whole-world recruiting fix). Empty on legacy single-league saves.
    division_map = {}
    if pyramid_world_active(conn):
        from .persistence import load_division_map

        division_map = load_division_map(conn, season_id)
    for profile in active_profiles:
        # V24 Phase 6: AI clubs see only prospects within their Scouting Network
        # reach (level by division tier + a deterministic blind-spot jitter), so
        # gems fall through the cracks — a national prodigy is invisible to most
        # D3 clubs, a far-district kid invisible to clubs outside his region. A
        # club is never blinded to the WHOLE class (safety fallback). Pyramid
        # only — division_map is empty on legacy single-league saves.
        club_prospects = prospects
        if division_map:
            visible = _ai_network_visible_prospects(
                profile.club_id, prospects, division_map=division_map,
                clubs=clubs, season_id=season_id,
            )
            if visible:
                club_prospects = visible
        board = build_recruitment_board(
            root_seed=root_seed,
            season_id=season_id,
            profile=profile,
            prospects=club_prospects,
            roster_needs=_default_roster_needs(),
        )

        # Apply V12 AI Recruiting preference weight shim
        archetype = clubs.get(profile.club_id).program_archetype if profile.club_id in clubs else "Balanced Rebuild"
        adjusted_board = []
        for row in board:
            prospect = next(p for p in prospects if p.player_id == row.player_id)
            total_score = row.total_score

            if archetype == "Development Factory":
                # Favors high potential / raw upside (using the high band)
                ceiling = prospect.public_ratings_band["ovr"][1]
                total_score += round((ceiling - 60) * 0.3, 4)
            elif archetype == "Contender":
                # Favors verified ready-now stars (using the low/floor band)
                floor = prospect.public_ratings_band["ovr"][0]
                total_score += round((floor - 50) * 0.3, 4)
            elif archetype == "Aging Veterans":
                # Favors ready-now depth immediately
                midpoint = (prospect.public_ratings_band["ovr"][0] + prospect.public_ratings_band["ovr"][1]) / 2.0
                total_score += round((midpoint - 55) * 0.2, 4)

            # V24: division-tier ceiling preference — top tiers chase upside so
            # the Worlds feeders keep pace with a compounding user.
            seat = division_map.get(profile.club_id)
            if seat is not None:
                total_score += _tier_ceiling_bonus(
                    seat.tier, prospect.public_ratings_band["ovr"][1]
                )

            adjusted_board.append(
                RecruitmentBoardRow(
                    club_id=row.club_id,
                    player_id=row.player_id,
                    rank=row.rank,
                    public_score=row.public_score,
                    need_score=row.need_score,
                    preference_score=row.preference_score,
                    total_score=round(total_score, 4),
                    visible_reason=row.visible_reason,
                )
            )

        ranked = sorted(adjusted_board, key=lambda r: (-r.total_score, r.player_id))
        final_board = [
            RecruitmentBoardRow(
                club_id=row.club_id,
                player_id=row.player_id,
                rank=index,
                public_score=row.public_score,
                need_score=row.need_score,
                preference_score=row.preference_score,
                total_score=row.total_score,
                visible_reason=row.visible_reason,
            )
            for index, row in enumerate(ranked, start=1)
        ]

        save_recruitment_board(conn, season_id, final_board)
        boards[profile.club_id] = final_board or load_recruitment_board(conn, season_id, profile.club_id)

    offers = prepare_ai_offers(root_seed, season_id, round_number, active_profiles, boards, already_signed_ids)
    save_recruitment_round(conn, season_id, round_number, "prepared", {"prepared_offer_count": len(offers)})
    save_recruitment_offers(conn, offers)
    return tuple(offers)

def build_recruitment_day_summary(
    conn: sqlite3.Connection,
    season_id: str,
    class_year: int,
    user_club_id: Optional[str],
) -> Dict[str, int]:
    from .persistence import load_prospect_pool, load_recruitment_signings

    prospects = load_prospect_pool(conn, class_year=class_year)
    signings = load_recruitment_signings(conn, season_id)
    signed_ids = {signing.player_id for signing in signings}
    return {
        "available_prospects": sum(
            1
            for prospect in prospects
            if prospect.player_id not in signed_ids
            and not _is_already_signed(conn, class_year, prospect.player_id)
        ),
        "signed_count": len(signings),
        "sniped_count": sum(1 for signing in signings if user_club_id and signing.club_id != user_club_id),
        "current_round": _next_recruitment_round_number(conn, season_id),
    }

@dataclass(frozen=True)
class ContestedPickOutcome:
    """The resolved Signing Day round from the user's perspective."""

    result: Any  # RecruitmentRoundResult
    user_won: bool
    signed_player: Optional[Any]  # Player when the user won
    user_offer_strength: float
    interest: int
    actions_taken: int
    winning_club_id: Optional[str]
    winning_offer_strength: Optional[float]
    # Best opposing bid on the user's pick (None when uncontested).
    rival_club_id: Optional[str] = None
    rival_offer_strength: Optional[float] = None
    # V24: the 0-1 motivation fit folded into the user offer, and whether the
    # prospect's dealbreaker vetoed the verbal (pyramid only).
    motivation_fit: float = 0.0
    dealbreaker_veto: bool = False


def _apply_round_signings(
    conn: sqlite3.Connection,
    result,
    class_year: int,
    user_club_id: Optional[str],
):
    """Convert round signings into roster players, with honest lineup care.

    The user's manual lineup default must survive a signing (raw
    ``sign_prospect_to_club`` rewrites it to roster order); AI clubs get their
    lineup re-optimized, matching the offseason convention.
    """
    from .lineup import optimize_ai_lineup
    from .persistence import (
        load_all_rosters,
        load_clubs,
        load_lineup_default,
        load_prospect_pool,
        save_lineup_default,
    )

    prospects_by_id = {p.player_id: p for p in load_prospect_pool(conn, class_year)}
    clubs = load_clubs(conn)
    signed_players: dict[str, Any] = {}
    for signing in result.signings:
        if signing.club_id not in clubs or _is_already_signed(conn, class_year, signing.player_id):
            continue
        prospect = prospects_by_id.get(signing.player_id)
        if prospect is None:
            continue
        if user_club_id is not None and signing.club_id == user_club_id:
            from .offseason_ceremony import _lineup_default_after_signing

            prior_default = load_lineup_default(conn, user_club_id)
            player = sign_prospect_to_club(conn, prospect, signing.club_id, class_year)
            roster = list(load_all_rosters(conn).get(user_club_id, []))
            save_lineup_default(
                conn,
                user_club_id,
                _lineup_default_after_signing(prior_default, roster, player.id),
            )
        else:
            player = sign_prospect_to_club(conn, prospect, signing.club_id, class_year)
            roster = list(load_all_rosters(conn).get(signing.club_id, []))
            save_lineup_default(conn, signing.club_id, optimize_ai_lineup(roster))
        signed_players[signing.player_id] = player

    # V24 class wire: a league-wide news line whenever a STAR/GENERATIONAL
    # prospect signs anywhere (this chokepoint covers both the user's contested
    # round and the AI offseason sweep).
    from .persistence import get_state

    season_id = get_state(conn, "active_season_id")
    if season_id:
        _emit_class_wire(conn, season_id, result.signings, prospects_by_id, clubs)
    return signed_players


def _emit_class_wire(conn, season_id, signings, prospects_by_id, clubs) -> None:
    """Write a class-wire headline (reusing news_headlines) for each STAR or
    GENERATIONAL prospect that signs. Idempotent per (season, prospect)."""
    from .persistence import load_news_headlines, save_news_headlines

    elite = []
    for signing in signings:
        prospect = prospects_by_id.get(signing.player_id)
        if prospect is None:
            continue
        if prospect.hidden_trajectory not in (
            Trajectory.STAR.value,
            Trajectory.GENERATIONAL.value,
        ):
            continue
        elite.append((signing, prospect))
    if not elite:
        return

    existing = {h["headline_id"] for h in load_news_headlines(conn, season_id)}
    rows = []
    for signing, prospect in elite:
        headline_id = f"classwire_{season_id}_{signing.player_id}"
        if headline_id in existing:
            continue
        club_name = getattr(clubs.get(signing.club_id), "name", signing.club_id)
        arc = (
            "generational"
            if prospect.hidden_trajectory == Trajectory.GENERATIONAL.value
            else "star"
        )
        rows.append({
            "headline_id": headline_id,
            "category": "class_wire",
            "headline_text": f"CLASS WIRE: {club_name} land {arc}-arc prospect {prospect.name}",
            "entity_ids": [signing.player_id, signing.club_id],
        })
    if rows:
        save_news_headlines(conn, season_id, 0, rows)


def conduct_recruitment_round(
    conn: sqlite3.Connection,
    root_seed: int,
    season_id: str,
    class_year: int,
    user_club_id: str,
    selected_player_id: str,
) -> ContestedPickOutcome:
    """Resolve the user's Signing Day pick as a contested round (V16 Task 3).

    Eligible AI clubs bid on their own board targets in the same round — the
    user's pick can be sniped, and AI winners sign for real (league churn).
    Interest built through in-season courtship strengthens the user's offer.
    """
    from .config import (
        CONTESTED_USER_OFFER_BASE,
        CONTESTED_USER_OFFER_INTEREST_WEIGHT,
    )
    from .persistence import (
        load_command_history_all_seasons,
        load_json_state,
        load_prospect_pool,
        load_recruitment_offers,
        save_recruitment_offers,
        save_recruitment_round,
        save_recruitment_signings,
    )
    from .recruiting_actions import current_interest
    from .recruiting_office import _credibility_score
    from .recruitment_domain import RecruitmentOffer, resolve_recruitment_round

    round_number = _next_recruitment_round_number(conn, season_id)
    eligible = _eligible_ai_offer_clubs(conn, season_id, user_club_id)
    _ensure_recruitment_prepared(
        conn,
        root_seed,
        season_id,
        class_year,
        user_club_id=user_club_id,
        round_number=round_number,
        eligible_club_ids=eligible,
    )
    prepared_offers = load_recruitment_offers(conn, season_id, round_number)
    prospect = next((p for p in load_prospect_pool(conn, class_year) if p.player_id == selected_player_id), None)
    if prospect is None:
        raise ValueError(f"Unknown prospect: {selected_player_id}")
    actions = load_json_state(conn, "prospect_recruitment_actions_json", {})
    # Career-wide credibility, matching what the in-season recruit board shows
    # for the same prospect (Audit 7.4: credibility is a career number).
    history = load_command_history_all_seasons(conn)
    credibility = _credibility_score(conn, season_id, user_club_id, history)
    prospect_actions = actions.get(selected_player_id, {})
    interest = current_interest(
        prospect_actions,
        pipeline_tier=prospect.pipeline_tier,
        credibility_score=credibility,
    )
    # V24: on pyramid saves the offer also reflects how well the club satisfies
    # the prospect's motivations; a dealbreaker veto floors it (never verbals).
    fit_score = 0.0
    fit_veto = False
    from .world import pyramid_world_active

    if pyramid_world_active(conn):
        from .motivations import build_club_context, club_fit

        fit = club_fit(build_club_context(conn, user_club_id, season_id), prospect)
        fit_score, fit_veto = fit.fit, fit.veto
    user_strength = _user_offer_strength(interest, fit_score, fit_veto)
    user_offer = RecruitmentOffer(
        season_id=season_id,
        round_number=round_number,
        club_id=user_club_id,
        player_id=selected_player_id,
        offer_strength=user_strength,
        source="user",
        need_score=5.0,
        playing_time_pitch=0.5,
        prestige=0.5,
        round_order_value=0.5,
        visible_reason=f"user target; interest {interest}% from your recruiting work",
    )
    result = resolve_recruitment_round(
        season_id,
        round_number,
        prepared_offers,
        user_offer=user_offer,
        shortlist_player_ids=(selected_player_id,),
    )
    save_recruitment_signings(conn, result.signings)
    save_recruitment_round(
        conn,
        season_id,
        round_number,
        "resolved",
        {"signing_count": len(result.signings), "snipe_count": len(result.snipes)},
    )
    # Persist the user's bid too (after resolution, so a crashed round retries
    # cleanly): the Signing Day class report needs to know which rival
    # signings actually beat a user offer.
    save_recruitment_offers(conn, [user_offer])
    signed_players = _apply_round_signings(conn, result, class_year, user_club_id)

    winner = next(
        (s for s in result.signings if s.player_id == selected_player_id), None
    )
    user_won = winner is not None and winner.club_id == user_club_id
    actions_taken = sum(
        1 for flag in ("scouted", "contacted", "visited") if prospect_actions.get(flag)
    )
    rival = max(
        (o for o in prepared_offers if o.player_id == selected_player_id),
        key=lambda o: o.offer_strength,
        default=None,
    )
    return ContestedPickOutcome(
        result=result,
        user_won=user_won,
        signed_player=signed_players.get(selected_player_id) if user_won else None,
        user_offer_strength=user_strength,
        interest=interest,
        actions_taken=actions_taken,
        winning_club_id=winner.club_id if winner else None,
        winning_offer_strength=round(winner.offer_strength, 4) if winner else None,
        rival_club_id=rival.club_id if rival else None,
        rival_offer_strength=round(rival.offer_strength, 4) if rival else None,
        motivation_fit=round(fit_score, 4),
        dealbreaker_veto=fit_veto,
    )


def run_ai_offseason_signings(
    conn: sqlite3.Connection,
    root_seed: int,
    season_id: str,
    class_year: int,
    user_club_id: Optional[str],
):
    """AI-only Signing Day rounds: every eligible AI club pursues its top
    board target until each has signed (cap D3) or the pool runs dry.

    Deterministic: all draws derive from ``root_seed`` via the existing
    recruitment namespaces keyed on (season, round, club, prospect).
    Returns the tuple of AI signings made by this sweep.
    """
    from .persistence import (
        load_recruitment_offers,
        save_recruitment_round,
        save_recruitment_signings,
    )
    from .recruitment_domain import resolve_recruitment_round

    swept: list = []
    # Bounded: each iteration either signs at least one prospect or stops.
    for _ in range(16):
        eligible = _eligible_ai_offer_clubs(conn, season_id, user_club_id)
        if not eligible:
            break
        if not _available_unsigned_prospects(conn, season_id, class_year):
            break
        round_number = _next_recruitment_round_number(conn, season_id)
        _ensure_recruitment_prepared(
            conn,
            root_seed,
            season_id,
            class_year,
            user_club_id=user_club_id,
            round_number=round_number,
            eligible_club_ids=eligible,
        )
        offers = load_recruitment_offers(conn, season_id, round_number)
        if not offers:
            save_recruitment_round(conn, season_id, round_number, "resolved", {"signing_count": 0})
            break
        result = resolve_recruitment_round(season_id, round_number, offers)
        save_recruitment_signings(conn, result.signings)
        save_recruitment_round(
            conn,
            season_id,
            round_number,
            "resolved",
            {"signing_count": len(result.signings), "snipe_count": 0},
        )
        _apply_round_signings(conn, result, class_year, user_club_id)
        swept.extend(result.signings)
        if not result.signings:
            break
    return tuple(swept)


def _available_unsigned_prospects(
    conn: sqlite3.Connection, season_id: str, class_year: int
) -> list:
    from .persistence import load_prospect_pool, load_recruitment_signings

    already = {s.player_id for s in load_recruitment_signings(conn, season_id)}
    return [
        p
        for p in load_prospect_pool(conn, class_year)
        if p.player_id not in already and not _is_already_signed(conn, class_year, p.player_id)
    ]



def _is_already_signed(conn, class_year, player_id):
    row = conn.execute(
        "SELECT is_signed FROM prospect_pool WHERE class_year = ? AND player_id = ?",
        (class_year, player_id),
    ).fetchone()
    return bool(row and row["is_signed"])
