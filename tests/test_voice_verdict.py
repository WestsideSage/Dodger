"""Tests for the post-match Verdict generator (ADR 0001).

The Verdict is the single honest sentence shown after each match stating
whether the chosen Approach's intended mechanical behaviour actually showed
up in the box score — not merely whether the match was won.

These tests pin the binding decisions from ADR 0001:
- Signature-not-result honesty (verdict tracks signature, not win/loss)
- Comparative metrics vs the opponent
- Data injection (numbers appear in the sentence)
- No-op as a first-class state
- Approach labels, never raw Intent ids
"""
from __future__ import annotations

import pytest

from dodgeball_sim.voice_verdict import render_verdict


# --- Fixtures and helpers ------------------------------------------------

# Engine default CoachPolicy().as_dict() — see models.py CoachPolicy
DEFAULT_BASE = {
    "target_stars": 0.7,
    "target_ball_holder": 0.5,
    "risk_tolerance": 0.5,
    "sync_throws": 0.2,
    "rush_frequency": 0.5,
    "rush_proximity": 0.5,
    "tempo": 0.5,
    "catch_bias": 0.5,
}


def _round(d: dict) -> dict:
    return {k: round(float(v), 2) for k, v in d.items()}


def _policy_with(**overrides) -> dict:
    base = dict(DEFAULT_BASE)
    base.update(overrides)
    return _round(base)


def _tactics_for(intent: str, base: dict | None = None) -> dict:
    """Mimic command_center._policy_for_intent for tests."""
    base = dict(base or DEFAULT_BASE)
    values = dict(base)
    if intent == "Win Now":
        values["target_stars"] = max(values["target_stars"], 0.75)
        values["catch_bias"] = max(values["catch_bias"], 0.55)
    elif intent == "Preserve Health":
        values["rush_frequency"] = min(values["rush_frequency"], 0.25)
        values["tempo"] = min(values["tempo"], 0.35)
    elif intent == "Prepare For Playoffs":
        values["sync_throws"] = max(values["sync_throws"], 0.55)
        values["target_ball_holder"] = max(values["target_ball_holder"], 0.6)
    return _round(values)


def _team_box(
    *,
    outs_recorded: int = 4,
    catches: int = 3,
    living: int = 4,
    throws: int = 20,
    hits: int = 4,
) -> dict:
    """Build a minimal team box-score sub-dict matching engine._build_box_score."""
    return {
        "name": "Test Club",
        "totals": {
            "outs_recorded": outs_recorded,
            "hits": hits,
            "catches": catches,
            "dodges": 2,
            "living": living,
        },
        "players": {
            f"p{i}": {
                "name": f"Player {i}",
                "throws": throws // 6,
                "hits": hits // 6,
                "catches": catches // 6,
                "dodges": 0,
                "caught": 0,
                "is_out": i < (6 - living),
            }
            for i in range(6)
        },
    }


# --- Approach label rule (Q2 binding decision) ---------------------------

def test_verdict_never_leaks_raw_intent_id():
    """A player who picked 'Aggressive' must never see 'Win Now' in the verdict."""
    verdict = render_verdict(
        intent="Win Now",
        tactics=_tactics_for("Win Now"),
        base_tactics=_round(DEFAULT_BASE),
        result="Win",
        player_team_box=_team_box(catches=7),
        opponent_team_box=_team_box(catches=3),
    )
    assert "Win Now" not in verdict
    assert "Aggressive" in verdict


@pytest.mark.parametrize(
    "intent,expected_label",
    [
        ("Win Now", "Aggressive"),
        ("Balanced", "Balanced"),
        ("Prepare For Playoffs", "Control"),
        ("Preserve Health", "Defensive"),
    ],
)
def test_verdict_uses_approach_label(intent, expected_label):
    verdict = render_verdict(
        intent=intent,
        tactics=_tactics_for(intent),
        base_tactics=_round(DEFAULT_BASE),
        result="Win",
        player_team_box=_team_box(),
        opponent_team_box=_team_box(),
    )
    assert expected_label in verdict


# --- Aggressive signature: catches comparison ----------------------------

def test_aggressive_win_signature_present():
    """Aggressive + Win + catches > opponent's = signature present."""
    verdict = render_verdict(
        intent="Win Now",
        tactics=_tactics_for("Win Now"),
        base_tactics=_round(DEFAULT_BASE),
        result="Win",
        player_team_box=_team_box(catches=7),
        opponent_team_box=_team_box(catches=3),
    )
    assert "7" in verdict and "3" in verdict
    assert any(token in verdict.lower() for token in ("delivered", "worked", "showed up"))


def test_aggressive_win_signature_absent():
    """Win despite the plan — must say so."""
    verdict = render_verdict(
        intent="Win Now",
        tactics=_tactics_for("Win Now"),
        base_tactics=_round(DEFAULT_BASE),
        result="Win",
        player_team_box=_team_box(catches=2),
        opponent_team_box=_team_box(catches=6),
    )
    assert "2" in verdict and "6" in verdict
    assert any(token in verdict.lower() for token in ("despite", "never", "didn't", "did not"))


def test_aggressive_loss_signature_present():
    """Plan worked but lost — must say so. (Honesty property core case.)"""
    verdict = render_verdict(
        intent="Win Now",
        tactics=_tactics_for("Win Now"),
        base_tactics=_round(DEFAULT_BASE),
        result="Loss",
        player_team_box=_team_box(catches=8),
        opponent_team_box=_team_box(catches=4),
    )
    assert "8" in verdict and "4" in verdict
    assert any(token in verdict.lower() for token in ("delivered", "promised", "worked"))
    assert any(token in verdict.lower() for token in ("lost", "loss", "edged"))


def test_aggressive_loss_signature_absent():
    verdict = render_verdict(
        intent="Win Now",
        tactics=_tactics_for("Win Now"),
        base_tactics=_round(DEFAULT_BASE),
        result="Loss",
        player_team_box=_team_box(catches=1),
        opponent_team_box=_team_box(catches=5),
    )
    assert "1" in verdict and "5" in verdict
    assert any(token in verdict.lower() for token in ("never", "didn't", "did not"))


# --- Defensive signature: own-eliminations comparison --------------------

def test_defensive_signature_present_when_fewer_of_ours_eliminated():
    """Defensive signature = opponent.outs_recorded < player.outs_recorded
    (fewer of our players got eliminated than theirs)."""
    verdict = render_verdict(
        intent="Preserve Health",
        tactics=_tactics_for("Preserve Health"),
        base_tactics=_round(DEFAULT_BASE),
        result="Win",
        player_team_box=_team_box(outs_recorded=6),  # we eliminated 6 of theirs
        opponent_team_box=_team_box(outs_recorded=2),  # they eliminated 2 of ours
    )
    # The "evidence" pair for Defensive is (ours_eliminated, theirs_eliminated)
    # which is (opponent.outs_recorded=2, player.outs_recorded=6).
    assert "2" in verdict and "6" in verdict
    assert any(token in verdict.lower() for token in ("held", "delivered", "limited"))


def test_defensive_signature_absent_when_we_were_chewed_up():
    verdict = render_verdict(
        intent="Preserve Health",
        tactics=_tactics_for("Preserve Health"),
        base_tactics=_round(DEFAULT_BASE),
        result="Loss",
        player_team_box=_team_box(outs_recorded=2),
        opponent_team_box=_team_box(outs_recorded=6),
    )
    assert "6" in verdict
    assert any(token in verdict.lower() for token in ("never", "didn't", "did not"))


# --- Control signature: hit-rate comparison ------------------------------

def test_control_signature_present_when_hit_rate_higher():
    """Control signature = player hit-rate > opponent hit-rate.
    hit-rate = outs_recorded / total_throws across all players."""
    # Player: 6 outs / 18 throws = 33% hit rate
    # Opponent: 2 outs / 18 throws = 11% hit rate
    verdict = render_verdict(
        intent="Prepare For Playoffs",
        tactics=_tactics_for("Prepare For Playoffs"),
        base_tactics=_round(DEFAULT_BASE),
        result="Win",
        player_team_box=_team_box(outs_recorded=6, throws=18),
        opponent_team_box=_team_box(outs_recorded=2, throws=18),
    )
    # The numerical evidence appears as a percentage like "33" and "11".
    assert "%" in verdict
    assert any(token in verdict.lower() for token in ("executed", "delivered", "showed up"))


def test_control_signature_absent_when_hit_rate_lower():
    verdict = render_verdict(
        intent="Prepare For Playoffs",
        tactics=_tactics_for("Prepare For Playoffs"),
        base_tactics=_round(DEFAULT_BASE),
        result="Loss",
        player_team_box=_team_box(outs_recorded=2, throws=18),
        opponent_team_box=_team_box(outs_recorded=6, throws=18),
    )
    assert any(token in verdict.lower() for token in ("never", "didn't", "did not"))


def test_control_handles_zero_throws_without_crashing():
    """Degenerate match where no throws were recorded — must not divide by zero."""
    player_box = _team_box(throws=0, outs_recorded=0)
    opponent_box = _team_box(throws=0, outs_recorded=0)
    # Manually zero out player throws (helper uses //6 which rounds to 0 already)
    verdict = render_verdict(
        intent="Prepare For Playoffs",
        tactics=_tactics_for("Prepare For Playoffs"),
        base_tactics=_round(DEFAULT_BASE),
        result="Draw",
        player_team_box=player_box,
        opponent_team_box=opponent_box,
    )
    assert verdict  # non-empty string, no crash
    assert "Control" in verdict


# --- Balanced: no signature axis, three result verdicts ------------------

@pytest.mark.parametrize("result", ["Win", "Loss", "Draw"])
def test_balanced_has_no_signature_claim(result):
    verdict = render_verdict(
        intent="Balanced",
        tactics=_tactics_for("Balanced"),
        base_tactics=_round(DEFAULT_BASE),
        result=result,
        player_team_box=_team_box(catches=7),  # high catches — would be 'signature' for Aggressive
        opponent_team_box=_team_box(catches=1),
    )
    assert "Balanced" in verdict
    # Balanced verdicts must NOT claim a signature one way or the other.
    forbidden = ["delivered", "never materialized", "didn't take hold", "executed"]
    assert not any(token in verdict.lower() for token in forbidden)


# --- No-op detection (binding decision #4 from ADR 0001) -----------------

def test_aggressive_is_noop_when_base_already_satisfies_clamps():
    """If the club's base policy already meets/exceeds the Aggressive clamps,
    selecting Aggressive changes nothing — the verdict must say so."""
    saturated_base = _policy_with(target_stars=0.9, catch_bias=0.7)
    tactics = _tactics_for("Win Now", base=saturated_base)
    assert tactics == saturated_base  # sanity: the clamps are no-ops here
    verdict = render_verdict(
        intent="Win Now",
        tactics=tactics,
        base_tactics=saturated_base,
        result="Win",
        player_team_box=_team_box(catches=7),
        opponent_team_box=_team_box(catches=3),
    )
    # No-op verdicts must say *both* "Aggressive" and that the plan was a no-op.
    assert "Aggressive" in verdict
    assert any(
        token in verdict.lower()
        for token in ("no real lever", "identical", "no-op")
    )


def test_defensive_noop_overrides_signature_claim():
    """Even when the signature would otherwise be present, a no-op must report
    no-op — the player's choice didn't actually change anything."""
    saturated_base = _policy_with(rush_frequency=0.1, tempo=0.2)
    tactics = _tactics_for("Preserve Health", base=saturated_base)
    assert tactics == saturated_base
    verdict = render_verdict(
        intent="Preserve Health",
        tactics=tactics,
        base_tactics=saturated_base,
        result="Win",
        player_team_box=_team_box(outs_recorded=6),
        opponent_team_box=_team_box(outs_recorded=1),
    )
    assert "Defensive" in verdict
    assert any(
        token in verdict.lower()
        for token in ("no real lever", "identical", "no-op")
    )


# --- Draws as a first-class third result row -----------------------------

def test_aggressive_draw_signature_present():
    verdict = render_verdict(
        intent="Win Now",
        tactics=_tactics_for("Win Now"),
        base_tactics=_round(DEFAULT_BASE),
        result="Draw",
        player_team_box=_team_box(catches=5),
        opponent_team_box=_team_box(catches=2),
    )
    assert "draw" in verdict.lower()
    assert "5" in verdict and "2" in verdict


def test_aggressive_draw_signature_absent():
    verdict = render_verdict(
        intent="Win Now",
        tactics=_tactics_for("Win Now"),
        base_tactics=_round(DEFAULT_BASE),
        result="Draw",
        player_team_box=_team_box(catches=1),
        opponent_team_box=_team_box(catches=4),
    )
    assert "draw" in verdict.lower()
    assert any(token in verdict.lower() for token in ("never", "didn't", "did not"))


# --- Unknown intent fallback (e.g. legacy/AI-only "Develop Youth") -------

def test_unknown_intent_falls_back_to_neutral():
    """Develop Youth has no Approach mapping (AI-only). Verdict must be neutral
    — never invent a claim about an Approach the player didn't pick."""
    verdict = render_verdict(
        intent="Develop Youth",
        tactics={},
        base_tactics={},
        result="Win",
        player_team_box=_team_box(),
        opponent_team_box=_team_box(),
    )
    assert verdict  # non-empty
    # No approach label should appear.
    for approach in ("Aggressive", "Defensive", "Control"):
        assert approach not in verdict


# --- The honesty property test (the key one) ----------------------------

@pytest.mark.parametrize(
    "intent,player_box_kwargs_present,player_box_kwargs_absent,"
    "opp_box_kwargs_present,opp_box_kwargs_absent",
    [
        # Aggressive: catches comparison
        ("Win Now", {"catches": 8}, {"catches": 1}, {"catches": 2}, {"catches": 7}),
        # Defensive: own-eliminations comparison (player.outs_recorded vs opponent.outs_recorded)
        ("Preserve Health", {"outs_recorded": 6}, {"outs_recorded": 1}, {"outs_recorded": 1}, {"outs_recorded": 6}),
        # Control: hit-rate (outs/throws)
        ("Prepare For Playoffs", {"outs_recorded": 6, "throws": 18}, {"outs_recorded": 1, "throws": 18},
         {"outs_recorded": 1, "throws": 18}, {"outs_recorded": 6, "throws": 18}),
    ],
)
def test_honesty_property_signature_distinguishes_loss_states(
    intent, player_box_kwargs_present, player_box_kwargs_absent,
    opp_box_kwargs_present, opp_box_kwargs_absent,
):
    """The core honesty property: for the SAME result (Loss), a match where
    the approach's signature was present must produce a meaningfully different
    verdict than a match where it was absent. The verdict tracks the signature,
    not the result."""
    verdict_present = render_verdict(
        intent=intent,
        tactics=_tactics_for(intent),
        base_tactics=_round(DEFAULT_BASE),
        result="Loss",
        player_team_box=_team_box(**player_box_kwargs_present),
        opponent_team_box=_team_box(**opp_box_kwargs_present),
    )
    verdict_absent = render_verdict(
        intent=intent,
        tactics=_tactics_for(intent),
        base_tactics=_round(DEFAULT_BASE),
        result="Loss",
        player_team_box=_team_box(**player_box_kwargs_absent),
        opponent_team_box=_team_box(**opp_box_kwargs_absent),
    )
    assert verdict_present != verdict_absent, (
        f"Verdict failed honesty property for {intent}: signature presence "
        f"made no difference in the Loss verdict."
    )
    # Present: positive-shape language about the plan.
    assert any(t in verdict_present.lower() for t in ("delivered", "promised", "held", "showed up", "executed", "worked"))
    # Absent: negative-shape language.
    assert any(t in verdict_absent.lower() for t in ("never", "didn't", "did not"))
