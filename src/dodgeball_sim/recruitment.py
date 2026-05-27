from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from .archetype_derivation import derive_archetype
from .config import ScoutingBalanceConfig
from .models import Player, PlayerArchetype, PlayerRatings, PlayerTraits
from .rng import DeterministicRNG
from .scouting_center import Prospect, Trajectory
from typing import Any, Dict, Optional, Tuple
from typing import Any, Dict, Optional, Tuple
from typing import Any, Dict, Optional, Tuple


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

def get_current_recruiting_budget(conn: sqlite3.Connection, season_id: str, week: int) -> dict[str, list[int]]:
    from .persistence import get_state
    budget = {
        "scout": [0, 3],
        "contact": [0, 5],
        "visit": [0, 1],
    }
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

    if current_used >= max_allowed:
        raise ValueError(f"No {verb} slots remaining this week")

    used[verb] = current_used + 1
    set_state(conn, key, __import__("json").dumps(used))
    conn.commit()


_FIRST_NAMES = (
    "Rin", "Avery", "Kai", "River", "Mara", "Ezra", "Sloane", "Jules",
    "Remy", "Quinn", "Niko", "Sable", "Ash", "Lyra", "Zeph", "Cass",
    "Talia", "Noor", "Imani", "Briar", "Callum", "Elio", "Mika", "Nia",
    "Rowan", "Selah", "Tobin", "Vale", "Wren", "Zara", "Kellan", "Luca",
)
_LAST_NAMES = (
    "Voss", "Helix", "Turner", "Lark", "Orion", "Vega", "Keene", "Hart",
    "Rowe", "Slate", "Frost", "Drake", "Munn", "Cole", "Beck", "Thorn",
    "Bishop", "Vale", "Cross", "Mercer", "Rhodes", "Santos", "Ibarra", "Kline",
    "Novak", "Parr", "Sol", "Tanner", "West", "Yardley", "Zane", "Okafor",
    "Chavez", "Duval", "Nakamura", "Jensen", "Olsen", "Griffin", "Sterling", "Hawthorne",
    "Crosby", "Sinclair", "Garrison", "Fitzgerald", "Kerrigan", "O'Neill", "Rousseau", "Mendoza",
    "Petrov", "Saito", "Takahashi", "Chen", "Kim", "Park", "Patel", "Sharma",
    "Singh", "Das", "Ali", "Hassan", "Mensah", "Diallo", "Toure", "Kone",
    "Ivanov", "Smirnov", "Hansen", "Nielsen", "Johansen", "Moreau", "Dubois", "Leroy",
    "Garcia", "Martinez", "Rodriguez", "Lopez", "Gonzalez", "Perez", "Sanchez", "Ramirez",
    "Torres", "Flores", "Sato", "Aura", "Zenith", "Apex", "Prism", "Bloom",
    "Knox", "Mace", "Ash", "Moss", "Fern", "Shore"
)
_GROWTH_CURVES = ("early", "steady", "late")

_RECRUITMENT_DISPLAY_NAMES: dict[PlayerArchetype, str] = {
    PlayerArchetype.THROWER: "Sharpshooter",
    PlayerArchetype.CATCHER: "Net Specialist",
    PlayerArchetype.BALL_HAWK: "Ball Hawk",
    PlayerArchetype.DODGER_ANCHOR: "Iron Anchor",
    PlayerArchetype.THROWER_CATCHER: "Two-Way Threat",
    PlayerArchetype.THROWER_DODGER: "Skirmisher",
    PlayerArchetype.CATCHER_HAWK: "Possession Specialist",
    PlayerArchetype.HAWK_DODGER: "Hit-and-Run",
}


def _display_name_for_archetype(archetype: PlayerArchetype, ratings: PlayerRatings) -> str:
    return _RECRUITMENT_DISPLAY_NAMES[archetype]


def archetype_for_player(player: Player) -> str:
    return _display_name_for_archetype(player.archetype, player.ratings)


def _unique_name(
    *,
    rng: DeterministicRNG,
    used_names: set[str],
    used_last_names: set[str] | None = None,
    fallback_tag: str,
) -> str:
    # Build all possible combos, shuffle once with rng, pick first unused.
    # This consumes a fixed amount of RNG state regardless of collisions.
    combos = [(first, last) for first in _FIRST_NAMES for last in _LAST_NAMES]
    combos = rng.shuffle(combos)  # one shuffle, fixed RNG consumption
    for first, last in combos:
        name = f"{first} {last}"
        if name in used_names:
            continue
        if used_last_names is not None and last in used_last_names:
            continue
        used_names.add(name)
        if used_last_names is not None:
            used_last_names.add(last)
        return name
    for first, last in combos:
        name = f"{first} {last}"
        if name not in used_names:
            used_names.add(name)
            if used_last_names is not None:
                used_last_names.add(last)
            return name
    # Fallback: pool exhausted (only possible with classes > 1024)
    base = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)} {fallback_tag}"
    used_names.add(base)
    if used_last_names is not None:
        used_last_names.add(base.split()[-1])
    return base


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
) -> list[Prospect]:
    """Generate hidden prospect truths and a wide public baseline."""
    prospects: list[Prospect] = []
    used_names: set[str] = set()
    used_last_names: set[str] = set()
    archetype_pool = tuple(_RECRUITMENT_DISPLAY_NAMES.values())
    trait_pool = ("IRONWALL", "CLUTCH", "QUICK_RELEASE", "GLOVES", "READ_AND_REACT")

    for index in range(config.prospect_class_size):
        full_name = _unique_name(
            rng=rng,
            used_names=used_names,
            used_last_names=used_last_names,
            fallback_tag=f"#{index + 1}",
        )
        potential_ceiling = rng.roll(55.0, 96.0)
        ratings = {
            "accuracy": round(rng.roll(35.0, potential_ceiling - 4.0), 2),
            "power": round(rng.roll(35.0, potential_ceiling - 4.0), 2),
            "dodge": round(rng.roll(35.0, potential_ceiling - 4.0), 2),
            "catch": round(rng.roll(35.0, potential_ceiling - 4.0), 2),
            "stamina": round(rng.roll(40.0, min(88.0, potential_ceiling - 2.0)), 2),
            "tactical_iq": round(rng.roll(35.0, potential_ceiling - 4.0), 2),
            "catch_courage": round(rng.roll(35.0, potential_ceiling - 4.0), 2),
            "throw_selection_iq": round(rng.roll(35.0, potential_ceiling - 4.0), 2),
            "conditioning_curve": round(rng.roll(35.0, potential_ceiling - 4.0), 2),
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
        public_low = max(0, int(round(true_ovr - half_width)))
        public_high = min(100, int(round(true_ovr + half_width)))
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
                hometown=rng.choice(_LAST_NAMES),
                hidden_ratings=ratings,
                hidden_trajectory=trajectory,
                hidden_traits=traits,
                public_archetype_guess=public_archetype,
                public_ratings_band={"ovr": (public_low, public_high)},
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
    player = Player(
        id=prospect.player_id,
        name=prospect.name,
        age=prospect.age,
        club_id=club_id,
        newcomer=True,
        ratings=ratings,
        archetype=derive_archetype(ratings),
        traits=PlayerTraits(
            potential=min(100.0, max(70.0, max(prospect.hidden_ratings.values()) + 8.0)),
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
    return round(rng.roll(70.0, 96.0), 2)


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

def _ensure_recruitment_prepared(
    conn: sqlite3.Connection,
    root_seed: int,
    season_id: str,
    class_year: int,
    user_club_id: Optional[str] = None,
    round_number: int = 1,
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
        profile = profiles.get(club_id)
        if profile is None:
            profile = build_recruitment_profile(root_seed, club_id)
            save_club_recruitment_profile(conn, profile)
        active_profiles.append(profile)

    boards = {}
    from .persistence import load_clubs
    clubs = load_clubs(conn)
    for profile in active_profiles:
        board = build_recruitment_board(
            root_seed=root_seed,
            season_id=season_id,
            profile=profile,
            prospects=prospects,
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

def conduct_recruitment_round(
    conn: sqlite3.Connection,
    root_seed: int,
    season_id: str,
    class_year: int,
    user_club_id: str,
    selected_player_id: str,
):
    from .persistence import (
        load_clubs,
        load_prospect_pool,
        load_recruitment_offers,
        save_recruitment_round,
        save_recruitment_signings,
    )
    from .recruitment_domain import RecruitmentOffer, resolve_recruitment_round

    round_number = _next_recruitment_round_number(conn, season_id)
    _ensure_recruitment_prepared(
        conn,
        root_seed,
        season_id,
        class_year,
        user_club_id=user_club_id,
        round_number=round_number,
    )
    prepared_offers = load_recruitment_offers(conn, season_id, round_number)
    prospect = next((p for p in load_prospect_pool(conn, class_year) if p.player_id == selected_player_id), None)
    if prospect is None:
        raise ValueError(f"Unknown prospect: {selected_player_id}")
    user_offer = RecruitmentOffer(
        season_id=season_id,
        round_number=round_number,
        club_id=user_club_id,
        player_id=selected_player_id,
        offer_strength=100.0,
        source="user",
        need_score=5.0,
        playing_time_pitch=0.5,
        prestige=0.5,
        round_order_value=0.5,
        visible_reason="user target; private scouting priority",
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
    prospects_by_id = {p.player_id: p for p in load_prospect_pool(conn, class_year)}
    clubs = load_clubs(conn)
    for signing in result.signings:
        if signing.club_id not in clubs or _is_already_signed(conn, class_year, signing.player_id):
            continue
        sign_prospect_to_club(conn, prospects_by_id[signing.player_id], signing.club_id, class_year)
    return result



def _is_already_signed(conn, class_year, player_id):
    row = conn.execute(
        "SELECT is_signed FROM prospect_pool WHERE class_year = ? AND player_id = ?",
        (class_year, player_id),
    ).fetchone()
    return bool(row and row["is_signed"])
