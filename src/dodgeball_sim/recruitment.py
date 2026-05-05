from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from .config import ScoutingBalanceConfig
from .models import Player, PlayerRatings, PlayerTraits
from .rng import DeterministicRNG
from .scouting_center import Prospect, Trajectory


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
    "Novak", "Penn", "Sol", "Tanner", "West", "Yardley", "Zane", "Okafor",
)
_GROWTH_CURVES = ("early", "steady", "late")


def _unique_name(
    *,
    rng: DeterministicRNG,
    used_names: set[str],
    fallback_tag: str,
) -> str:
    # Build all possible combos, shuffle once with rng, pick first unused.
    # This consumes a fixed amount of RNG state regardless of collisions.
    combos = [f"{f} {l}" for f in _FIRST_NAMES for l in _LAST_NAMES]
    combos = rng.shuffle(combos)  # one shuffle, fixed RNG consumption
    for name in combos:
        if name not in used_names:
            used_names.add(name)
            return name
    # Fallback: pool exhausted (only possible with classes > 1024)
    base = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)} {fallback_tag}"
    used_names.add(base)
    return base


def generate_rookie_class(
    season_id: str,
    rng: DeterministicRNG,
    size: int = 12,
) -> list[Player]:
    """Generate a deterministic rookie class for one season."""
    rookies: list[Player] = []
    used_names: set[str] = set()
    for index in range(size):
        full_name = _unique_name(rng=rng, used_names=used_names, fallback_tag=f"#{index + 1}")
        growth_curve = rng.choice(_GROWTH_CURVES)
        rookies.append(
            Player(
                id=f"{season_id}_rookie_{index + 1:02d}",
                name=full_name,
                age=18 + int(rng.roll(0, 4)),
                club_id=None,
                newcomer=True,
                ratings=PlayerRatings(
                    accuracy=_rating_roll(rng),
                    power=_rating_roll(rng),
                    dodge=_rating_roll(rng),
                    catch=_rating_roll(rng),
                    stamina=_stamina_roll(rng),
                ).apply_bounds(),
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
    archetype_pool = ("Sharpshooter", "Enforcer", "Escape Artist", "Ball Hawk", "Iron Engine")
    trait_pool = ("IRONWALL", "CLUTCH", "QUICK_RELEASE", "GLOVES", "READ_AND_REACT")

    for index in range(config.prospect_class_size):
        full_name = _unique_name(rng=rng, used_names=used_names, fallback_tag=f"#{index + 1}")
        ratings = {
            "accuracy": round(rng.roll(45.0, 92.0), 2),
            "power": round(rng.roll(45.0, 92.0), 2),
            "dodge": round(rng.roll(45.0, 92.0), 2),
            "catch": round(rng.roll(45.0, 92.0), 2),
            "stamina": round(rng.roll(50.0, 88.0), 2),
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

        true_archetype = _archetype_for_ratings(ratings)
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
    player = Player(
        id=prospect.player_id,
        name=prospect.name,
        age=prospect.age,
        club_id=club_id,
        newcomer=True,
        ratings=PlayerRatings(
            accuracy=prospect.hidden_ratings["accuracy"],
            power=prospect.hidden_ratings["power"],
            dodge=prospect.hidden_ratings["dodge"],
            catch=prospect.hidden_ratings["catch"],
            stamina=prospect.hidden_ratings["stamina"],
        ).apply_bounds(),
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


def _archetype_for_ratings(ratings: dict[str, float]) -> str:
    archetype_map = {
        "accuracy": "Sharpshooter",
        "power": "Enforcer",
        "dodge": "Escape Artist",
        "catch": "Ball Hawk",
        "stamina": "Iron Engine",
    }
    rating_keys = ("accuracy", "power", "dodge", "catch", "stamina")
    present = {key: ratings.get(key, 0.0) for key in rating_keys}
    dominant = max(present, key=present.get)
    return archetype_map[dominant]


def _rating_roll(rng: DeterministicRNG) -> float:
    return round(rng.roll(45.0, 78.0), 2)


def _stamina_roll(rng: DeterministicRNG) -> float:
    return round(rng.roll(50.0, 82.0), 2)


def _potential_roll(rng: DeterministicRNG) -> float:
    return round(rng.roll(70.0, 96.0), 2)


__all__ = [
    "FreeAgent",
    "TransactionEvent",
    "build_transaction_event",
    "generate_prospect_pool",
    "generate_rookie_class",
    "sign_prospect_to_club",
]
