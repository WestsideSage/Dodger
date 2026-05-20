from dodgeball_sim.models import CoachPolicy, Player, PlayerRatings
from dodgeball_sim.official_events import OfficialEventKind
from dodgeball_sim.official_engine import run_autonomous_game
from dodgeball_sim.official_stats import derive_box_score
from dodgeball_sim.rulesets import CLOTH_OPEN, FOAM_OPEN


def _make_team(prefix: str, count: int = 6):
    return {
        f"{prefix}{i}": Player(
            id=f"{prefix}{i}", name=f"{prefix}{i}",
            ratings=PlayerRatings(
                accuracy=55 + i, power=55 + i, dodge=50, catch=50,
            ),
        ) for i in range(count)
    }


def test_autonomous_foam_game_runs_to_completion():
    a = _make_team("a")
    b = _make_team("b")
    lookup = {**a, **b}
    result = run_autonomous_game(
        profile=FOAM_OPEN, match_id="m1",
        team_a_id="A", team_b_id="B",
        starters_a=tuple(a.keys()), starters_b=tuple(b.keys()),
        player_lookup=lookup,
        policy_a=CoachPolicy(), policy_b=CoachPolicy(),
        seed=42,
    )
    # One side eliminated or max ticks reached
    assert result.ticks > 0
    assert result.final_active_a >= 0
    assert result.final_active_b >= 0
    # At least some sequence events emitted
    assert len(result.events) >= 1


def test_autonomous_game_deterministic_for_same_seed():
    a = _make_team("a")
    b = _make_team("b")
    lookup = {**a, **b}
    r1 = run_autonomous_game(
        profile=FOAM_OPEN, match_id="m1",
        team_a_id="A", team_b_id="B",
        starters_a=tuple(a.keys()), starters_b=tuple(b.keys()),
        player_lookup=lookup,
        policy_a=CoachPolicy(), policy_b=CoachPolicy(),
        seed=12345,
    )
    r2 = run_autonomous_game(
        profile=FOAM_OPEN, match_id="m1",
        team_a_id="A", team_b_id="B",
        starters_a=tuple(a.keys()), starters_b=tuple(b.keys()),
        player_lookup=lookup,
        policy_a=CoachPolicy(), policy_b=CoachPolicy(),
        seed=12345,
    )
    assert r1.winner_team_id == r2.winner_team_id
    assert r1.ticks == r2.ticks
    assert len(r1.events) == len(r2.events)


def test_autonomous_game_higher_ratings_wins_more_often():
    weak = {f"w{i}": Player(
        id=f"w{i}", name=f"w{i}",
        ratings=PlayerRatings(accuracy=20, power=20, dodge=20, catch=20),
    ) for i in range(6)}
    strong = {f"s{i}": Player(
        id=f"s{i}", name=f"s{i}",
        ratings=PlayerRatings(accuracy=90, power=90, dodge=90, catch=90),
    ) for i in range(6)}
    lookup = {**weak, **strong}

    strong_wins = 0
    trials = 20
    for seed in range(trials):
        r = run_autonomous_game(
            profile=FOAM_OPEN, match_id="m1",
            team_a_id="WEAK", team_b_id="STRONG",
            starters_a=tuple(weak.keys()), starters_b=tuple(strong.keys()),
            player_lookup=lookup,
            policy_a=CoachPolicy(), policy_b=CoachPolicy(),
            seed=seed,
        )
        if r.winner_team_id == "STRONG":
            strong_wins += 1
    # Strong should dominate -- generous bar to avoid flakiness, but the
    # ratings gap is huge so anything below 70% is a real signal.
    assert strong_wins >= trials * 0.7


def test_autonomous_game_box_score_derives_cleanly():
    a = _make_team("a")
    b = _make_team("b")
    lookup = {**a, **b}
    team_map = {**{pid: "A" for pid in a}, **{pid: "B" for pid in b}}
    result = run_autonomous_game(
        profile=FOAM_OPEN, match_id="m1",
        team_a_id="A", team_b_id="B",
        starters_a=tuple(a.keys()), starters_b=tuple(b.keys()),
        player_lookup=lookup,
        policy_a=CoachPolicy(), policy_b=CoachPolicy(),
        seed=7,
    )
    box = derive_box_score(
        result.events, team_a_id="A", team_b_id="B",
        player_team_map=team_map,
    )
    assert "A" in box["teams"]
    assert "B" in box["teams"]
    assert (
        box["teams"]["A"]["totals"]["outs_recorded"]
        + box["teams"]["B"]["totals"]["outs_recorded"]
    ) > 0


def test_autonomous_cloth_game_also_runs():
    a = _make_team("a")
    b = _make_team("b")
    lookup = {**a, **b}
    result = run_autonomous_game(
        profile=CLOTH_OPEN, match_id="m1",
        team_a_id="A", team_b_id="B",
        starters_a=tuple(a.keys()), starters_b=tuple(b.keys()),
        player_lookup=lookup,
        policy_a=CoachPolicy(), policy_b=CoachPolicy(),
        seed=3,
    )
    assert result.ticks > 0


def test_autonomous_game_exposes_official_replay_state():
    a = _make_team("a")
    b = _make_team("b")
    lookup = {**a, **b}
    result = run_autonomous_game(
        profile=FOAM_OPEN,
        match_id="m2",
        team_a_id="A",
        team_b_id="B",
        starters_a=tuple(a.keys()),
        starters_b=tuple(b.keys()),
        player_lookup=lookup,
        policy_a=CoachPolicy(),
        policy_b=CoachPolicy(),
        seed=9,
    )
    assert result.replay_state.ruleset == FOAM_OPEN.name
    assert result.replay_state.game_clock is not None
    assert result.replay_state.balls
    assert result.replay_state.teams
    assert result.replay_state.rule_calls
    assert any(event.kind == OfficialEventKind.BURDEN for event in result.events)
