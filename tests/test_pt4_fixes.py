"""Playtest 4 trust-fix gates (PLAYTEST_JOURNAL_4.md findings).

Pins:
- PT4-02: on a bye week the career cursor sits ON the bye week — the header
  and the bye body can never disagree about the current week again.
- PT4-05: the week's scout/contact/visit work reaches the Prospect Pulse
  (recruit_reactions derive from the week-stamped action log; "no movement"
  only when no action was taken).
- PT4-07: signing cards carry display archetypes, never raw enum keys.
"""
from __future__ import annotations

import sqlite3

from dodgeball_sim.career_setup import (
    build_expansion_club,
    generate_expansion_roster,
    initialize_curated_manager_career,
)
from dodgeball_sim.persistence import load_career_state_cursor, load_season
from dodgeball_sim.recruiting_office import (
    apply_recruiting_action,
    recruit_reactions_for_week,
)
from dodgeball_sim.use_cases import simulate_week

ROOT_SEED = 20260613


def _founding_save() -> tuple[sqlite3.Connection, str]:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    club = build_expansion_club(
        name="PT4 Gate Club",
        primary_color="#111111",
        secondary_color="#EEEEEE",
        venue_name="Gate Hall",
        home_region="Gateview",
        tagline="gate",
    )
    roster = generate_expansion_roster(club.club_id, ROOT_SEED)
    initialize_curated_manager_career(
        conn,
        club.club_id,
        ROOT_SEED,
        custom_club=club,
        custom_roster=roster,
        ruleset_selection="official_foam",
        world="pyramid",
    )
    return conn, club.club_id


class TestByeWeekCursorTruth:
    def test_cursor_lands_on_the_bye_week_not_past_it(self):
        conn, club_id = _founding_save()
        season = load_season(conn, "season_1")
        user_weeks = {
            m.week
            for m in season.scheduled_matches
            if club_id in (m.home_club_id, m.away_club_id) and "_p_" not in m.match_id
        }
        bye_week = next(w for w in range(1, 8) if w not in user_weeks)
        assert bye_week > 1  # the week-1 rotation guarantees an opening match

        for _ in range(7):
            cursor = load_career_state_cursor(conn)
            if cursor.state.value != "season_active_pre_match":
                break
            pre_sim_week = cursor.week
            result = simulate_week(conn, update=None)
            dashboard = result.get("dashboard") or {}
            # The week the player was parked on must be the week the sim
            # serves — including the bye (the cursor used to skip to the
            # next MATCH week while the body served the bye).
            assert dashboard.get("week") == pre_sim_week, (
                pre_sim_week,
                dashboard.get("week"),
                dashboard.get("opponent_name"),
            )
            if dashboard.get("opponent_name") == "Bye Week":
                assert pre_sim_week == bye_week
                return
        raise AssertionError("season ended without serving the bye week")


class TestProspectPulseTruth:
    def test_week_actions_surface_as_recruit_reactions(self):
        conn, club_id = _founding_save()
        cursor = load_career_state_cursor(conn)
        week = int(cursor.week or 1)

        from dodgeball_sim.persistence import load_prospect_pool

        pool = load_prospect_pool(conn, 1)
        assert pool, "founding save has no class-1 prospect pool"
        target = pool[0]

        apply_recruiting_action(
            conn,
            prospect_id=target.player_id,
            action="contact",
            season_id="season_1",
            player_club_id=club_id,
            root_seed=ROOT_SEED,
            history=[],
        )
        apply_recruiting_action(
            conn,
            prospect_id=target.player_id,
            action="visit",
            season_id="season_1",
            player_club_id=club_id,
            root_seed=ROOT_SEED,
            history=[],
        )

        reactions = recruit_reactions_for_week(conn, "season_1", week)
        assert len(reactions) == 1
        reaction = reactions[0]
        assert reaction["prospect_name"] == target.name
        delta = int(reaction["interest_delta"].rstrip("%"))
        assert delta > 0  # contact + visit both raise interest
        assert "interest" in reaction["evidence"]
        # Other weeks stay honestly empty.
        assert recruit_reactions_for_week(conn, "season_1", week + 1) == []

    def test_scout_only_week_reports_the_band_not_phantom_interest(self):
        conn, club_id = _founding_save()
        cursor = load_career_state_cursor(conn)
        week = int(cursor.week or 1)

        from dodgeball_sim.persistence import load_prospect_pool

        target = load_prospect_pool(conn, 1)[1]
        apply_recruiting_action(
            conn,
            prospect_id=target.player_id,
            action="scout",
            season_id="season_1",
            player_club_id=club_id,
            root_seed=ROOT_SEED,
            history=[],
        )
        reactions = recruit_reactions_for_week(conn, "season_1", week)
        assert len(reactions) == 1
        assert reactions[0]["interest_delta"] == "+0%"
        assert "Scout" in reactions[0]["evidence"]


class TestGrowthPacingCap:
    def test_one_season_never_teleports_a_founder_to_his_ceiling(self):
        """V23 balance: the +40 single-season jump is dead.

        A founding-class player (huge natural headroom + GENERATIONAL arc +
        full reps + practice credit) gains at most the pacing cap per
        offseason — elite arcs sustain the cap for years instead of
        teleporting (climb_resistance_probe BEFORE: +40, Worlds by S4 on
        auto-pilot; AFTER: ≤ +10 with promotion contention from S3).
        """
        from dodgeball_sim.archetype_derivation import derive_archetype
        from dodgeball_sim.development import (
            _MAX_SEASON_GROWTH_OVR,
            apply_season_development,
        )
        from dodgeball_sim.models import Player, PlayerRatings, PlayerTraits
        from dodgeball_sim.rng import DeterministicRNG
        from dodgeball_sim.stats import PlayerMatchStats

        ratings = PlayerRatings(
            accuracy=50, power=52, dodge=48, catch=51, stamina=50,
            tactical_iq=50, catch_courage=50, throw_selection_iq=50,
            conditioning_curve=50,
        ).apply_bounds()
        founder = Player(
            id="cap_probe", name="Cap Probe", age=19, club_id="probe",
            newcomer=True, ratings=ratings, archetype=derive_archetype(ratings),
            traits=PlayerTraits(potential=96, growth_curve=50, consistency=0.5, pressure=0.5),
        )
        before = founder.overall_skill()
        developed = apply_season_development(
            founder,
            PlayerMatchStats(),
            facilities=(),
            rng=DeterministicRNG(4242),
            trajectory="GENERATIONAL",
            matches_played=10,
            club_matches=10,
            practice_credit_ovr=1.6,
            staff_development_modifier=0.4,
        )
        gained = developed.overall_skill() - before
        # +1 tolerance for per-stat integer rounding on the 5-skill mean.
        assert gained <= _MAX_SEASON_GROWTH_OVR + 1.0, gained
        assert gained >= 6.0, f"the cap must pace growth, not kill it ({gained})"


class TestSigningCardRoleDisplay:
    def test_role_is_a_display_name_not_an_enum_key(self):
        from dodgeball_sim.models import PlayerArchetype
        from dodgeball_sim.signing_day_payload import build_signing_cards

        class _Signing:
            player_id = "p1"
            club_id = "aurora"
            round_number = 1
            source = "ai"

        class _Player:
            id = "p1"
            name = "Test Player"
            archetype = PlayerArchetype.DODGER_ANCHOR

            def overall_skill(self):
                return 70

        class _Club:
            name = "Aurora Sentinels"

        cards = build_signing_cards(
            signings=[_Signing()],
            rosters={"aurora": [_Player()]},
            prospects_by_id={},
            clubs={"aurora": _Club()},
            player_club_id="user_club",
            actions_by_player={},
            user_bid_player_ids=set(),
        )
        assert cards, "no card built"
        role = cards[0]["role"]
        assert "_" not in role, f"raw enum key leaked: {role!r}"
        assert role == PlayerArchetype.DODGER_ANCHOR.display_name
