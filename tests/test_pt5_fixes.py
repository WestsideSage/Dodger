"""Playtest 5 fixes — regression guards for the trust-breaks Codex's PT5 audit
found (PLAYTEST_JOURNAL_5.md). Each test reproduces a journal symptom and was
RED before its fix.

This file collects the PT5 regressions; some also extend the relevant
per-feature suites. See docs / the PT5 findings memory for the root causes.
"""
from __future__ import annotations

import sqlite3

import pytest


# ---------------------------------------------------------------------------
# P0 — falsifying final score (V20 survivors-vs-game-points family)
# ---------------------------------------------------------------------------


class _Club:
    def __init__(self, club_id, name):
        self.club_id = club_id
        self.name = name


def _row(**kwargs):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cols = ", ".join(f"? AS {k}" for k in kwargs)
    return conn.execute(f"SELECT {cols}", tuple(kwargs.values())).fetchone()


class TestLeagueWireScore:
    def test_official_wire_uses_game_points_not_survivors(self):
        """Surface B: an official (foam) match's League Wire item must read game
        points, never the 0-0 survivors of the final game."""
        from dodgeball_sim.view_models import build_wire_items

        row = _row(
            match_id="season_1_w1_m1", season_id="season_1", week=1,
            home_club_id="aurora", away_club_id="lunar", winner_club_id="aurora",
            home_survivors=0, away_survivors=0,
            scoring_model="foam", home_game_points=12, away_game_points=2,
        )
        clubs = {"aurora": _Club("aurora", "Aurora"), "lunar": _Club("lunar", "Lunar")}
        items = build_wire_items([row], clubs)
        result = next(i for i in items if i.match_id == "season_1_w1_m1")
        assert "12-2 on game points" in result.text
        assert "survivors" not in result.text


# ---------------------------------------------------------------------------
# P0 + V28 follow-up — the standings ticker's wire_headlines must carry only the
# NEWS headlines (class/event/meta/league_bulletin), NOT the match-result rows
# (recent_matches already shows those — folding build_news_payload["items"]
# wholesale duplicated them and surfaced the survivors bug).
# ---------------------------------------------------------------------------


def _pyramid_conn():
    from dodgeball_sim.career_setup import initialize_curated_manager_career
    from dodgeball_sim.persistence import create_schema

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", 20260619, ruleset_selection="official_foam", world="pyramid"
    )
    conn.commit()
    return conn


class TestStandingsWireHeadlines:
    def test_wire_headlines_are_headlines_only_not_match_rows(self):
        from dodgeball_sim.persistence import get_state, save_match_result, save_news_headlines
        from dodgeball_sim.web_status_service import build_standings_payload

        conn = _pyramid_conn()
        sid = get_state(conn, "active_season_id")
        # A persisted official match (a RESULT row the recent-results strip owns).
        save_match_result(
            conn, match_id=f"{sid}_w1_m1", season_id=sid, week=1,
            home_club_id="aurora", away_club_id="ridgeline", winner_club_id="aurora",
            home_survivors=0, away_survivors=0, home_roster_hash="h", away_roster_hash="a",
            config_version="official:official_foam", ruleset_version="v1", seed=1,
            event_log_hash="e", final_state_hash="f", scoring_model="foam",
            home_game_points=12, away_game_points=2,
        )
        # A news bulletin (a headline the ticker SHOULD surface).
        save_news_headlines(conn, sid, 0, [{
            "headline_id": f"meta_x_{sid}", "category": "meta_report",
            "headline_text": "META WIRE LINE", "entity_ids": [],
        }])
        conn.commit()
        payload = build_standings_payload(conn)
        wire = payload["wire_headlines"]
        texts = [w["text"] for w in wire]
        assert "META WIRE LINE" in texts, "news bulletin missing from wire_headlines"
        # No match-RESULT rows: those belong to recent_matches, not wire_headlines.
        assert all(w.get("tag") != "RESULT" for w in wire), (
            "wire_headlines leaked match-result rows (duplicate of recent_matches)"
        )
        assert not any("survivors" in w["text"] for w in wire)


class TestMatchCardHeroScore:
    """Surface A: the debrief hero must show the real game-point total, not 0-0,
    even when a reloaded official_metadata carries `games` but omits the totals."""

    def test_totals_derived_from_games_when_metadata_omits_them(self):
        from dodgeball_sim.use_cases import _official_card_score

        games = (
            [{"game_number": i + 1, "winner_team_id": "tacoma",
              "team_a_points": 1, "team_b_points": 0, "result_type": "win"} for i in range(12)]
            + [{"game_number": 13, "winner_team_id": "riverton",
                "team_a_points": 0, "team_b_points": 1, "result_type": "loss"},
               {"game_number": 14, "winner_team_id": "riverton",
                "team_a_points": 0, "team_b_points": 1, "result_type": "loss"}]
        )
        meta = {"team_a_id": "tacoma", "games": games}  # totals ABSENT (reload)
        sm, home, away, card_games = _official_card_score(meta, "official:official_foam", "tacoma")
        assert sm == "foam"
        assert (home, away) == (12, 2), "hero totals must derive from the per-game story, not 0-0"
        assert len(card_games) == 14

    def test_totals_guarded_by_team_a_id_when_team_a_is_away(self):
        from dodgeball_sim.use_cases import _official_card_score

        # team_a is the AWAY club; home must get team_b's points (guarded mapping).
        meta = {"team_a_id": "riverton", "team_a_game_points": 2, "team_b_game_points": 12, "games": []}
        _sm, home, away, _games = _official_card_score(meta, "official:official_foam", "tacoma")
        assert (home, away) == (12, 2), "unguarded team_a->home swaps the scoreboard"


class TestScoutingNetworkBoardCount:
    def test_paid_upgrade_never_shrinks_the_board(self):
        """PT5: a paid Scouting Network upgrade must never show FEWER recruit-board
        rows (the founder/custom-home path dropped 30->26 as the teaser tail
        shrank under the 25-visible cap). Total must be non-decreasing in level."""
        from dodgeball_sim.career_setup import (
            build_expansion_club, generate_expansion_roster, initialize_curated_manager_career,
        )
        from dodgeball_sim.economy import set_treasury_k
        from dodgeball_sim.persistence import create_schema, get_state
        from dodgeball_sim.recruiting_office import (
            build_recruiting_state, network_level, upgrade_scouting_network,
        )

        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        # home_region "Eastside" is NOT a district => home_recognized=False, the
        # founder path the playtester hit (the curated D3 club instead RISES).
        club = build_expansion_club(
            name="Founders FC", primary_color="#101010", secondary_color="#FAFAFA",
            venue_name="The Yard", home_region="Eastside", tagline="x",
        )
        roster = generate_expansion_roster(club.club_id, 3)
        initialize_curated_manager_career(
            conn, club.club_id, 3, custom_club=club, custom_roster=roster,
            ruleset_selection="official_foam", world="pyramid",
        )
        conn.commit()
        sid = get_state(conn, "active_season_id")
        set_treasury_k(conn, 10_000)  # afford both upgrades

        def count():
            return len(build_recruiting_state(
                conn, season_id=sid, player_club_id=club.club_id, root_seed=3, history=[]
            )["prospects"])

        assert network_level(conn) == 1
        l1 = count()
        upgrade_scouting_network(conn)
        l2 = count()
        upgrade_scouting_network(conn)
        l3 = count()
        assert l2 >= l1 and l3 >= l2, f"paid upgrade shrank the board: L1={l1} L2={l2} L3={l3}"


class TestSigningReceiptOffers:
    """PT5: the snipe receipt 'their offer 106 beat yours 106' was self-
    contradictory — integer rounding collapsed two distinct 4-decimal offers."""

    def test_offer_pair_reveals_a_sub_unit_gap(self):
        from dodgeball_sim.offseason_ceremony import _format_offer_pair

        hi, lo = _format_offer_pair(106.51, 106.48)  # both bare round() to 106
        assert hi != lo, "rounding collapsed distinct offers to one number"
        assert float(hi) >= float(lo)

    def test_offer_pair_keeps_integers_when_clean(self):
        from dodgeball_sim.offseason_ceremony import _format_offer_pair

        assert _format_offer_pair(110.0, 104.0) == ("110", "104")

    def test_offer_pair_guards_bankers_rounding_inversion(self):
        from dodgeball_sim.offseason_ceremony import _format_offer_pair

        # round(106.5)->106 and round(105.5)->106 (round-half-to-even): must not
        # display the winner <= the loser.
        hi, lo = _format_offer_pair(106.5, 105.5)
        assert hi != lo and float(hi) >= float(lo)


class TestWorldsRecapUserRun:
    """PT6: a club that REACHED Worlds (Premier/Circuit champion or runner-up)
    but lost the SEMIFINAL was never receipted — the recap printed only the
    Worlds final (two other clubs). worlds_user surfaces the user's own run."""

    def test_premier_champion_who_lost_the_semi_is_receipted(self):
        import json

        from dodgeball_sim.offseason_presentation import _pyramid_movement_block
        from dodgeball_sim.persistence import get_state, load_clubs, set_state
        from dodgeball_sim.pyramid_postseason import postseason_ledger_key

        conn = _pyramid_conn()  # takeover: aurora is a Premier club
        sid = get_state(conn, "active_season_id")
        # Aurora wins the Premier title (a Worlds seed) but the Worlds FINAL is
        # contested by two Circuit clubs — i.e. Aurora lost its Worlds semifinal.
        ledger = {
            "season_id": sid, "complete": True,
            "champions": {"premier": "aurora", "circuit": "osaka"},
            "runners_up": {"premier": "ridgeline", "circuit": "bahia"},
            "promoted": {}, "relegated": {},
            "worlds": {
                "champion_club_id": "osaka", "champion_name": "Osaka",
                "runner_up_club_id": "bahia", "runner_up_name": "Bahia",
                "final_match_id": f"{sid}_p_worlds_final",
            },
        }
        set_state(conn, postseason_ledger_key(sid), json.dumps(ledger))
        conn.commit()
        clubs = load_clubs(conn)
        block = _pyramid_movement_block(
            conn, sid, "aurora", lambda cid: clubs[cid].name if cid in clubs else cid
        )
        assert block is not None
        assert block["worlds_user"] == {
            "qualified_as": "premier_champion", "result": "semifinalist",
        }

    def test_non_qualifier_has_no_worlds_user(self):
        import json

        from dodgeball_sim.offseason_presentation import _pyramid_movement_block
        from dodgeball_sim.persistence import get_state, load_clubs, set_state
        from dodgeball_sim.pyramid_postseason import postseason_ledger_key

        conn = _pyramid_conn()
        sid = get_state(conn, "active_season_id")
        ledger = {
            "season_id": sid, "complete": True,
            "champions": {"premier": "ridgeline", "circuit": "osaka"},
            "runners_up": {"premier": "solstice", "circuit": "bahia"},
            "promoted": {}, "relegated": {},
            "worlds": {"champion_club_id": "osaka", "champion_name": "Osaka",
                       "runner_up_club_id": "ridgeline", "runner_up_name": "Ridgeline",
                       "final_match_id": f"{sid}_p_worlds_final"},
        }
        set_state(conn, postseason_ledger_key(sid), json.dumps(ledger))
        conn.commit()
        clubs = load_clubs(conn)
        block = _pyramid_movement_block(
            conn, sid, "aurora", lambda cid: clubs[cid].name if cid in clubs else cid
        )
        assert block is not None and block["worlds_user"] is None


class TestPremierStakesCopy:
    """PT5: the Premier stakes related the Top-4 playoff cut and the Top-2 Worlds
    berth as two unrelated facts ('Top two reach WORLDS' beside a 'Top 4' cut).
    The fix relates them — accurately (Worlds is vs the International Circuit, not
    'every region')."""

    def test_premier_summary_relates_playoffs_and_worlds(self):
        from dodgeball_sim.web_status_service import _division_movement_rules

        summary = _division_movement_rules("premier")["summary"].lower()
        assert "playoff" in summary and "worlds" in summary
        assert "international circuit" in summary
        assert "every region" not in summary
        # PT6: Worlds entrants are the two PLAYOFF finalists, not the standings
        # top two — the copy must not imply a standings berth.
        assert "finalist" in summary


class TestLauncherPort:
    """PT5 setup: `--port 8010` was ignored (the launcher took no args and always
    started from 8000, killing the owner's same-repo game)."""

    def test_parse_args_honors_port(self):
        from dodgeball_sim.web_cli import _parse_args

        args = _parse_args(["--port", "8010"])
        assert args.port == 8010 and args.no_browser is False

    def test_parse_args_defaults(self):
        from dodgeball_sim.web_cli import _parse_args

        args = _parse_args([])
        assert args.port is None and args.no_browser is False

    def test_explicit_port_is_honored_verbatim(self):
        from dodgeball_sim.web_cli import _choose_launch_ports

        # No auto-increment: the caller asked for 8010, gets 8010.
        assert _choose_launch_ports(dev_mode=False, explicit_port=8010).backend == 8010
