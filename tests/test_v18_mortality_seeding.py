"""V18 Task 3 gates: vet seeding + synthetic career history + honest mortality.

The BEFORE baseline (V18 sprint plan) measured ZERO league retirements for
eight straight seasons on every probed seed, then a season-9 cliff: curated
rosters seeded uniform ages 18-29 with no career history, and
``should_retire``'s age-34/36 gates require ``seasons_played`` >= 8-10 that a
seeded player cannot have before season 8 of the sim.

Task 3 contract (owner-approved 2026-06-10, Teamfight Manager 2 mix):
curated rosters seed a vet (31-33) / prime / rising / prodigy age texture,
seeded players carry a synthetic prior-career length consistent with their
age (``seasons_played_prior`` — retirement biology only; HoF, records, and
every display surface keep the RECORDED ``seasons_played``), and a vet
benched for the whole just-finalized season reads recent_eliminations=0
instead of a stale number from their last fielded season.
"""
from __future__ import annotations

import sqlite3
from dataclasses import replace

from dodgeball_sim.career_setup import (
    build_curated_roster,
    initialize_curated_manager_career,
)
from dodgeball_sim.development import should_retire
from dodgeball_sim.models import PlayerArchetype, PlayerRatings, PlayerTraits, Player
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_all_rosters,
    load_player_career_stats,
    save_player_career_stats,
    save_player_season_stats,
)
from dodgeball_sim.rng import derive_seed
from dodgeball_sim.stats import PlayerMatchStats

ROOT_SEED = 20260610


def _career_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", ROOT_SEED)
    conn.commit()
    return conn


class TestVetSeeding:
    def test_every_curated_club_seeds_the_age_mix(self):
        conn = _career_conn()
        rosters = load_all_rosters(conn)
        assert rosters, "curated league seeded no rosters"
        for club_id, roster in rosters.items():
            ages = sorted(player.age for player in roster)
            # Captain band is 30-34 (widened from 31-33 to spread the
            # retirement cohort across seasons instead of an S5 cliff).
            assert any(30 <= age <= 34 for age in ages), (
                f"{club_id}: no 30-34 veteran in seeded ages {ages}"
            )
            assert any(age <= 20 for age in ages), (
                f"{club_id}: no prodigy (<=20) in seeded ages {ages}"
            )
            assert any(22 <= age <= 29 for age in ages), (
                f"{club_id}: no prime/rising player in seeded ages {ages}"
            )

    def test_curated_roster_is_deterministic_with_age_bands(self):
        a = build_curated_roster("aurora", "Aurora", derive_seed(ROOT_SEED, "roster", "aurora"))
        b = build_curated_roster("aurora", "Aurora", derive_seed(ROOT_SEED, "roster", "aurora"))
        assert [(p.name, p.age, p.traits.potential) for p in a] == [
            (p.name, p.age, p.traits.potential) for p in b
        ]

    def test_seeded_vets_carry_prior_career_history(self):
        conn = _career_conn()
        rosters = load_all_rosters(conn)
        for roster in rosters.values():
            for player in roster:
                stats = load_player_career_stats(conn, player.id) or {}
                prior = int(stats.get("seasons_played_prior", 0))
                if player.age >= 31:
                    assert prior >= 8, (
                        f"{player.id} (age {player.age}) seeded prior={prior}; "
                        "the retirement gates need an age-consistent career length"
                    )
                # Recorded sim history stays empty at creation — priors must
                # not fabricate displayable careers.
                assert int(stats.get("seasons_played", 0)) == 0


class TestRetirementGatesWithPrior:
    def _vet(self, age: int, ovr: int = 60) -> Player:
        ratings = PlayerRatings(
            accuracy=ovr, power=ovr, dodge=ovr, catch=ovr, stamina=ovr,
            tactical_iq=ovr, catch_courage=ovr, throw_selection_iq=ovr,
            conditioning_curve=ovr,
        )
        return Player(
            id="vet", name="Vet", ratings=ratings,
            archetype=PlayerArchetype.THROWER,
            traits=PlayerTraits(potential=ovr, growth_curve=50, consistency=50, pressure=50),
            age=age, club_id="aurora", newcomer=False,
        )

    def test_benched_36yo_with_prior_history_retires(self):
        """The trap from the plan: recorded seasons alone (3) never trip the
        gate; the synthetic prior must count toward career length."""
        stats = {"seasons_played": 3, "seasons_played_prior": 11, "recent_eliminations": 0}
        assert should_retire(self._vet(36), stats) is True

    def test_same_vet_without_prior_does_not_retire_yet(self):
        stats = {"seasons_played": 3, "recent_eliminations": 0}
        assert should_retire(self._vet(36), stats) is False

    def test_performing_36yo_starter_keeps_playing(self):
        stats = {"seasons_played": 3, "seasons_played_prior": 11, "recent_eliminations": 9}
        assert should_retire(self._vet(36, ovr=66), stats) is False


class TestCareerSummaryHonesty:
    def test_prior_survives_summary_rewrite_and_benched_recent_is_zero(self):
        """_update_career_summaries recomputes from recorded rows; the seeded
        prior must ride along, and a player with no row in the season being
        finalized must read recent_eliminations=0, not their last fielded
        season's stale count."""
        from dodgeball_sim.offseason_ceremony import _update_career_summaries

        conn = _career_conn()
        rosters = load_all_rosters(conn)
        club_id = get_state(conn, "player_club_id")
        player = rosters[club_id][0]
        save_player_career_stats(
            conn, player.id,
            {
                "player_id": player.id, "player_name": player.name,
                "club_id": club_id, "seasons_played": 0,
                "seasons_played_prior": 12,
            },
        )
        # One real fielded season (season_1) with a big elimination count...
        save_player_season_stats(
            conn, "season_1",
            {player.id: PlayerMatchStats(eliminations_by_throw=14)},
            {player.id: club_id}, {player.id: 5}, frozenset(),
        )
        # ...then the player sits out all of season_2 (no row written).
        _update_career_summaries(conn, rosters, awards=(), season_id="season_2")
        summary = load_player_career_stats(conn, player.id)
        assert int(summary.get("seasons_played_prior", 0)) == 12
        assert int(summary.get("seasons_played", 0)) == 1  # recorded only
        assert int(summary.get("recent_eliminations", -1)) == 0, (
            "benched season must zero recent_eliminations, not reuse season_1's 14"
        )
        # Totals stay real: the recorded season's numbers are untouched.
        assert int(summary.get("total_eliminations", 0)) == 14

    def test_fielded_season_keeps_real_recent_count(self):
        from dodgeball_sim.offseason_ceremony import _update_career_summaries

        conn = _career_conn()
        rosters = load_all_rosters(conn)
        club_id = get_state(conn, "player_club_id")
        player = rosters[club_id][0]
        save_player_season_stats(
            conn, "season_1",
            {player.id: PlayerMatchStats(eliminations_by_throw=14)},
            {player.id: club_id}, {player.id: 5}, frozenset(),
        )
        _update_career_summaries(conn, rosters, awards=(), season_id="season_1")
        summary = load_player_career_stats(conn, player.id)
        assert int(summary.get("recent_eliminations", -1)) == 14
