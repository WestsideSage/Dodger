"""First-hour growth truth — curated rosters must obey the ceiling contract.

`traits.potential` is consumed everywhere as the highest OVR a player can
reach (development closes the potential-OVR headroom gap; the roster page
renders it as "Ceiling"; tiers bucket the absolute value). The curated career
seed predates that contract: it rolled gauss(50, 15), so roughly half of a
fresh takeover roster carried a "ceiling" below its current OVR — zero
headroom, zero development, and a first offseason where every starter moved
+0 (verified on a live save before this fix). These tests pin the repaired
contract end to end:

1. Curated rosters never seed a ceiling below current OVR.
2. A fresh curated league contains genuine growth targets (headroom > 0).
3. A curated young player actually develops in their first offseason.
4. The roster payload never *displays* a ceiling below current OVR, even for
   legacy saves whose stored potential predates the fix.
5. The payload honors the scouted-trajectory potential floor the development
   engine applies.
"""
from __future__ import annotations

import sqlite3

from dodgeball_sim.career_setup import build_curated_roster, initialize_curated_manager_career
from dodgeball_sim.development import apply_season_development, _normalize_growth_curve, _peak_window
from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings, PlayerTraits
from dodgeball_sim.stats import PlayerMatchStats
from dodgeball_sim.persistence import create_schema, load_clubs, save_club, save_player_trajectory
from dodgeball_sim.rng import DeterministicRNG, derive_seed
from dodgeball_sim.sample_data import curated_clubs
from dodgeball_sim.web_status_service import build_roster_payload

ROOT_SEED = 20260426


def _curated_league_rosters():
    return {
        club.club_id: build_curated_roster(
            club.club_id, club.name, derive_seed(ROOT_SEED, "roster", club.club_id)
        )
        for club in curated_clubs()
    }


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def _make_player(pid: str, *, potential: int, ovr: int, age: int) -> Player:
    ratings = PlayerRatings(
        accuracy=ovr, power=ovr, dodge=ovr, catch=ovr, stamina=ovr,
        tactical_iq=50, catch_courage=50, throw_selection_iq=50, conditioning_curve=50,
    )
    return Player(
        id=pid,
        name=pid.title(),
        ratings=ratings,
        archetype=PlayerArchetype.THROWER,
        traits=PlayerTraits(potential=potential, growth_curve=50, consistency=50, pressure=50),
        age=age,
        club_id="aurora",
        newcomer=False,
    )


class TestCuratedSeedCeilingContract:
    def test_curated_roster_ceiling_never_below_ovr(self):
        for club_id, roster in _curated_league_rosters().items():
            for player in roster:
                ovr = int(round(player.overall_skill()))
                assert player.traits.potential >= ovr, (
                    f"{club_id}/{player.name}: seeded ceiling {player.traits.potential} "
                    f"below current OVR {ovr}"
                )

    def test_curated_league_contains_real_growth_targets(self):
        """A fresh league must have players the development engine can move."""
        headrooms = [
            player.traits.potential - int(round(player.overall_skill()))
            for roster in _curated_league_rosters().values()
            for player in roster
        ]
        assert any(h >= 5 for h in headrooms), (
            "No curated player has >=5 headroom — development has nothing to act on"
        )

    def test_curated_roster_is_deterministic(self):
        seed = derive_seed(ROOT_SEED, "roster", "aurora")
        first = build_curated_roster("aurora", "Aurora Sentinels", seed)
        second = build_curated_roster("aurora", "Aurora Sentinels", seed)
        assert [(p.name, p.age, p.traits.potential) for p in first] == [
            (p.name, p.age, p.traits.potential) for p in second
        ]

    def test_curated_young_player_actually_develops(self):
        """Cause -> effect: the first offseason is no longer a +0 wall.

        Before the fix every curated player had zero headroom, so even a
        teenager on full practice reps moved +0. Pick the young, growable
        players a fresh league seeds and require that development moves at
        least one of them.
        """
        young_growers = []
        for roster in _curated_league_rosters().values():
            for player in roster:
                curve = _normalize_growth_curve(player.traits.growth_curve)
                peak_start, _ = _peak_window(curve)
                headroom = player.traits.potential - int(round(player.overall_skill()))
                if player.age < peak_start and headroom >= 5:
                    young_growers.append(player)
        assert young_growers, "Fresh league seeds no young player with real headroom"

        grew = 0
        for player in young_growers:
            developed = apply_season_development(
                player=player,
                season_stats=PlayerMatchStats(),  # zero minutes: practice-reps path
                facilities=(),
                rng=DeterministicRNG(derive_seed(ROOT_SEED, "growth-truth", player.id)),
            )
            if developed.overall_skill() > player.overall_skill():
                grew += 1
        assert grew > 0, (
            f"None of {len(young_growers)} young high-headroom players developed "
            "across a practice offseason"
        )


class TestRosterPayloadCeilingTruth:
    def test_payload_never_displays_ceiling_below_ovr_for_legacy_potential(self):
        """Legacy saves persist potential values below current OVR; the payload
        must clamp the displayed ceiling to the OVR the player already holds."""
        conn = _make_conn()
        initialize_curated_manager_career(conn, "aurora", root_seed=ROOT_SEED)
        club = load_clubs(conn)["aurora"]
        legacy = _make_player("p_legacy", potential=26, ovr=66, age=24)
        save_club(conn, club, [legacy])
        conn.commit()

        payload = build_roster_payload(conn)
        card = next(p for p in payload["roster"] if p["id"] == "p_legacy")
        assert card["potential_ceiling"] == 66
        assert card["headroom"] == 0
        assert card["potential_ceiling"] >= card["overall"]

    def test_payload_applies_trajectory_potential_floor(self):
        """The development engine raises potential to the scouted-trajectory
        floor; the displayed ceiling must match what the engine will do."""
        conn = _make_conn()
        initialize_curated_manager_career(conn, "aurora", root_seed=ROOT_SEED)
        club = load_clubs(conn)["aurora"]
        prospect = _make_player("p_star", potential=50, ovr=60, age=19)
        save_club(conn, club, [prospect])
        save_player_trajectory(conn, "p_star", "STAR")
        conn.commit()

        payload = build_roster_payload(conn)
        card = next(p for p in payload["roster"] if p["id"] == "p_star")
        assert card["potential_ceiling"] == 90  # STAR floor
        assert card["headroom"] == 30

    def test_fresh_takeover_roster_is_not_all_bottom_tier(self):
        """The first roster a new player sees must not read as all-Raw."""
        conn = _make_conn()
        initialize_curated_manager_career(conn, "aurora", root_seed=ROOT_SEED)
        conn.commit()

        payload = build_roster_payload(conn)
        tiers = {p["potential_tier"] for p in payload["roster"]}
        assert tiers != {"Raw"}, "Entire fresh takeover roster reads as Raw potential"
        for p in payload["roster"]:
            assert p["potential_ceiling"] >= p["overall"]
