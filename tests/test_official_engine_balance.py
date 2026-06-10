"""Phase 4a — official-engine balance + moment-coverage gate.

The shipping official match engine (``run_autonomous_match``, the path real
official careers play through) previously did NOT reward OVR: the favorite at a
+72 net edge won only ~44% with ~22% draws, because a catch (which outs the
thrower AND resurrects a defender) was the default outcome of an on-target
throw, so throwing was net-negative EV and games stalled to clock-expiry draws.
Phase 4a retuned the catch math in ``official_resolution`` so OVR expresses, and
taught the engine to emit recognition moments. This is the graduated gate that
both balance and moment coverage must keep passing before the foam-official
default flips for new careers (Phase 4b).

Smoke size kept modest so the suite stays fast; for tighter intervals run
``python tools/official_match_probe.py --trials 500``.
"""
from __future__ import annotations

from collections import Counter

from dodgeball_sim.official_engine import OfficialMatchEngineDriver
from tools.probe_lib import make_match_input, run_ovr_curve


def test_official_ovr_curve_gate():
    results = run_ovr_curve(
        OfficialMatchEngineDriver(),
        rungs=(0, 4, 8, 12),
        trials_per_rung=250,
        seed_offset=0,
    )
    rates = [r.win_rate for r in results]
    # Monotonic within binomial noise at smoke size.
    for prev, curr in zip(rates, rates[1:]):
        assert curr >= prev - 0.04, f"official OVR curve regressed: {rates}"
    # Slope: the +72 net-OVR favorite must win >= 10pp above the even baseline.
    assert rates[-1] - rates[0] >= 0.10, f"official OVR slope too flat: {rates}"
    # Top-rung floor: a clearly stronger six must be a real favorite (gate 60%;
    # 0.56 lower bound leaves room for binomial noise at 250 trials).
    assert rates[-1] >= 0.56, f"+72 net OVR favorite wins only {rates[-1] * 100:.1f}%"
    # Draws must not swamp the signal at a large edge (coupled to the slope —
    # the old failure was catch-resurrection -> no elimination -> 0-0 draws).
    top = results[-1]
    draw_rate = sum(1 for o in top.outputs if o.winner_team_id is None) / len(top.outputs)
    assert draw_rate <= 0.25, f"+72 draw rate too high: {draw_rate * 100:.1f}%"


def test_official_driver_emits_recognition_moments():
    """The shipping official driver must emit the moment kinds the rec driver
    surfaces and the official loop can detect: DRAMATIC_CATCH, LATE_GAME_ESCAPE,
    ONE_V_ONE_FINALE, COMEBACK. GASSED_COLLAPSE and FLOOD_THROW are intentionally
    deferred (the official loop models no fatigue and no batch-throw tracker)."""
    driver = OfficialMatchEngineDriver()
    kinds: Counter[str] = Counter()
    for trial in range(150):
        mi = make_match_input(seed=trial, rating_a=70.0, rating_b=63.0)
        out = driver.run(mi)
        for moment in out.moment_events:
            kinds[moment.kind.value] += 1

    for required in ("dramatic_catch", "late_game_escape", "one_v_one_finale", "comeback"):
        assert kinds[required] > 0, f"official engine never emitted {required}: {dict(kinds)}"


# --- WT-7: DRAMATIC_CATCH moment-rate cap (presentation only) -----------------
#
# A live-ball catch-and-return fires on most on-target throws, so the official
# loop used to append a DRAMATIC_CATCH *moment* on every one (~24/match), turning
# recognition into replay noise. WT-7 gates the moment append to clutch catches
# (catching side even-or-behind, OR a side on its last live player) WITHOUT
# touching any outcome or the COMEBACK bookkeeping.
#
# The constants below drive OfficialMatchEngineDriver over seeds range(24) at
# 70 vs 63. They were originally captured before the WT-7 gate landed and have
# been RE-CAPTURED twice on 2026-06-10 for the two intentional, owner-greenlit
# V17 outcome changes (docs/specs/2026-06-10-post-v16-greenlit-backlog-
# sequencing-plan.md): Task 1 (catch-economy retune) and Task 2 (WT-20 live
# rules: ball lifecycle, blocking + No Blocking enforcement, opening rush).
# They are the immovable reference the gate is checked against until the next
# intentional engine change. (The favorite now wins 22/24: the WT-20 ball-
# lifecycle fix means a 24-minute match plays ~13 real games instead of 2-4
# stall-eaten ones, and a best-of-13 expresses a +7 OVR edge far more
# reliably.)
_WT7_SEEDS = range(24)
_WT7_RATING_A = 70.0
_WT7_RATING_B = 63.0
# UNCAPPED catch-and-return mean per match over _WT7_SEEDS (the moments the
# gate would emit with no cap). Measured cap-independently by counting the
# engine's CATCH_QUEUE return_on_catch events (the same condition the
# pre-WT-7 baseline measured).
# RE-CAPTURED 2026-06-10 (third time, V19a engine consumers): stamina
# erosion, tactical_iq timing/read, and slot-role fit are owner-greenlit
# outcome changes (V19 sprint plan), so the frozen sweep values moved.
_WT7_BASELINE_DRAMATIC_MEAN = 24.75
# Post-V19a winner_team_id sequence over _WT7_SEEDS — must be byte-identical
# under presentation-only changes (the WT-7 cap changes no outcome). The +7
# OVR favorite now takes all 24 (the two WT-20-era draws resolved — the V19a
# consumers express the edge slightly more reliably).
_WT7_BASELINE_WINNERS = [
    "fav", "fav", "fav", "fav", "fav", "fav", "fav", "fav", "fav", "fav",
    "fav", "fav", "fav", "fav", "fav", "fav", "fav", "fav", "fav", "fav",
    "fav", "fav", "fav", "fav",
]
# Post-V19a totals for the non-DRAMATIC moment kinds over _WT7_SEEDS.
# Gating only the DramaticCatch append must leave these untouched; in
# particular `comeback` is direct proof the comeback_catches increment still
# fires on every qualifying catch (it is keyed off the same
# catch_own <= catch_opp guard the gate reuses).
_WT7_BASELINE_OTHER_KINDS = {
    "late_game_escape": 316,
    "comeback": 58,
    "one_v_one_finale": 44,
}


def _wt7_run_sweep():
    """Drive the shipping official driver over the WT-7 seed sweep.

    Returns (winners, per_match_dramatic_counts, kind_totals).
    """
    driver = OfficialMatchEngineDriver()
    winners: list[str | None] = []
    dramatic_per_match: list[int] = []
    kind_totals: Counter[str] = Counter()
    for seed in _WT7_SEEDS:
        mi = make_match_input(seed=seed, rating_a=_WT7_RATING_A, rating_b=_WT7_RATING_B)
        out = driver.run(mi)
        winners.append(out.winner_team_id)
        dramatic = 0
        for moment in out.moment_events:
            kind = moment.kind.value
            kind_totals[kind] += 1
            if kind == "dramatic_catch":
                dramatic += 1
        dramatic_per_match.append(dramatic)
    return winners, dramatic_per_match, kind_totals


def test_wt7_dramatic_catch_rate_is_capped_without_changing_outcomes():
    """The DRAMATIC_CATCH moment rate must drop materially from the uncapped
    baseline, every recognition kind must still surface, and no match outcome may
    move — the cap is presentation-rate only."""
    winners, dramatic_per_match, kind_totals = _wt7_run_sweep()

    # (a) The per-match DRAMATIC_CATCH rate is materially reduced from ~24+.
    post_mean = sum(dramatic_per_match) / len(dramatic_per_match)
    assert post_mean <= 0.7 * _WT7_BASELINE_DRAMATIC_MEAN, (
        f"WT-7 cap not material: post mean {post_mean:.2f} vs baseline "
        f"{_WT7_BASELINE_DRAMATIC_MEAN:.2f} (require <= 70%)"
    )
    # Sanity: the gate must not silence DRAMATIC_CATCH entirely — clutch catches
    # still flow through.
    assert kind_totals["dramatic_catch"] > 0, "WT-7 gate silenced dramatic_catch entirely"

    # (b) Match outcomes are byte-identical pre/post: the cap changed no result.
    assert winners == _WT7_BASELINE_WINNERS, (
        f"WT-7 cap changed outcomes: {winners} != {_WT7_BASELINE_WINNERS}"
    )

    # (c) Gating ONLY the DramaticCatch append leaves every other moment kind's
    # total untouched. comeback == 45 unchanged proves the outcome-relevant
    # comeback_catches increment still fires on every qualifying catch.
    for kind, expected in _WT7_BASELINE_OTHER_KINDS.items():
        assert kind_totals[kind] == expected, (
            f"WT-7 cap perturbed non-dramatic kind {kind}: "
            f"{kind_totals[kind]} != {expected} (gate must touch dramatic_catch only)"
        )


# --- 2026-06-09 systems audit: PLAY_SAFE must never be a forfeit --------------
#
# PLAY_SAFE previously computed a catch-attempt threshold of 0.75 — above
# virtually every real roster's catch band — so a play-safe team NEVER attempted
# a catch. Catches are the official scoring economy (out the thrower AND
# resurrect a teammate), so the posture measured ZERO wins in 400 even-strength
# matches on both uniform and realistic-variance fixtures, and "Preserve Health"
# (whose intent preset selects play_safe) was a hidden self-destruct button on
# official careers. The fix: threshold 0.65 (strong catchers still attempt) plus
# a play-safe evasion bonus when the catch is declined
# (official_resolution._PLAY_SAFE_EVASION_BONUS). Measured after the fix on the
# fixture below: ~37% wins vs a ~44% default mirror — a real tradeoff, not a
# forfeit. This gate keeps it that way.
#
# The fixture uses a per-player catch/dodge spread around the same 63 mean
# (career seeds draw each attribute ~gauss(62,10), so real rosters always carry
# this variance). A uniform-rating fixture is the degenerate worst case for any
# threshold rule and does not represent a real roster.
_PLAY_SAFE_SPREAD = (48, 55, 60, 66, 72, 77)


def _play_safe_fixture(seed: int, policy_a):
    from dataclasses import replace as dc_replace

    mi = make_match_input(seed=seed, rating_a=63.0, rating_b=63.0, policy_a=policy_a)
    lookup = dict(mi.player_lookup)
    for starters in (mi.starters_a, mi.starters_b):
        for index, pid in enumerate(starters):
            player = lookup[pid]
            lookup[pid] = dc_replace(
                player,
                ratings=dc_replace(
                    player.ratings,
                    catch=_PLAY_SAFE_SPREAD[index],
                    dodge=_PLAY_SAFE_SPREAD[-1 - index],
                ),
            )
    return dc_replace(mi, player_lookup=lookup)


def test_play_safe_posture_is_not_a_forfeit():
    from dodgeball_sim.models import CatchPosture, CoachPolicy

    driver = OfficialMatchEngineDriver()
    play_safe = CoachPolicy(catch_posture=CatchPosture.PLAY_SAFE)
    trials = 150
    wins = 0
    for trial in range(trials):
        out = driver.run(_play_safe_fixture(21_000_000 + trial, play_safe))
        if out.winner_team_id == "fav":
            wins += 1
    win_rate = wins / trials
    # Floor: a play-safe side at even strength must stay a competitive
    # underdog (measured ~37%; 0.25 leaves room for binomial noise at 150).
    # The pre-fix forfeit measured 0.0% — any re-cliffing fails loudly here.
    assert win_rate >= 0.25, (
        f"play_safe won only {win_rate * 100:.1f}% at even strength — "
        "the posture has regressed toward a forfeit (see 2026-06-09 audit)"
    )


def test_play_safe_team_still_attempts_catches():
    """The 0.65 threshold must leave realistic rosters with real attempters —
    a play-safe side that records zero catches across a sweep has been cliffed
    out of the catch economy again."""
    from dodgeball_sim.models import CatchPosture, CoachPolicy
    from dodgeball_sim.official_events import OfficialEventKind

    driver = OfficialMatchEngineDriver()
    play_safe = CoachPolicy(catch_posture=CatchPosture.PLAY_SAFE)
    catches = 0
    for trial in range(12):
        out = driver.run(_play_safe_fixture(33_000_000 + trial, play_safe))
        for event in out.events:
            payload = getattr(event, "payload", None) or {}
            if (
                getattr(event, "kind", None) == OfficialEventKind.SEQUENCE
                and payload.get("kind") == "sequence_final"
                and payload.get("thrower_team_id") == "dog"
                and payload.get("catches")
            ):
                catches += len(payload.get("catches"))
    assert catches > 0, "play-safe side never attempted/landed a catch across 12 matches"


# --- V17: catch-economy retune — no displayed core skill is a liability -------
#
# The 2026-06-09 systems audit (§3.4) measured the pre-V17 economy at even
# strength: +12 accuracy = 30.9% and +12 dodge = 28.2% against a 38.7%
# baseline. p(catch|attempt) at even ratings was ~0.527 — far above the 1/3
# EV-neutral line (a catch is a -2 swing for the throwing team vs +1 for a
# hit) — so on-target throws FED the opponent's catch economy: two of the five
# displayed core skills lowered your win rate. The V17 retune shades
# catchability by throw quality (official_resolution._CATCH_THROW_QUALITY_SLOPE)
# and rebalances _CATCH_BIAS so the even-strength catch rate sits just below
# EV-neutral. Measured at 400 trials post-retune (probe records in the V17
# retro): baseline 35.5%, +12 accuracy 54.2%, +12 dodge 39.2%, +12 catch
# 62.7%, +12 power 48.2%. Seeds are fixed, so these gates are deterministic;
# margins leave room for future seed-flow changes while any regression toward
# the old inverted economy (accuracy/dodge ~7pp BELOW baseline) fails loudly.
_V17_EV_TRIALS = 150
_V17_EV_SEED_BASE = 64_000_000


def _v17_attr_win_rate(attr: str | None) -> float:
    from dataclasses import replace as dc_replace

    driver = OfficialMatchEngineDriver()
    wins = 0
    for trial in range(_V17_EV_TRIALS):
        mi = make_match_input(
            seed=_V17_EV_SEED_BASE + trial, rating_a=63.0, rating_b=63.0
        )
        if attr is not None:
            lookup = dict(mi.player_lookup)
            for pid in mi.starters_a:
                player = lookup[pid]
                lookup[pid] = dc_replace(
                    player, ratings=dc_replace(player.ratings, **{attr: 75})
                )
            mi = dc_replace(mi, player_lookup=lookup)
        if driver.run(mi).winner_team_id == "fav":
            wins += 1
    return wins / _V17_EV_TRIALS


def test_v17_no_displayed_core_skill_is_a_liability():
    """+12 in any displayed core skill must never sit materially BELOW the
    even-strength baseline — the pre-V17 economy had accuracy and dodge as
    outright liabilities, which silently inverted every roster/recruiting
    decision built on the displayed sheet."""
    baseline = _v17_attr_win_rate(None)
    accuracy = _v17_attr_win_rate("accuracy")
    dodge = _v17_attr_win_rate("dodge")

    assert accuracy >= baseline + 0.05, (
        f"+12 accuracy ({accuracy * 100:.1f}%) no longer clearly beats the even"
        f" baseline ({baseline * 100:.1f}%) — the catch economy has regressed"
        " toward throw-EV-negative (see 2026-06-09 audit §3.4)"
    )
    assert dodge >= baseline - 0.05, (
        f"+12 dodge ({dodge * 100:.1f}%) sits materially below the even"
        f" baseline ({baseline * 100:.1f}%) — dodge has regressed to a"
        " liability (see 2026-06-09 audit §3.4)"
    )


def test_v17_catch_remains_the_premium_skill():
    """The retune must reduce catch's dominance, not delete the catch economy:
    catching stays the strongest single-skill investment on officials."""
    baseline = _v17_attr_win_rate(None)
    catch = _v17_attr_win_rate("catch")
    assert catch >= baseline + 0.10, (
        f"+12 catch ({catch * 100:.1f}%) is no longer a clearly premium skill"
        f" vs baseline ({baseline * 100:.1f}%) — the retune overshot and"
        " removed the catch economy"
    )


def test_wt7_all_recognition_kinds_survive_the_cap():
    """The four detectable recognition kinds must all still emit after the cap.
    Uses the same 150-trial config as test_official_driver_emits_recognition_moments
    because one_v_one_finale / comeback are rare and would flake at small N."""
    driver = OfficialMatchEngineDriver()
    kinds: Counter[str] = Counter()
    for trial in range(150):
        mi = make_match_input(seed=trial, rating_a=70.0, rating_b=63.0)
        out = driver.run(mi)
        for moment in out.moment_events:
            kinds[moment.kind.value] += 1

    for required in ("dramatic_catch", "late_game_escape", "one_v_one_finale", "comeback"):
        assert kinds[required] > 0, f"WT-7 cap starved {required}: {dict(kinds)}"
