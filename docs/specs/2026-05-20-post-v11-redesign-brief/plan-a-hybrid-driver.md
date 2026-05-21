# Plan A — Hybrid Driver Architecture + Tier 1 Engine

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the hybrid driver architecture as a thin slice — extract only the primitives the Tier 1 (Local Rec League) match loop needs, define a stable `EngineDriver` interface, define a replay/event contract for the six recognition moments, and prove with a sanity probe that Tier 1 matches resolve — all while keeping V11 / USAD behavior covered by existing tests.

**Architecture:** Brief §7.1 Option C, thin-slice. Existing primitive modules (`ball_state`, `catch_queue`, `sequence`, `player_state`) stay where they are and are not refactored — the "shared primitive layer" is conceptual, not a directory move. New primitives (`fatigue`, `flood_throws`, `stall_timer`, `moment_events`) are added flat in `src/dodgeball_sim/`. Two drivers implement `EngineDriver`: `RecTier1Driver` (new, composes primitives per the brief §3.5 rule contract) and `OfficialDriver` (thin wrapper around the existing `run_autonomous_game` in `official_engine.py`). V11 modules `burden`, `discipline`, and `no_blocking` are **not** touched by this plan.

**Tech Stack:** Python 3.11+, pytest, existing dodgeball_sim package layout, hatchling build. No new runtime dependencies.

**Parent docs:** [tier-1-roadmap.md](./tier-1-roadmap.md), [brief.md](./brief.md).

---

## Plan-level guarantees

These are the load-bearing promises of Plan A. Every task should be checked against them.

1. **V11 / USAD tests stay green throughout.** After every task, `python -m pytest -q` reports the same baseline 659 passing tests *plus* any new tests this plan adds. If a refactor step would break an existing test, the task is wrong.
2. **No directory moves.** `ball_state.py`, `catch_queue.py`, `sequence.py`, `player_state.py` stay flat in `src/dodgeball_sim/`. Imports do not change. This protects V11 from churn.
3. **No new primitives that Tier 1 doesn't use.** `fatigue`, `flood_throws`, `stall_timer`, `moment_events` are all in the brief §3.5 contract. `burden`, `discipline`, `no_blocking` are deliberately not extended in this plan — they stay V11-only until a later tier driver needs them.
4. **Driver interface is the only public contract for B/C/D.** B/C/D consume `EngineDriver`, `DriverMatchInput`, `DriverMatchOutput`, and `MomentEvent` types. They do not import the rec or official driver internals.
5. **Tier 1 sanity probe is the gate.** Plan A is not done until `python -m dodgeball_sim.tools.tier_1_sanity_probe` runs end-to-end across 25 Tier 1 matches and reports no exceptions, every match resolves with a winner or draw, and at least one moment event fires per match on average.

## Repository orientation (read before starting)

If you are picking this plan up cold, read these in order:

1. `AGENTS.md` — repo rules and workflow.
2. `docs/STATUS.md` — current build state.
3. `docs/specs/2026-05-20-post-v11-redesign-brief/brief.md` — the vision and the Tier 1 rule contract in §3.5.
4. `docs/specs/2026-05-20-post-v11-redesign-brief/tier-1-roadmap.md` — this milestone's roadmap.
5. `src/dodgeball_sim/official_engine.py` — the V11 driver you are *not* rewriting, just wrapping.
6. `src/dodgeball_sim/ball_state.py`, `catch_queue.py`, `sequence.py`, `player_state.py` — the existing primitives that Tier 1 reuses.
7. `src/dodgeball_sim/rulesets.py` — the existing `RulesetProfile`. Tier 1 uses its own config, but you should understand the existing shape.

## File map

**Create (new):**
- `src/dodgeball_sim/engine_driver.py` — `EngineDriver` protocol + I/O dataclasses.
- `src/dodgeball_sim/moment_events.py` — six moment event types + union.
- `src/dodgeball_sim/fatigue.py` — in-match fatigue primitive.
- `src/dodgeball_sim/flood_throws.py` — simultaneous-throw primitive.
- `src/dodgeball_sim/stall_timer.py` — Tier 1 stall cap primitive.
- `src/dodgeball_sim/tier_1_rules.py` — encoded §3.5 rule contract.
- `src/dodgeball_sim/rec_engine.py` — `RecTier1Driver`.
- `src/dodgeball_sim/official_driver.py` — `OfficialDriver` wrapper.
- `tools/tier_1_sanity_probe.py` — Tier 1 match resolution sanity probe.
- `tests/test_engine_driver.py`
- `tests/test_moment_events.py`
- `tests/test_fatigue.py`
- `tests/test_flood_throws.py`
- `tests/test_stall_timer.py`
- `tests/test_tier_1_rules.py`
- `tests/test_rec_engine.py`
- `tests/test_official_driver.py`
- `tests/test_tier_1_integration.py`
- `tests/test_tier_1_sanity_probe.py`

**Modify:**
- `docs/STATUS.md` — add a line under "Shipped And Verified" once Plan A lands.

**Do not touch:**
- `src/dodgeball_sim/burden.py`, `discipline.py`, `no_blocking.py` — V11-only.
- `src/dodgeball_sim/official_engine.py` — wrapped, not edited. The only allowed edit is adding a `__all__` export if needed for the wrapper.
- Any file under `src/dodgeball_sim/official_*.py` other than via the wrapper.
- Frontend (`frontend/`).

---

## Task 1: `EngineDriver` interface and I/O dataclasses

**Files:**
- Create: `src/dodgeball_sim/engine_driver.py`
- Create: `tests/test_engine_driver.py`

This task defines the protocol that B, C, and D will build against. It is intentionally tiny — the interface should be the smallest thing that lets two drivers coexist.

- [x] **Step 1: Write the failing test**
Create `tests/test_engine_driver.py`:
```python
from dodgeball_sim.engine_driver import (
    EngineDriver,
    DriverMatchInput,
    DriverMatchOutput,
)


def test_driver_input_holds_required_fields():
    inp = DriverMatchInput(
        match_id="m1",
        team_a_id="a",
        team_b_id="b",
        starters_a=("p1", "p2"),
        starters_b=("p3", "p4"),
        player_lookup={},
        policy_a=None,
        policy_b=None,
        seed=42,
    )
    assert inp.match_id == "m1"
    assert inp.seed == 42
    assert inp.starters_a == ("p1", "p2")
    assert inp.config == {}


def test_driver_output_defaults():
    out = DriverMatchOutput(
        events=(),
        winner_team_id=None,
        final_active_a=0,
        final_active_b=0,
    )
    assert out.moment_events == ()
    assert out.replay_state is None


def test_stub_driver_satisfies_protocol():
    class StubDriver:
        tier_id = "stub"

        def run(self, match_input: DriverMatchInput) -> DriverMatchOutput:
            return DriverMatchOutput(
                events=(),
                winner_team_id=match_input.team_a_id,
                final_active_a=1,
                final_active_b=0,
            )

    drv: EngineDriver = StubDriver()
    out = drv.run(
        DriverMatchInput(
            match_id="m",
            team_a_id="a",
            team_b_id="b",
            starters_a=(),
            starters_b=(),
            player_lookup={},
            policy_a=None,
            policy_b=None,
            seed=1,
        )
    )
    assert out.winner_team_id == "a"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_engine_driver.py -v`
Expected: `ModuleNotFoundError: No module named 'dodgeball_sim.engine_driver'`

- [x] **Step 3: Write the minimal implementation**

Create `src/dodgeball_sim/engine_driver.py`:

```python
"""Engine driver interface for the hybrid tier-driver architecture.

Plan A of the post-V11 redesign introduces multiple per-tier engine
drivers (rec, official) that compose a shared primitive layer. B/C/D
consume only this module's types — they do not import driver internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Protocol, Tuple


@dataclass(frozen=True)
class DriverMatchInput:
    """Inputs required to run a single match through any tier driver."""

    match_id: str
    team_a_id: str
    team_b_id: str
    starters_a: Tuple[str, ...]
    starters_b: Tuple[str, ...]
    player_lookup: Dict[str, Any]
    policy_a: Any
    policy_b: Any
    seed: int
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DriverMatchOutput:
    """Outputs produced by any tier driver after a single match."""

    events: Tuple[Any, ...]
    winner_team_id: str | None
    final_active_a: int
    final_active_b: int
    moment_events: Tuple[Any, ...] = ()
    replay_state: Any | None = None


class EngineDriver(Protocol):
    """Protocol implemented by per-tier engine drivers."""

    tier_id: str

    def run(self, match_input: DriverMatchInput) -> DriverMatchOutput:
        ...


__all__ = ["EngineDriver", "DriverMatchInput", "DriverMatchOutput"]
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_engine_driver.py -v`
Expected: 3 passed.

- [x] **Step 5: Run the full suite to confirm no regressions**

Run: `python -m pytest -q`
Expected: 662 passed (659 baseline + 3 new).

- [x] **Step 6: Commit**

```bash
git add src/dodgeball_sim/engine_driver.py tests/test_engine_driver.py
git commit -m "feat(engine): add EngineDriver protocol and I/O dataclasses

Defines the hybrid driver interface. B/C/D consume this contract;
no driver-internal imports cross plan boundaries."
```

---

## Task 2: Moment event types

**Files:**
- Create: `src/dodgeball_sim/moment_events.py`
- Create: `tests/test_moment_events.py`

Defines the six recognition moments as immutable event dataclasses, plus a `MomentEvent` union. Surfacing in the replay UI waits for Plan C — Plan A only commits to the *contract*.

- [x] **Step 1: Write the failing test**

Create `tests/test_moment_events.py`:

```python
from dodgeball_sim.moment_events import (
    DramaticCatch,
    LateGameEscape,
    OneVOneFinale,
    GassedCollapse,
    FloodThrow,
    Comeback,
    MomentEvent,
    MomentKind,
)


def test_moment_kinds_are_unique():
    kinds = {
        MomentKind.DRAMATIC_CATCH,
        MomentKind.LATE_GAME_ESCAPE,
        MomentKind.ONE_V_ONE_FINALE,
        MomentKind.GASSED_COLLAPSE,
        MomentKind.FLOOD_THROW,
        MomentKind.COMEBACK,
    }
    assert len(kinds) == 6


def test_dramatic_catch_fields():
    ev = DramaticCatch(
        match_id="m1",
        tick=12,
        catcher_id="p7",
        catcher_team_id="a",
        thrower_id="p2",
        thrower_team_id="b",
        returning_player_id="p9",
        active_count_a=3,
        active_count_b=4,
    )
    assert ev.kind == MomentKind.DRAMATIC_CATCH
    assert ev.catcher_id == "p7"
    assert ev.returning_player_id == "p9"


def test_late_game_escape_requires_three_or_more_attackers():
    ev = LateGameEscape(
        match_id="m1",
        tick=40,
        survivor_id="p1",
        survivor_team_id="a",
        attacker_team_id="b",
        attacker_count=4,
    )
    assert ev.kind == MomentKind.LATE_GAME_ESCAPE
    assert ev.attacker_count >= 3


def test_one_v_one_finale_fields():
    ev = OneVOneFinale(
        match_id="m1",
        tick=55,
        player_a_id="p1",
        player_b_id="p10",
        tick_started=53,
    )
    assert ev.kind == MomentKind.ONE_V_ONE_FINALE


def test_gassed_collapse_fields():
    ev = GassedCollapse(
        match_id="m1",
        tick=44,
        player_id="p5",
        team_id="a",
        fatigue_pct=0.86,
    )
    assert ev.kind == MomentKind.GASSED_COLLAPSE
    assert ev.fatigue_pct >= 0.75


def test_flood_throw_three_or_more_simultaneous():
    ev = FloodThrow(
        match_id="m1",
        tick=22,
        thrower_team_id="b",
        thrower_ids=("p2", "p3", "p5"),
    )
    assert ev.kind == MomentKind.FLOOD_THROW
    assert len(ev.thrower_ids) >= 3


def test_comeback_records_deficit():
    ev = Comeback(
        match_id="m1",
        tick=60,
        team_id="a",
        deficit_at_low_point=4,
        catches_during_comeback=5,
    )
    assert ev.kind == MomentKind.COMEBACK
    assert ev.deficit_at_low_point >= 3


def test_moment_event_union_accepts_all_six():
    events: list[MomentEvent] = [
        DramaticCatch("m", 0, "a", "ta", "b", "tb", "c", 1, 1),
        LateGameEscape("m", 0, "a", "ta", "tb", 3),
        OneVOneFinale("m", 0, "a", "b", 0),
        GassedCollapse("m", 0, "a", "ta", 0.8),
        FloodThrow("m", 0, "ta", ("a", "b", "c")),
        Comeback("m", 0, "ta", 3, 3),
    ]
    assert len(events) == 6
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_moment_events.py -v`
Expected: `ModuleNotFoundError`.

- [x] **Step 3: Write the implementation**

Create `src/dodgeball_sim/moment_events.py`:

```python
"""Six recognition moments — replay/event contract.

These are emitted by tier drivers when state changes match the moment
definition from brief.md §4. Surfacing in the replay UI is Plan C; the
emission contract lives here so B/C/D can build against it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Union


class MomentKind(str, Enum):
    DRAMATIC_CATCH = "dramatic_catch"
    LATE_GAME_ESCAPE = "late_game_escape"
    ONE_V_ONE_FINALE = "one_v_one_finale"
    GASSED_COLLAPSE = "gassed_collapse"
    FLOOD_THROW = "flood_throw"
    COMEBACK = "comeback"


@dataclass(frozen=True)
class DramaticCatch:
    """A live-ball catch that returns a teammate from the queue."""

    match_id: str
    tick: int
    catcher_id: str
    catcher_team_id: str
    thrower_id: str
    thrower_team_id: str
    returning_player_id: str
    active_count_a: int
    active_count_b: int
    kind: MomentKind = MomentKind.DRAMATIC_CATCH


@dataclass(frozen=True)
class LateGameEscape:
    """A single survivor faces three or more opposing actives."""

    match_id: str
    tick: int
    survivor_id: str
    survivor_team_id: str
    attacker_team_id: str
    attacker_count: int
    kind: MomentKind = MomentKind.LATE_GAME_ESCAPE


@dataclass(frozen=True)
class OneVOneFinale:
    """Last two players on court, one per side."""

    match_id: str
    tick: int
    player_a_id: str
    player_b_id: str
    tick_started: int
    kind: MomentKind = MomentKind.ONE_V_ONE_FINALE


@dataclass(frozen=True)
class GassedCollapse:
    """A player went out while their fatigue exceeded the gassed threshold."""

    match_id: str
    tick: int
    player_id: str
    team_id: str
    fatigue_pct: float
    kind: MomentKind = MomentKind.GASSED_COLLAPSE


@dataclass(frozen=True)
class FloodThrow:
    """Three or more throws released in the same tick from one side."""

    match_id: str
    tick: int
    thrower_team_id: str
    thrower_ids: Tuple[str, ...]
    kind: MomentKind = MomentKind.FLOOD_THROW


@dataclass(frozen=True)
class Comeback:
    """A team came back from a multi-player deficit via clutch catches."""

    match_id: str
    tick: int
    team_id: str
    deficit_at_low_point: int
    catches_during_comeback: int
    kind: MomentKind = MomentKind.COMEBACK


MomentEvent = Union[
    DramaticCatch,
    LateGameEscape,
    OneVOneFinale,
    GassedCollapse,
    FloodThrow,
    Comeback,
]


__all__ = [
    "MomentKind",
    "MomentEvent",
    "DramaticCatch",
    "LateGameEscape",
    "OneVOneFinale",
    "GassedCollapse",
    "FloodThrow",
    "Comeback",
]
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_moment_events.py -v`
Expected: 8 passed.

- [x] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: 670 passed (662 + 8 new).

- [x] **Step 6: Commit**

```bash
git add src/dodgeball_sim/moment_events.py tests/test_moment_events.py
git commit -m "feat(engine): add six-moment event contract

DramaticCatch, LateGameEscape, OneVOneFinale, GassedCollapse,
FloodThrow, Comeback. Emission is Plan A; UI surfacing is Plan C."
```

---

## Task 3: `Fatigue` primitive

**Files:**
- Create: `src/dodgeball_sim/fatigue.py`
- Create: `tests/test_fatigue.py`

Per-player in-match fatigue accumulation and decay. Plan B will later attach a `conditioning_curve` attribute that modulates accumulation; Plan A defines the primitive with a sensible default so Tier 1 matches produce the gassed-star moment.

- [x] **Step 1: Write the failing test**

Create `tests/test_fatigue.py`:

```python
import math

from dodgeball_sim.fatigue import (
    FatigueState,
    FatigueParams,
    GASSED_THRESHOLD,
    accumulate,
    recover,
    effectiveness,
)


def test_fresh_player_has_zero_fatigue():
    state = FatigueState.fresh()
    assert state.value == 0.0
    assert not state.is_gassed()


def test_accumulate_increases_fatigue():
    params = FatigueParams()
    state = FatigueState.fresh()
    state = accumulate(state, action_cost=0.05, params=params)
    assert state.value > 0.0
    assert state.value <= 1.0


def test_accumulate_caps_at_one():
    params = FatigueParams()
    state = FatigueState(value=0.95)
    state = accumulate(state, action_cost=0.5, params=params)
    assert state.value == 1.0


def test_recover_decreases_fatigue():
    params = FatigueParams()
    state = FatigueState(value=0.5)
    state = recover(state, seconds_idle=10, params=params)
    assert state.value < 0.5
    assert state.value >= 0.0


def test_recover_floors_at_zero():
    params = FatigueParams()
    state = FatigueState(value=0.02)
    state = recover(state, seconds_idle=600, params=params)
    assert state.value == 0.0


def test_gassed_threshold_constant():
    assert GASSED_THRESHOLD == 0.75


def test_is_gassed_at_or_above_threshold():
    assert FatigueState(value=GASSED_THRESHOLD).is_gassed()
    assert FatigueState(value=0.9).is_gassed()
    assert not FatigueState(value=0.74).is_gassed()


def test_effectiveness_drops_with_fatigue():
    fresh_eff = effectiveness(FatigueState(value=0.0))
    gassed_eff = effectiveness(FatigueState(value=0.9))
    assert fresh_eff == 1.0
    assert gassed_eff < 0.6
    assert gassed_eff > 0.0


def test_effectiveness_monotonic_decrease():
    """Effectiveness must not increase as fatigue grows."""
    last = math.inf
    for v in [0.0, 0.25, 0.5, 0.75, 0.9, 1.0]:
        eff = effectiveness(FatigueState(value=v))
        assert eff <= last + 1e-9, f"effectiveness rose at fatigue={v}"
        last = eff


def test_conditioning_curve_slows_accumulation():
    """Higher conditioning_curve attribute should slow fatigue gain."""
    soft_params = FatigueParams(conditioning_curve=20.0)  # poor conditioning
    hard_params = FatigueParams(conditioning_curve=90.0)  # elite conditioning
    soft_state = accumulate(FatigueState.fresh(), action_cost=0.1, params=soft_params)
    hard_state = accumulate(FatigueState.fresh(), action_cost=0.1, params=hard_params)
    assert soft_state.value > hard_state.value
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fatigue.py -v`
Expected: `ModuleNotFoundError`.

- [x] **Step 3: Write the implementation**

Create `src/dodgeball_sim/fatigue.py`:

```python
"""In-match fatigue primitive.

Tracks per-player fatigue from 0.0 (fresh) to 1.0 (collapsed). Used by
both the rec and (eventually) official drivers to produce the
gassed-star recognition moment. The ``conditioning_curve`` parameter is
exposed for Plan B to attach a per-player attribute; Plan A uses the
default which produces fatigue effects with the existing
``PlayerRatings.stamina`` field unmodified.
"""

from __future__ import annotations

from dataclasses import dataclass


GASSED_THRESHOLD: float = 0.75
"""Fatigue value at which a player is considered gassed for moment emission."""


@dataclass(frozen=True)
class FatigueParams:
    """Tunable parameters. Plan B may attach per-player conditioning_curve."""

    base_accumulation: float = 1.0
    base_recovery_per_second: float = 0.01
    conditioning_curve: float = 50.0  # 0..100, higher = slower fatigue gain

    def accumulation_multiplier(self) -> float:
        # conditioning_curve 0 -> 1.5x, 50 -> 1.0x, 100 -> 0.5x
        return 1.5 - (self.conditioning_curve / 100.0)


@dataclass(frozen=True)
class FatigueState:
    value: float = 0.0

    @classmethod
    def fresh(cls) -> "FatigueState":
        return cls(value=0.0)

    def is_gassed(self) -> bool:
        return self.value >= GASSED_THRESHOLD


def accumulate(
    state: FatigueState,
    *,
    action_cost: float,
    params: FatigueParams,
) -> FatigueState:
    """Add fatigue from an action. action_cost is in [0, 1]."""
    delta = params.base_accumulation * action_cost * params.accumulation_multiplier()
    new_value = min(1.0, state.value + delta)
    return FatigueState(value=new_value)


def recover(
    state: FatigueState,
    *,
    seconds_idle: float,
    params: FatigueParams,
) -> FatigueState:
    """Reduce fatigue from idle time."""
    delta = params.base_recovery_per_second * seconds_idle
    new_value = max(0.0, state.value - delta)
    return FatigueState(value=new_value)


def effectiveness(state: FatigueState) -> float:
    """Return an effectiveness multiplier in (0, 1] for throws/dodges.

    Linear-ish curve: fresh = 1.0, gassed threshold = ~0.75, fully gassed = 0.4.
    """
    return max(0.4, 1.0 - 0.6 * state.value)


__all__ = [
    "FatigueState",
    "FatigueParams",
    "GASSED_THRESHOLD",
    "accumulate",
    "recover",
    "effectiveness",
]
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_fatigue.py -v`
Expected: 10 passed.

- [x] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: 680 passed (670 + 10 new).

- [x] **Step 6: Commit**

```bash
git add src/dodgeball_sim/fatigue.py tests/test_fatigue.py
git commit -m "feat(engine): add in-match fatigue primitive

Per-player accumulation/decay/effectiveness with hook for Plan B's
conditioning_curve attribute. Feeds the gassed-star moment."
```

---

## Task 4: `FloodThrows` primitive

**Files:**
- Create: `src/dodgeball_sim/flood_throws.py`
- Create: `tests/test_flood_throws.py`

A throw is a "flood" candidate when three or more throwers release within the same engine tick. The primitive tracks pending releases per tick and reports flood-throws when the threshold is met. The actual `SequenceLedger` in `sequence.py` is unchanged; the rec driver simply opens multiple sequences in one tick and routes them through this primitive's detector to emit the moment.

- [x] **Step 1: Write the failing test**

Create `tests/test_flood_throws.py`:

```python
from dodgeball_sim.flood_throws import (
    FloodThrowTracker,
    FLOOD_THRESHOLD,
    PendingThrow,
)


def test_flood_threshold_is_three():
    assert FLOOD_THRESHOLD == 3


def test_no_flood_with_two_throws():
    tracker = FloodThrowTracker()
    tracker.record(PendingThrow(thrower_id="p1", team_id="a", tick=5))
    tracker.record(PendingThrow(thrower_id="p2", team_id="a", tick=5))
    detected = tracker.detect_flood(tick=5)
    assert detected is None


def test_flood_with_three_same_team_same_tick():
    tracker = FloodThrowTracker()
    tracker.record(PendingThrow("p1", "a", 5))
    tracker.record(PendingThrow("p2", "a", 5))
    tracker.record(PendingThrow("p3", "a", 5))
    detected = tracker.detect_flood(tick=5)
    assert detected is not None
    assert detected.team_id == "a"
    assert set(detected.thrower_ids) == {"p1", "p2", "p3"}


def test_no_flood_across_different_teams():
    """Three throws in one tick split 2-1 across teams should not flood."""
    tracker = FloodThrowTracker()
    tracker.record(PendingThrow("p1", "a", 5))
    tracker.record(PendingThrow("p2", "a", 5))
    tracker.record(PendingThrow("p3", "b", 5))
    detected = tracker.detect_flood(tick=5)
    assert detected is None


def test_flood_clears_per_tick():
    tracker = FloodThrowTracker()
    tracker.record(PendingThrow("p1", "a", 5))
    tracker.record(PendingThrow("p2", "a", 5))
    tracker.record(PendingThrow("p3", "a", 5))
    assert tracker.detect_flood(tick=5) is not None
    # Next tick starts clean
    tracker.record(PendingThrow("p4", "a", 6))
    assert tracker.detect_flood(tick=6) is None


def test_flood_records_team_with_majority_when_split_above_threshold():
    """4-1 split: flood credited to the majority team."""
    tracker = FloodThrowTracker()
    tracker.record(PendingThrow("p1", "a", 5))
    tracker.record(PendingThrow("p2", "a", 5))
    tracker.record(PendingThrow("p3", "a", 5))
    tracker.record(PendingThrow("p4", "a", 5))
    tracker.record(PendingThrow("p5", "b", 5))
    detected = tracker.detect_flood(tick=5)
    assert detected is not None
    assert detected.team_id == "a"
    assert len(detected.thrower_ids) == 4
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_flood_throws.py -v`
Expected: `ModuleNotFoundError`.

- [x] **Step 3: Write the implementation**

Create `src/dodgeball_sim/flood_throws.py`:

```python
"""Flood-throw detection primitive.

A flood throw is three or more throws released in the same engine tick
from the same team. The primitive accumulates pending throws per tick
and reports a detection when the threshold is met. The existing
``SequenceLedger`` is not modified — the driver opens N sequences in
one tick and feeds this tracker in parallel.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


FLOOD_THRESHOLD: int = 3


@dataclass(frozen=True)
class PendingThrow:
    thrower_id: str
    team_id: str
    tick: int


@dataclass(frozen=True)
class FloodDetection:
    team_id: str
    thrower_ids: Tuple[str, ...]
    tick: int


@dataclass
class FloodThrowTracker:
    """Per-tick accumulator. State is keyed by tick and cleared on read."""

    _by_tick: Dict[int, List[PendingThrow]] = field(default_factory=lambda: defaultdict(list))

    def record(self, throw: PendingThrow) -> None:
        self._by_tick[throw.tick].append(throw)

    def detect_flood(self, *, tick: int) -> FloodDetection | None:
        throws = self._by_tick.get(tick, [])
        if len(throws) < FLOOD_THRESHOLD:
            return None
        # Bucket by team
        by_team: Dict[str, List[PendingThrow]] = defaultdict(list)
        for t in throws:
            by_team[t.team_id].append(t)
        # Pick the team with the most throws this tick
        best_team, best_throws = max(by_team.items(), key=lambda kv: len(kv[1]))
        if len(best_throws) < FLOOD_THRESHOLD:
            return None
        return FloodDetection(
            team_id=best_team,
            thrower_ids=tuple(t.thrower_id for t in best_throws),
            tick=tick,
        )


__all__ = [
    "FLOOD_THRESHOLD",
    "PendingThrow",
    "FloodDetection",
    "FloodThrowTracker",
]
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_flood_throws.py -v`
Expected: 6 passed.

- [x] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: 686 passed (680 + 6 new).

- [x] **Step 6: Commit**

```bash
git add src/dodgeball_sim/flood_throws.py tests/test_flood_throws.py
git commit -m "feat(engine): add flood-throw detection primitive

Detects 3+ same-team same-tick releases. SequenceLedger unchanged;
driver feeds this tracker alongside opening N sequences in one tick."
```

---

## Task 5: `StallTimer` primitive

**Files:**
- Create: `src/dodgeball_sim/stall_timer.py`
- Create: `tests/test_stall_timer.py`

The rec-league stall cap from brief §3.5: if one side controls all balls for more than 10 seconds without releasing a throw, balls are rolled to the opposing side. No cards, no warning.

- [x] **Step 1: Write the failing test**

Create `tests/test_stall_timer.py`:

```python
from dodgeball_sim.stall_timer import (
    StallTimerState,
    STALL_CAP_SECONDS,
    advance_holding,
    reset_on_throw,
    should_reset_balls,
)


def test_stall_cap_constant():
    assert STALL_CAP_SECONDS == 10


def test_fresh_state_no_reset():
    state = StallTimerState.fresh()
    assert state.seconds_holding == 0.0
    assert not should_reset_balls(state)


def test_advance_below_cap_no_reset():
    state = StallTimerState.fresh()
    state = advance_holding(state, seconds=5.0, side_controls_all_balls=True)
    assert state.seconds_holding == 5.0
    assert not should_reset_balls(state)


def test_advance_past_cap_triggers_reset():
    state = StallTimerState.fresh()
    state = advance_holding(state, seconds=11.0, side_controls_all_balls=True)
    assert state.seconds_holding >= STALL_CAP_SECONDS
    assert should_reset_balls(state)


def test_advance_when_not_holding_clears_timer():
    state = StallTimerState(seconds_holding=8.0)
    state = advance_holding(state, seconds=2.0, side_controls_all_balls=False)
    assert state.seconds_holding == 0.0


def test_reset_on_throw_clears_timer():
    state = StallTimerState(seconds_holding=7.0)
    state = reset_on_throw(state)
    assert state.seconds_holding == 0.0
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_stall_timer.py -v`
Expected: `ModuleNotFoundError`.

- [x] **Step 3: Write the implementation**

Create `src/dodgeball_sim/stall_timer.py`:

```python
"""Rec-league stall timer primitive (brief §3.5).

If a side holds every ball for STALL_CAP_SECONDS without a release,
balls are rolled to the opposite side. No cards, no warnings. Used by
the Tier 1 driver only; V11 / USAD uses the formal ``burden`` module.
"""

from __future__ import annotations

from dataclasses import dataclass


STALL_CAP_SECONDS: float = 10.0


@dataclass(frozen=True)
class StallTimerState:
    seconds_holding: float = 0.0

    @classmethod
    def fresh(cls) -> "StallTimerState":
        return cls(seconds_holding=0.0)


def advance_holding(
    state: StallTimerState,
    *,
    seconds: float,
    side_controls_all_balls: bool,
) -> StallTimerState:
    if not side_controls_all_balls:
        return StallTimerState(seconds_holding=0.0)
    return StallTimerState(seconds_holding=state.seconds_holding + seconds)


def reset_on_throw(state: StallTimerState) -> StallTimerState:
    return StallTimerState(seconds_holding=0.0)


def should_reset_balls(state: StallTimerState) -> bool:
    return state.seconds_holding >= STALL_CAP_SECONDS


__all__ = [
    "STALL_CAP_SECONDS",
    "StallTimerState",
    "advance_holding",
    "reset_on_throw",
    "should_reset_balls",
]
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_stall_timer.py -v`
Expected: 6 passed.

- [x] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: 692 passed (686 + 6 new).

- [x] **Step 6: Commit**

```bash
git add src/dodgeball_sim/stall_timer.py tests/test_stall_timer.py
git commit -m "feat(engine): add rec-league stall timer primitive

10-second hold cap; balls roll to opponent side. Tier 1 only;
V11 uses the formal burden module."
```

---

## Task 6: Tier 1 rules config

**Files:**
- Create: `src/dodgeball_sim/tier_1_rules.py`
- Create: `tests/test_tier_1_rules.py`

A small frozen dataclass encoding the §3.5 rule contract. No behavior — just the configuration the rec driver consumes. Keeping this separate from `rec_engine.py` makes it cheap for B/C to read tier 1's contract without importing driver code.

- [x] **Step 1: Write the failing test**

Create `tests/test_tier_1_rules.py`:

```python
from dodgeball_sim.tier_1_rules import TIER_1_RULES, TierRules


def test_tier_1_id():
    assert TIER_1_RULES.tier_id == "local_rec_league"
    assert TIER_1_RULES.display_name == "Local Rec League"


def test_tier_1_team_and_ball_counts():
    assert TIER_1_RULES.team_size == 6
    assert TIER_1_RULES.ball_count == 6
    assert TIER_1_RULES.balls_per_side_at_rush == 3


def test_tier_1_headshot_inverted():
    assert TIER_1_RULES.headshot_thrower_out is True


def test_tier_1_no_refs_no_discipline():
    assert TIER_1_RULES.refs_present is False
    assert TIER_1_RULES.discipline_modeled is False
    assert TIER_1_RULES.no_blocking_mode_enabled is False


def test_tier_1_chaos_retrieval():
    assert TIER_1_RULES.designated_retriever is False


def test_tier_1_burden_not_modeled():
    assert TIER_1_RULES.burden_modeled is False


def test_tier_1_game_end():
    assert TIER_1_RULES.time_cap_seconds == 300  # 5 min
    assert TIER_1_RULES.match_format == "single_game"


def test_tier_1_stall_cap():
    from dodgeball_sim.stall_timer import STALL_CAP_SECONDS
    assert TIER_1_RULES.stall_cap_seconds == STALL_CAP_SECONDS


def test_rules_dataclass_is_frozen():
    import dataclasses
    assert TierRules.__dataclass_params__.frozen is True
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_tier_1_rules.py -v`
Expected: `ModuleNotFoundError`.

- [x] **Step 3: Write the implementation**

Create `src/dodgeball_sim/tier_1_rules.py`:

```python
"""Tier 1 (Local Rec League) rule contract — encoded from brief §3.5.

This is config, not behavior. The rec driver consumes it; B/C consume
it indirectly via driver outputs. Higher tiers will add their own
``tier_N_rules.py`` modules in their respective sub-projects.
"""

from __future__ import annotations

from dataclasses import dataclass

from .stall_timer import STALL_CAP_SECONDS


@dataclass(frozen=True)
class TierRules:
    tier_id: str
    display_name: str
    team_size: int
    ball_count: int
    balls_per_side_at_rush: int
    headshot_thrower_out: bool
    refs_present: bool
    discipline_modeled: bool
    burden_modeled: bool
    no_blocking_mode_enabled: bool
    designated_retriever: bool
    stall_cap_seconds: float
    time_cap_seconds: int
    match_format: str  # "single_game" | "best_of_3" | ...
    substitutions_allowed: bool


TIER_1_RULES = TierRules(
    tier_id="local_rec_league",
    display_name="Local Rec League",
    team_size=6,
    ball_count=6,
    balls_per_side_at_rush=3,
    headshot_thrower_out=True,
    refs_present=False,
    discipline_modeled=False,
    burden_modeled=False,
    no_blocking_mode_enabled=False,
    designated_retriever=False,
    stall_cap_seconds=STALL_CAP_SECONDS,
    time_cap_seconds=300,
    match_format="single_game",
    substitutions_allowed=False,
)


__all__ = ["TierRules", "TIER_1_RULES"]
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_tier_1_rules.py -v`
Expected: 9 passed.

- [x] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: 701 passed (692 + 9 new).

- [x] **Step 6: Commit**

```bash
git add src/dodgeball_sim/tier_1_rules.py tests/test_tier_1_rules.py
git commit -m "feat(engine): encode Tier 1 rule contract from brief §3.5

Frozen TierRules dataclass; TIER_1_RULES instance for Local Rec League.
Higher tiers will add their own tier_N_rules modules."
```

---

## Task 7: `RecTier1Driver` core game loop (no moment emission yet)

**Files:**
- Create: `src/dodgeball_sim/rec_engine.py`
- Create: `tests/test_rec_engine.py`

This is the largest task. Implements `RecTier1Driver` end-to-end with the §3.5 rules, fatigue, stall, and flood detection — but does **not** yet emit moment events (that's Task 8 to keep this task reviewable).

The driver composes:
- Existing `ball_state`, `catch_queue`, `sequence`, `player_state` primitives.
- New `fatigue`, `stall_timer`, `flood_throws` primitives.
- `TIER_1_RULES` config.

It does **not** use `burden`, `discipline`, or `no_blocking`.

- [x] **Step 1: Write the failing test**

Create `tests/test_rec_engine.py`:

```python
import random

from dodgeball_sim.rec_engine import RecTier1Driver
from dodgeball_sim.engine_driver import DriverMatchInput
from dodgeball_sim.models import Player, PlayerRatings, CoachPolicy


def _make_player(pid: str, club: str) -> Player:
    return Player(
        id=pid,
        name=pid.upper(),
        ratings=PlayerRatings(
            accuracy=50, power=50, dodge=50, catch=50, stamina=60, tactical_iq=50
        ),
        club_id=club,
    )


def _make_input(seed: int = 42) -> DriverMatchInput:
    starters_a = tuple(f"a{i}" for i in range(6))
    starters_b = tuple(f"b{i}" for i in range(6))
    players = {pid: _make_player(pid, "a") for pid in starters_a}
    players.update({pid: _make_player(pid, "b") for pid in starters_b})
    return DriverMatchInput(
        match_id="m1",
        team_a_id="a",
        team_b_id="b",
        starters_a=starters_a,
        starters_b=starters_b,
        player_lookup=players,
        policy_a=CoachPolicy(),
        policy_b=CoachPolicy(),
        seed=seed,
    )


def test_driver_tier_id_is_local_rec_league():
    driver = RecTier1Driver()
    assert driver.tier_id == "local_rec_league"


def test_match_resolves_with_winner_or_draw():
    driver = RecTier1Driver()
    out = driver.run(_make_input(seed=1))
    assert out.winner_team_id in {"a", "b", None}


def test_match_emits_at_least_one_event():
    driver = RecTier1Driver()
    out = driver.run(_make_input(seed=2))
    assert len(out.events) > 0


def test_match_returns_final_active_counts():
    driver = RecTier1Driver()
    out = driver.run(_make_input(seed=3))
    assert out.final_active_a >= 0
    assert out.final_active_b >= 0
    assert out.final_active_a + out.final_active_b > 0  # match shouldn't kill everyone


def test_match_is_deterministic_for_seed():
    driver = RecTier1Driver()
    out1 = driver.run(_make_input(seed=99))
    out2 = driver.run(_make_input(seed=99))
    assert out1.winner_team_id == out2.winner_team_id
    assert out1.final_active_a == out2.final_active_a
    assert out1.final_active_b == out2.final_active_b


def test_different_seeds_produce_different_outcomes_over_many_runs():
    driver = RecTier1Driver()
    winners = {driver.run(_make_input(seed=s)).winner_team_id for s in range(50)}
    # over 50 seeds, both sides should win at least once given equal rosters
    assert "a" in winners
    assert "b" in winners


def test_time_cap_prevents_infinite_matches():
    driver = RecTier1Driver()
    # Run many seeds; none should fail to terminate
    for seed in range(20):
        out = driver.run(_make_input(seed=seed))
        assert out is not None
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_rec_engine.py -v`
Expected: `ModuleNotFoundError`.

- [x] **Step 3: Write the implementation**

Create `src/dodgeball_sim/rec_engine.py`:

```python
"""Rec Tier 1 driver — Local Rec League match loop.

Implements EngineDriver against TIER_1_RULES (brief §3.5). Composes:
  - existing primitives: ball_state, catch_queue, sequence, player_state
  - new primitives: fatigue, stall_timer, flood_throws

Does NOT use burden, discipline, or no_blocking — those are V11/USAD only.

Moment-event emission lives in this driver's `_emit_moments` hook
(populated in Task 8). Task 7 produces resolvable matches with events
but no moment_events tuple yet.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from .ball_state import BallState, OfficialBall
from .catch_queue import CatchQueueState, enqueue_out_player, return_player_on_catch
from .engine_driver import DriverMatchInput, DriverMatchOutput
from .fatigue import FatigueParams, FatigueState, accumulate, effectiveness, recover
from .flood_throws import FloodThrowTracker, PendingThrow
from .models import CoachPolicy, Player
from .moment_events import MomentEvent
from .player_state import OfficialPlayerState, OfficialPlayerStatus
from .rulesets import BallMaterial
from .stall_timer import (
    StallTimerState,
    advance_holding,
    reset_on_throw,
    should_reset_balls,
)
from .tier_1_rules import TIER_1_RULES, TierRules


TICK_SECONDS: float = 6.0
"""Engine tick in seconds; matches official_engine.py for consistency."""


@dataclass
class _MatchRuntime:
    """Mutable per-match runtime state held by the driver."""

    rng: random.Random
    rules: TierRules
    players: Dict[str, OfficialPlayerState]
    balls: List[OfficialBall]
    queues: Dict[str, CatchQueueState]
    fatigue: Dict[str, FatigueState]
    fatigue_params: Dict[str, FatigueParams]
    stall_a: StallTimerState
    stall_b: StallTimerState
    flood_tracker: FloodThrowTracker
    events: List[Any] = field(default_factory=list)
    moment_events: List[MomentEvent] = field(default_factory=list)
    tick: int = 0
    elapsed_seconds: float = 0.0


class RecTier1Driver:
    """Local Rec League driver. Implements EngineDriver."""

    tier_id: str = TIER_1_RULES.tier_id

    def run(self, match_input: DriverMatchInput) -> DriverMatchOutput:
        rt = self._init_runtime(match_input)
        team_a, team_b = match_input.team_a_id, match_input.team_b_id

        while not self._match_over(rt, team_a, team_b):
            self._tick(rt, match_input, team_a, team_b)
            rt.tick += 1
            rt.elapsed_seconds += TICK_SECONDS
            if rt.elapsed_seconds >= rt.rules.time_cap_seconds:
                break
            if rt.tick > 500:  # hard safety cap
                break

        active_a = sum(
            1
            for p in rt.players.values()
            if p.team_id == team_a and p.status == OfficialPlayerStatus.ACTIVE
        )
        active_b = sum(
            1
            for p in rt.players.values()
            if p.team_id == team_b and p.status == OfficialPlayerStatus.ACTIVE
        )

        if active_a > 0 and active_b == 0:
            winner = team_a
        elif active_b > 0 and active_a == 0:
            winner = team_b
        elif active_a > active_b:
            winner = team_a
        elif active_b > active_a:
            winner = team_b
        else:
            winner = None  # draw

        return DriverMatchOutput(
            events=tuple(rt.events),
            winner_team_id=winner,
            final_active_a=active_a,
            final_active_b=active_b,
            moment_events=tuple(rt.moment_events),
            replay_state=None,
        )

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------

    def _init_runtime(self, mi: DriverMatchInput) -> _MatchRuntime:
        rng = random.Random(mi.seed)
        rules = TIER_1_RULES

        # Players
        players: Dict[str, OfficialPlayerState] = {}
        for pid in mi.starters_a:
            players[pid] = OfficialPlayerState(
                player_id=pid,
                team_id=mi.team_a_id,
                status=OfficialPlayerStatus.ACTIVE,
                is_starter=True,
            )
        for pid in mi.starters_b:
            players[pid] = OfficialPlayerState(
                player_id=pid,
                team_id=mi.team_b_id,
                status=OfficialPlayerStatus.ACTIVE,
                is_starter=True,
            )

        # Balls — split evenly at opening rush. Tier 1 always uses foam.
        # Construct OfficialBall with the existing dataclass fields from
        # src/dodgeball_sim/ball_state.py (ball_id, material required;
        # state defaults to INACTIVE_CENTER; activated defaults to False).
        per_side = rules.balls_per_side_at_rush
        balls: List[OfficialBall] = []
        for i in range(per_side):
            balls.append(
                OfficialBall(
                    ball_id=f"ball_a_{i}",
                    material=BallMaterial.FOAM,
                    side=mi.team_a_id,
                )
            )
        for i in range(per_side):
            balls.append(
                OfficialBall(
                    ball_id=f"ball_b_{i}",
                    material=BallMaterial.FOAM,
                    side=mi.team_b_id,
                )
            )

        # Fatigue: derive params from existing PlayerRatings.stamina
        # (Plan B will replace this with conditioning_curve attribute)
        fatigue_params: Dict[str, FatigueParams] = {}
        fatigue: Dict[str, FatigueState] = {}
        for pid in list(mi.starters_a) + list(mi.starters_b):
            stamina = float(mi.player_lookup[pid].ratings.stamina)
            fatigue_params[pid] = FatigueParams(conditioning_curve=stamina)
            fatigue[pid] = FatigueState.fresh()

        queues = {
            mi.team_a_id: CatchQueueState(team_id=mi.team_a_id),
            mi.team_b_id: CatchQueueState(team_id=mi.team_b_id),
        }

        return _MatchRuntime(
            rng=rng,
            rules=rules,
            players=players,
            balls=balls,
            queues=queues,
            fatigue=fatigue,
            fatigue_params=fatigue_params,
            stall_a=StallTimerState.fresh(),
            stall_b=StallTimerState.fresh(),
            flood_tracker=FloodThrowTracker(),
        )

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def _match_over(self, rt: _MatchRuntime, team_a: str, team_b: str) -> bool:
        a_alive = any(
            p.status == OfficialPlayerStatus.ACTIVE and p.team_id == team_a
            for p in rt.players.values()
        )
        b_alive = any(
            p.status == OfficialPlayerStatus.ACTIVE and p.team_id == team_b
            for p in rt.players.values()
        )
        return not (a_alive and b_alive)

    def _tick(
        self,
        rt: _MatchRuntime,
        mi: DriverMatchInput,
        team_a: str,
        team_b: str,
    ) -> None:
        # 1. Choose throwers (any active player holding a ball may throw)
        throwers_by_team = self._select_throwers(rt, mi, team_a, team_b)

        # 2. Record throws into flood tracker; resolve each
        for team_id, thrower_ids in throwers_by_team.items():
            for thrower_id in thrower_ids:
                rt.flood_tracker.record(
                    PendingThrow(thrower_id=thrower_id, team_id=team_id, tick=rt.tick)
                )
                self._resolve_throw(rt, mi, thrower_id, team_id, team_a, team_b)

        # 3. Stall handling — if either side controls all balls and didn't throw
        self._update_stall(rt, team_a, team_b, threw_a=bool(throwers_by_team.get(team_a)),
                           threw_b=bool(throwers_by_team.get(team_b)))

        # 4. Fatigue recovery for idle players
        threw_pids = {
            pid for pids in throwers_by_team.values() for pid in pids
        }
        for pid, state in list(rt.fatigue.items()):
            if pid in threw_pids:
                rt.fatigue[pid] = accumulate(
                    state, action_cost=0.05, params=rt.fatigue_params[pid]
                )
            else:
                rt.fatigue[pid] = recover(
                    state, seconds_idle=TICK_SECONDS, params=rt.fatigue_params[pid]
                )

    def _select_throwers(
        self,
        rt: _MatchRuntime,
        mi: DriverMatchInput,
        team_a: str,
        team_b: str,
    ) -> Dict[str, List[str]]:
        """Pick up to ~2 throwers per team per tick from active players on that side.

        Tier 1 is intentionally non-tactical (Plan C adds the four knobs).
        For now, randomly select active players who are on a side that
        controls at least one ball. This produces matches that resolve
        and gives flood-throws an emergent chance.
        """
        result: Dict[str, List[str]] = {team_a: [], team_b: []}
        for team_id in (team_a, team_b):
            active = [
                p for p in rt.players.values()
                if p.team_id == team_id and p.status == OfficialPlayerStatus.ACTIVE
            ]
            if not active:
                continue
            # Lower chance to throw when gassed
            candidates = []
            for p in active:
                eff = effectiveness(rt.fatigue[p.player_id])
                if rt.rng.random() < 0.4 * eff:
                    candidates.append(p.player_id)
            # Cap throws per tick
            result[team_id] = candidates[:3]
        return result

    def _resolve_throw(
        self,
        rt: _MatchRuntime,
        mi: DriverMatchInput,
        thrower_id: str,
        thrower_team_id: str,
        team_a: str,
        team_b: str,
    ) -> None:
        # Pick a target from the opposing team's active players
        opp_team = team_b if thrower_team_id == team_a else team_a
        opp_active = [
            p for p in rt.players.values()
            if p.team_id == opp_team and p.status == OfficialPlayerStatus.ACTIVE
        ]
        if not opp_active:
            return

        thrower = mi.player_lookup[thrower_id]
        target_state = rt.rng.choice(opp_active)
        target = mi.player_lookup[target_state.player_id]

        thrower_eff = effectiveness(rt.fatigue[thrower_id])
        target_eff = effectiveness(rt.fatigue[target_state.player_id])

        # Headshot inverted: 5% headshot chance regardless
        if rt.rng.random() < 0.05:
            # thrower goes out, target stays
            self._mark_out(rt, thrower_id, thrower_team_id, team_a, team_b)
            rt.events.append({"type": "headshot_thrower_out", "thrower": thrower_id})
            reset_on_throw_call(rt, thrower_team_id, team_a)
            return

        # Resolve as basic accuracy-vs-dodge with effectiveness modulating
        accuracy = (thrower.ratings.accuracy / 100.0) * thrower_eff
        dodge = (target.ratings.dodge / 100.0) * target_eff
        catch_skill = (target.ratings.catch / 100.0) * target_eff

        roll = rt.rng.random()
        if roll < catch_skill * 0.4:
            # CATCH — thrower out, one returning teammate
            self._mark_out(rt, thrower_id, thrower_team_id, team_a, team_b)
            catcher_team = target_state.team_id
            ret_event, returning_pid = return_player_on_catch(
                rt.queues[catcher_team],
                sequence_id=f"t{rt.tick}",
                match_id=mi.match_id,
            )
            if ret_event is not None and returning_pid is not None:
                rt.events.append({"type": "catch_return", "catcher": target_state.player_id})
                returning = rt.players[returning_pid]
                returning.status = OfficialPlayerStatus.ACTIVE
        elif roll < catch_skill * 0.4 + accuracy * (1.0 - dodge):
            # HIT — target out
            self._mark_out(rt, target_state.player_id, target_state.team_id, team_a, team_b)
            rt.events.append({"type": "hit", "thrower": thrower_id, "target": target_state.player_id})
        else:
            # DODGE / miss — no state change
            rt.events.append({"type": "miss", "thrower": thrower_id, "target": target_state.player_id})

        reset_on_throw_call(rt, thrower_team_id, team_a)

    def _mark_out(
        self,
        rt: _MatchRuntime,
        player_id: str,
        team_id: str,
        team_a: str,
        team_b: str,
    ) -> None:
        player = rt.players.get(player_id)
        if player is None or player.status != OfficialPlayerStatus.ACTIVE:
            return
        player.status = OfficialPlayerStatus.QUEUED
        enqueue_out_player(
            rt.queues[team_id],
            player_id=player_id,
            is_starter=player.is_starter,
            match_id="rt",
        )

    def _update_stall(
        self,
        rt: _MatchRuntime,
        team_a: str,
        team_b: str,
        *,
        threw_a: bool,
        threw_b: bool,
    ) -> None:
        # "Side controls all balls" for Tier 1 just means every ball's
        # `side` field points at that team. No state filter — Tier 1's
        # stall mechanic ignores ball state, only ownership.
        a_controls_all = all(b.side == team_a for b in rt.balls)
        b_controls_all = all(b.side == team_b for b in rt.balls)

        if threw_a:
            rt.stall_a = reset_on_throw(rt.stall_a)
        else:
            rt.stall_a = advance_holding(rt.stall_a, seconds=TICK_SECONDS, side_controls_all_balls=a_controls_all)
        if threw_b:
            rt.stall_b = reset_on_throw(rt.stall_b)
        else:
            rt.stall_b = advance_holding(rt.stall_b, seconds=TICK_SECONDS, side_controls_all_balls=b_controls_all)

        if should_reset_balls(rt.stall_a):
            for b in rt.balls:
                if b.side == team_a:
                    b.side = team_b
            rt.stall_a = StallTimerState.fresh()
            rt.events.append({"type": "stall_reset", "from": team_a})
        if should_reset_balls(rt.stall_b):
            for b in rt.balls:
                if b.side == team_b:
                    b.side = team_a
            rt.stall_b = StallTimerState.fresh()
            rt.events.append({"type": "stall_reset", "from": team_b})


def reset_on_throw_call(rt: _MatchRuntime, team_id: str, team_a: str) -> None:
    if team_id == team_a:
        rt.stall_a = reset_on_throw(rt.stall_a)
    else:
        rt.stall_b = reset_on_throw(rt.stall_b)


__all__ = ["RecTier1Driver"]
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_rec_engine.py -v`
Expected: 7 passed.

- [x] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: 708 passed (701 + 7 new). **V11 tests must still all pass.**

- [x] **Step 6: Commit**

```bash
git add src/dodgeball_sim/rec_engine.py tests/test_rec_engine.py
git commit -m "feat(engine): add RecTier1Driver core game loop

Composes ball_state, catch_queue, fatigue, stall_timer, flood_throws
per TIER_1_RULES (§3.5). Headshot-thrower-out, chaos retrieval, 5-min
time cap, single game. Moment-event emission added in Task 8.
V11/USAD tests unchanged."
```

---

## Task 8: Moment event emission in `RecTier1Driver`

**Files:**
- Modify: `src/dodgeball_sim/rec_engine.py`
- Modify: `tests/test_rec_engine.py`

The driver now detects and emits the six moment events. This task is separated from Task 7 so the core resolution logic can be reviewed independently from the moment-detection heuristics.

Detection rules:
- **`DramaticCatch`** — emitted in `_resolve_throw` when a catch returns a player from the queue.
- **`LateGameEscape`** — emitted in `_tick` when one team has exactly 1 active and the other has ≥3. Suppressed within one match after first emission to avoid spam.
- **`OneVOneFinale`** — emitted when both teams have exactly 1 active. Suppressed after first emission.
- **`GassedCollapse`** — emitted in `_mark_out` when the player going out has `fatigue.is_gassed()`.
- **`FloodThrow`** — emitted at end of each tick if `flood_tracker.detect_flood(tick=rt.tick)` returns non-None.
- **`Comeback`** — emitted when a team that was at one point ≥3 down ties or leads in active count. Each team can emit at most once.

- [x] **Step 1: Write the failing test**

Append to `tests/test_rec_engine.py`:

```python
from dodgeball_sim.moment_events import (
    Comeback,
    DramaticCatch,
    FloodThrow,
    GassedCollapse,
    LateGameEscape,
    OneVOneFinale,
    MomentKind,
)


def _moment_kinds_across_seeds(seeds=range(80)) -> set[MomentKind]:
    driver = RecTier1Driver()
    seen: set[MomentKind] = set()
    for s in seeds:
        out = driver.run(_make_input(seed=s))
        for ev in out.moment_events:
            seen.add(ev.kind)
    return seen


def test_emits_at_least_some_moments_across_runs():
    driver = RecTier1Driver()
    any_emitted = False
    for s in range(20):
        out = driver.run(_make_input(seed=s))
        if out.moment_events:
            any_emitted = True
            break
    assert any_emitted, "no moments emitted across 20 seeds — emission is broken"


def test_dramatic_catch_emits_when_catch_returns_player():
    """Run many seeds; at least one match should produce a dramatic catch."""
    seen = _moment_kinds_across_seeds()
    assert MomentKind.DRAMATIC_CATCH in seen


def test_flood_throw_or_late_escape_emerges_across_seeds():
    """Either flood throws or late-game escapes should appear across enough seeds."""
    seen = _moment_kinds_across_seeds()
    assert seen & {MomentKind.FLOOD_THROW, MomentKind.LATE_GAME_ESCAPE}


def test_one_v_one_finale_emerges_across_seeds():
    seen = _moment_kinds_across_seeds()
    assert MomentKind.ONE_V_ONE_FINALE in seen
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_rec_engine.py -v`
Expected: the four new tests fail (moments not emitted).

- [x] **Step 3: Implement moment emission**

Modify `src/dodgeball_sim/rec_engine.py`:

In `_MatchRuntime`, add suppressing flags:

```python
@dataclass
class _MatchRuntime:
    # ... existing fields ...
    late_escape_emitted_for: Dict[str, bool] = field(default_factory=dict)
    one_v_one_emitted: bool = False
    comeback_emitted_for: Dict[str, bool] = field(default_factory=dict)
    low_water_active: Dict[str, int] = field(default_factory=dict)
    comeback_catches: Dict[str, int] = field(default_factory=dict)
```

Update `_init_runtime` to initialize these:

```python
        return _MatchRuntime(
            rng=rng,
            rules=rules,
            players=players,
            balls=balls,
            queues=queues,
            fatigue=fatigue,
            fatigue_params=fatigue_params,
            stall_a=StallTimerState.fresh(),
            stall_b=StallTimerState.fresh(),
            flood_tracker=FloodThrowTracker(),
            late_escape_emitted_for={mi.team_a_id: False, mi.team_b_id: False},
            comeback_emitted_for={mi.team_a_id: False, mi.team_b_id: False},
            low_water_active={
                mi.team_a_id: len(mi.starters_a),
                mi.team_b_id: len(mi.starters_b),
            },
            comeback_catches={mi.team_a_id: 0, mi.team_b_id: 0},
        )
```

Add the emitters. Place at end of `_tick`:

```python
        # 5. Moment detection: flood, late escape, 1v1, comeback
        flood = rt.flood_tracker.detect_flood(tick=rt.tick)
        if flood is not None:
            rt.moment_events.append(
                FloodThrow(
                    match_id=mi.match_id,
                    tick=rt.tick,
                    thrower_team_id=flood.team_id,
                    thrower_ids=flood.thrower_ids,
                )
            )

        active_a = sum(
            1 for p in rt.players.values()
            if p.team_id == team_a and p.status == OfficialPlayerStatus.ACTIVE
        )
        active_b = sum(
            1 for p in rt.players.values()
            if p.team_id == team_b and p.status == OfficialPlayerStatus.ACTIVE
        )

        # Late escape
        if active_a == 1 and active_b >= 3 and not rt.late_escape_emitted_for[team_a]:
            survivor = next(
                p for p in rt.players.values()
                if p.team_id == team_a and p.status == OfficialPlayerStatus.ACTIVE
            )
            rt.moment_events.append(
                LateGameEscape(
                    match_id=mi.match_id,
                    tick=rt.tick,
                    survivor_id=survivor.player_id,
                    survivor_team_id=team_a,
                    attacker_team_id=team_b,
                    attacker_count=active_b,
                )
            )
            rt.late_escape_emitted_for[team_a] = True
        if active_b == 1 and active_a >= 3 and not rt.late_escape_emitted_for[team_b]:
            survivor = next(
                p for p in rt.players.values()
                if p.team_id == team_b and p.status == OfficialPlayerStatus.ACTIVE
            )
            rt.moment_events.append(
                LateGameEscape(
                    match_id=mi.match_id,
                    tick=rt.tick,
                    survivor_id=survivor.player_id,
                    survivor_team_id=team_b,
                    attacker_team_id=team_a,
                    attacker_count=active_a,
                )
            )
            rt.late_escape_emitted_for[team_b] = True

        # 1v1 finale
        if active_a == 1 and active_b == 1 and not rt.one_v_one_emitted:
            a_alive = next(
                p for p in rt.players.values()
                if p.team_id == team_a and p.status == OfficialPlayerStatus.ACTIVE
            )
            b_alive = next(
                p for p in rt.players.values()
                if p.team_id == team_b and p.status == OfficialPlayerStatus.ACTIVE
            )
            rt.moment_events.append(
                OneVOneFinale(
                    match_id=mi.match_id,
                    tick=rt.tick,
                    player_a_id=a_alive.player_id,
                    player_b_id=b_alive.player_id,
                    tick_started=rt.tick,
                )
            )
            rt.one_v_one_emitted = True

        # Update low-water mark and check comeback
        rt.low_water_active[team_a] = min(rt.low_water_active[team_a], active_a)
        rt.low_water_active[team_b] = min(rt.low_water_active[team_b], active_b)
        for team_id, opp in [(team_a, active_b), (team_b, active_a)]:
            low = rt.low_water_active[team_id]
            my_active = active_a if team_id == team_a else active_b
            other_starters = len(
                mi.starters_b if team_id == team_a else mi.starters_a
            )
            deficit_at_low = other_starters - low
            if (
                deficit_at_low >= 3
                and my_active >= opp
                and not rt.comeback_emitted_for[team_id]
            ):
                rt.moment_events.append(
                    Comeback(
                        match_id=mi.match_id,
                        tick=rt.tick,
                        team_id=team_id,
                        deficit_at_low_point=deficit_at_low,
                        catches_during_comeback=rt.comeback_catches[team_id],
                    )
                )
                rt.comeback_emitted_for[team_id] = True
```

Update `_resolve_throw` to emit `DramaticCatch` on catch and count `comeback_catches`:

```python
        if roll < catch_skill * 0.4:
            # CATCH
            self._mark_out(rt, thrower_id, thrower_team_id, team_a, team_b)
            catcher_team = target_state.team_id
            ret_event, returning_pid = return_player_on_catch(
                rt.queues[catcher_team],
                sequence_id=f"t{rt.tick}",
                match_id=mi.match_id,
            )
            if ret_event is not None and returning_pid is not None:
                rt.events.append({"type": "catch_return", "catcher": target_state.player_id})
                returning = rt.players[returning_pid]
                returning.status = OfficialPlayerStatus.ACTIVE
                # Count toward comeback
                rt.comeback_catches[catcher_team] = rt.comeback_catches.get(catcher_team, 0) + 1
                # Emit DramaticCatch
                active_a_now = sum(
                    1 for p in rt.players.values()
                    if p.team_id == team_a and p.status == OfficialPlayerStatus.ACTIVE
                )
                active_b_now = sum(
                    1 for p in rt.players.values()
                    if p.team_id == team_b and p.status == OfficialPlayerStatus.ACTIVE
                )
                rt.moment_events.append(
                    DramaticCatch(
                        match_id=mi.match_id,
                        tick=rt.tick,
                        catcher_id=target_state.player_id,
                        catcher_team_id=catcher_team,
                        thrower_id=thrower_id,
                        thrower_team_id=thrower_team_id,
                        returning_player_id=returning_pid,
                        active_count_a=active_a_now,
                        active_count_b=active_b_now,
                    )
                )
```

Update `_mark_out` to emit `GassedCollapse`:

```python
    def _mark_out(
        self,
        rt: _MatchRuntime,
        player_id: str,
        team_id: str,
        team_a: str,
        team_b: str,
    ) -> None:
        player = rt.players.get(player_id)
        if player is None or player.status != OfficialPlayerStatus.ACTIVE:
            return
        # Gassed collapse check before status change
        fstate = rt.fatigue.get(player_id)
        if fstate is not None and fstate.is_gassed():
            rt.moment_events.append(
                GassedCollapse(
                    match_id="rt",
                    tick=rt.tick,
                    player_id=player_id,
                    team_id=team_id,
                    fatigue_pct=fstate.value,
                )
            )
        player.status = OfficialPlayerStatus.QUEUED
        enqueue_out_player(
            rt.queues[team_id],
            player_id=player_id,
            is_starter=player.is_starter,
            match_id="rt",
        )
```

Add the imports at the top of `rec_engine.py`:

```python
from .moment_events import (
    Comeback,
    DramaticCatch,
    FloodThrow,
    GassedCollapse,
    LateGameEscape,
    MomentEvent,
    OneVOneFinale,
)
```

(Replace the previous single `MomentEvent` import.)

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_rec_engine.py -v`
Expected: 11 passed.

- [x] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: 712 passed (708 + 4 new).

- [x] **Step 6: Commit**

```bash
git add src/dodgeball_sim/rec_engine.py tests/test_rec_engine.py
git commit -m "feat(engine): emit six recognition moments from RecTier1Driver

DramaticCatch on returning catches; LateGameEscape on 1vN≥3;
OneVOneFinale on 1v1; GassedCollapse when an out player is past
the gassed threshold; FloodThrow on tick-level 3+ same-team
releases; Comeback when a team recovers from a ≥3 deficit.

UI surfacing is Plan C; this is just the emission contract."
```

---

## Task 9: `OfficialDriver` — wrap V11's autonomous engine

**Files:**
- Create: `src/dodgeball_sim/official_driver.py`
- Create: `tests/test_official_driver.py`

A thin adapter so V11's existing `run_autonomous_game` satisfies the `EngineDriver` protocol. This is the architectural proof that hybrid works — the existing official engine is *unbundled* from primitive ownership without being rewritten.

- [x] **Step 1: Write the failing test**

Create `tests/test_official_driver.py`:

```python
from dodgeball_sim.official_driver import OfficialDriver
from dodgeball_sim.engine_driver import DriverMatchInput
from dodgeball_sim.models import Player, PlayerRatings, CoachPolicy


def _make_player(pid: str, club: str) -> Player:
    return Player(
        id=pid,
        name=pid.upper(),
        ratings=PlayerRatings(50, 50, 50, 50, 60, 50),
        club_id=club,
    )


def _make_input(seed: int = 1) -> DriverMatchInput:
    starters_a = tuple(f"a{i}" for i in range(6))
    starters_b = tuple(f"b{i}" for i in range(6))
    players = {pid: _make_player(pid, "a") for pid in starters_a}
    players.update({pid: _make_player(pid, "b") for pid in starters_b})
    return DriverMatchInput(
        match_id="m1",
        team_a_id="a",
        team_b_id="b",
        starters_a=starters_a,
        starters_b=starters_b,
        player_lookup=players,
        policy_a=CoachPolicy(),
        policy_b=CoachPolicy(),
        seed=seed,
        config={"ruleset": "official_foam"},
    )


def test_official_driver_tier_id():
    driver = OfficialDriver()
    assert driver.tier_id == "official"


def test_official_driver_runs_match():
    driver = OfficialDriver()
    out = driver.run(_make_input(seed=7))
    assert out.winner_team_id in {"a", "b", None}
    assert isinstance(out.final_active_a, int)
    assert isinstance(out.final_active_b, int)


def test_official_driver_deterministic_for_seed():
    driver = OfficialDriver()
    out1 = driver.run(_make_input(seed=42))
    out2 = driver.run(_make_input(seed=42))
    assert out1.winner_team_id == out2.winner_team_id
    assert out1.final_active_a == out2.final_active_a
    assert out1.final_active_b == out2.final_active_b


def test_official_driver_supports_ruleset_config():
    driver = OfficialDriver()
    inp = _make_input(seed=5)
    out = driver.run(inp)
    assert out is not None
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_official_driver.py -v`
Expected: `ModuleNotFoundError`.

- [x] **Step 3: Write the implementation**

Create `src/dodgeball_sim/official_driver.py`:

```python
"""Thin wrapper around V11's autonomous official engine to satisfy
``EngineDriver``. Does not rewrite the engine; just adapts the I/O.
"""

from __future__ import annotations

from typing import Dict

from .engine_driver import DriverMatchInput, DriverMatchOutput
from .official_engine import AutonomousGameResult, run_autonomous_game
from .rulesets import RulesetSelection


_DEFAULT_RULESET = "official_foam"


class OfficialDriver:
    tier_id: str = "official"

    def run(self, match_input: DriverMatchInput) -> DriverMatchOutput:
        ruleset_name: str = match_input.config.get("ruleset", _DEFAULT_RULESET)
        # RulesetSelection is a str-Enum; .to_profile() returns the
        # corresponding RulesetProfile. See src/dodgeball_sim/rulesets.py.
        profile = RulesetSelection(ruleset_name).to_profile()

        result: AutonomousGameResult = run_autonomous_game(
            profile=profile,
            match_id=match_input.match_id,
            team_a_id=match_input.team_a_id,
            team_b_id=match_input.team_b_id,
            starters_a=match_input.starters_a,
            starters_b=match_input.starters_b,
            player_lookup=match_input.player_lookup,
            policy_a=match_input.policy_a,
            policy_b=match_input.policy_b,
            seed=match_input.seed,
        )

        return DriverMatchOutput(
            events=result.events,
            winner_team_id=result.winner_team_id,
            final_active_a=result.final_active_a,
            final_active_b=result.final_active_b,
            moment_events=(),  # V11 does not emit moments; Plan A scope
            replay_state=result.replay_state,
        )


__all__ = ["OfficialDriver"]
```

- [x] **Step 4: Sanity-check the ruleset accessor still works**

Run: `python -c "from dodgeball_sim.rulesets import RulesetSelection; print(RulesetSelection('official_foam').to_profile().name)"`
Expected: prints a profile name (e.g. `foam_open`). If this errors, `RulesetSelection` may have shifted upstream — search for `to_profile` usage in `franchise.py` and adjust if necessary.

- [x] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_official_driver.py -v`
Expected: 4 passed.

- [x] **Step 6: Run the full suite**

Run: `python -m pytest -q`
Expected: 716 passed (712 + 4 new). **All V11 tests must still pass.**

- [x] **Step 7: Commit**

```bash
git add src/dodgeball_sim/official_driver.py tests/test_official_driver.py
git commit -m "feat(engine): wrap V11 official engine as OfficialDriver

Thin adapter satisfying EngineDriver protocol. run_autonomous_game
is unchanged. Proves the hybrid architecture: existing official
engine is unbundled from primitive ownership without rewrites."
```

---

## Task 10: Full V11 regression gate

**Files:**
- None (verification only)

This is a gate task, not a coding task. Plan A is wrong if any existing V11 test has regressed.

- [x] **Step 1: Run the full test suite**

Run: `python -m pytest -q`
Expected: 716 passed. **No failures, no errors, no skips that weren't there before.**

- [x] **Step 2: Spot-check the V11 conformance matrix specifically**

Run: `python -m pytest tests/test_official_conformance_matrix.py -v`
Expected: All previously-passing entries still pass.

- [x] **Step 3: Spot-check the autonomous game test**

Run: `python -m pytest tests/test_official_autonomous_game.py -v`
Expected: All previously-passing entries still pass.

- [x] **Step 4: Commit a checkpoint marker if any incidental fixes were needed**

If steps 1–3 all passed cleanly, **no commit is needed** — Plan A's invariant is intact. If any incidental fix was required to keep V11 green (e.g. an import shadowing), commit it separately with message starting `fix(engine): preserve V11 invariant —`.

---

## Task 11: Tier 1 integration test

**Files:**
- Create: `tests/test_tier_1_integration.py`

End-to-end test that proves Plan A's invariants hold across drivers: rec driver resolves, official driver resolves, both implement the same protocol, results have the expected shape.

- [x] **Step 1: Write the integration test**

Create `tests/test_tier_1_integration.py`:

```python
from dodgeball_sim.engine_driver import (
    DriverMatchInput,
    DriverMatchOutput,
    EngineDriver,
)
from dodgeball_sim.rec_engine import RecTier1Driver
from dodgeball_sim.official_driver import OfficialDriver
from dodgeball_sim.models import Player, PlayerRatings, CoachPolicy


def _make_player(pid: str, club: str) -> Player:
    return Player(
        id=pid,
        name=pid.upper(),
        ratings=PlayerRatings(60, 50, 55, 55, 65, 50),
        club_id=club,
    )


def _make_input(seed: int = 1, config: dict | None = None) -> DriverMatchInput:
    starters_a = tuple(f"a{i}" for i in range(6))
    starters_b = tuple(f"b{i}" for i in range(6))
    players = {pid: _make_player(pid, "a") for pid in starters_a}
    players.update({pid: _make_player(pid, "b") for pid in starters_b})
    return DriverMatchInput(
        match_id="m1",
        team_a_id="a",
        team_b_id="b",
        starters_a=starters_a,
        starters_b=starters_b,
        player_lookup=players,
        policy_a=CoachPolicy(),
        policy_b=CoachPolicy(),
        seed=seed,
        config=config or {},
    )


def test_both_drivers_satisfy_protocol():
    drivers: list[EngineDriver] = [RecTier1Driver(), OfficialDriver()]
    for drv in drivers:
        assert isinstance(drv.tier_id, str)
        out = drv.run(_make_input(seed=11, config={"ruleset": "official_foam"}))
        assert isinstance(out, DriverMatchOutput)


def test_rec_driver_produces_moments_official_does_not():
    rec_out = RecTier1Driver().run(_make_input(seed=7))
    off_out = OfficialDriver().run(_make_input(seed=7, config={"ruleset": "official_foam"}))
    # Official driver doesn't emit moments in Plan A scope
    assert off_out.moment_events == ()
    # Rec driver should emit at least sometimes — verify across a few seeds
    any_moments = False
    for s in range(20):
        if RecTier1Driver().run(_make_input(seed=s)).moment_events:
            any_moments = True
            break
    assert any_moments


def test_match_outcomes_distributed_across_seeds():
    """Across 50 seeds with even rosters, both teams should win some matches in both drivers."""
    for driver_cls, cfg in [(RecTier1Driver, {}), (OfficialDriver, {"ruleset": "official_foam"})]:
        winners = {
            driver_cls().run(_make_input(seed=s, config=cfg)).winner_team_id
            for s in range(50)
        }
        assert "a" in winners
        assert "b" in winners
```

- [x] **Step 2: Run the integration test**

Run: `python -m pytest tests/test_tier_1_integration.py -v`
Expected: 3 passed.

- [x] **Step 3: Run the full suite**

Run: `python -m pytest -q`
Expected: 719 passed (716 + 3 new).

- [x] **Step 4: Commit**

```bash
git add tests/test_tier_1_integration.py
git commit -m "test(engine): tier 1 integration — both drivers satisfy protocol

Cross-driver invariants: protocol satisfaction, moment emission only
from rec driver in Plan A scope, balanced outcomes across seeds."
```

---

## Task 12: Tier 1 sanity probe

**Files:**
- Create: `tools/tier_1_sanity_probe.py`
- Create: `tests/test_tier_1_sanity_probe.py`

The Plan A gate. A runnable script that simulates 25 Tier 1 matches, reports any failures, and asserts the per-match invariants from the plan-level guarantees. This is *not* the full simulation-health probe — that's Plan D. This probe just proves Tier 1 matches resolve and emit moments.

- [x] **Step 1: Write the test for the probe**

Create `tests/test_tier_1_sanity_probe.py`:

```python
from tools.tier_1_sanity_probe import run_sanity_probe, SanityProbeReport


def test_sanity_probe_runs_25_matches_by_default():
    report = run_sanity_probe()
    assert report.matches_run == 25


def test_all_matches_resolve():
    report = run_sanity_probe()
    assert report.matches_resolved == report.matches_run
    assert report.exceptions == []


def test_average_moment_events_per_match_at_least_one():
    report = run_sanity_probe()
    assert report.total_moment_events / max(1, report.matches_run) >= 1.0


def test_report_is_dataclass_with_expected_fields():
    report = run_sanity_probe(matches=5)
    assert isinstance(report, SanityProbeReport)
    assert hasattr(report, "matches_run")
    assert hasattr(report, "matches_resolved")
    assert hasattr(report, "total_moment_events")
    assert hasattr(report, "exceptions")
    assert hasattr(report, "winner_counts")
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_tier_1_sanity_probe.py -v`
Expected: `ModuleNotFoundError`.

- [x] **Step 3: Create the tools directory marker if missing**

Run: `python -c "import os; os.makedirs('tools', exist_ok=True); open('tools/__init__.py','a').close()"`

(Tools is treated as a package so the test can `import tools.tier_1_sanity_probe`.)

- [x] **Step 4: Write the sanity probe**

Create `tools/tier_1_sanity_probe.py`:

```python
"""Tier 1 sanity probe — Plan A gate.

Runs N Tier 1 matches end-to-end and asserts that they all resolve,
emit at least one moment event on average, and produce no exceptions.

Plan D will introduce the full simulation-health probe with statistical
outputs across both drivers. This probe is intentionally small.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import List

from dodgeball_sim.engine_driver import DriverMatchInput
from dodgeball_sim.models import CoachPolicy, Player, PlayerRatings
from dodgeball_sim.rec_engine import RecTier1Driver


@dataclass
class SanityProbeReport:
    matches_run: int = 0
    matches_resolved: int = 0
    total_moment_events: int = 0
    exceptions: List[str] = field(default_factory=list)
    winner_counts: Counter = field(default_factory=Counter)


def _make_player(pid: str, club: str) -> Player:
    return Player(
        id=pid,
        name=pid.upper(),
        ratings=PlayerRatings(55, 55, 55, 55, 60, 55),
        club_id=club,
    )


def _make_input(seed: int) -> DriverMatchInput:
    starters_a = tuple(f"a{i}" for i in range(6))
    starters_b = tuple(f"b{i}" for i in range(6))
    players = {pid: _make_player(pid, "a") for pid in starters_a}
    players.update({pid: _make_player(pid, "b") for pid in starters_b})
    return DriverMatchInput(
        match_id=f"sanity_{seed}",
        team_a_id="a",
        team_b_id="b",
        starters_a=starters_a,
        starters_b=starters_b,
        player_lookup=players,
        policy_a=CoachPolicy(),
        policy_b=CoachPolicy(),
        seed=seed,
    )


def run_sanity_probe(matches: int = 25, seed_start: int = 1) -> SanityProbeReport:
    report = SanityProbeReport()
    driver = RecTier1Driver()
    for i in range(matches):
        seed = seed_start + i
        report.matches_run += 1
        try:
            out = driver.run(_make_input(seed))
        except Exception as e:  # pragma: no cover - probe-level safety
            report.exceptions.append(f"seed={seed}: {type(e).__name__}: {e}")
            continue
        report.matches_resolved += 1
        report.total_moment_events += len(out.moment_events)
        winner = out.winner_team_id or "draw"
        report.winner_counts[winner] += 1
    return report


def main() -> int:
    report = run_sanity_probe()
    print("=== Tier 1 Sanity Probe ===")
    print(f"Matches run:         {report.matches_run}")
    print(f"Matches resolved:    {report.matches_resolved}")
    print(f"Total moment events: {report.total_moment_events}")
    avg = report.total_moment_events / max(1, report.matches_run)
    print(f"Avg moments/match:   {avg:.2f}")
    print(f"Winner counts:       {dict(report.winner_counts)}")
    if report.exceptions:
        print("EXCEPTIONS:")
        for line in report.exceptions:
            print(f"  - {line}")
        return 1
    if avg < 1.0:
        print("FAIL: average moments per match below 1.0")
        return 2
    print("OK")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [x] **Step 5: Run the probe directly to confirm it prints OK**

Run: `python tools/tier_1_sanity_probe.py`
Expected output ends with `OK` and exit code 0.

- [x] **Step 6: Run the test**

Run: `python -m pytest tests/test_tier_1_sanity_probe.py -v`
Expected: 4 passed.

- [x] **Step 7: Run the full suite**

Run: `python -m pytest -q`
Expected: 723 passed (719 + 4 new).

- [x] **Step 8: Commit**

```bash
git add tools/__init__.py tools/tier_1_sanity_probe.py tests/test_tier_1_sanity_probe.py
git commit -m "feat(tools): add Tier 1 sanity probe — Plan A gate

Runs 25 matches and asserts resolution + >=1 moment/match average.
Replaces nothing yet; tools/o1_variance_probe.py deletion is Plan D."
```

---

## Task 13: Documentation — STATUS.md update

**Files:**
- Modify: `docs/STATUS.md`

Record that Plan A landed so future agents can see the post-V11 redesign is in motion.

- [x] **Step 1: Read the current STATUS.md "Shipped And Verified" section**

Open `docs/STATUS.md` and find the "Shipped And Verified" section. Note its current structure (bulleted list of milestones).

- [x] **Step 2: Add an entry for Plan A**

Insert after the V11 entry, before the V1–V10 bullet:

```markdown
- **Post-V11 redesign — Plan A: Hybrid driver architecture + Tier 1 engine** (landed YYYY-MM-DD) — see `docs/specs/2026-05-20-post-v11-redesign-brief/plan-a-hybrid-driver.md`. New `EngineDriver` protocol with `RecTier1Driver` (Local Rec League, brief §3.5) and `OfficialDriver` (wraps V11). New primitives: `fatigue`, `flood_throws`, `stall_timer`, `moment_events` (six-moment contract). V11 / USAD tests all still pass. Tier 1 sanity probe at `tools/tier_1_sanity_probe.py`. Plans B/C/D still to come per `tier-1-roadmap.md`.
```

Replace `YYYY-MM-DD` with the actual landing date (commit date).

- [x] **Step 3: Update the "Current Phase" paragraph**

Change "No milestone is in active development" → "Post-V11 redesign in progress; Plan A (hybrid driver architecture + Tier 1 engine) shipped. Plans B/C/D in `docs/specs/2026-05-20-post-v11-redesign-brief/`."

- [x] **Step 4: Run the full suite one more time as a final sanity check**

Run: `python -m pytest -q`
Expected: 724 passed.

- [x] **Step 5: Commit**

```bash
git add docs/STATUS.md
git commit -m "docs(status): record Plan A — hybrid driver architecture landed

EngineDriver protocol + RecTier1Driver + OfficialDriver wrapper
shipped. Plans B/C/D queued per tier-1-roadmap.md."
```

---

## Plan A: definition of done

All of the following are true before Plan A is considered complete:

- [x] All 13 tasks above are checked off.
- [x] `python -m pytest -q` reports 724 passing tests (659 baseline + 65 new). If the baseline has shifted upstream, the delta should be exactly +65.
- [x] `python tools/tier_1_sanity_probe.py` exits 0 and prints `OK`.
- [x] No file under `src/dodgeball_sim/burden.py`, `discipline.py`, `no_blocking.py` has been modified.
- [x] `src/dodgeball_sim/official_engine.py` has not been edited (only re-exported / wrapped).
- [x] `docs/STATUS.md` reflects Plan A landing.
- [x] Tests for all six moment kinds emit at least once across the sanity probe's 25-match run.

## Self-review checklist (run before handing off)

The plan author should walk this once before invoking the executor.

1. **Spec coverage** — Does Plan A deliver on every "must" from the brief's
   §7 "First sub-project" scope? Specifically:
   - Tier 1 engine (rec rules, simpler than V11): ✓ (Task 7)
   - In-match fatigue: ✓ (Task 3)
   - Flood-throw support: ✓ (Task 4)
   - Replay/event contract for six moments: ✓ (Task 2 + Task 8)
   - Hybrid architecture proof: ✓ (Tasks 1, 9)
   - Sanity probe: ✓ (Task 12)
   - V11 tests preserved: ✓ (plan-level invariant + Task 10 gate)
2. **Placeholder scan** — every step has actual code or exact commands. No `TODO` strings remain. ✓
3. **Type consistency** — `EngineDriver`, `DriverMatchInput`, `DriverMatchOutput`, `MomentEvent`, `FatigueState`, `FloodThrowTracker`, `StallTimerState`, `TierRules`, `RecTier1Driver`, `OfficialDriver`, `SanityProbeReport` — names are used identically in their introducing task and all later references. ✓

---

## Execution handoff

Plan complete and saved to
`docs/specs/2026-05-20-post-v11-redesign-brief/plan-a-hybrid-driver.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — Fresh subagent per task, review between tasks, fast iteration. Use `superpowers:subagent-driven-development`.
2. **Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Which approach? After Plan A merges, return here to write Plans B, C, and D in order.
