import random

from dodgeball_sim.models import CoachPolicy, Player, PlayerRatings
from dodgeball_sim.official_resolution import (
    compute_throw_probabilities,
    resolve_throw,
)
from dodgeball_sim.official_stats import derive_box_score
from dodgeball_sim.official_tactics import (
    decide_catch_attempt,
    proactive_action_weights,
    select_target,
    select_thrower,
)
from dodgeball_sim.player_state import OfficialPlayerState, OfficialPlayerStatus
from dodgeball_sim.rulesets import BallMaterial
from dodgeball_sim.sequence import SequenceOfPlay, resolve_sequence


def _p(pid, accuracy=60, power=60, dodge=50, catch=50):
    return Player(
        id=pid, name=pid,
        ratings=PlayerRatings(
            accuracy=accuracy, power=power, dodge=dodge, catch=catch
        ),
    )


def _active(pid, team):
    return OfficialPlayerState(
        player_id=pid, team_id=team, status=OfficialPlayerStatus.ACTIVE, is_starter=True,
    )


def test_select_thrower_prefers_higher_accuracy_at_low_risk():
    policy = CoachPolicy(risk_tolerance=0.0)  # all accuracy weight
    lookup = {"hi": _p("hi", accuracy=90), "lo": _p("lo", accuracy=40)}
    states = [_active("hi", "A"), _active("lo", "A")]
    rng = random.Random(0)
    chosen = select_thrower(candidates=states, player_lookup=lookup, policy=policy, rng=rng)
    assert chosen.player_id == "hi"


def test_select_thrower_prefers_power_at_high_risk():
    policy = CoachPolicy(risk_tolerance=1.0)
    lookup = {"acc": _p("acc", accuracy=90, power=30), "pwr": _p("pwr", accuracy=30, power=90)}
    states = [_active("acc", "A"), _active("pwr", "A")]
    chosen = select_thrower(candidates=states, player_lookup=lookup, policy=policy, rng=random.Random(0))
    assert chosen.player_id == "pwr"


def test_select_target_prefers_star_at_high_target_stars():
    policy = CoachPolicy(target_stars=1.0, target_ball_holder=0.0)
    lookup = {"star": _p("star", accuracy=90, power=90, dodge=90, catch=90),
              "scrub": _p("scrub", accuracy=20, power=20, dodge=20, catch=20)}
    states = [_active("star", "B"), _active("scrub", "B")]
    chosen = select_target(
        defense_states=states, player_lookup=lookup, policy=policy,
        recent_pressure_player_id=None, rng=random.Random(0),
    )
    assert chosen.player_id == "star"


def test_select_target_prefers_vulnerable_at_low_target_stars():
    policy = CoachPolicy(target_stars=0.0, target_ball_holder=0.0)
    lookup = {"safe": _p("safe", dodge=90), "vuln": _p("vuln", dodge=10)}
    states = [_active("safe", "B"), _active("vuln", "B")]
    chosen = select_target(
        defense_states=states, player_lookup=lookup, policy=policy,
        recent_pressure_player_id=None, rng=random.Random(0),
    )
    assert chosen.player_id == "vuln"


def test_decide_catch_attempt_high_catch_high_risk():
    policy = CoachPolicy(risk_tolerance=1.0, catch_bias=1.0)
    lookup = {"c": _p("c", catch=90, dodge=20)}
    target = _active("c", "B")
    decision = decide_catch_attempt(target=target, player_lookup=lookup, policy=policy)
    assert decision.attempt is True


def test_decide_catch_attempt_low_catch_low_risk():
    policy = CoachPolicy(risk_tolerance=0.0, catch_bias=0.0)
    lookup = {"c": _p("c", catch=20, dodge=80)}
    target = _active("c", "B")
    decision = decide_catch_attempt(target=target, player_lookup=lookup, policy=policy)
    assert decision.attempt is False


def test_throw_probabilities_bounded_0_1():
    probs = compute_throw_probabilities(thrower=_p("t"), target=_p("d"))
    assert 0.0 <= probs.p_on_target <= 1.0
    assert 0.0 <= probs.p_catch_given_attempt <= 1.0


def test_resolve_throw_mutates_sequence_deterministically():
    policy = CoachPolicy()
    lookup = {"t": _p("t", accuracy=90, power=70), "d": _p("d", dodge=10, catch=10)}
    thrower = _active("t", "A")
    target = _active("d", "B")
    seq = SequenceOfPlay(
        sequence_id="s1", match_id="m1", game_id=None,
        thrower_id="t", thrower_team_id="A", ball_id="b1",
        release_time_ms=0, material=BallMaterial.FOAM,
    )
    rng = random.Random(0)
    probs, outcome = resolve_throw(
        seq=seq, thrower_state=thrower, target_state=target,
        player_lookup=lookup, policy=policy, rng=rng,
    )
    assert outcome in ("hit", "caught", "dodged")
    # Resolve sequence finality must not crash
    resolve_sequence(seq)
    assert seq.final is not None


def test_resolve_throw_low_accuracy_high_dodge_misses():
    policy = CoachPolicy()
    lookup = {"t": _p("t", accuracy=5, power=5), "d": _p("d", dodge=99, catch=5)}
    thrower = _active("t", "A")
    target = _active("d", "B")
    seq = SequenceOfPlay(
        sequence_id="s1", match_id="m1", game_id=None,
        thrower_id="t", thrower_team_id="A", ball_id="b1",
        release_time_ms=0, material=BallMaterial.FOAM,
    )
    _, outcome = resolve_throw(
        seq=seq, thrower_state=thrower, target_state=target,
        player_lookup=lookup, policy=policy, rng=random.Random(0),
    )
    assert outcome == "dodged"


def test_proactive_weights_clock_pressure_boosts_throw():
    weights = proactive_action_weights(
        legal_kinds=["throw", "wait"], policy=CoachPolicy(),
        has_held_ball=True, burden_on_team=True, clock_pressure=True,
    )
    assert weights[0] > weights[1]


def test_box_score_derives_from_event_stream():
    # Build a tiny synthetic event stream
    from dodgeball_sim.official_events import OfficialEvent, OfficialEventKind, RuleReference
    events = [
        OfficialEvent(
            event_id="e1", kind=OfficialEventKind.SEQUENCE, match_id="m1",
            sequence_id="s1", ball_ids=("b1",), player_ids=("tA", "vB"),
            team_ids=("A",), rule_refs=(RuleReference("20"),),
            replay_summary="hit",
            payload={
                "kind": "sequence_final", "thrower_id": "tA",
                "thrower_team_id": "A", "outs": ["vB"], "catches": [],
                "thrower_out": False,
            },
        ),
        OfficialEvent(
            event_id="e2", kind=OfficialEventKind.SEQUENCE, match_id="m1",
            sequence_id="s2", ball_ids=("b1",), player_ids=("tA", "cB"),
            team_ids=("A",), rule_refs=(RuleReference("22"),),
            replay_summary="catch",
            payload={
                "kind": "sequence_final", "thrower_id": "tA",
                "thrower_team_id": "A", "outs": ["tA"], "catches": ["cB"],
                "thrower_out": True,
            },
        ),
    ]
    box = derive_box_score(events, team_a_id="A", team_b_id="B")
    # Canonical shape: teams keyed by id
    assert "A" in box["teams"]
    assert box["teams"]["A"]["totals"]["hits"] == 1
    assert box["teams"]["B"]["totals"]["catches"] == 1
