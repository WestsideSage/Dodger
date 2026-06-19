"""V28 The Weather — Phase 3: officiating points of emphasis.

A ``SeasonEmphasis`` (catch_delta / block_delta) shifts the EXISTING catch/block
sigmoid bias BEFORE the EXISTING roll — adding NO new RNG draw — so a default
``SeasonEmphasis()`` (deltas 0.0) is byte-identical to pre-V28. The shift is
applied symmetrically (every throw passes through the same shaded bias) and,
when it flips a call, logged as a ``RuleDiscretionEvent(selection_basis=
'emphasis_<season>')``.

THE PRE-V28 byte-identical guarantee is enforced by the EXISTING official-engine
golden suite: ``test_official_engine_balance.py`` (_WT7_BASELINE_WINNERS /
_WT7_BASELINE_OTHER_KINDS frozen literals), ``test_attribute_consumers.py``
(_official_fingerprint invariance), and ``test_wt20_live_rules.py`` (the block
pins). A default ``SeasonEmphasis()`` MUST NOT move any of them. The pins below
add the dataclass contract, the default==explicit-zero no-op, the "it bites"
divergence (the shift is wired and non-trivial), symmetry, and logging.

Spec: docs/specs/2026-06-17-v28-the-weather-spec.md (Phase 3).
"""
from __future__ import annotations

import random
from dataclasses import replace as dc_replace

import pytest

from dodgeball_sim.config import DEFAULT_WEATHER
from dodgeball_sim.models import CatchPosture, CoachPolicy
from dodgeball_sim.official_engine import OfficialMatchEngineDriver
from dodgeball_sim.official_resolution import resolve_throw
from dodgeball_sim.player_state import OfficialPlayerState, OfficialPlayerStatus
from dodgeball_sim.rulesets import RulesetSelection
from dodgeball_sim.season_emphasis import SeasonEmphasis
from dodgeball_sim.sequence import SequenceLedger, SequenceOfPlay
from tools.probe_lib import make_match_input

_PROFILE = RulesetSelection("official_foam").to_profile()


def _official_fingerprint(out) -> tuple:
    return (out.winner_team_id, out.final_active_a, out.final_active_b, tuple(out.events))


def _driver_fp(emphasis, seed: int) -> tuple:
    """Full-match fingerprint through the official driver, optionally with an
    emphasis injected via the free-form config channel (same rail as preps)."""
    driver = OfficialMatchEngineDriver()
    mi = make_match_input(seed=seed, rating_a=63.0, rating_b=63.0)
    if emphasis is not None:
        mi = dc_replace(mi, config={**mi.config, "season_emphasis": emphasis})
    return _official_fingerprint(driver.run(mi))


def _throw(seed: int, *, season_emphasis=None, block_branch: bool = False):
    """Drive resolve_throw directly on a catch-attempting target (the catch
    roll is what catch_delta shifts). Returns a comparable outcome tuple."""
    mi = make_match_input(seed=seed)
    lookup = dict(mi.player_lookup)
    target_id = mi.starters_b[0]
    thrower_id = mi.starters_a[0]
    target = lookup[target_id]
    if block_branch:
        # Low catch => decline the attempt; the holder block branch fires so a
        # block_delta is what separates the runs.
        lookup[target_id] = dc_replace(
            target, ratings=dc_replace(target.ratings, catch=20, dodge=40)
        )
        policy = CoachPolicy(catch_posture=CatchPosture.OPPORTUNISTIC)
    else:
        # High catch + low dodge => GO_FOR_CATCHES attempts; the catch roll is
        # what catch_delta shifts.
        lookup[target_id] = dc_replace(
            target, ratings=dc_replace(target.ratings, catch=80, dodge=30)
        )
        policy = CoachPolicy(catch_posture=CatchPosture.GO_FOR_CATCHES)
    seq = SequenceOfPlay(
        sequence_id="s1",
        match_id="emph",
        game_id=None,
        thrower_id=thrower_id,
        thrower_team_id=mi.team_a_id,
        ball_id="a0",
        release_time_ms=0,
        material=_PROFILE.material,
    )
    ledger = SequenceLedger()
    ledger.open_sequence(seq)
    kwargs = dict(
        seq=seq,
        thrower_state=OfficialPlayerState(
            player_id=thrower_id, team_id=mi.team_a_id,
            status=OfficialPlayerStatus.ACTIVE, is_starter=True,
        ),
        target_state=OfficialPlayerState(
            player_id=target_id, team_id=mi.team_b_id,
            status=OfficialPlayerStatus.ACTIVE, is_starter=True,
        ),
        player_lookup=lookup,
        policy=policy,
        rng=random.Random(seed),
        target_holds_ball=block_branch,
    )
    if season_emphasis is not None:
        kwargs["season_emphasis"] = season_emphasis
    probs, label = resolve_throw(**kwargs)
    ledger.close_sequence("s1")
    return (label, round(probs.p_catch_given_attempt, 12), round(probs.p_on_target, 12))


# ---------------------------------------------------------------------------
# Task 3.1 — SeasonEmphasis dataclass + threading + byte-identical fence
# ---------------------------------------------------------------------------


class TestSeasonEmphasisDataclass:
    def test_defaults_are_zero_noop(self):
        e = SeasonEmphasis()
        assert e.catch_delta == 0.0
        assert e.block_delta == 0.0
        assert e.announcement == ""

    def test_is_frozen(self):
        e = SeasonEmphasis()
        with pytest.raises(Exception):
            e.catch_delta = 0.5  # type: ignore[misc]


class TestByteIdenticalFence:
    def test_default_emphasis_equals_no_emphasis_engine(self):
        """Threading SeasonEmphasis() (default) is a no-op vs passing nothing."""
        for seed in range(6):
            assert _driver_fp(None, seed) == _driver_fp(SeasonEmphasis(), seed), (
                f"default SeasonEmphasis() perturbed the engine at seed {seed}"
            )

    def test_resolve_throw_default_is_noop(self):
        """resolve_throw with no emphasis arg == with an explicit default."""
        for seed in range(40):
            assert _throw(seed) == _throw(seed, season_emphasis=SeasonEmphasis()), (
                f"default emphasis changed resolve_throw at seed {seed}"
            )


class TestEmphasisBites:
    def test_nonzero_catch_emphasis_changes_outcomes_engine(self):
        """A bounded catch_delta MUST change at least one full-match outcome —
        proving the shift is wired (a byte-identical fence passes trivially if
        emphasis is simply ignored)."""
        emph = SeasonEmphasis(catch_delta=DEFAULT_WEATHER.emphasis_catch_delta_max)
        diverged = any(_driver_fp(None, seed) != _driver_fp(emph, seed) for seed in range(24))
        assert diverged, "bounded catch emphasis changed no engine outcome over 24 seeds"
        # (block emphasis bites + symmetry + logging are pinned in Task 3.2, which
        # uses a held-ball decliner fixture that actually exercises the block roll —
        # the uniform-63 engine fixture rarely declines a catch.)
