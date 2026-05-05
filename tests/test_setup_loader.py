from __future__ import annotations

import json
from pathlib import Path

from dodgeball_sim.persistence import match_setup_to_dict
from dodgeball_sim.setup_loader import (
    describe_matchup,
    format_matchup_summary,
    format_team_summary,
    load_match_setup_from_path,
    match_setup_from_dict,
    summarize_matchup,
    summarize_team,
)

from .factories import make_match_setup, make_player, make_team


def test_match_setup_roundtrip():
    team_a = make_team("alpha", [make_player("a1", accuracy=72)])
    team_b = make_team("beta", [make_player("b1", dodge=65)])
    original = make_match_setup(team_a, team_b)
    payload = match_setup_to_dict(original)
    loaded = match_setup_from_dict(payload)
    assert loaded.team_a.name == original.team_a.name
    assert loaded.team_b.players[0].ratings.accuracy == original.team_b.players[0].ratings.accuracy


def test_load_setup_from_path():
    team_a = make_team("alpha", [make_player("a1", accuracy=72)])
    team_b = make_team("beta", [make_player("b1", dodge=65)])
    setup = make_match_setup(team_a, team_b)
    payload = match_setup_to_dict(setup)
    path = Path("output") / "test_setup_loader_setup.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    loaded = load_match_setup_from_path(path)
    assert loaded.team_a.id == "alpha"
    assert loaded.team_b.id == "beta"
    desc = describe_matchup(loaded).lower()
    assert "alpha" in desc and "beta" in desc



def test_format_matchup_summary_includes_player_lines():
    team_a = make_team(
        "alpha",
        [
            make_player("a1", accuracy=80, power=70, dodge=65, catch=60),
            make_player("a2", accuracy=70, power=62, dodge=58, catch=55),
        ],
    )
    team_b = make_team(
        "beta",
        [
            make_player("b1", accuracy=60, power=65, dodge=55, catch=50),
            make_player("b2", accuracy=55, power=58, dodge=52, catch=53),
        ],
    )
    setup = make_match_setup(team_a, team_b)
    summary_text = format_matchup_summary(setup)
    assert "alpha" in summary_text.lower()
    assert "beta" in summary_text.lower()
    summarized = summarize_matchup(setup)
    assert summarized["team_a"]["average_ratings"]["accuracy"] > 0
    formatted = format_team_summary(team_a)
    assert "ACC=" in formatted
