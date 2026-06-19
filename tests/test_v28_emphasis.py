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
from dodgeball_sim.official_resolution import compute_throw_probabilities, resolve_throw
from dodgeball_sim.official_translator import collect_official_metadata
from dodgeball_sim.player_state import OfficialPlayerState, OfficialPlayerStatus
from dodgeball_sim.rulesets import RulesetSelection
from dodgeball_sim.season_emphasis import SeasonEmphasis
from dodgeball_sim.sequence import SequenceLedger, SequenceOfPlay
from tools.probe_lib import make_match_input, make_player

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


# ---------------------------------------------------------------------------
# Task 3.2 — symmetry + discretion logging
# ---------------------------------------------------------------------------


class TestEmphasisSymmetry:
    def test_catch_emphasis_applies_to_both_sides(self):
        """The shift is a global sigmoid bias, not a per-team buff: a positive
        catch_delta raises catch leniency in BOTH throwing directions."""
        fast = make_player("x", "alpha", 70.0)
        slow = make_player("y", "beta", 55.0)
        emph = DEFAULT_WEATHER.emphasis_catch_delta_max
        base_xy = compute_throw_probabilities(thrower=fast, target=slow).p_catch_given_attempt
        emph_xy = compute_throw_probabilities(
            thrower=fast, target=slow, catch_emphasis=emph
        ).p_catch_given_attempt
        base_yx = compute_throw_probabilities(thrower=slow, target=fast).p_catch_given_attempt
        emph_yx = compute_throw_probabilities(
            thrower=slow, target=fast, catch_emphasis=emph
        ).p_catch_given_attempt
        assert emph_xy > base_xy, "catch emphasis did not raise leniency for x->y"
        assert emph_yx > base_yx, "catch emphasis did not raise leniency for y->x"

    def test_identical_matchup_is_mirror_identical(self):
        """Two identical players: the emphasized catch prob is the same whichever
        side throws (no home/away favoritism — symmetry by construction)."""
        p = make_player("p", "alpha", 63.0)
        q = make_player("q", "beta", 63.0)
        emph = DEFAULT_WEATHER.emphasis_catch_delta_max
        pq = compute_throw_probabilities(thrower=p, target=q, catch_emphasis=emph).p_catch_given_attempt
        qp = compute_throw_probabilities(thrower=q, target=p, catch_emphasis=emph).p_catch_given_attempt
        assert pq == qp


class TestBlockEmphasis:
    def test_block_emphasis_raises_block_rate(self):
        """A positive block_delta is monotonic on the held-ball decliner fixture:
        every seed that blocked at delta 0 still blocks, plus some new ones."""
        emph = SeasonEmphasis(block_delta=DEFAULT_WEATHER.emphasis_block_delta_max)
        base = sum(_throw(s, block_branch=True)[0] == "blocked" for s in range(300))
        bumped = sum(
            _throw(s, season_emphasis=emph, block_branch=True)[0] == "blocked"
            for s in range(300)
        )
        assert bumped > base, f"block emphasis did not raise the block rate ({bumped} <= {base})"


class TestEmphasisLogging:
    def _emphasis_disc(self, out):
        events = collect_official_metadata(out.events)["discretion_events"]
        return [
            d for d in events
            if str(d["payload"].get("selection_basis", "")).startswith("emphasis_")
        ]

    def test_flips_emit_emphasis_discretion_events(self):
        """A flipped call emits a RuleDiscretionEvent(selection_basis=
        'emphasis_<season>') visible in collect_official_metadata."""
        emph = SeasonEmphasis(
            catch_delta=DEFAULT_WEATHER.emphasis_catch_delta_max,
            selection_basis="emphasis_season_3",
        )
        total = 0
        for seed in range(24):
            driver = OfficialMatchEngineDriver()
            mi = make_match_input(seed=seed)
            mi = dc_replace(mi, config={**mi.config, "season_emphasis": emph})
            recs = self._emphasis_disc(driver.run(mi))
            total += len(recs)
            for d in recs:
                assert d["payload"]["selection_basis"] == "emphasis_season_3"
                # an emitted discretion is an actual flip: default != selected.
                assert d["payload"]["default_ruling"] != d["payload"]["selected_ruling"]
        assert total > 0, "no emphasis discretion events emitted over 24 seeds"

    def test_default_emphasis_emits_no_discretion(self):
        """A no-bulletin season logs no emphasis discretion events."""
        for seed in range(8):
            driver = OfficialMatchEngineDriver()
            assert self._emphasis_disc(driver.run(make_match_input(seed=seed))) == []


# ---------------------------------------------------------------------------
# Task 3.3 — select_season_emphasis / generate_officiating_bulletin / load
# ---------------------------------------------------------------------------

import sqlite3 as _sqlite3  # noqa: E402

from dodgeball_sim.career_setup import initialize_curated_manager_career  # noqa: E402
from dodgeball_sim.persistence import (  # noqa: E402
    create_schema,
    get_state,
    load_news_headlines,
    set_state,
)
from dodgeball_sim.season_emphasis import (  # noqa: E402
    generate_officiating_bulletin,
    load_season_emphasis,
    select_season_emphasis,
)

_SEED = 20260618


def _pyramid_conn():
    conn = _sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = _sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam", world="pyramid"
    )
    conn.commit()
    return conn


def _legacy_conn():
    conn = _sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = _sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", _SEED, ruleset_selection="official_foam")
    conn.commit()
    return conn


class TestSeasonEmphasisSelection:
    def test_select_is_deterministic_bounded_and_tagged(self):
        conn = _pyramid_conn()
        e1 = select_season_emphasis(conn, "season_2", _SEED)
        e2 = select_season_emphasis(conn, "season_2", _SEED)  # idempotent
        assert (e1.catch_delta, e1.block_delta, e1.announcement) == (
            e2.catch_delta, e2.block_delta, e2.announcement
        )
        assert abs(e1.catch_delta) <= DEFAULT_WEATHER.emphasis_catch_delta_max
        assert abs(e1.block_delta) <= DEFAULT_WEATHER.emphasis_block_delta_max
        assert e1.selection_basis == "emphasis_season_2"
        assert e1.announcement  # always announced (even a neutral "call it straight")

    def test_select_persists_and_load_round_trips(self):
        conn = _pyramid_conn()
        selected = select_season_emphasis(conn, "season_2", _SEED)
        set_state(conn, "active_season_id", "season_2")
        loaded = load_season_emphasis(conn)
        assert (loaded.catch_delta, loaded.block_delta, loaded.selection_basis) == (
            selected.catch_delta, selected.block_delta, selected.selection_basis
        )

    def test_generate_writes_league_bulletin(self):
        conn = _pyramid_conn()
        generate_officiating_bulletin(conn, "season_2", _SEED)
        bulletins = [
            h for h in load_news_headlines(conn, "season_2")
            if h["category"] == "league_bulletin"
        ]
        assert bulletins, "no league_bulletin headline written"
        emph = select_season_emphasis(conn, "season_2", _SEED)
        assert any(h["headline_text"] == emph.announcement for h in bulletins)

    def test_generate_surfaces_in_news_payload(self):
        from dodgeball_sim.web_status_service import build_news_payload

        conn = _pyramid_conn()
        generate_officiating_bulletin(conn, "season_2", _SEED)
        set_state(conn, "active_season_id", "season_2")
        conn.commit()
        texts = {item["text"] for item in build_news_payload(conn)["items"]}
        emph = select_season_emphasis(conn, "season_2", _SEED)
        assert emph.announcement in texts

    def test_load_default_when_absent(self):
        conn = _pyramid_conn()
        set_state(conn, "active_season_id", "season_1")
        e = load_season_emphasis(conn)
        assert e.catch_delta == 0.0 and e.block_delta == 0.0

    def test_legacy_save_is_byte_identical(self):
        conn = _legacy_conn()
        e = select_season_emphasis(conn, get_state(conn, "active_season_id"), _SEED)
        assert e.catch_delta == 0.0 and e.block_delta == 0.0
        generate_officiating_bulletin(conn, get_state(conn, "active_season_id"), _SEED)
        bulletins = [
            h for h in load_news_headlines(conn, get_state(conn, "active_season_id"))
            if h["category"] == "league_bulletin"
        ]
        assert bulletins == []


# ---------------------------------------------------------------------------
# Task 4.1 — frontend surfaces (Python guards on the rendered backend strings)
# ---------------------------------------------------------------------------


class TestSeasonPreviewSurface:
    def test_build_season_preview_carries_officiating_emphasis(self):
        from dodgeball_sim.season_preview import build_season_preview

        preview = build_season_preview(
            regular_season_weeks=10, bye_week=4, playoff_cut=4, total_clubs=8,
            roster=[], officiating_emphasis="Points of emphasis: reward catches.",
        )
        assert preview["officiating_emphasis"] == "Points of emphasis: reward catches."

    def test_default_preview_emphasis_is_none(self):
        from dodgeball_sim.season_preview import build_season_preview

        preview = build_season_preview(
            regular_season_weeks=10, bye_week=4, playoff_cut=4, total_clubs=8, roster=[],
        )
        assert preview["officiating_emphasis"] is None


class TestNewsWireSurface:
    def test_standings_payload_carries_wire_headlines(self):
        from dodgeball_sim.web_status_service import build_standings_payload

        conn = _pyramid_conn()
        # Write a league_bulletin for the active season and confirm it rides the
        # standings payload (the existing League Wire ticker's data source).
        sid = get_state(conn, "active_season_id")
        generate_officiating_bulletin(conn, sid, _SEED)
        payload = build_standings_payload(conn)
        assert "wire_headlines" in payload
        texts = {item["text"] for item in payload["wire_headlines"]}
        emph = select_season_emphasis(conn, sid, _SEED)
        assert emph.announcement in texts
