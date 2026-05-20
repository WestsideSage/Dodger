import pytest

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.models import MatchSetup, Player, PlayerRatings, Team
from dodgeball_sim.official_adapter import OfficialEngineAdapter, OfficialMatchResult
from dodgeball_sim.persistence import connect, get_state
from dodgeball_sim.rulesets import RulesetSelection


def _team(prefix: str):
    players = tuple(
        Player(id=f"{prefix}{i}", name=f"{prefix}{i}",
               ratings=PlayerRatings(60, 60, 50, 50))
        for i in range(6)
    )
    return Team(id=prefix, name=prefix, players=players)


def test_ruleset_selection_enum_classification():
    assert RulesetSelection.GENERIC.is_official() is False
    assert RulesetSelection.OFFICIAL_FOAM.is_official()
    assert RulesetSelection.OFFICIAL_FOAM.to_profile().name == "foam-open"
    assert RulesetSelection.OFFICIAL_CLOTH.to_profile().name == "cloth-open"


def test_generic_selection_has_no_profile():
    with pytest.raises(ValueError):
        RulesetSelection.GENERIC.to_profile()


def test_official_adapter_rejects_generic_selection():
    with pytest.raises(ValueError):
        OfficialEngineAdapter(RulesetSelection.GENERIC)


def test_official_adapter_runs_match_and_returns_box_score():
    adapter = OfficialEngineAdapter(RulesetSelection.OFFICIAL_FOAM)
    setup = MatchSetup(team_a=_team("A"), team_b=_team("B"))
    result = adapter.run(setup, seed=42)
    assert isinstance(result, OfficialMatchResult)
    assert result.ruleset_selection == "official_foam"
    # Canonical shape uses teams keyed by id
    assert "A" in result.box_score["teams"]
    assert "B" in result.box_score["teams"]
    assert "totals" in result.box_score["teams"]["A"]


def test_official_adapter_run_generic_returns_match_result():
    from dodgeball_sim.engine import MatchResult
    adapter = OfficialEngineAdapter(RulesetSelection.OFFICIAL_FOAM)
    setup = MatchSetup(team_a=_team("A"), team_b=_team("B"))
    mr = adapter.run_generic(setup, seed=42)
    assert isinstance(mr, MatchResult)
    assert mr.events[0].event_type == "match_start"
    assert mr.events[-1].event_type == "match_end"
    assert mr.config_version.startswith("official:")
    assert mr.winner_team_id in {"A", "B", None}
    assert "teams" in mr.box_score


def test_official_adapter_deterministic_for_same_seed():
    adapter = OfficialEngineAdapter(RulesetSelection.OFFICIAL_FOAM)
    setup = MatchSetup(team_a=_team("A"), team_b=_team("B"))
    r1 = adapter.run(setup, seed=42)
    r2 = adapter.run(setup, seed=42)
    assert r1.winner_team_id == r2.winner_team_id
    assert r1.ticks == r2.ticks


def test_career_creation_default_has_no_ruleset_selection():
    conn = connect(":memory:")
    initialize_curated_manager_career(conn, "aurora", root_seed=1)
    assert get_state(conn, "ruleset_selection") is None


def test_career_creation_with_official_ruleset_persists_choice():
    conn = connect(":memory:")
    initialize_curated_manager_career(
        conn, "aurora", root_seed=1, ruleset_selection="official_foam",
    )
    assert get_state(conn, "ruleset_selection") == "official_foam"


def test_career_creation_rejects_unknown_ruleset_string():
    conn = connect(":memory:")
    with pytest.raises(ValueError):
        initialize_curated_manager_career(
            conn, "aurora", root_seed=1, ruleset_selection="not-a-real-ruleset",
        )
