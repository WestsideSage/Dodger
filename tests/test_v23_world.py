"""V23 Phase 1 gates — the 28-club pyramid world exists and is honest.

Pins, per docs/specs/2026-06-12-v23-the-world-spec.md:

1. Pyramid creation builds exactly 4 divisions × 7 clubs (28 total) on both
   creation paths, with the user club seated where the vision says: takeover
   in the Premier League, a founded club at the bottom of the District League.
2. The season schedule is four aligned intra-division round-robins — no
   cross-division fixture exists during the regular season.
3. Tier strength is real: Circuit > Premier > Challenger > District on
   seeded roster means.
4. The world is deterministic per seed.
5. The legacy world is untouched: a creation without ``world="pyramid"``
   produces the exact pre-V23 single-league save (no memberships, no flag).
"""
from __future__ import annotations

import sqlite3
from statistics import mean

from dodgeball_sim.career_setup import (
    build_expansion_club,
    generate_expansion_roster,
    initialize_curated_manager_career,
)
from dodgeball_sim.persistence import (
    get_state,
    load_all_rosters,
    load_clubs,
    load_division_map,
    load_division_memberships,
    load_season,
)
from dodgeball_sim.world import (
    DIVISION_SIZE,
    DIVISIONS,
    WORLD_MODEL_PYRAMID,
    WORLD_MODEL_STATE_KEY,
    pyramid_world_active,
)

ROOT_SEED = 20260612


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _new_takeover(conn: sqlite3.Connection, seed: int = ROOT_SEED) -> None:
    initialize_curated_manager_career(
        conn, "aurora", seed, ruleset_selection="official_foam", world="pyramid"
    )


def _new_founding(conn: sqlite3.Connection, seed: int = ROOT_SEED) -> str:
    club = build_expansion_club(
        name="Orphanage Athletic",
        primary_color="#101010",
        secondary_color="#FAFAFA",
        venue_name="The Yard",
        home_region="Eastside",
        tagline="Founded from nothing",
    )
    roster = generate_expansion_roster(club.club_id, seed)
    initialize_curated_manager_career(
        conn,
        club.club_id,
        seed,
        custom_club=club,
        custom_roster=roster,
        ruleset_selection="official_foam",
        world="pyramid",
    )
    return club.club_id


class TestPyramidCreation:
    def test_takeover_world_is_4x7_with_user_in_premier(self):
        conn = _conn()
        _new_takeover(conn)
        memberships = load_division_memberships(conn, "season_1")
        assert len(memberships) == 4 * DIVISION_SIZE == 28
        by_division: dict[str, list[str]] = {}
        for m in memberships:
            by_division.setdefault(m.division_id, []).append(m.club_id)
        assert set(by_division) == {d.division_id for d in DIVISIONS}
        for division_id, club_ids in by_division.items():
            assert len(club_ids) == DIVISION_SIZE, division_id
        assert "aurora" in by_division["premier"]
        # Takeover worlds field the full district cast including Eastreach.
        assert "eastreach" in by_division["district"]
        # Every membership club exists as a real persisted club with a roster.
        clubs = load_clubs(conn)
        rosters = load_all_rosters(conn)
        for m in memberships:
            assert m.club_id in clubs
            assert len(rosters[m.club_id]) == 6
        assert pyramid_world_active(conn)
        assert get_state(conn, WORLD_MODEL_STATE_KEY) == WORLD_MODEL_PYRAMID

    def test_founding_world_seats_user_at_the_bottom_of_d3(self):
        conn = _conn()
        user_club_id = _new_founding(conn)
        division_map = load_division_map(conn, "season_1")
        assert len(division_map) == 28
        user_seat = division_map[user_club_id]
        assert user_seat.division_id == "district"
        assert user_seat.tier == 3
        # The founded club takes the seventh district seat — Eastreach sits out.
        assert "eastreach" not in division_map
        per_division: dict[str, int] = {}
        for m in division_map.values():
            per_division[m.division_id] = per_division.get(m.division_id, 0) + 1
        assert per_division == {
            "premier": 7, "challenger": 7, "district": 7, "circuit": 7,
        }


class TestPyramidSchedule:
    def test_all_fixtures_are_intra_division_and_weeks_align(self):
        conn = _conn()
        _new_takeover(conn)
        season = load_season(conn, "season_1")
        division_map = load_division_map(conn, "season_1")
        assert season.total_weeks() == 7  # 7-club round robin with byes
        appearances: dict[str, int] = {}
        for match in season.scheduled_matches:
            home = division_map[match.home_club_id]
            away = division_map[match.away_club_id]
            assert home.division_id == away.division_id, match.match_id
            appearances[match.home_club_id] = appearances.get(match.home_club_id, 0) + 1
            appearances[match.away_club_id] = appearances.get(match.away_club_id, 0) + 1
        # Full single round robin: every one of the 28 clubs plays 6 matches.
        assert set(appearances) == set(division_map)
        assert set(appearances.values()) == {6}
        # 4 divisions × C(7,2) fixtures.
        assert len(season.scheduled_matches) == 4 * 21

    def test_user_club_always_plays_week_one(self):
        # A new season must never open on "your bye week" — the user's
        # division rotates its round labels so the climb starts immediately.
        for build in (_new_takeover, _new_founding):
            conn = _conn()
            result = build(conn)
            user_club_id = result if isinstance(result, str) else "aurora"
            season = load_season(conn, "season_1")
            week_one_clubs = {
                club
                for match in season.matches_for_week(1)
                for club in (match.home_club_id, match.away_club_id)
            }
            assert user_club_id in week_one_clubs

    def test_world_is_deterministic_per_seed(self):
        conn_a, conn_b = _conn(), _conn()
        _new_takeover(conn_a)
        _new_takeover(conn_b)
        season_a = load_season(conn_a, "season_1")
        season_b = load_season(conn_b, "season_1")
        assert [m.match_id for m in season_a.scheduled_matches] == [
            m.match_id for m in season_b.scheduled_matches
        ]
        rosters_a = load_all_rosters(conn_a)
        rosters_b = load_all_rosters(conn_b)
        assert {
            cid: [(p.id, p.name, p.overall_skill()) for p in roster]
            for cid, roster in rosters_a.items()
        } == {
            cid: [(p.id, p.name, p.overall_skill()) for p in roster]
            for cid, roster in rosters_b.items()
        }


class TestTierStrength:
    def test_division_strength_orders_circuit_premier_challenger_district(self):
        conn = _conn()
        _new_takeover(conn)
        division_map = load_division_map(conn, "season_1")
        rosters = load_all_rosters(conn)
        division_means = {
            division_id: mean(
                player.overall_skill()
                for m in division_map.values()
                if m.division_id == division_id
                for player in rosters[m.club_id]
            )
            for division_id in ("circuit", "premier", "challenger", "district")
        }
        assert (
            division_means["circuit"]
            > division_means["premier"]
            > division_means["challenger"]
            > division_means["district"]
        ), division_means


class TestLegacyWorldUntouched:
    def test_default_creation_remains_the_classic_single_league(self):
        conn = _conn()
        initialize_curated_manager_career(
            conn, "aurora", ROOT_SEED, ruleset_selection="official_foam"
        )
        assert load_division_memberships(conn, "season_1") == []
        assert not pyramid_world_active(conn)
        clubs = load_clubs(conn)
        assert len(clubs) == 6  # the curated cast only
        season = load_season(conn, "season_1")
        assert season.league_id == "manager_league"
