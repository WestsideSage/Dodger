"""WT-20 — Official Live Rules enforcement gates (2026-06-10).

Owner-greenlit milestone (docs/fable/2026-06-10-owner-decision-log.md §1.1;
plan: docs/specs/2026-06-10-post-v16-greenlit-backlog-sequencing-plan.md).
Covers the four shipped enforcement pieces:

1. Held-ball blocking exists in regulation and is REMOVED under No Blocking
   (the proposed reduced-blocking resolution — the primary source names the
   trigger/terminal but not the mechanics; disclosed sim-design).
2. Ball lifecycle: out players forfeit held balls (Section 24-core) and loose
   balls re-enter play — the pre-WT-20 zombie-ball leak dead-aired uniform
   games to the tick cap (measured 552 stalled no_point games / 1572 across
   400 even matches; 0 after).
3. No Blocking activation truth: balls do not reset (sourced; the old
   three_per_side contradicted the primary source) and the match-end source
   exists.
4. Opening rush is live on officials (initiative + designated-ball holder
   ordering — disclosed sim-design), so the rush knobs are no longer
   announced-only.

Draw-texture gate (folded into WT-20 per the owner decision): every started
game concludes; even-strength match draws are honest equal-split scorelines
at a bounded rate.
"""
from __future__ import annotations

import random
from dataclasses import replace as dc_replace

from dodgeball_sim.models import (
    CatchPosture,
    CoachPolicy,
    OpeningRushCommit,
    OpeningRushTarget,
)
from dodgeball_sim.no_blocking import NoBlockingSource
from dodgeball_sim.official_engine import (
    OfficialMatchEngineDriver,
    run_autonomous_game,
    run_autonomous_match,
)
from dodgeball_sim.official_events import OfficialEventKind
from dodgeball_sim.official_resolution import resolve_throw
from dodgeball_sim.player_state import OfficialPlayerState, OfficialPlayerStatus
from dodgeball_sim.rulesets import RulesetSelection
from dodgeball_sim.sequence import SequenceLedger, SequenceOfPlay
from tools.probe_lib import make_match_input

_PROFILE = RulesetSelection("official_foam").to_profile()
_SPREAD = (48, 55, 60, 66, 72, 77)


def _spread_fixture(seed: int):
    mi = make_match_input(seed=seed, rating_a=63.0, rating_b=63.0)
    lookup = dict(mi.player_lookup)
    for starters in (mi.starters_a, mi.starters_b):
        for index, pid in enumerate(starters):
            player = lookup[pid]
            lookup[pid] = dc_replace(
                player,
                ratings=dc_replace(
                    player.ratings,
                    catch=_SPREAD[index],
                    dodge=_SPREAD[-1 - index],
                ),
            )
    return dc_replace(mi, player_lookup=lookup)


def _run_match(mi):
    return run_autonomous_match(
        profile=_PROFILE,
        match_id=mi.match_id,
        team_a_id=mi.team_a_id,
        team_b_id=mi.team_b_id,
        starters_a=mi.starters_a,
        starters_b=mi.starters_b,
        player_lookup=mi.player_lookup,
        policy_a=mi.policy_a,
        policy_b=mi.policy_b,
        seed=mi.seed,
    )


# ---------------------------------------------------------------------------
# 1. Blocking exists in regulation; No Blocking removes it
# ---------------------------------------------------------------------------


def _throw_once(*, target_holds_ball: bool, no_blocking_active: bool, seed: int):
    """Drive resolve_throw directly with a decline-the-catch defender."""
    mi = make_match_input(seed=seed)
    # Low catch => the opportunistic default declines the attempt; high dodge
    # keeps the dodge-roll path alive so the block branch is what separates
    # the two configurations.
    lookup = dict(mi.player_lookup)
    target_id = mi.starters_b[0]
    thrower_id = mi.starters_a[0]
    target = lookup[target_id]
    lookup[target_id] = dc_replace(
        target, ratings=dc_replace(target.ratings, catch=20, dodge=40)
    )
    seq = SequenceOfPlay(
        sequence_id="s1",
        match_id="wt20",
        game_id=None,
        thrower_id=thrower_id,
        thrower_team_id=mi.team_a_id,
        ball_id="a0",
        release_time_ms=0,
        material=_PROFILE.material,
    )
    ledger = SequenceLedger()
    ledger.open_sequence(seq)
    _, label = resolve_throw(
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
        policy=CoachPolicy(catch_posture=CatchPosture.OPPORTUNISTIC),
        rng=random.Random(seed),
        target_holds_ball=target_holds_ball,
        no_blocking_active=no_blocking_active,
    )
    ledger.close_sequence("s1")
    return label, seq


def test_ball_holding_decliner_blocks_in_regulation():
    labels = {
        _throw_once(target_holds_ball=True, no_blocking_active=False, seed=seed)[0]
        for seed in range(40)
    }
    assert "blocked" in labels, (
        "a ball-holding catch-decliner never blocked across 40 seeds — the "
        "WT-20 block branch is not reachable"
    )


def test_blocked_sequence_resolves_with_no_outs_and_honest_payload():
    for seed in range(40):
        label, seq = _throw_once(
            target_holds_ball=True, no_blocking_active=False, seed=seed
        )
        if label != "blocked":
            continue
        assert seq.final is not None
        assert seq.final.outs == ()
        assert seq.final.catches == ()
        assert "block" in seq.final.replay_summary.lower()
        from dodgeball_sim.sequence import sequence_event

        payload = sequence_event(seq).payload
        assert payload["blocked"] is True
        assert payload["blocker_id"] == seq.contacts[-1].player_id
        return
    raise AssertionError("no blocked sequence found to inspect")


def test_no_blocking_disables_the_block_branch():
    """Same seeds, same fixture: with No Blocking active the block label must
    never appear — the held ball no longer protects (Section 27)."""
    labels = {
        _throw_once(target_holds_ball=True, no_blocking_active=True, seed=seed)[0]
        for seed in range(40)
    }
    assert "blocked" not in labels, (
        "a block resolved while No Blocking was active — Section 27 "
        "enforcement regressed to announce-only"
    )


def test_non_holder_never_blocks():
    labels = {
        _throw_once(target_holds_ball=False, no_blocking_active=False, seed=seed)[0]
        for seed in range(40)
    }
    assert "blocked" not in labels, "a defender with no held ball blocked a throw"


# ---------------------------------------------------------------------------
# 2 + 3. Ball lifecycle + No Blocking activation truth (live game)
# ---------------------------------------------------------------------------


def _run_game(seed: int, *, policy_a=None, policy_b=None, match_clock_limit: int = 0,
              elapsed_match_seconds: int = 0):
    mi = make_match_input(seed=seed, rating_a=63.0, rating_b=63.0)
    return mi, run_autonomous_game(
        profile=_PROFILE,
        match_id=mi.match_id,
        team_a_id=mi.team_a_id,
        team_b_id=mi.team_b_id,
        starters_a=mi.starters_a,
        starters_b=mi.starters_b,
        player_lookup=mi.player_lookup,
        policy_a=policy_a or mi.policy_a,
        policy_b=policy_b or mi.policy_b,
        seed=seed,
        match_clock_limit=match_clock_limit,
        elapsed_match_seconds=elapsed_match_seconds,
    )


def test_out_players_forfeit_held_balls_and_loose_balls_reenter():
    forfeits = retrievals = 0
    for seed in range(12):
        _, res = _run_game(seed)
        for ev in res.events:
            payload = ev.payload or {}
            if payload.get("kind") == "queue_held_ball_forfeit":
                forfeits += 1
            if payload.get("kind") == "loose_ball_retrieved":
                retrievals += 1
    assert forfeits > 0, "no out player ever forfeited a held ball (Section 24-core)"
    assert retrievals > 0, "no loose ball was ever retrieved back into play"


def test_uniform_even_games_no_longer_stall_to_the_tick_cap():
    """The zombie-ball leak measured 35% of uniform even games dead-airing to
    max_ticks with both sides alive. Every game must now conclude."""
    for trial in range(25):
        mi = make_match_input(seed=88_000_000 + trial, rating_a=63.0, rating_b=63.0)
        res = _run_match(mi)
        for game in res.official_match_score.games:
            assert game.result_type != "no_point" or (
                game.final_active_a == 0 or game.final_active_b == 0
            ), (
                f"seed {trial}: game {game.game_number} stalled with both sides "
                f"alive ({game.final_active_a}v{game.final_active_b}) — the "
                "ball-lifecycle fix has regressed"
            )


def test_no_blocking_activation_says_balls_do_not_reset():
    """Sourced: 'Balls do not reset.' The pre-WT-20 activation hardcoded an
    unsourced three_per_side reset."""
    found = 0
    for seed in range(20):
        _, res = _run_game(seed)
        for ev in res.events:
            if ev.kind == OfficialEventKind.NO_BLOCKING:
                found += 1
                assert (ev.payload or {}).get("ball_reset") == "none", (
                    "No Blocking activated with a ball reset — contradicts the "
                    "primary source ('Balls do not reset')"
                )
    # NB only triggers when a game survives past the 180s line; the sweep must
    # exercise at least one activation for the assertion to mean anything.
    assert found > 0, "no No Blocking activation observed across the sweep"


def test_match_clock_expiry_activates_match_end_no_blocking():
    """Sourced: the current game becomes a 'match-end No Blocking game' when
    the match clock expires — play continues without interruption."""
    found = False
    for seed in range(30):
        # Start the game with the match clock already expired.
        _, res = _run_game(seed, match_clock_limit=600, elapsed_match_seconds=600)
        for ev in res.events:
            if ev.kind == OfficialEventKind.NO_BLOCKING:
                payload = ev.payload or {}
                if payload.get("source") == NoBlockingSource.MATCH_TIME_END.value:
                    found = True
        if found:
            break
    assert found, "match-clock expiry never produced a MATCH_TIME_END No Blocking game"


# ---------------------------------------------------------------------------
# 4. Opening rush is live (no longer announced-only)
# ---------------------------------------------------------------------------


def test_rush_target_orders_designated_ball_holders():
    """STRONGEST_SIDE must put the team's strongest throwers on the opening
    balls (activation events name the holders)."""
    mi = make_match_input(seed=4, rating_a=63.0, rating_b=63.0)
    # Give team A a clear power gradient so the ordering is deterministic.
    lookup = dict(mi.player_lookup)
    powers = (40, 50, 60, 70, 80, 90)
    for index, pid in enumerate(mi.starters_a):
        player = lookup[pid]
        lookup[pid] = dc_replace(
            player, ratings=dc_replace(player.ratings, power=powers[index])
        )
    mi = dc_replace(mi, player_lookup=lookup)

    res = run_autonomous_game(
        profile=_PROFILE,
        match_id=mi.match_id,
        team_a_id=mi.team_a_id,
        team_b_id=mi.team_b_id,
        starters_a=mi.starters_a,
        starters_b=mi.starters_b,
        player_lookup=mi.player_lookup,
        policy_a=CoachPolicy(rush_target=OpeningRushTarget.STRONGEST_SIDE),
        policy_b=mi.policy_b,
        seed=4,
    )
    activation_holders = [
        (ev.player_ids[0] if ev.player_ids else None)
        for ev in res.events
        if (ev.payload or {}).get("kind") == "activation"
        and ev.ball_ids and ev.ball_ids[0].startswith("a")
    ]
    expected_strongest = list(reversed(mi.starters_a))[:3]
    assert activation_holders == expected_strongest, (
        f"STRONGEST_SIDE holders {activation_holders} != strongest throwers "
        f"{expected_strongest}"
    )


def test_rush_knobs_change_official_outcomes_same_seed():
    """The rush axes were structurally dead on officials (same-seed
    byte-identical). WT-20 wires them: at least one seed must diverge for
    each axis."""
    driver = OfficialMatchEngineDriver()
    powers = (40, 50, 60, 70, 80, 90)

    def fingerprint(policy):
        outs = []
        for seed in range(6):
            mi = make_match_input(seed=seed, policy_a=policy)
            # A power gradient on team A: rush_target ordering is a no-op on a
            # uniform roster (sorting equal keys is stable), so the divergence
            # check needs real rating variance.
            lookup = dict(mi.player_lookup)
            for index, pid in enumerate(mi.starters_a):
                player = lookup[pid]
                lookup[pid] = dc_replace(
                    player, ratings=dc_replace(player.ratings, power=powers[index])
                )
            out = driver.run(dc_replace(mi, player_lookup=lookup))
            outs.append((out.winner_team_id, tuple(out.events)))
        return outs

    base = fingerprint(CoachPolicy())
    assert fingerprint(
        CoachPolicy(rush_commit=OpeningRushCommit.ALL_IN)
    ) != base, "rush_commit is still outcome-dead on officials"
    # NEAREST (slot order) vs STRONGEST_SIDE (power desc): with only power
    # varied, the default CENTER (overall desc) coincides with power order, so
    # the divergence check compares the two orderings that genuinely differ.
    assert fingerprint(
        CoachPolicy(rush_target=OpeningRushTarget.STRONGEST_SIDE)
    ) != fingerprint(
        CoachPolicy(rush_target=OpeningRushTarget.NEAREST)
    ), "rush_target is still outcome-dead on officials"


# ---------------------------------------------------------------------------
# Draw-texture gate (folded into WT-20)
# ---------------------------------------------------------------------------


def test_even_strength_draws_are_bounded_and_honest():
    """Post-enforcement texture (400-trial probe, 2026-06-10): uniform-even
    draws 10.5%, spread-even draws 11.0%, every draw an equal game-point
    split, zero stalled games. Gate at <= 18% on a 100-trial fixed-seed slice
    and require every draw to carry a real equal scoreline."""
    draws = 0
    trials = 100
    for trial in range(trials):
        mi = _spread_fixture(99_000_000 + trial)
        res = _run_match(mi)
        score = res.official_match_score
        if res.winner_team_id is None:
            draws += 1
            assert score.team_a_game_points == score.team_b_game_points
            assert score.team_a_game_points > 0, (
                "a 0-0 stall draw survived the WT-20 lifecycle fix"
            )
    assert draws / trials <= 0.18, (
        f"even-strength draw rate {draws}/{trials} exceeds the WT-20 ceiling"
    )
