from __future__ import annotations

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.models import MatchSetup, Player, PlayerArchetype, PlayerRatings, Team
from dodgeball_sim.persistence import connect, get_state, load_club_roster, load_clubs, load_season
from dodgeball_sim.replay_service import match_replay_payload


def _team(prefix: str) -> Team:
    players = tuple(
        Player(
            id=f"{prefix}{index}",
            name=f"{prefix}{index}",
            club_id=prefix,
            archetype=PlayerArchetype.CATCHER,
            ratings=PlayerRatings(
                accuracy=60,
                power=60,
                dodge=55,
                catch=55,
                stamina=60,
                tactical_iq=55,
                catch_courage=55,
                throw_selection_iq=55,
                conditioning_curve=55,
            ),
        )
        for index in range(6)
    )
    return Team(id=prefix, name=prefix, players=players)


def test_rec_adapter_run_generic_returns_match_result_with_moment_events():
    from dodgeball_sim.engine import MatchResult
    from dodgeball_sim.rec_adapter import RecEngineAdapter

    adapter = RecEngineAdapter()
    setup = MatchSetup(team_a=_team("A"), team_b=_team("B"))
    result = adapter.run_generic(setup, seed=7, match_id="rec-1")

    assert isinstance(result, MatchResult)
    assert result.events[0].event_type == "match_start"
    assert result.events[-1].event_type == "match_end"
    assert "moment_events" in result.events[-1].context
    assert result.winner_team_id in {"A", "B", None}
    assert "teams" in result.box_score


def test_default_career_replay_payload_exposes_tier1_moment_events():
    from dodgeball_sim.game_loop import simulate_scheduled_match

    conn = connect(":memory:")
    initialize_curated_manager_career(conn, "aurora", root_seed=42)
    season = load_season(conn, get_state(conn, "active_season_id"))
    clubs = load_clubs(conn)
    scheduled = season.matches_for_week(1)[0]
    rosters = {club_id: load_club_roster(conn, club_id) for club_id in clubs}

    record = simulate_scheduled_match(
        conn,
        scheduled=scheduled,
        clubs=clubs,
        rosters=rosters,
        root_seed=42,
        difficulty="pro",
        record_engine_match=True,
    )
    payload = match_replay_payload(conn, record.match_id)

    assert payload["config_version"] == "phase1.v1"
    assert "moment_events" in payload
    assert isinstance(payload["moment_events"], list)
    if payload["moment_events"]:
        assert {"kind", "tick"} <= set(payload["moment_events"][0])
