# V2-D Expanded CoachPolicy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Target Ball-Holder, Catch Bias, and Rush Proximity as real, logged `CoachPolicy` tendencies while preserving deterministic simulation integrity.

**Architecture:** Extend the `CoachPolicy` dataclass and all policy serialization/formatting paths first, then add engine behavior in small TDD loops. Target Ball-Holder uses match runtime state for recent opposing throwers, Catch Bias changes catch-attempt willingness without changing `p_catch`, and Rush Proximity adds deterministic rush context terms configured in `BalanceConfig`.

**Tech Stack:** Python dataclasses, pytest, deterministic engine tests, JSON golden regression.

---

## File Map

- Modify `src/dodgeball_sim/models.py`: add three `CoachPolicy` fields, normalization, and `as_dict`.
- Modify `src/dodgeball_sim/config.py`: add V2-D rush tuning constants to `BalanceConfig`.
- Modify `src/dodgeball_sim/engine.py`: add runtime recent-thrower state, target-ball-holder scoring, catch-bias threshold, rush context, and event-log payloads.
- Modify `src/dodgeball_sim/setup_loader.py`: load new fields with `0.5` defaults.
- Modify `src/dodgeball_sim/randomizer.py`: generate new policy values.
- Modify `src/dodgeball_sim/ui_formatters.py`: render eight policy rows and effect strings.
- Check `src/dodgeball_sim/manager_gui.py` / `src/dodgeball_sim/gui.py`: update policy key lists if present.
- Add/modify tests in `tests/test_coach_policy.py`, `tests/test_engine.py`, `tests/test_setup_loader.py`, `tests/test_regression.py`, and existing formatter tests if present.
- Update `tests/golden_logs/phase1_baseline.json` only after behavior and audit payload changes are intentional and documented.

---

### Task 1: Policy Model And Formatting

**Files:**
- Modify: `src/dodgeball_sim/models.py`
- Modify: `src/dodgeball_sim/setup_loader.py`
- Modify: `src/dodgeball_sim/randomizer.py`
- Modify: `src/dodgeball_sim/ui_formatters.py`
- Test: `tests/test_coach_policy.py`

- [ ] **Step 1: Write failing policy serialization and formatter tests**

Add tests:

```python
from dodgeball_sim.models import CoachPolicy
from dodgeball_sim.setup_loader import _coach_policy_from_dict
from dodgeball_sim.ui_formatters import policy_effect, policy_rows


def test_coach_policy_defaults_include_v2d_fields():
    payload = CoachPolicy().as_dict()
    assert payload["target_ball_holder"] == 0.5
    assert payload["catch_bias"] == 0.5
    assert payload["rush_proximity"] == 0.5


def test_coach_policy_loads_missing_v2d_fields_as_neutral():
    policy = _coach_policy_from_dict(
        {
            "target_stars": 0.8,
            "risk_tolerance": 0.2,
            "sync_throws": 0.3,
            "tempo": 0.4,
            "rush_frequency": 0.6,
        }
    )
    assert policy.target_ball_holder == 0.5
    assert policy.catch_bias == 0.5
    assert policy.rush_proximity == 0.5


def test_policy_rows_render_all_eight_tendencies():
    labels = [label for label, _value, _effect in policy_rows(CoachPolicy())]
    assert labels == [
        "Target Stars",
        "Target Ball Holder",
        "Risk Tolerance",
        "Sync Throws",
        "Rush Frequency",
        "Rush Proximity",
        "Tempo",
        "Catch Bias",
    ]


def test_policy_effect_explains_v2d_tendencies():
    assert "possession" in policy_effect("target_ball_holder", 0.8).lower()
    assert "catch" in policy_effect("catch_bias", 0.8).lower()
    assert "pressure" in policy_effect("rush_proximity", 0.8).lower()
```

- [ ] **Step 2: Run red test**

Run:

```powershell
python -m pytest tests/test_coach_policy.py -q -p no:cacheprovider
```

Expected: FAIL because fields and formatter rows do not exist yet.

- [ ] **Step 3: Implement minimal model/loader/formatter support**

Add fields to `CoachPolicy`, include them in `normalized()` and `as_dict()`, update `_coach_policy_from_dict`, randomizer, and `policy_rows`/`policy_effect`.

- [ ] **Step 4: Run green test**

Run:

```powershell
python -m pytest tests/test_coach_policy.py -q -p no:cacheprovider
```

Expected: PASS.

---

### Task 2: Catch Bias Behavior

**Files:**
- Modify: `src/dodgeball_sim/engine.py`
- Test: `tests/test_coach_policy.py`

- [ ] **Step 1: Write failing catch-bias tests**

Add tests using `MatchEngine._should_attempt_catch` directly:

```python
from dataclasses import replace

from dodgeball_sim.engine import MatchEngine
from dodgeball_sim.models import CoachPolicy, PlayerState
from tests.factories import make_player


def test_catch_bias_increases_catch_attempt_willingness_without_changing_probability_model():
    target = PlayerState(make_player("target", dodge=70, catch=50))
    low = CoachPolicy(catch_bias=0.0)
    neutral = CoachPolicy(catch_bias=0.5)
    high = CoachPolicy(catch_bias=1.0)

    low_attempt, low_meta = MatchEngine()._should_attempt_catch(target, low)
    neutral_attempt, neutral_meta = MatchEngine()._should_attempt_catch(target, neutral)
    high_attempt, high_meta = MatchEngine()._should_attempt_catch(target, high)

    assert low_attempt is False
    assert neutral_attempt is False
    assert high_attempt is True
    assert low_meta["catch_bias"] == 0.0
    assert neutral_meta["catch_bias"] == 0.5
    assert high_meta["catch_bias"] == 1.0
    assert high_meta["threshold"] < neutral_meta["threshold"] < low_meta["threshold"]
```

- [ ] **Step 2: Run red test**

Run:

```powershell
python -m pytest tests/test_coach_policy.py::test_catch_bias_increases_catch_attempt_willingness_without_changing_probability_model -q -p no:cacheprovider
```

Expected: FAIL because `catch_bias` is not used in the threshold/meta.

- [ ] **Step 3: Implement catch-bias threshold**

Change `_should_attempt_catch` so neutral `catch_bias=0.5` preserves the existing threshold:

```python
base_threshold = 0.3 + 0.4 * (1 - policy.risk_tolerance)
catch_bias_adjustment = (0.5 - policy.catch_bias) * 0.3
threshold = base_threshold + catch_bias_adjustment
attempt = normalized_catch >= max(threshold, normalized_dodge - 0.15 + catch_bias_adjustment)
```

Include `base_threshold`, `catch_bias`, and `catch_bias_adjustment` in `catch_decision`.

- [ ] **Step 4: Run green test**

Run the focused test. Expected: PASS.

---

### Task 3: Target Ball-Holder Runtime State

**Files:**
- Modify: `src/dodgeball_sim/engine.py`
- Test: `tests/test_coach_policy.py`

- [ ] **Step 1: Write failing target-selection tests**

Add tests:

```python
from dodgeball_sim.engine import MatchEngine
from dodgeball_sim.models import CoachPolicy, TeamState
from tests.factories import make_player, make_team


def test_target_ball_holder_prioritizes_recent_opposing_thrower():
    recent = make_player("recent_thrower", accuracy=50, power=50, dodge=90, catch=50)
    star = make_player("star", accuracy=95, power=95, dodge=80, catch=70)
    defense = TeamState(make_team("def", [recent, star]))
    rng = __import__("dodgeball_sim.rng", fromlist=["DeterministicRNG"]).DeterministicRNG(123)
    difficulty = __import__("dodgeball_sim.config", fromlist=["DEFAULT_CONFIG"]).DEFAULT_CONFIG.difficulty_profiles["elite"]

    target, meta = MatchEngine()._select_target(
        defense,
        CoachPolicy(target_stars=0.0, target_ball_holder=1.0),
        rng,
        difficulty,
        recent_pressure_player_id="recent_thrower",
    )

    assert target.player.id == "recent_thrower"
    score = next(row for row in meta["scores"] if row["player_id"] == "recent_thrower")
    assert score["ball_holder_pressure"] > 0
```

- [ ] **Step 2: Run red test**

Run focused test. Expected: FAIL because `_select_target` has no `recent_pressure_player_id` argument and no score component.

- [ ] **Step 3: Implement recent pressure scoring**

Add optional `recent_pressure_player_id: str | None = None` to `_select_target`. Add:

```python
ball_holder_pressure = 1.0 if player.id == recent_pressure_player_id else 0.0
base = (
    policy.target_stars * normalized_overall
    + (1 - policy.target_stars) * vulnerability
    + policy.target_ball_holder * ball_holder_pressure
)
```

Add `ball_holder_pressure` and component values to target-selection rows.

- [ ] **Step 4: Wire runtime state**

In `run`, maintain `recent_thrower_by_team: dict[str, str]`. Pass the defense team's most recent thrower into `_process_throw`, then into `_select_target`. After a throw event is produced, update `recent_thrower_by_team[offense.team.id]`.

- [ ] **Step 5: Run green test**

Run focused test and existing engine tests. Expected: PASS.

---

### Task 4: Rush Proximity Context

**Files:**
- Modify: `src/dodgeball_sim/config.py`
- Modify: `src/dodgeball_sim/engine.py`
- Test: `tests/test_coach_policy.py`

- [ ] **Step 1: Write failing rush tests**

Add tests that run two single throws through helper-visible context or inspect the first throw event from a short match:

```python
from dodgeball_sim.engine import MatchEngine
from dodgeball_sim.models import CoachPolicy, MatchSetup
from tests.factories import make_player, make_team


def test_rush_proximity_logs_stronger_context_for_high_policy():
    offense_low = make_team("off_low", [make_player("low_thrower", accuracy=70, power=70)], CoachPolicy(rush_frequency=1.0, rush_proximity=0.0))
    offense_high = make_team("off_high", [make_player("high_thrower", accuracy=70, power=70)], CoachPolicy(rush_frequency=1.0, rush_proximity=1.0))
    defense = make_team("def", [make_player("target", dodge=60, catch=60)])

    low_event = next(e for e in MatchEngine().run(MatchSetup(offense_low, defense), seed=77).events if e.event_type == "throw")
    high_event = next(e for e in MatchEngine().run(MatchSetup(offense_high, defense), seed=77).events if e.event_type == "throw")

    assert low_event.context["rush_context"]["active"] is True
    assert high_event.context["rush_context"]["active"] is True
    assert high_event.context["rush_context"]["proximity_modifier"] > low_event.context["rush_context"]["proximity_modifier"]
```

- [ ] **Step 2: Run red test**

Expected: FAIL because `rush_context` does not exist.

- [ ] **Step 3: Add config constants**

Add to `BalanceConfig`:

```python
rush_accuracy_modifier_max: float
rush_fatigue_cost_max: float
```

Set default values in `phase1.v1` to small values, for example `0.08` and `0.35`.

- [ ] **Step 4: Implement deterministic rush context**

Use deterministic activation for V2-D:

```python
rush_active = offense_policy.rush_frequency > 0.0
proximity_modifier = offense_policy.rush_proximity * cfg.rush_accuracy_modifier_max if rush_active else 0.0
rush_fatigue_delta = offense_policy.rush_proximity * cfg.rush_fatigue_cost_max if rush_active else 0.0
```

Pass `rush_accuracy_modifier` into `compute_throw_probabilities` as an additional context term added to `p_on_target` input. Apply `rush_fatigue_delta` visibly to thrower fatigue. Log `rush_context`.

- [ ] **Step 5: Run green test**

Run focused rush test. Expected: PASS.

---

### Task 5: Event Audit And Regression

**Files:**
- Modify: `src/dodgeball_sim/engine.py`
- Modify: `tests/test_regression.py` or `tests/golden_logs/phase1_baseline.json`
- Test: `tests/test_coach_policy.py`, `tests/test_regression.py`

- [ ] **Step 1: Write failing audit test**

Add:

```python
def test_throw_event_logs_v2d_policy_components():
    team_a = make_team("a", [make_player("a1", accuracy=80, power=70)], CoachPolicy(target_ball_holder=0.7, catch_bias=0.8, rush_frequency=1.0, rush_proximity=0.9))
    team_b = make_team("b", [make_player("b1", dodge=60, catch=60)])
    event = next(e for e in MatchEngine().run(MatchSetup(team_a, team_b), seed=99).events if e.event_type == "throw")

    assert "target_ball_holder" in event.context["policy_snapshot"]
    assert "catch_bias" in event.context["policy_snapshot"]
    assert "rush_proximity" in event.context["policy_snapshot"]
    assert "rush_context" in event.context
    assert "ball_holder_pressure" in event.context["target_selection"]["scores"][0]
```

- [ ] **Step 2: Run red/green**

Run the audit test. If prior tasks already make it pass, confirm it would have failed before by checking the old fields were absent in baseline; otherwise complete logging.

- [ ] **Step 3: Run regression**

Run:

```powershell
python -m pytest tests/test_regression.py -q -p no:cacheprovider
```

Expected: likely FAIL due added policy fields and audit payloads, possibly behavior changes.

- [ ] **Step 4: Update golden intentionally**

Regenerate `phase1_baseline.json` from the current deterministic result if all invariant tests pass. Add a short note to the final implementation summary explaining that V2-D changed policy audit payloads and rush/catch/targeting behavior.

---

### Task 6: Full Verification

**Files:**
- No new code unless tests reveal defects.

- [ ] **Step 1: Run targeted V2-D tests**

```powershell
python -m pytest tests/test_coach_policy.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 2: Run integrity/regression tests**

```powershell
python -m pytest tests/test_invariants.py tests/test_monte_carlo.py tests/test_regression.py -q -p no:cacheprovider
```

Expected: PASS. If a file name differs, run the closest existing invariant/Monte Carlo tests found by `rg "monotonic|symmetry|difficulty" tests`.

- [ ] **Step 3: Run full suite**

```powershell
python -m pytest -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 4: Update milestone notes if needed**

If implementation reveals a spec mismatch, update `docs/specs/2026-04-28-v2-d-expanded-coach-policy/design.md` narrowly with the verified decision.

---

## Self-Review

- Spec coverage: plan covers model fields, backcompat, engine hooks, event audit, UI formatting, golden logs, and integrity verification.
- Placeholder scan: no implementation placeholders are intentionally left for core behavior.
- Type consistency: new policy fields are `target_ball_holder`, `catch_bias`, and `rush_proximity` throughout.

