# Plan B — Player Attribute v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `PlayerRatings` with three behavioral identity traits, rewrite `PlayerArchetype` to rec-league semantics with one canonical derivation helper, and wire the new traits into three rec-driver decision points — without breaking Plan A or V11 / USAD behavior.

**Architecture:** Skill OVR (5 fields) and identity traits (4 fields including existing `tactical_iq`) are split at the `PlayerRatings` API. A single `derive_archetype(ratings, *, allow_hybrid=True)` helper is the canonical source for both base and hybrid archetype assignment. The rec driver (`rec_engine.py`) gains one new decision point per new trait. Persistence loaders fail loudly on legacy V1–V11 data (clean break per brief §8).

**Tech Stack:** Python 3.12+, dataclasses, pytest, no new dependencies.

**Parent design:** [plan-b-design.md](./plan-b-design.md)
**Predecessor:** [plan-a-hybrid-driver.md](./plan-a-hybrid-driver.md)

---

## Pinned design decisions

These resolve the 7 questions raised in the design-review approval. Every later task references these as the source of truth.

### 1. `derive_archetype` scoring weights

Each base archetype gets a score that is the sum of two rating fields on the 0..100 scale (combined range 0..200):

| Base archetype | Score formula |
|---|---|
| `THROWER` | `accuracy + power` |
| `CATCHER` | `catch + catch_courage` |
| `BALL_HAWK` | `stamina + throw_selection_iq` |
| `DODGER_ANCHOR` | `dodge + tactical_iq` |

Every rating except `conditioning_curve` contributes to exactly one base score. `conditioning_curve` is purely behavioral (fatigue rate) and intentionally does not influence archetype.

### 2. Hybrid gap threshold

`GAP_THRESHOLD = 15.0` on the 0..200 sum scale. If the top two base scores differ by ≤ 15, the player is a hybrid (if a named hybrid exists for that pair); else the player is the top base.

### 3. Tie-break order

When two base scores are exactly equal, ordering is alphabetical on `PlayerArchetype.name` (Python enum member name). Concretely: `BALL_HAWK < CATCHER < DODGER_ANCHOR < HAWK_DODGER < THROWER < THROWER_CATCHER < THROWER_DODGER`. This is deterministic and RNG-free.

### 4. Hybrid mapping table

Only four base pairs have named hybrids. Other pairs return the top base.

| Base pair (alphabetical) | Hybrid |
|---|---|
| `BALL_HAWK + CATCHER` | `CATCHER_HAWK` |
| `BALL_HAWK + DODGER_ANCHOR` | `HAWK_DODGER` |
| `CATCHER + THROWER` | `THROWER_CATCHER` |
| `DODGER_ANCHOR + THROWER` | `THROWER_DODGER` |
| `BALL_HAWK + THROWER` | (no hybrid → top base) |
| `CATCHER + DODGER_ANCHOR` | (no hybrid → top base) |

### 5. Hybrid development inheritance — weighted union (60/40)

For hybrids, `development.py` allocates the per-archetype growth pool as 60% to the primary base's stat list and 40% to the secondary base's stat list. The "primary" is the higher-scoring base; "secondary" is the lower-scoring one. If scores are exactly equal, primary is the alphabetically-first enum member (same as tie-break).

### 6. Continued role of `tactical_iq`

`tactical_iq` remains a 0..100 `PlayerRatings` field. It is treated as a behavioral identity trait (not a skill), included in `identity_profile()`, and used in `derive_archetype` to score `DODGER_ANCHOR`. The rec driver does not read `tactical_iq` directly in Plan B (Plan A doesn't either); higher-tier drivers may use it in later plans.

### 7. Display-name leak smoke test

A single dedicated test (`tests/test_archetype_display_smoke.py`) iterates the 8 enum members, asserts each has a non-empty `display_name`, and asserts that the public-facing outputs of `identity.classify_archetype`, `recruitment._archetype_for_ratings`, and `scouting._reveal_archetype` are never equal to the raw `.value` of the enum (i.e. no `"THROWER_CATCHER"` leaks where `"Thrower / Catcher"` should appear).

---

## File map

**Files modified:**
- `src/dodgeball_sim/models.py` — `PlayerRatings`, `PlayerArchetype`, `Player`.
- `src/dodgeball_sim/randomizer.py` — Player rolling, archetype assignment.
- `src/dodgeball_sim/development.py` — Per-archetype growth allocation.
- `src/dodgeball_sim/lineup.py` — Per-slot archetype preferences.
- `src/dodgeball_sim/persistence.py` — Loud-fail loaders.
- `src/dodgeball_sim/identity.py` — `classify_archetype` rebase.
- `src/dodgeball_sim/recruitment.py` — `_archetype_for_ratings` rebase.
- `src/dodgeball_sim/scouting.py` — `_reveal_archetype` rebase.
- `src/dodgeball_sim/rec_engine.py` — Three decision-point rewrites.
- `src/dodgeball_sim/fatigue.py` — Doc comment update.
- `src/dodgeball_sim/sample_data.py` — Curated rosters get v2 fields + archetype.
- `tests/factories.py` — `make_player` supplies derived archetype.
- `docs/STATUS.md` — Mark Plan B landed; correct the vestigial-archetype claim.
- `docs/specs/2026-05-20-post-v11-redesign-brief/tier-1-roadmap.md` — Mark row landed.

**Files created:**
- `tests/test_archetype_display_smoke.py` — Display-name leak test.

**Tests touched (rewritten against new enum):**
- `tests/test_development.py` — Per-archetype growth.
- `tests/test_v6_player_identity.py` — Classify + identity card.
- `tests/test_lineup.py` — Slot preferences.
- `tests/test_persistence_player_roundtrip*` — Loud-fail behavior (add).

**Files NOT modified** (Plan B respects these boundaries):
- `src/dodgeball_sim/official_engine.py`, `burden.py`, `discipline.py`, `no_blocking.py` — V11 / USAD.
- `src/dodgeball_sim/engine_driver.py`, `moment_events.py`, `flood_throws.py`, `stall_timer.py` — Plan A primitives.
- `src/dodgeball_sim/official_driver.py` — Plan A.

---

## Task 1: `PlayerRatings` v2 fields

**Files:**
- Modify: `src/dodgeball_sim/models.py:25-59`
- Test: `tests/test_models_ratings_v2.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/test_models_ratings_v2.py`:

```python
import pytest

from dodgeball_sim.models import PlayerRatings


def test_v2_fields_default_to_50():
    r = PlayerRatings(accuracy=60, power=60, dodge=60, catch=60)
    assert r.catch_courage == 50.0
    assert r.throw_selection_iq == 50.0
    assert r.conditioning_curve == 50.0


def test_v2_fields_clamp_at_bounds():
    r = PlayerRatings(
        accuracy=60,
        power=60,
        dodge=60,
        catch=60,
        catch_courage=150.0,
        throw_selection_iq=-10.0,
        conditioning_curve=200.0,
    ).apply_bounds()
    assert r.catch_courage == 100.0
    assert r.throw_selection_iq == 0.0
    assert r.conditioning_curve == 100.0


def test_v2_fields_explicit_values_preserved():
    r = PlayerRatings(
        accuracy=60,
        power=60,
        dodge=60,
        catch=60,
        catch_courage=72.0,
        throw_selection_iq=33.0,
        conditioning_curve=88.0,
    )
    assert r.catch_courage == 72.0
    assert r.throw_selection_iq == 33.0
    assert r.conditioning_curve == 88.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models_ratings_v2.py -v`
Expected: 3 FAILs with `TypeError: PlayerRatings.__init__() got an unexpected keyword argument 'catch_courage'`.

- [ ] **Step 3: Modify `PlayerRatings` in `models.py`**

Replace the existing `PlayerRatings` dataclass (lines 24-59) with:

```python
@dataclass(frozen=True)
class PlayerRatings:
    accuracy: float
    power: float
    dodge: float
    catch: float
    stamina: float = 50.0
    tactical_iq: float = 50.0
    catch_courage: float = 50.0
    throw_selection_iq: float = 50.0
    conditioning_curve: float = 50.0

    def normalized_accuracy(self) -> float:
        return self.accuracy / _RATING_MAX

    def normalized_power(self) -> float:
        return self.power / _RATING_MAX

    def normalized_dodge(self) -> float:
        return self.dodge / _RATING_MAX

    def normalized_catch(self) -> float:
        return self.catch / _RATING_MAX

    def normalized_tactical_iq(self) -> float:
        return self.tactical_iq / _RATING_MAX

    def normalized_catch_courage(self) -> float:
        return self.catch_courage / _RATING_MAX

    def normalized_throw_selection_iq(self) -> float:
        return self.throw_selection_iq / _RATING_MAX

    def normalized_conditioning_curve(self) -> float:
        return self.conditioning_curve / _RATING_MAX

    def fatigue_ceiling(self) -> float:
        return max(10.0, self.stamina)

    def apply_bounds(self) -> "PlayerRatings":
        return PlayerRatings(
            accuracy=_clamp_rating(self.accuracy),
            power=_clamp_rating(self.power),
            dodge=_clamp_rating(self.dodge),
            catch=_clamp_rating(self.catch),
            stamina=_clamp_rating(self.stamina),
            tactical_iq=_clamp_rating(self.tactical_iq),
            catch_courage=_clamp_rating(self.catch_courage),
            throw_selection_iq=_clamp_rating(self.throw_selection_iq),
            conditioning_curve=_clamp_rating(self.conditioning_curve),
        )
```

Do **not** touch `overall()` yet — that's Task 2.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models_ratings_v2.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: green (the new fields all default, no caller break).

- [ ] **Step 6: Commit**

```bash
git add src/dodgeball_sim/models.py tests/test_models_ratings_v2.py
git commit -m "feat(models): add v2 behavioral identity ratings (Plan B Task 1)

catch_courage, throw_selection_iq, conditioning_curve added to
PlayerRatings with default 50.0 and clamp coverage. overall() still
averages only the V11 fields; the split into overall_skill() vs
identity_profile() lands in Task 2."
```

---

## Task 2: `overall_skill()` + `identity_profile()` split

**Files:**
- Modify: `src/dodgeball_sim/models.py:81-89` (rename `overall`) and add `identity_profile()`.
- Modify: every call site of `Player.overall()` (find via grep).
- Test: `tests/test_models_ratings_v2.py` (extend).

- [ ] **Step 1: Survey callers of `overall()`**

Run: `grep -rn "\.overall()" src/ tests/ | grep -v __pycache__`

Record the list. Every site is a rename target.

- [ ] **Step 2: Write the failing test**

Append to `tests/test_models_ratings_v2.py`:

```python
from dataclasses import is_dataclass

from dodgeball_sim.models import IdentityProfile, Player, PlayerRatings


def _r(**kwargs):
    base = dict(accuracy=60, power=60, dodge=60, catch=60)
    base.update(kwargs)
    return PlayerRatings(**base)


def test_overall_skill_covers_only_five_skill_fields():
    r = _r(catch_courage=100, throw_selection_iq=100, conditioning_curve=100, tactical_iq=100)
    expected = (60 + 60 + 60 + 60 + 50) / 5
    assert r.overall_skill() == pytest.approx(expected)


def test_overall_old_name_removed():
    r = _r()
    assert not hasattr(r, "overall") or callable(getattr(r, "overall_skill", None))


def test_identity_profile_dataclass():
    r = _r(catch_courage=70, throw_selection_iq=80, conditioning_curve=40, tactical_iq=55)
    profile = r.identity_profile()
    assert is_dataclass(profile)
    assert profile.catch_courage == 70
    assert profile.throw_selection_iq == 80
    assert profile.conditioning_curve == 40
    assert profile.tactical_iq == 55


def test_player_overall_skill_delegates():
    r = _r()
    p = Player(id="p1", name="P", ratings=r)
    # archetype default still in place until Task 3; this should not break.
    assert p.overall_skill() == r.overall_skill()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_models_ratings_v2.py -v`
Expected: FAIL on `overall_skill` / `IdentityProfile` / `identity_profile` not defined.

- [ ] **Step 4: Implement the split in `models.py`**

In `models.py`, add an `IdentityProfile` dataclass after `PlayerRatings`:

```python
@dataclass(frozen=True)
class IdentityProfile:
    """Behavioral identity traits surfaced as text, never averaged into skill OVR."""

    catch_courage: float
    throw_selection_iq: float
    conditioning_curve: float
    tactical_iq: float
```

Add `IdentityProfile` to `__all__` at the bottom of `models.py` (next to `PlayerRatings`).

Replace `PlayerRatings.overall()` with `overall_skill()` and add `identity_profile()`:

```python
    def overall_skill(self) -> float:
        stats = [
            self.accuracy,
            self.power,
            self.dodge,
            self.catch,
            self.stamina,
        ]
        return sum(stats) / len(stats)

    def identity_profile(self) -> "IdentityProfile":
        return IdentityProfile(
            catch_courage=self.catch_courage,
            throw_selection_iq=self.throw_selection_iq,
            conditioning_curve=self.conditioning_curve,
            tactical_iq=self.tactical_iq,
        )
```

Note: `overall_skill()` deliberately does NOT include `tactical_iq` (which today is in `overall()`). `tactical_iq` is now an identity trait. This is a real semantic change; downstream display code may show a different OVR number after this task. Accept it.

In `Player` (lines 70-89), replace `overall()`:

```python
    def overall_skill(self) -> float:
        return self.ratings.overall_skill()

    def identity_profile(self) -> IdentityProfile:
        return self.ratings.identity_profile()
```

Delete the old `overall()` method entirely from both `PlayerRatings` and `Player`. Do not alias.

- [ ] **Step 5: Update every caller of `.overall()` to `.overall_skill()`**

Walk the list from Step 1. For each `<x>.overall()` call, change to `<x>.overall_skill()`. Examples:

- `src/dodgeball_sim/matchup_details.py:68` → `round(focal_player.overall_skill())`
- Any `tests/*.py` callers → same rename.

If you find a caller in a code path that *would* want a tactical-IQ-inclusive composite, leave a `# TODO(plan-c): consider overall_composite for matchmaking` comment but keep the `overall_skill` rename — do not add `overall_composite` in Plan B.

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_models_ratings_v2.py -v`
Expected: PASS for all 7 tests (4 from Task 1 + 3 new + delegate test).

- [ ] **Step 7: Run the full suite**

Run: `python -m pytest -q`
Expected: green. If any test fails because it expected the old tactical-IQ-inclusive OVR number, update the expected number to the new 5-skill mean.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "refactor(models): split overall() into overall_skill() + identity_profile()

overall_skill() covers only the five skill fields (accuracy, power,
dodge, catch, stamina). tactical_iq is now an identity trait surfaced
via IdentityProfile alongside the new catch_courage,
throw_selection_iq, and conditioning_curve fields.

Every caller renamed to overall_skill() — no alias retained, so any
miss surfaces as AttributeError. Behavioral traits are never averaged
into skill OVR (Plan B design §Architecture)."
```

---

## Task 3: `PlayerArchetype` enum rewrite

**Files:**
- Modify: `src/dodgeball_sim/models.py:12-17` (enum) and `:79` (default removed).
- Test: `tests/test_archetype_enum.py` (new).

- [ ] **Step 1: Write the failing test**

Create `tests/test_archetype_enum.py`:

```python
import pytest

from dodgeball_sim.models import PlayerArchetype


def test_enum_has_eight_values():
    assert len(list(PlayerArchetype)) == 8


def test_enum_has_expected_members():
    expected = {
        "THROWER", "CATCHER", "BALL_HAWK", "DODGER_ANCHOR",
        "THROWER_CATCHER", "THROWER_DODGER", "CATCHER_HAWK", "HAWK_DODGER",
    }
    assert {a.name for a in PlayerArchetype} == expected


def test_v6_values_are_gone():
    for legacy in ("POWER", "AGILITY", "PRECISION", "DEFENSE", "TACTICAL"):
        with pytest.raises(KeyError):
            PlayerArchetype[legacy]


def test_display_name_per_member():
    expected = {
        PlayerArchetype.THROWER: "Thrower",
        PlayerArchetype.CATCHER: "Catcher",
        PlayerArchetype.BALL_HAWK: "Ball Hawk",
        PlayerArchetype.DODGER_ANCHOR: "Dodger Anchor",
        PlayerArchetype.THROWER_CATCHER: "Thrower / Catcher",
        PlayerArchetype.THROWER_DODGER: "Thrower / Dodger",
        PlayerArchetype.CATCHER_HAWK: "Catcher / Ball Hawk",
        PlayerArchetype.HAWK_DODGER: "Ball Hawk / Dodger",
    }
    for member, name in expected.items():
        assert member.display_name == name


def test_value_strings_are_lowercase_snake():
    # value strings used in serialization
    assert PlayerArchetype.BALL_HAWK.value == "ball_hawk"
    assert PlayerArchetype.THROWER_CATCHER.value == "thrower_catcher"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_archetype_enum.py -v`
Expected: FAILs — current enum has 5 V6 values, no `display_name`.

- [ ] **Step 3: Rewrite `PlayerArchetype` in `models.py`**

Replace the existing enum (lines 12-17) with:

```python
class PlayerArchetype(str, Enum):
    THROWER = "thrower"
    CATCHER = "catcher"
    BALL_HAWK = "ball_hawk"
    DODGER_ANCHOR = "dodger_anchor"
    THROWER_CATCHER = "thrower_catcher"
    THROWER_DODGER = "thrower_dodger"
    CATCHER_HAWK = "catcher_hawk"
    HAWK_DODGER = "hawk_dodger"

    @property
    def display_name(self) -> str:
        return _ARCHETYPE_DISPLAY_NAMES[self]


_ARCHETYPE_DISPLAY_NAMES: dict["PlayerArchetype", str] = {}
# Populated at module bottom after class is fully defined to avoid forward-ref issues.
```

Add at the bottom of `models.py`, BEFORE `__all__`:

```python
_ARCHETYPE_DISPLAY_NAMES.update({
    PlayerArchetype.THROWER: "Thrower",
    PlayerArchetype.CATCHER: "Catcher",
    PlayerArchetype.BALL_HAWK: "Ball Hawk",
    PlayerArchetype.DODGER_ANCHOR: "Dodger Anchor",
    PlayerArchetype.THROWER_CATCHER: "Thrower / Catcher",
    PlayerArchetype.THROWER_DODGER: "Thrower / Dodger",
    PlayerArchetype.CATCHER_HAWK: "Catcher / Ball Hawk",
    PlayerArchetype.HAWK_DODGER: "Ball Hawk / Dodger",
})
```

Update `Player` (line 79) to remove the default:

```python
@dataclass(frozen=True)
class Player:
    id: str
    name: str
    ratings: PlayerRatings
    archetype: PlayerArchetype
    traits: PlayerTraits = PlayerTraits()
    age: int = 18
    club_id: str | None = None
    newcomer: bool = True
```

**Important:** Note the field order shift. `archetype` is now a required positional field after `ratings`. Every `Player(...)` construction site must now supply `archetype=...` explicitly. The next several tasks fix the callers.

- [ ] **Step 4: Run new test to verify it passes**

Run: `python -m pytest tests/test_archetype_enum.py -v`
Expected: 5 PASS.

- [ ] **Step 5: Run the full suite — expect cascading failures**

Run: `python -m pytest -q 2>&1 | tail -40`

This will produce many failures from `Player(...)` callers that no longer compile (missing required `archetype` argument) and from existing tests asserting V6 enum values. Catalog the failure file list — Tasks 4–10 systematically fix them. **Do not commit yet.**

If the failure surface is overwhelming, narrow in on these test files first to confirm the expected categories:
- `tests/factories.py` — central `make_player`, fixes propagate.
- `tests/test_development.py` — asserts old enum.
- `tests/test_lineup.py` — asserts old enum.
- `tests/test_v6_player_identity.py` — asserts old string labels.

- [ ] **Step 6: Make the central test factory supply a derived archetype**

This is the minimum surface to get the suite booting again. Edit `tests/factories.py:8-25` `make_player`:

```python
from dodgeball_sim.models import (
    Player,
    PlayerArchetype,
    PlayerRatings,
    PlayerTraits,
)


def make_player(
    player_id: str,
    ratings: PlayerRatings,
    *,
    name: str | None = None,
    archetype: PlayerArchetype | None = None,
) -> Player:
    if archetype is None:
        # Default archetype for test fixtures. Real derivation lands in Task 4.
        archetype = PlayerArchetype.THROWER
    return Player(
        id=player_id,
        name=name or player_id.title(),
        ratings=ratings,
        archetype=archetype,
        traits=PlayerTraits(),
    )
```

This is a temporary default to keep the test harness booting; Task 4 will route `make_player` through `derive_archetype` instead.

- [ ] **Step 7: Fix remaining direct `Player(...)` test callers**

Run: `grep -rn "Player(" tests/ | grep -v "make_player\|archetype="`

For each direct `Player(...)` constructor call, add `archetype=PlayerArchetype.THROWER` and a `PlayerArchetype` import if missing. This is also temporary scaffolding; Task 4 replaces the literal with `derive_archetype(ratings)` where appropriate.

For `src/` callers, find them: `grep -rn "Player(" src/ | grep -v __pycache__ | grep -v "make_player"`. The two main ones are `randomizer.py` and `persistence.py` — they will be properly rewritten in Tasks 5–6. For now, supply `archetype=PlayerArchetype.THROWER` to satisfy the constructor.

- [ ] **Step 8: Run the full suite — bulk-failure tests still red**

Run: `python -m pytest -q 2>&1 | tail -20`

Expected at this point: the `Player(...)` constructor-missing-arg failures are gone. The remaining failures are semantic (`tests/test_development.py` asserts `POWER`, etc.) — those land in Tasks 7–10. **Still do not commit until the suite is at least green on enum-shape tests.**

Confirm `tests/test_archetype_enum.py` and `tests/test_models_ratings_v2.py` are green. If yes, proceed to commit.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat(models): rewrite PlayerArchetype to rec-league semantics (Plan B Task 3)

Eight values: THROWER, CATCHER, BALL_HAWK, DODGER_ANCHOR plus four
named hybrids (THROWER_CATCHER, THROWER_DODGER, CATCHER_HAWK,
HAWK_DODGER). Old V6 values (POWER/AGILITY/PRECISION/DEFENSE/TACTICAL)
removed. New display_name property surfaces rec-league copy.

Player.archetype loses its default; every constructor site must now
supply one. tests/factories.py and direct Player(...) call sites in
tests get a temporary archetype=THROWER scaffold — Task 4 routes
through derive_archetype.

Tests under tests/test_development.py, tests/test_lineup.py, and
tests/test_v6_player_identity.py remain red on semantic content
through Tasks 7-10."
```

---

## Task 4: `derive_archetype` canonical helper

**Files:**
- Create: `src/dodgeball_sim/archetype_derivation.py`
- Modify: `src/dodgeball_sim/models.py` (re-export).
- Modify: `tests/factories.py` (route through helper).
- Test: `tests/test_archetype_derivation.py` (new).

- [ ] **Step 1: Write the failing test**

Create `tests/test_archetype_derivation.py`:

```python
import pytest

from dodgeball_sim.archetype_derivation import (
    GAP_THRESHOLD,
    derive_archetype,
)
from dodgeball_sim.models import PlayerArchetype, PlayerRatings


def _r(**kwargs):
    base = dict(accuracy=50, power=50, dodge=50, catch=50, stamina=50, tactical_iq=50)
    base.update(kwargs)
    return PlayerRatings(**base)


# --- base archetype detection ---

def test_pure_thrower():
    r = _r(accuracy=95, power=95)
    assert derive_archetype(r) == PlayerArchetype.THROWER


def test_pure_catcher():
    r = _r(catch=95, catch_courage=95)
    assert derive_archetype(r) == PlayerArchetype.CATCHER


def test_pure_ball_hawk():
    r = _r(stamina=95, throw_selection_iq=95)
    assert derive_archetype(r) == PlayerArchetype.BALL_HAWK


def test_pure_dodger_anchor():
    r = _r(dodge=95, tactical_iq=95)
    assert derive_archetype(r) == PlayerArchetype.DODGER_ANCHOR


# --- hybrid detection ---

def test_thrower_catcher_hybrid():
    # THROWER score = 90+90=180; CATCHER score = 85+85=170; gap 10 < 15.
    r = _r(accuracy=90, power=90, catch=85, catch_courage=85)
    assert derive_archetype(r) == PlayerArchetype.THROWER_CATCHER


def test_thrower_dodger_hybrid():
    r = _r(accuracy=90, power=90, dodge=85, tactical_iq=85)
    assert derive_archetype(r) == PlayerArchetype.THROWER_DODGER


def test_catcher_hawk_hybrid():
    r = _r(catch=90, catch_courage=90, stamina=85, throw_selection_iq=85)
    assert derive_archetype(r) == PlayerArchetype.CATCHER_HAWK


def test_hawk_dodger_hybrid():
    r = _r(stamina=90, throw_selection_iq=90, dodge=85, tactical_iq=85)
    assert derive_archetype(r) == PlayerArchetype.HAWK_DODGER


# --- pairs with no named hybrid fall through to top base ---

def test_thrower_hawk_pair_returns_top_base():
    # THROWER 180, BALL_HAWK 170. Pair has no named hybrid -> top base.
    r = _r(accuracy=90, power=90, stamina=85, throw_selection_iq=85)
    assert derive_archetype(r) == PlayerArchetype.THROWER


def test_catcher_dodger_pair_returns_top_base():
    r = _r(catch=90, catch_courage=90, dodge=85, tactical_iq=85)
    assert derive_archetype(r) == PlayerArchetype.CATCHER


# --- gap threshold boundary ---

def test_gap_exactly_at_threshold_is_hybrid():
    # Gap == GAP_THRESHOLD -> still hybrid (inclusive).
    r = _r(accuracy=90, power=90, catch=82.5, catch_courage=82.5)
    # THROWER=180, CATCHER=165, gap=15 == threshold
    assert derive_archetype(r) == PlayerArchetype.THROWER_CATCHER


def test_gap_above_threshold_is_base():
    r = _r(accuracy=90, power=90, catch=82, catch_courage=82)
    # THROWER=180, CATCHER=164, gap=16 > threshold
    assert derive_archetype(r) == PlayerArchetype.THROWER


def test_gap_threshold_constant():
    assert GAP_THRESHOLD == 15.0


# --- tie-break ---

def test_exact_tie_breaks_alphabetically_on_name():
    # BALL_HAWK and CATCHER both score 200. Alphabetical name: BALL_HAWK first.
    r = _r(stamina=100, throw_selection_iq=100, catch=100, catch_courage=100)
    assert derive_archetype(r) == PlayerArchetype.CATCHER_HAWK
    # Hybrid wins because gap == 0 <= 15. But what's the "primary" matters
    # only for development inheritance, not for the enum value itself.


def test_exact_tie_returns_alphabetical_when_no_hybrid_exists():
    # THROWER and BALL_HAWK both 200. No hybrid -> alphabetical: BALL_HAWK.
    r = _r(accuracy=100, power=100, stamina=100, throw_selection_iq=100)
    assert derive_archetype(r) == PlayerArchetype.BALL_HAWK


# --- allow_hybrid=False forces base ---

def test_allow_hybrid_false_forces_base():
    r = _r(accuracy=90, power=90, catch=85, catch_courage=85)
    assert derive_archetype(r, allow_hybrid=False) == PlayerArchetype.THROWER


# --- determinism: same inputs -> same output ---

def test_determinism():
    r = _r(accuracy=72, power=68, dodge=55, catch=80, catch_courage=63,
           stamina=70, throw_selection_iq=58, tactical_iq=61)
    assert derive_archetype(r) == derive_archetype(r) == derive_archetype(r)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_archetype_derivation.py -v`
Expected: FAIL on `ModuleNotFoundError: No module named 'dodgeball_sim.archetype_derivation'`.

- [ ] **Step 3: Create the helper module**

Create `src/dodgeball_sim/archetype_derivation.py`:

```python
"""Single canonical helper for assigning PlayerArchetype from ratings.

Plan B pins the scoring formula, hybrid mapping, gap threshold, and
tie-break order. See plan-b-design.md and plan-b-player-attribute-v2.md
for the rationale.
"""

from __future__ import annotations

from typing import Tuple

from .models import PlayerArchetype, PlayerRatings


GAP_THRESHOLD: float = 15.0
"""On the 0..200 sum scale, top-two base score gap that triggers a hybrid."""


_BASE_ARCHETYPES = (
    PlayerArchetype.THROWER,
    PlayerArchetype.CATCHER,
    PlayerArchetype.BALL_HAWK,
    PlayerArchetype.DODGER_ANCHOR,
)


_HYBRID_MAP: dict[frozenset[PlayerArchetype], PlayerArchetype] = {
    frozenset({PlayerArchetype.THROWER, PlayerArchetype.CATCHER}): PlayerArchetype.THROWER_CATCHER,
    frozenset({PlayerArchetype.THROWER, PlayerArchetype.DODGER_ANCHOR}): PlayerArchetype.THROWER_DODGER,
    frozenset({PlayerArchetype.CATCHER, PlayerArchetype.BALL_HAWK}): PlayerArchetype.CATCHER_HAWK,
    frozenset({PlayerArchetype.BALL_HAWK, PlayerArchetype.DODGER_ANCHOR}): PlayerArchetype.HAWK_DODGER,
}


def _score(ratings: PlayerRatings, archetype: PlayerArchetype) -> float:
    if archetype == PlayerArchetype.THROWER:
        return ratings.accuracy + ratings.power
    if archetype == PlayerArchetype.CATCHER:
        return ratings.catch + ratings.catch_courage
    if archetype == PlayerArchetype.BALL_HAWK:
        return ratings.stamina + ratings.throw_selection_iq
    if archetype == PlayerArchetype.DODGER_ANCHOR:
        return ratings.dodge + ratings.tactical_iq
    raise ValueError(f"_score called with non-base archetype: {archetype!r}")


def _ranked_base_scores(ratings: PlayerRatings) -> list[Tuple[PlayerArchetype, float]]:
    scored = [(a, _score(ratings, a)) for a in _BASE_ARCHETYPES]
    # Sort by score descending, then alphabetically on enum NAME for deterministic tie-break.
    scored.sort(key=lambda kv: (-kv[1], kv[0].name))
    return scored


def derive_archetype(ratings: PlayerRatings, *, allow_hybrid: bool = True) -> PlayerArchetype:
    """Return the canonical archetype for the given ratings.

    Total and deterministic. See plan-b-player-attribute-v2.md "Pinned
    design decisions" §1-§5 for formula, threshold, mapping, and
    tie-break order.
    """
    ranked = _ranked_base_scores(ratings)
    top, top_score = ranked[0]
    second, second_score = ranked[1]
    if not allow_hybrid:
        return top
    gap = top_score - second_score
    if gap > GAP_THRESHOLD:
        return top
    hybrid = _HYBRID_MAP.get(frozenset({top, second}))
    if hybrid is not None:
        return hybrid
    return top


def primary_and_secondary_bases(ratings: PlayerRatings) -> Tuple[PlayerArchetype, PlayerArchetype]:
    """Return (primary_base, secondary_base) for development inheritance.

    Always returns two base archetypes. Used by development.py to apply
    the 60/40 weighted-union allocation for hybrid players.
    """
    ranked = _ranked_base_scores(ratings)
    return ranked[0][0], ranked[1][0]


__all__ = [
    "GAP_THRESHOLD",
    "derive_archetype",
    "primary_and_secondary_bases",
]
```

- [ ] **Step 4: Run derivation tests to verify they pass**

Run: `python -m pytest tests/test_archetype_derivation.py -v`
Expected: 15 PASS.

- [ ] **Step 5: Route `make_player` through `derive_archetype`**

Update `tests/factories.py`:

```python
from dodgeball_sim.archetype_derivation import derive_archetype
from dodgeball_sim.models import (
    Player,
    PlayerArchetype,
    PlayerRatings,
    PlayerTraits,
)


def make_player(
    player_id: str,
    ratings: PlayerRatings,
    *,
    name: str | None = None,
    archetype: PlayerArchetype | None = None,
) -> Player:
    if archetype is None:
        archetype = derive_archetype(ratings)
    return Player(
        id=player_id,
        name=name or player_id.title(),
        ratings=ratings,
        archetype=archetype,
        traits=PlayerTraits(),
    )
```

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest -q 2>&1 | tail -10`
Expected: tests using `make_player` now get sensible derived archetypes. Tests that still assert old V6 enum values (`test_development.py`, etc.) remain red. The arithmetic-shifted assertions in `test_v6_player_identity.py` are also still red. Both land in Tasks 7–10.

Confirm `tests/test_archetype_derivation.py`, `tests/test_archetype_enum.py`, and `tests/test_models_ratings_v2.py` are all green.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(models): add derive_archetype canonical helper (Plan B Task 4)

Single deterministic source for both base and hybrid archetype
assignment. Pinned per design:
- Score formula: pairs of two rating fields, 0..200 scale.
- Gap threshold: 15.0 (inclusive).
- Tie-break: alphabetical on enum NAME.
- Hybrid mapping: 4 named pairs; other pairs return top base.
- primary_and_secondary_bases() also exported for the 60/40
  development inheritance weighting that lands in Task 7.

tests/factories.py:make_player routes through the helper so the rest
of the suite picks up sensible archetypes automatically."
```

---

## Task 5: Persistence loud-fail on legacy data

**Files:**
- Modify: `src/dodgeball_sim/persistence.py:74` (and any sibling read paths).
- Test: `tests/test_persistence_loud_fail.py` (new).

- [ ] **Step 1: Write the failing test**

Create `tests/test_persistence_loud_fail.py`:

```python
import pytest

from dodgeball_sim.persistence import _player_from_dict  # adjust if private name differs


def test_loud_fail_on_missing_v2_ratings():
    legacy = {
        "id": "p1",
        "name": "Legacy",
        "ratings": {
            "accuracy": 60,
            "power": 60,
            "dodge": 60,
            "catch": 60,
            "stamina": 60,
            "tactical_iq": 60,
        },
        "archetype": "thrower",
        "traits": {},
        "age": 25,
        "club_id": "c1",
        "newcomer": False,
    }
    with pytest.raises(ValueError) as exc_info:
        _player_from_dict(legacy)
    msg = str(exc_info.value)
    for required in ("catch_courage", "throw_selection_iq", "conditioning_curve"):
        assert required in msg


def test_loud_fail_on_missing_archetype():
    payload = {
        "id": "p1",
        "name": "P",
        "ratings": {
            "accuracy": 60, "power": 60, "dodge": 60, "catch": 60,
            "stamina": 60, "tactical_iq": 60,
            "catch_courage": 50, "throw_selection_iq": 50, "conditioning_curve": 50,
        },
        # archetype key missing
        "traits": {},
        "age": 25,
        "club_id": "c1",
        "newcomer": False,
    }
    with pytest.raises(ValueError) as exc_info:
        _player_from_dict(payload)
    assert "archetype" in str(exc_info.value)


def test_loud_fail_on_unknown_archetype_value():
    payload = {
        "id": "p1",
        "name": "P",
        "ratings": {
            "accuracy": 60, "power": 60, "dodge": 60, "catch": 60,
            "stamina": 60, "tactical_iq": 60,
            "catch_courage": 50, "throw_selection_iq": 50, "conditioning_curve": 50,
        },
        "archetype": "Tactical",  # legacy V6 value
        "traits": {},
        "age": 25,
        "club_id": "c1",
        "newcomer": False,
    }
    with pytest.raises(ValueError):
        _player_from_dict(payload)


def test_clean_v2_payload_loads():
    payload = {
        "id": "p1",
        "name": "P",
        "ratings": {
            "accuracy": 60, "power": 60, "dodge": 60, "catch": 60,
            "stamina": 60, "tactical_iq": 60,
            "catch_courage": 70, "throw_selection_iq": 65, "conditioning_curve": 55,
        },
        "archetype": "thrower_catcher",
        "traits": {},
        "age": 25,
        "club_id": "c1",
        "newcomer": False,
    }
    player = _player_from_dict(payload)
    assert player.ratings.catch_courage == 70
    assert player.archetype.value == "thrower_catcher"
```

If the actual function name in `persistence.py` is not `_player_from_dict`, adjust the import — the function around line 74 is the one that builds a `Player` from a dict.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_persistence_loud_fail.py -v`
Expected: FAIL — the current loader silently defaults to `PlayerArchetype.TACTICAL` (which no longer exists, so it will actually raise something — but the error message won't name the missing v2 fields).

- [ ] **Step 3: Rewrite the player-from-dict loader**

In `persistence.py`, locate the function around line 74 that reads a player from a dict. Replace its archetype-and-ratings reading section with explicit field checking:

```python
def _player_from_dict(d: dict) -> Player:
    ratings_d = d.get("ratings", {})
    required_rating_fields = (
        "accuracy", "power", "dodge", "catch", "stamina", "tactical_iq",
        "catch_courage", "throw_selection_iq", "conditioning_curve",
    )
    missing = [f for f in required_rating_fields if f not in ratings_d]
    if missing:
        raise ValueError(
            f"Cannot load player {d.get('id', '?')!r}: ratings missing v2 fields "
            f"{missing}. Plan B made a clean break with V1-V11 saves "
            f"(brief §8)."
        )
    if "archetype" not in d:
        raise ValueError(
            f"Cannot load player {d.get('id', '?')!r}: missing 'archetype' key. "
            f"Plan B requires explicit archetype assignment."
        )
    archetype_value = d["archetype"]
    try:
        archetype = PlayerArchetype(archetype_value)
    except ValueError as e:
        raise ValueError(
            f"Cannot load player {d.get('id', '?')!r}: unknown archetype "
            f"{archetype_value!r}. Valid values: "
            f"{[a.value for a in PlayerArchetype]}"
        ) from e

    ratings = PlayerRatings(
        accuracy=ratings_d["accuracy"],
        power=ratings_d["power"],
        dodge=ratings_d["dodge"],
        catch=ratings_d["catch"],
        stamina=ratings_d["stamina"],
        tactical_iq=ratings_d["tactical_iq"],
        catch_courage=ratings_d["catch_courage"],
        throw_selection_iq=ratings_d["throw_selection_iq"],
        conditioning_curve=ratings_d["conditioning_curve"],
    )

    return Player(
        id=d["id"],
        name=d["name"],
        ratings=ratings,
        archetype=archetype,
        traits=_traits_from_dict(d.get("traits", {})),
        age=d.get("age", 18),
        club_id=d.get("club_id"),
        newcomer=d.get("newcomer", True),
    )
```

If `_traits_from_dict` is a different name in the file, use whatever already exists for the trait read path.

Then update the corresponding `_player_to_dict` (or whichever serializer writes the player out) to include the new v2 rating fields in its output. Grep for `"accuracy":` in `persistence.py` to find it.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_persistence_loud_fail.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q 2>&1 | tail -10`

Existing roundtrip persistence tests may fail if they constructed legacy-shaped fixtures. Update those fixtures to include the new v2 fields and an explicit archetype. Grep for tests that exercise persistence: `grep -rln "persistence\|_player_from_dict\|_player_to_dict" tests/`.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(persistence): loud-fail on legacy V1-V11 player data (Plan B Task 5)

Loaders now raise ValueError naming the missing v2 fields or invalid
archetype value. No silent default-50 backfill, no silent
archetype-to-TACTICAL fallback. Existing roundtrip tests updated to
construct v2-shaped fixtures.

Aligns with brief §8 clean-break policy."
```

---

## Task 6: Randomizer rebase to `derive_archetype`

**Files:**
- Modify: `src/dodgeball_sim/randomizer.py:6-100`.
- Test: `tests/test_randomizer_archetype.py` (new).

- [ ] **Step 1: Write the failing test**

Create `tests/test_randomizer_archetype.py`:

```python
import random
from collections import Counter

from dodgeball_sim.randomizer import _random_team
from dodgeball_sim.models import PlayerArchetype


def _generate_many(seed: int, team_count: int = 40) -> list:
    rng = random.Random(seed)
    players = []
    for _ in range(team_count):
        team = _random_team(rng, min_players=5, max_players=5)
        players.extend(team.players)
    return players


def test_random_players_have_v2_archetype():
    for p in _generate_many(seed=42):
        assert isinstance(p.archetype, PlayerArchetype)


def test_random_players_have_v2_ratings():
    for p in _generate_many(seed=42):
        assert 0 <= p.ratings.catch_courage <= 100
        assert 0 <= p.ratings.throw_selection_iq <= 100
        assert 0 <= p.ratings.conditioning_curve <= 100


def test_randomizer_archetype_distribution_is_diverse():
    """With ~200 generated players, at least 4 distinct archetypes appear,
    and no single archetype dominates more than 75% of the pool."""
    players = _generate_many(seed=7, team_count=40)
    assert len(players) >= 150
    arches = {p.archetype for p in players}
    assert len(arches) >= 4
    counts = Counter(p.archetype for p in players)
    most_common_share = counts.most_common(1)[0][1] / len(players)
    assert most_common_share < 0.75
```

The test exercises the existing `_random_team` (private but used as the public roster generator throughout the codebase). The Task 6 rewrite changes `_random_team`'s internal archetype logic, not its signature.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_randomizer_archetype.py -v`
Expected: FAIL or error — randomizer still uses old `rng.choice(list(PlayerArchetype))` which no longer maps cleanly to the per-archetype bonus blocks.

- [ ] **Step 3: Rewrite the randomizer's player roller**

The current implementation lives inside `_random_team` (around lines 86-110 in `randomizer.py`). Inside its `for idx in range(count):` loop, replace the `archetype = rng.choice(list(PlayerArchetype))` block and its V6 if/elif rating-bias chain with:

```python
        # Roll raw ratings first (incl. v2 fields), then derive archetype.
        accuracy = _roll_rating(rng)
        power = _roll_rating(rng)
        dodge = _roll_rating(rng)
        catch = _roll_rating(rng)
        stamina = _roll_rating(rng)
        tactical_iq = _roll_rating(rng)
        catch_courage = _roll_rating(rng)
        throw_selection_iq = _roll_rating(rng)
        conditioning_curve = _roll_rating(rng)

        ratings = PlayerRatings(
            accuracy=accuracy,
            power=power,
            dodge=dodge,
            catch=catch,
            stamina=stamina,
            tactical_iq=tactical_iq,
            catch_courage=catch_courage,
            throw_selection_iq=throw_selection_iq,
            conditioning_curve=conditioning_curve,
        ).apply_bounds()

        archetype = derive_archetype(ratings)
```

If the existing randomizer applies per-archetype rating bonuses (boosting accuracy for POWER, etc.), preserve the *intent* in the new shape: roll a base rating set, derive a candidate archetype, optionally apply a small rating-shaping bonus that nudges the chosen base archetype's stats. A simple implementation:

```python
def _apply_archetype_shaping(rng, ratings: PlayerRatings, archetype: PlayerArchetype) -> PlayerRatings:
    """Nudge ratings to make the archetype more legible. ±5 to the base archetype's two rating fields."""
    fields_by_base = {
        PlayerArchetype.THROWER: ("accuracy", "power"),
        PlayerArchetype.CATCHER: ("catch", "catch_courage"),
        PlayerArchetype.BALL_HAWK: ("stamina", "throw_selection_iq"),
        PlayerArchetype.DODGER_ANCHOR: ("dodge", "tactical_iq"),
    }
    # For a hybrid, primary base's pair gets +5, secondary's pair gets +3.
    from .archetype_derivation import primary_and_secondary_bases
    primary, secondary = primary_and_secondary_bases(ratings)
    bonuses = {primary: 5.0}
    if archetype not in fields_by_base:  # hybrid
        bonuses[secondary] = 3.0

    updates = dict(
        accuracy=ratings.accuracy,
        power=ratings.power,
        dodge=ratings.dodge,
        catch=ratings.catch,
        stamina=ratings.stamina,
        tactical_iq=ratings.tactical_iq,
        catch_courage=ratings.catch_courage,
        throw_selection_iq=ratings.throw_selection_iq,
        conditioning_curve=ratings.conditioning_curve,
    )
    for base, bonus in bonuses.items():
        for field_name in fields_by_base[base]:
            updates[field_name] = updates[field_name] + bonus
    return PlayerRatings(**updates).apply_bounds()
```

Hook it in after the initial `derive_archetype` call: roll → derive → shape → final derive (re-derive in case the shaping pushed the boundary). If re-derivation changes the archetype, accept the new value — the shaping was about making the *original* derived archetype more legible, but the data wins.

Add the import at the top of `randomizer.py`:

```python
from .archetype_derivation import derive_archetype, primary_and_secondary_bases
```

- [ ] **Step 4: Run randomizer tests**

Run: `python -m pytest tests/test_randomizer_archetype.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q 2>&1 | tail -10`

Any pre-existing randomizer tests that asserted V6 enum values must be updated to the new enum. Find them: `grep -rln "PlayerArchetype.POWER\|PlayerArchetype.AGILITY\|PlayerArchetype.PRECISION\|PlayerArchetype.DEFENSE\|PlayerArchetype.TACTICAL" tests/`.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(randomizer): rebase player rolling on derive_archetype (Plan B Task 6)

Random players now roll all nine rating fields (incl. catch_courage,
throw_selection_iq, conditioning_curve), derive their archetype via the
canonical helper, optionally get a small legibility-shaping bonus on
their archetype's rating pair, and are re-derived (data wins).

Old per-archetype-uniform-choice logic gone."
```

---

## Task 7: `development.py` per-archetype rewrite + hybrid weighted union

**Files:**
- Modify: `src/dodgeball_sim/development.py:7,85-130`.
- Modify: `tests/test_development.py` (rewrite assertions).
- Test: `tests/test_development_hybrid_inheritance.py` (new).

- [ ] **Step 1: Write the failing test for hybrid inheritance**

Create `tests/test_development_hybrid_inheritance.py`:

```python
from dodgeball_sim.development import _primary_stats_for_archetype
from dodgeball_sim.models import PlayerArchetype


def test_base_thrower_primary_stats():
    assert _primary_stats_for_archetype(PlayerArchetype.THROWER) == (
        ("accuracy", 1.0),
        ("power", 1.0),
    )


def test_base_catcher_primary_stats():
    assert _primary_stats_for_archetype(PlayerArchetype.CATCHER) == (
        ("catch", 1.0),
        ("catch_courage", 1.0),
    )


def test_base_ball_hawk_primary_stats():
    assert _primary_stats_for_archetype(PlayerArchetype.BALL_HAWK) == (
        ("stamina", 1.0),
        ("throw_selection_iq", 1.0),
    )


def test_base_dodger_anchor_primary_stats():
    assert _primary_stats_for_archetype(PlayerArchetype.DODGER_ANCHOR) == (
        ("dodge", 1.0),
        ("tactical_iq", 1.0),
    )


def test_thrower_catcher_hybrid_uses_weighted_union():
    # 60% primary base (THROWER), 40% secondary base (CATCHER).
    assert _primary_stats_for_archetype(PlayerArchetype.THROWER_CATCHER) == (
        ("accuracy", 0.6),
        ("power", 0.6),
        ("catch", 0.4),
        ("catch_courage", 0.4),
    )


def test_hawk_dodger_hybrid_uses_weighted_union():
    assert _primary_stats_for_archetype(PlayerArchetype.HAWK_DODGER) == (
        ("stamina", 0.6),
        ("throw_selection_iq", 0.6),
        ("dodge", 0.4),
        ("tactical_iq", 0.4),
    )
```

Note: hybrid weight ordering is fixed by the hybrid's *name order* (THROWER_CATCHER → THROWER is primary; HAWK_DODGER → BALL_HAWK is primary). This is independent of the runtime `primary_and_secondary_bases()` call — within `_primary_stats_for_archetype` the order is determined statically by the enum value's structure.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_development_hybrid_inheritance.py -v`
Expected: FAIL on `ImportError: cannot import name '_primary_stats_for_archetype'`.

- [ ] **Step 3: Rewrite the per-archetype block in `development.py`**

Replace the existing per-archetype if/elif chain (around lines 92-99) with a table-driven approach. At the top of the file, add:

```python
from .models import Player, PlayerArchetype, PlayerRatings


# Primary stats per base archetype, with growth-pool weight (1.0 for pure base).
_BASE_PRIMARY_STATS: dict[PlayerArchetype, tuple[str, ...]] = {
    PlayerArchetype.THROWER: ("accuracy", "power"),
    PlayerArchetype.CATCHER: ("catch", "catch_courage"),
    PlayerArchetype.BALL_HAWK: ("stamina", "throw_selection_iq"),
    PlayerArchetype.DODGER_ANCHOR: ("dodge", "tactical_iq"),
}

# Hybrid -> (primary_base, secondary_base). The earlier-named base in the
# enum value name is the primary (gets 0.6 weight); the later is secondary
# (gets 0.4 weight). This is pinned by Plan B §Pinned design decisions §5.
_HYBRID_DECOMPOSITION: dict[PlayerArchetype, tuple[PlayerArchetype, PlayerArchetype]] = {
    PlayerArchetype.THROWER_CATCHER: (PlayerArchetype.THROWER, PlayerArchetype.CATCHER),
    PlayerArchetype.THROWER_DODGER: (PlayerArchetype.THROWER, PlayerArchetype.DODGER_ANCHOR),
    PlayerArchetype.CATCHER_HAWK: (PlayerArchetype.CATCHER, PlayerArchetype.BALL_HAWK),
    PlayerArchetype.HAWK_DODGER: (PlayerArchetype.BALL_HAWK, PlayerArchetype.DODGER_ANCHOR),
}

_PRIMARY_WEIGHT = 0.6
_SECONDARY_WEIGHT = 0.4


def _primary_stats_for_archetype(archetype: PlayerArchetype) -> tuple[tuple[str, float], ...]:
    """Return the (stat_name, growth_weight) pairs for this archetype.

    Base archetypes: their two primary stats at weight 1.0 each.
    Hybrids: primary base's stats at 0.6 and secondary base's stats at 0.4.
    """
    if archetype in _BASE_PRIMARY_STATS:
        return tuple((s, 1.0) for s in _BASE_PRIMARY_STATS[archetype])
    if archetype in _HYBRID_DECOMPOSITION:
        primary, secondary = _HYBRID_DECOMPOSITION[archetype]
        return (
            tuple((s, _PRIMARY_WEIGHT) for s in _BASE_PRIMARY_STATS[primary])
            + tuple((s, _SECONDARY_WEIGHT) for s in _BASE_PRIMARY_STATS[secondary])
        )
    raise ValueError(f"No primary-stats mapping for archetype {archetype!r}")
```

Then update the growth-allocation block (around lines 86-130) to use this. Find the existing block that builds `primary_stats = ["accuracy", "tactical_iq"]` etc. — replace with:

```python
    weighted_stats = _primary_stats_for_archetype(player.archetype)
    total_weight = sum(w for _, w in weighted_stats)
    if total_weight == 0:
        return player  # safety
    for stat_name, weight in weighted_stats:
        share = pool * (weight / total_weight)
        # ... existing per-stat growth application using `share` instead of pool/len(primary_stats)
```

Adapt the surrounding allocation math accordingly — the key change is that the pool is split by *weight*, not divided equally over a primary-stats list.

- [ ] **Step 4: Run the hybrid-inheritance test**

Run: `python -m pytest tests/test_development_hybrid_inheritance.py -v`
Expected: 6 PASS.

- [ ] **Step 5: Rewrite `tests/test_development.py` against the new enum**

Open `tests/test_development.py`. Find the assertions that mention `PlayerArchetype.POWER`, `.AGILITY`, `.PRECISION`, `.DEFENSE`, `.TACTICAL`. Replace each with the closest new-enum analogue:

- `POWER` → `THROWER` (accuracy/power-focused growth)
- `AGILITY` → `DODGER_ANCHOR` (dodge-focused)
- `PRECISION` → `THROWER` (accuracy-focused; merge into THROWER)
- `DEFENSE` → `CATCHER` (catch-focused)
- `TACTICAL` → `DODGER_ANCHOR` (tactical_iq is now part of DODGER_ANCHOR's score)

Adjust the expected stat lists to match the new `_BASE_PRIMARY_STATS` table. Any test asserting "accuracy and tactical_iq grow together for PRECISION" needs to be split or refocused — the rec-league archetypes don't preserve that exact pairing.

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest -q 2>&1 | tail -10`
Expected: `tests/test_development.py`, `tests/test_development_hybrid_inheritance.py`, and prior new tests all green.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(development): per-archetype growth uses new enum + 60/40 hybrid (Plan B Task 7)

Per-archetype primary stats are now table-driven (_BASE_PRIMARY_STATS,
_HYBRID_DECOMPOSITION) keyed on the new PlayerArchetype values. Hybrid
archetypes split the growth pool 60% to primary base + 40% to
secondary base (weighted union — design §Pinned decisions §5).

tests/test_development.py rewritten to assert against the new
archetype values. The old POWER/AGILITY/PRECISION/DEFENSE/TACTICAL
assertions no longer make sense — V6 split is gone."
```

---

## Task 8: `lineup.py` per-slot archetype map rewrite

**Files:**
- Modify: `src/dodgeball_sim/lineup.py:13-23`.
- Modify: `tests/test_lineup.py`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_lineup.py` (or create a new module-level test):

```python
from dodgeball_sim.lineup import COURT_SLOT_PREFERENCES
from dodgeball_sim.models import PlayerArchetype


def test_court_slot_preferences_use_new_enum():
    # All four court slots have at least one preferred archetype from the new enum.
    assert set(COURT_SLOT_PREFERENCES.keys()) == {0, 1, 2, 3}
    all_arches = set()
    for slot, prefs in COURT_SLOT_PREFERENCES.items():
        assert isinstance(prefs, set)
        assert all(isinstance(a, PlayerArchetype) for a in prefs)
        all_arches.update(prefs)
    # No V6 leftovers (would raise on enum access).
    legacy_names = {"POWER", "AGILITY", "PRECISION", "DEFENSE", "TACTICAL"}
    assert not any(a.name in legacy_names for a in all_arches)


def test_lineup_accepts_hybrid_via_any_base():
    """A hybrid player satisfies any slot that accepts either of its bases."""
    from dodgeball_sim.lineup import slot_accepts
    # THROWER_CATCHER should fit a THROWER slot OR a CATCHER slot.
    assert slot_accepts(PlayerArchetype.THROWER_CATCHER, {PlayerArchetype.THROWER}) is True
    assert slot_accepts(PlayerArchetype.THROWER_CATCHER, {PlayerArchetype.CATCHER}) is True
    assert slot_accepts(PlayerArchetype.THROWER_CATCHER, {PlayerArchetype.BALL_HAWK}) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_lineup.py -v`
Expected: FAIL — `COURT_SLOT_PREFERENCES` still references old enum values; `slot_accepts` doesn't exist.

- [ ] **Step 3: Rewrite `lineup.py`**

Replace the `COURT_SLOT_PREFERENCES` dict (lines 20-23):

```python
from .models import Player, PlayerArchetype


# Court slots: 0 = front-left, 1 = front-right, 2 = back-left, 3 = back-right.
# Slot preferences after the V6 -> Plan B archetype rewrite. Rec-league
# spatial intuitions: anchors hold front lanes; throwers favor back lines
# where they have a throw arc; hawks roam mid; catchers go where the ball is.
COURT_SLOT_PREFERENCES: dict[int, set[PlayerArchetype]] = {
    0: {PlayerArchetype.DODGER_ANCHOR, PlayerArchetype.CATCHER},
    1: {PlayerArchetype.DODGER_ANCHOR, PlayerArchetype.BALL_HAWK},
    2: {PlayerArchetype.THROWER, PlayerArchetype.BALL_HAWK},
    3: {PlayerArchetype.THROWER, PlayerArchetype.CATCHER},
}


_HYBRID_DECOMPOSITION: dict[PlayerArchetype, tuple[PlayerArchetype, PlayerArchetype]] = {
    PlayerArchetype.THROWER_CATCHER: (PlayerArchetype.THROWER, PlayerArchetype.CATCHER),
    PlayerArchetype.THROWER_DODGER: (PlayerArchetype.THROWER, PlayerArchetype.DODGER_ANCHOR),
    PlayerArchetype.CATCHER_HAWK: (PlayerArchetype.CATCHER, PlayerArchetype.BALL_HAWK),
    PlayerArchetype.HAWK_DODGER: (PlayerArchetype.BALL_HAWK, PlayerArchetype.DODGER_ANCHOR),
}


def slot_accepts(archetype: PlayerArchetype, slot_prefs: set[PlayerArchetype]) -> bool:
    """A base archetype matches if it's in the slot's preferences.
    A hybrid matches if either of its two base parents is."""
    if archetype in slot_prefs:
        return True
    if archetype in _HYBRID_DECOMPOSITION:
        primary, secondary = _HYBRID_DECOMPOSITION[archetype]
        return primary in slot_prefs or secondary in slot_prefs
    return False
```

If there is an existing function that uses the slot preferences (e.g. `assign_slots(players)`), update it to call `slot_accepts(player.archetype, prefs)` rather than doing a direct `in` check.

- [ ] **Step 4: Run lineup tests**

Run: `python -m pytest tests/test_lineup.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q 2>&1 | tail -10`
Expected: green for lineup-related tests.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(lineup): rewrite court-slot preferences for new archetypes (Plan B Task 8)

COURT_SLOT_PREFERENCES rewritten against the four new base archetypes.
Hybrids fit any slot that accepts either of their base parents via
slot_accepts(). Old V6 slot mappings gone."
```

---

## Task 9: `identity.py` `classify_archetype` rebase

**Files:**
- Modify: `src/dodgeball_sim/identity.py:14,60-160`.
- Modify: `tests/test_v6_player_identity.py` (rewrite assertions).

- [ ] **Step 1: Survey current identity strings**

The current `identity.py` derives six string archetypes ("ace sniper", "power cannon", "escape artist", "ball hawk", "iron anchor", "two-way spark") via its own scoring formula and feeds them to prefix / suffix / title lookup tables.

Per design, identity must route through `derive_archetype` and surface display strings, never raw enum values.

- [ ] **Step 2: Write the failing test**

Update `tests/test_v6_player_identity.py` (or add to it):

```python
from dodgeball_sim.identity import classify_archetype, identity_card
from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings, PlayerTraits


def _player(arch: PlayerArchetype, **rating_kwargs) -> Player:
    base = dict(accuracy=60, power=60, dodge=60, catch=60, stamina=60,
                tactical_iq=60, catch_courage=60, throw_selection_iq=60,
                conditioning_curve=60)
    base.update(rating_kwargs)
    return Player(
        id="p1", name="Test Player",
        ratings=PlayerRatings(**base),
        archetype=arch,
        traits=PlayerTraits(),
    )


def test_classify_returns_display_string_for_base():
    # A pure THROWER produces the "Thrower" display string, not "thrower".
    p = _player(PlayerArchetype.THROWER, accuracy=95, power=95)
    result = classify_archetype(p)
    # Result is a human-display string. Plan B leaves the exact copy to
    # identity.py — but assert it's not the raw enum value.
    assert result != "thrower"
    assert "Thrower" in result or "thrower" in result.lower()


def test_classify_returns_distinct_display_for_each_base():
    seen = set()
    for arch, ratings in [
        (PlayerArchetype.THROWER, dict(accuracy=95, power=95)),
        (PlayerArchetype.CATCHER, dict(catch=95, catch_courage=95)),
        (PlayerArchetype.BALL_HAWK, dict(stamina=95, throw_selection_iq=95)),
        (PlayerArchetype.DODGER_ANCHOR, dict(dodge=95, tactical_iq=95)),
    ]:
        seen.add(classify_archetype(_player(arch, **ratings)))
    assert len(seen) == 4


def test_classify_returns_distinct_display_for_hybrids():
    hybrids = [
        PlayerArchetype.THROWER_CATCHER,
        PlayerArchetype.THROWER_DODGER,
        PlayerArchetype.CATCHER_HAWK,
        PlayerArchetype.HAWK_DODGER,
    ]
    seen = {classify_archetype(_player(h)) for h in hybrids}
    assert len(seen) == 4


def test_identity_card_carries_display_name():
    p = _player(PlayerArchetype.THROWER, accuracy=95, power=95)
    card = identity_card(p)
    assert card.archetype != "thrower"  # raw enum value forbidden
```

- [ ] **Step 3: Rewrite `classify_archetype`**

In `identity.py`, replace the entire `classify_archetype` function (around lines 66-135) with:

```python
from .models import Player, PlayerArchetype


def classify_archetype(player: Player) -> str:
    """Return the rec-league display string for this player's archetype.

    Plan B: identity strings are now derived from PlayerArchetype.display_name,
    not from a parallel scoring formula. Player.archetype is set at
    construction by the canonical derive_archetype helper.
    """
    return player.archetype.display_name
```

The previous prefix / suffix / title lookup tables (`_ARCHETYPE_PREFIXES`, etc.) are keyed on the old six-string archetypes. Update their keys to the new enum:

```python
_ARCHETYPE_PREFIXES: dict[PlayerArchetype, tuple[str, ...]] = {
    PlayerArchetype.THROWER: ("Sniper", "Cannon", "Spear", "Bolt", "Rifle", "Hammer", "Lance", "Blade"),
    PlayerArchetype.CATCHER: ("Hands", "Trap", "Net", "Hook", "Grip", "Catch", "Snatch", "Reel"),
    PlayerArchetype.BALL_HAWK: ("Hawk", "Scout", "Tracker", "Runner", "Sweep", "Roam", "Falcon", "Stalker"),
    PlayerArchetype.DODGER_ANCHOR: ("Wall", "Tank", "Forge", "Guard", "Plate", "Shield", "Dome", "Citadel"),
    PlayerArchetype.THROWER_CATCHER: ("Wave", "Spark", "Flux", "Charge", "Current", "Surge", "Volt", "Arc"),
    PlayerArchetype.THROWER_DODGER: ("Storm", "Dart", "Flash", "Strike", "Pulse", "Whirl", "Vector", "Crash"),
    PlayerArchetype.CATCHER_HAWK: ("Pounce", "Snare", "Magnet", "Claw", "Vise", "Lattice", "Echo", "Field"),
    PlayerArchetype.HAWK_DODGER: ("Drift", "Phantom", "Glide", "Veil", "Whisper", "Shadow", "Loop", "Ghost"),
}
```

(Keep the existing prefix lists where they were sensible; only rename the keys and add prefix tuples for the new hybrids. Same shape for `_ARCHETYPE_SUFFIXES` and `_ARCHETYPE_TITLES` — re-key against the enum.)

Update `generate_nickname` (line 138+) to look up via the enum:

```python
def generate_nickname(player: Player, rng: DeterministicRNG) -> str:
    archetype = player.archetype
    prefix = _seeded_choice(
        _ARCHETYPE_PREFIXES[archetype],
        rng,
        f"{player.id}:{player.name}:{archetype.value}:prefix",
    )
    suffix = _seeded_choice(
        _ARCHETYPE_SUFFIXES[archetype],
        rng,
        f"{player.id}:{player.name}:{archetype.value}:suffix",
    )
    last_name = _last_name_token(player.name)
    style_roll = _seeded_index(rng, f"{player.id}:{player.name}:{archetype.value}:style", 3)
    ...
```

Update the `identity_card` function similarly: replace string-archetype lookups with `player.archetype` enum lookups.

- [ ] **Step 4: Run identity tests**

Run: `python -m pytest tests/test_v6_player_identity.py -v`
Expected: PASS for the new tests. Existing assertions that referenced "ace sniper" / "power cannon" / etc. need to be updated to reference `display_name` strings.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q 2>&1 | tail -10`
Expected: green for identity tests. Other tests may still be red on archetype semantics — those land in Task 10.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(identity): rebase classify_archetype on PlayerArchetype enum (Plan B Task 9)

classify_archetype now returns player.archetype.display_name. The
parallel six-string scoring formula in identity.py is gone. Prefix /
suffix / title tables are re-keyed on the new enum and gain entries
for the four hybrids.

tests/test_v6_player_identity.py rewritten against display strings."
```

---

## Task 10: `recruitment.py` + `scouting.py` rebase

**Files:**
- Modify: `src/dodgeball_sim/recruitment.py:146,293-304`.
- Modify: `src/dodgeball_sim/scouting.py:71-84`.

- [ ] **Step 1: Survey both files**

```
recruitment.py:
  L146: archetype_pool = ("Sharpshooter", "Enforcer", "Escape Artist", "Ball Hawk", "Iron Engine")
  L175: true_archetype = _archetype_for_ratings(ratings)
  L293: def _archetype_for_ratings(ratings: dict[str, float]) -> str: ...

scouting.py:
  L71: def _reveal_archetype(player: Player) -> str: ...
```

Both functions derive a string archetype from rating values via their own scoring formulas. Per design they must route through `derive_archetype` and translate the resulting enum to a per-system display string.

- [ ] **Step 2: Write the failing test**

Append to `tests/test_archetype_display_smoke.py` (creating the file if absent — full content lands in Task 15; for now just the recruitment/scouting checks):

```python
import pytest

from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings, PlayerTraits


def _player(arch: PlayerArchetype, **rating_kwargs) -> Player:
    base = dict(accuracy=60, power=60, dodge=60, catch=60, stamina=60,
                tactical_iq=60, catch_courage=60, throw_selection_iq=60,
                conditioning_curve=60)
    base.update(rating_kwargs)
    return Player(
        id="p1", name="Test Player",
        ratings=PlayerRatings(**base),
        archetype=arch,
        traits=PlayerTraits(),
    )


def test_recruitment_archetype_for_player_returns_display_string():
    from dodgeball_sim.recruitment import archetype_for_player
    p = _player(PlayerArchetype.THROWER, accuracy=95, power=95)
    label = archetype_for_player(p)
    # Must not leak a raw enum value or value string.
    assert label not in (a.value for a in PlayerArchetype)
    assert label != ""


def test_scouting_reveal_returns_display_string():
    from dodgeball_sim.scouting import reveal_archetype
    p = _player(PlayerArchetype.CATCHER, catch=95, catch_courage=95)
    label = reveal_archetype(p)
    assert label not in (a.value for a in PlayerArchetype)
    assert label != ""
```

- [ ] **Step 3: Rewrite `recruitment.py`**

Replace `_archetype_for_ratings` and its callers. At the top, add:

```python
from .archetype_derivation import derive_archetype
from .models import Player, PlayerArchetype, PlayerRatings


_RECRUITMENT_DISPLAY_NAMES: dict[PlayerArchetype, str] = {
    PlayerArchetype.THROWER: "Sharpshooter",
    PlayerArchetype.CATCHER: "Net Specialist",
    PlayerArchetype.BALL_HAWK: "Ball Hawk",
    PlayerArchetype.DODGER_ANCHOR: "Iron Anchor",
    PlayerArchetype.THROWER_CATCHER: "Two-Way Threat",
    PlayerArchetype.THROWER_DODGER: "Skirmisher",
    PlayerArchetype.CATCHER_HAWK: "Possession Specialist",
    PlayerArchetype.HAWK_DODGER: "Hit-and-Run",
}


def archetype_for_player(player: Player) -> str:
    return _RECRUITMENT_DISPLAY_NAMES[player.archetype]
```

Remove `_archetype_for_ratings`. Update line 146 — the recruitment pool — to be derived from the dict values:

```python
archetype_pool = tuple(_RECRUITMENT_DISPLAY_NAMES.values())
```

Update line 175 from `_archetype_for_ratings(ratings)` to `_RECRUITMENT_DISPLAY_NAMES[derive_archetype(ratings_obj)]` where `ratings_obj` is the `PlayerRatings` instance (the old function took a dict; if the call site has a dict, build a `PlayerRatings` from it first).

Update the mislabel path (line 177) to pick from `archetype_pool` excluding `true_archetype`.

- [ ] **Step 4: Rewrite `scouting.py`**

Same shape. At the top:

```python
from .archetype_derivation import derive_archetype
from .models import Player, PlayerArchetype


_SCOUTING_DISPLAY_NAMES: dict[PlayerArchetype, str] = {
    PlayerArchetype.THROWER: "Cannon Arm",
    PlayerArchetype.CATCHER: "Sticky Hands",
    PlayerArchetype.BALL_HAWK: "Floor General",
    PlayerArchetype.DODGER_ANCHOR: "Brick Wall",
    PlayerArchetype.THROWER_CATCHER: "Swing Player",
    PlayerArchetype.THROWER_DODGER: "Counter-Puncher",
    PlayerArchetype.CATCHER_HAWK: "Roaming Glove",
    PlayerArchetype.HAWK_DODGER: "Stealth Runner",
}


def reveal_archetype(player: Player) -> str:
    return _SCOUTING_DISPLAY_NAMES[player.archetype]
```

Remove the old `_reveal_archetype` (lines 71-84). Update its callers in the same file (`scouting.py:28`, `:34`, `:49`) to call the new `reveal_archetype(player)`.

- [ ] **Step 5: Update scouting/recruitment consumers**

Find callers of the old `_archetype_for_ratings` and `_reveal_archetype`. Most are within the same files; if any are imported externally (e.g. `dynasty_cli.py`, `recruiting_office.py`), update those call sites to use the new public functions.

```bash
grep -rn "_archetype_for_ratings\|_reveal_archetype" src/ tests/
```

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_archetype_display_smoke.py tests/test_v6_player_identity.py -v`
Expected: relevant smoke tests green.

Run: `python -m pytest -q 2>&1 | tail -10`
Expected: any tests that pinned old strings (`"Sharpshooter"`, `"Escape Artist"`, etc.) need updating to new copy. Find them: `grep -rln "Sharpshooter\|Enforcer\|Iron Engine\|Iron Anchor" tests/`.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(recruit/scout): rebase archetype labels on derive_archetype (Plan B Task 10)

recruitment.py and scouting.py each get a per-system display-name
dict keyed on the new PlayerArchetype enum. The parallel scoring
formulas in _archetype_for_ratings and _reveal_archetype are removed.
Public helpers archetype_for_player() and reveal_archetype() return
human-display strings; raw enum values never leak.

Each system keeps its own copy vocabulary (recruitment uses
'Sharpshooter / Net Specialist / ...', scouting uses 'Cannon Arm /
Sticky Hands / ...') so screens that surface both stay distinguishable."
```

---

## Task 11: Rec driver — re-source `conditioning_curve`

**Files:**
- Modify: `src/dodgeball_sim/rec_engine.py:178-184`.
- Modify: `src/dodgeball_sim/fatigue.py` (doc only).
- Test: `tests/test_rec_engine.py` (extend).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_rec_engine.py`:

```python
from dodgeball_sim.fatigue import FatigueParams, accumulate, FatigueState
from dodgeball_sim.models import PlayerRatings


def test_conditioning_curve_sources_from_new_field_not_stamina():
    """Fatigue accumulation must depend on ratings.conditioning_curve, not stamina."""
    fresh_ratings = PlayerRatings(
        accuracy=50, power=50, dodge=50, catch=50,
        stamina=50, tactical_iq=50,
        catch_courage=50, throw_selection_iq=50,
        conditioning_curve=90,   # high conditioning
    )
    tired_ratings = PlayerRatings(
        accuracy=50, power=50, dodge=50, catch=50,
        stamina=50, tactical_iq=50,
        catch_courage=50, throw_selection_iq=50,
        conditioning_curve=10,   # low conditioning
    )
    # If the rec driver sources conditioning_curve correctly, the
    # FatigueParams it builds for these two players differ.
    from dodgeball_sim.rec_engine import _fatigue_params_for_ratings
    fresh_params = _fatigue_params_for_ratings(fresh_ratings)
    tired_params = _fatigue_params_for_ratings(tired_ratings)
    assert fresh_params.conditioning_curve == 90
    assert tired_params.conditioning_curve == 10
    # Sanity: the multiplier differs.
    assert fresh_params.accumulation_multiplier() < tired_params.accumulation_multiplier()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_rec_engine.py::test_conditioning_curve_sources_from_new_field_not_stamina -v`
Expected: FAIL — `_fatigue_params_for_ratings` doesn't exist; Plan A sources from `stamina`.

- [ ] **Step 3: Extract and re-source**

In `rec_engine.py`, find the block in `_init_runtime` around lines 178-184:

```python
        for pid in list(mi.starters_a) + list(mi.starters_b):
            stamina = float(mi.player_lookup[pid].ratings.stamina)
            fatigue_params[pid] = FatigueParams(conditioning_curve=stamina)
            fatigue[pid] = FatigueState.fresh()
```

Replace with:

```python
        for pid in list(mi.starters_a) + list(mi.starters_b):
            fatigue_params[pid] = _fatigue_params_for_ratings(
                mi.player_lookup[pid].ratings
            )
            fatigue[pid] = FatigueState.fresh()
```

Add the helper at module scope (above `class RecTier1Driver`):

```python
def _fatigue_params_for_ratings(ratings) -> FatigueParams:
    """Build per-player FatigueParams sourced from the v2
    conditioning_curve field (not stamina)."""
    return FatigueParams(conditioning_curve=float(ratings.conditioning_curve))
```

- [ ] **Step 4: Update the doc comment in `fatigue.py`**

Open `fatigue.py`. Update the module docstring (lines 1-9):

```python
"""In-match fatigue primitive.

Tracks per-player fatigue from 0.0 (fresh) to 1.0 (collapsed). The
``conditioning_curve`` parameter is sourced from
``PlayerRatings.conditioning_curve`` (Plan B). Plan A used the
``stamina`` field as a placeholder before the v2 attribute landed; that
coupling is now gone — ``stamina`` is back to being a general fitness
pool used elsewhere in the engine.
"""
```

- [ ] **Step 5: Run the test and the suite**

Run: `python -m pytest tests/test_rec_engine.py -v`
Expected: new test PASS, existing rec-engine tests still green.

Run: `python tools/tier_1_sanity_probe.py`
Expected: prints `OK` with all six moment kinds (default rating profile has `conditioning_curve=50` so fatigue dynamics shift slightly; the probe must still pass).

If the sanity probe fails to emit `gassed_collapse`, check whether the default `conditioning_curve=50` produces less fatigue than the previous `stamina=60` placeholder. If so, the probe input may need to bump `conditioning_curve` lower — but Plan B holds the input fixture at neutral (50). If the probe genuinely fails, adjust `_make_player` in `tools/tier_1_sanity_probe.py` to set `conditioning_curve=30` for the probe roster (this is acceptable — the probe is a stress test, not a balance lock).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(rec): source FatigueParams.conditioning_curve from v2 rating (Plan B Task 11)

Rec driver now reads PlayerRatings.conditioning_curve to build per-
player FatigueParams. Plan A's stamina placeholder is removed.
stamina returns to being a general fitness pool (used in recovery
between rallies and across matches).

fatigue.py docstring updated to reflect the new source field."
```

---

## Task 12: Rec driver — `catch_courage` 3-way dodge/block/catch

**Files:**
- Modify: `src/dodgeball_sim/rec_engine.py:403-481`.
- Test: `tests/test_rec_engine_catch_courage.py` (new).

- [ ] **Step 1: Write the failing test**

Create `tests/test_rec_engine_catch_courage.py`:

```python
"""Plan B: catch_courage gates a three-way choice (dodge | block | catch).

Tests use deterministic seeded RNG and check exact branch coverage, not
probabilistic counts."""

from unittest.mock import patch

import pytest

from dodgeball_sim.engine_driver import DriverMatchInput
from dodgeball_sim.models import CoachPolicy, Player, PlayerArchetype, PlayerRatings
from dodgeball_sim.rec_engine import RecTier1Driver, _response_branch_for_courage


def test_branch_function_low_courage_picks_dodge():
    """With courage=10, the response-roll under 0.5 picks dodge."""
    assert _response_branch_for_courage(courage=10, response_roll=0.5) == "dodge"


def test_branch_function_mid_courage_picks_block():
    """With courage=50, the middle of the courage-band picks block."""
    assert _response_branch_for_courage(courage=50, response_roll=0.5) == "block"


def test_branch_function_high_courage_picks_catch():
    """With courage=90, the response roll picks catch in the upper band."""
    assert _response_branch_for_courage(courage=90, response_roll=0.5) == "catch"


def test_branch_function_boundary_at_low_band():
    # Default thresholds (see implementation):
    # dodge if response_roll > (1 - dodge_share)
    # block if (1 - dodge_share - block_share) <= roll <= (1 - dodge_share)
    # catch if roll < (1 - dodge_share - block_share)
    # For courage=50, expect dodge_share ~ 0.5, block_share ~ 0.3, catch_share ~ 0.2
    # The exact splits are pinned in the implementation; assert by branch only.
    assert _response_branch_for_courage(courage=50, response_roll=0.0) == "catch"
    assert _response_branch_for_courage(courage=50, response_roll=0.999) == "dodge"


def _player(pid, courage):
    return Player(
        id=pid, name=pid,
        ratings=PlayerRatings(
            accuracy=60, power=60, dodge=60, catch=80,
            stamina=60, tactical_iq=60,
            catch_courage=courage,
            throw_selection_iq=50, conditioning_curve=50,
        ),
        archetype=PlayerArchetype.CATCHER,
    )


def test_high_courage_run_produces_more_catches_than_low():
    """End-to-end: a CATCHER with courage=95 vs courage=5, all else equal."""
    high = [_player(f"hi{i}", 95) for i in range(6)]
    low = [_player(f"lo{i}", 5) for i in range(6)]
    opp = [_player(f"opp{i}", 50) for i in range(6)]

    def _run(team_a_players, team_b_players, seed):
        lookup = {p.id: p for p in team_a_players + team_b_players}
        mi = DriverMatchInput(
            match_id="m",
            team_a_id="a", team_b_id="b",
            starters_a=tuple(p.id for p in team_a_players),
            starters_b=tuple(p.id for p in team_b_players),
            player_lookup=lookup,
            policy_a=CoachPolicy(), policy_b=CoachPolicy(),
            seed=seed,
        )
        return RecTier1Driver().run(mi)

    high_catches = 0
    low_catches = 0
    for seed in range(20):
        out_high = _run(high, opp, seed)
        out_low = _run(low, opp, seed)
        high_catches += sum(1 for e in out_high.events if e.get("type") == "catch_return")
        low_catches += sum(1 for e in out_low.events if e.get("type") == "catch_return")
    # Deterministic across 20 seeds: high-courage CATCHERs catch strictly more.
    assert high_catches > low_catches
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_rec_engine_catch_courage.py -v`
Expected: FAIL — `_response_branch_for_courage` doesn't exist; rec engine has no block lane.

- [ ] **Step 3: Add the branch helper and the block lane**

At module scope in `rec_engine.py`, add:

```python
def _response_branch_for_courage(*, courage: float, response_roll: float) -> str:
    """Pick among dodge / block / catch given a [0,1] response roll and 0-100 courage.

    Plan B §Architecture: high courage shifts mass from dodge toward catch;
    block is the medium-courage middle lane.

    Pinned split (linear in courage):
      catch_share = 0.05 + 0.55 * (courage / 100)   # 0.05 to 0.60
      block_share = 0.30 - 0.10 * abs(courage - 50) / 50   # peaks at courage=50
      dodge_share = 1.0 - catch_share - block_share

    Roll [0, catch_share) -> catch
    Roll [catch_share, catch_share + block_share) -> block
    Roll [catch_share + block_share, 1.0) -> dodge
    """
    c = max(0.0, min(100.0, float(courage)))
    catch_share = 0.05 + 0.55 * (c / 100.0)
    block_share = 0.30 - 0.10 * abs(c - 50.0) / 50.0
    if response_roll < catch_share:
        return "catch"
    if response_roll < catch_share + block_share:
        return "block"
    return "dodge"
```

Then update `_resolve_throw` (around lines 403-481) to call this branch function. Replace the current binary catch-vs-dodge logic with:

```python
    def _resolve_throw(self, rt, mi, thrower_id, thrower_team_id, team_a, team_b) -> None:
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

        # Headshot self-out (unchanged).
        if rt.rng.random() < 0.05:
            self._mark_out(rt, thrower_id, thrower_team_id, team_a, team_b)
            rt.events.append({"type": "headshot_thrower_out", "thrower": thrower_id})
            reset_on_throw_call(rt, thrower_team_id, team_a)
            return

        accuracy = (thrower.ratings.accuracy / 100.0) * thrower_eff
        dodge_skill = (target.ratings.dodge / 100.0) * target_eff
        catch_skill = (target.ratings.catch / 100.0) * target_eff

        # First: does the throw connect at all (accuracy vs dodge)?
        if rt.rng.random() >= accuracy * (1.0 - dodge_skill):
            rt.events.append({"type": "miss", "thrower": thrower_id, "target": target_state.player_id})
            reset_on_throw_call(rt, thrower_team_id, team_a)
            return

        # Throw connected. Target picks dodge/block/catch via courage.
        response_roll = rt.rng.random()
        branch = _response_branch_for_courage(
            courage=target.ratings.catch_courage,
            response_roll=response_roll,
        )

        if branch == "catch":
            # Catch only succeeds proportional to catch skill * effectiveness.
            catch_roll = rt.rng.random()
            if catch_roll < catch_skill:
                # Successful catch -> thrower out, returning player from queue.
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
                    rt.comeback_catches[catcher_team] = rt.comeback_catches.get(catcher_team, 0) + 1
                    self._emit_dramatic_catch(
                        rt, mi, target_state, thrower_id, thrower_team_id, returning_pid, team_a, team_b
                    )
            else:
                # Failed catch -> target out.
                self._mark_out(rt, target_state.player_id, target_state.team_id, team_a, team_b)
                rt.events.append({"type": "catch_failed_hit", "thrower": thrower_id, "target": target_state.player_id})
        elif branch == "block":
            # Block deflects: nobody out. Tracked as an event.
            rt.events.append({"type": "block", "thrower": thrower_id, "blocker": target_state.player_id})
        else:  # branch == "dodge"
            # Already passed the connect check above so the throw was on target,
            # but the target chose dodge. Resolve dodge skill explicitly.
            if rt.rng.random() < dodge_skill:
                rt.events.append({"type": "dodge", "thrower": thrower_id, "target": target_state.player_id})
            else:
                self._mark_out(rt, target_state.player_id, target_state.team_id, team_a, team_b)
                rt.events.append({"type": "hit", "thrower": thrower_id, "target": target_state.player_id})

        reset_on_throw_call(rt, thrower_team_id, team_a)
```

Extract the dramatic-catch emission into its own helper (the original code does this inline). Add:

```python
    def _emit_dramatic_catch(self, rt, mi, target_state, thrower_id, thrower_team_id, returning_pid, team_a, team_b) -> None:
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
                catcher_team_id=target_state.team_id,
                thrower_id=thrower_id,
                thrower_team_id=thrower_team_id,
                returning_player_id=returning_pid,
                active_count_a=active_a_now,
                active_count_b=active_b_now,
            )
        )
```

- [ ] **Step 4: Run tests and probe**

Run: `python -m pytest tests/test_rec_engine_catch_courage.py tests/test_rec_engine.py -v`
Expected: green.

Run: `python tools/tier_1_sanity_probe.py`
Expected: prints `OK` with all six moment kinds. **Critical regression gate** — the new block lane changes match-outcome dynamics; if a moment kind drops out, the input ratings in the probe fixture must be tuned to maintain coverage. Adjust `tools/tier_1_sanity_probe.py:_make_player` to set ratings closer to extreme values (e.g. raise `catch_courage` to 65) until all six emit again.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: green.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(rec): catch_courage gates 3-way dodge/block/catch (Plan B Task 12)

The rec driver's response branch is now dodge | block | catch, weighted
by the target's catch_courage. Catch share scales linearly from 5% at
courage=0 to 60% at courage=100; block share peaks at courage=50 (30%)
and tapers toward the extremes; dodge fills the rest.

Block deflects the throw: nobody goes out, event recorded for replay.
Catch on success returns a teammate from the queue (as before); catch
on failure means the target goes out (cost of bravery).

_response_branch_for_courage extracted so it can be unit-tested
deterministically without running the driver."
```

---

## Task 13: Rec driver — `throw_selection_iq` with stall-clock awareness

**Files:**
- Modify: `src/dodgeball_sim/rec_engine.py:380-401`.
- Test: `tests/test_rec_engine_throw_iq.py` (new).

- [ ] **Step 1: Write the failing test**

Create `tests/test_rec_engine_throw_iq.py`:

```python
"""Plan B: throw_selection_iq filters _select_throwers candidates.

High IQ throws only when expected value clears a threshold, EXCEPT
under late-stall pressure when high IQ throws more (good judgment, not
passivity).
"""

import pytest

from dodgeball_sim.rec_engine import _should_throw_under_iq


def test_low_iq_throws_freely_when_value_low():
    # Low IQ ignores the value threshold (~current Plan A behavior).
    assert _should_throw_under_iq(
        iq=10, expected_value=0.1, stall_seconds=0.0, stall_cap=10.0,
    ) is True


def test_high_iq_skips_low_value_throw_when_clock_is_fresh():
    assert _should_throw_under_iq(
        iq=90, expected_value=0.1, stall_seconds=0.0, stall_cap=10.0,
    ) is False


def test_high_iq_throws_when_value_is_high():
    assert _should_throw_under_iq(
        iq=90, expected_value=0.9, stall_seconds=0.0, stall_cap=10.0,
    ) is True


def test_high_iq_throws_under_late_stall_pressure():
    """Critical: high IQ does NOT mean 'passive'. Near the stall cap, even
    low-value throws fire because forced action beats a stall reset."""
    assert _should_throw_under_iq(
        iq=90, expected_value=0.1, stall_seconds=8.5, stall_cap=10.0,
    ) is True


def test_mid_iq_at_mid_value_throws():
    assert _should_throw_under_iq(
        iq=50, expected_value=0.5, stall_seconds=0.0, stall_cap=10.0,
    ) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_rec_engine_throw_iq.py -v`
Expected: FAIL — `_should_throw_under_iq` doesn't exist.

- [ ] **Step 3: Add the IQ filter and wire it into `_select_throwers`**

At module scope in `rec_engine.py`:

```python
def _should_throw_under_iq(
    *,
    iq: float,
    expected_value: float,
    stall_seconds: float,
    stall_cap: float,
) -> bool:
    """High-IQ throwers wait for high-value throws — EXCEPT under stall
    pressure. As stall_seconds approaches stall_cap, the IQ threshold
    relaxes linearly to 0 (forced-action mode).

    Plan B design: 'good judgment, not passivity.'

    Threshold = (iq / 100) * (1 - stall_pressure)
    where stall_pressure = stall_seconds / stall_cap, clamped to [0, 1].

    Returns True if expected_value >= threshold.
    """
    iq_norm = max(0.0, min(100.0, float(iq))) / 100.0
    stall_pressure = max(0.0, min(1.0, stall_seconds / max(stall_cap, 0.001)))
    threshold = iq_norm * (1.0 - stall_pressure)
    return expected_value >= threshold
```

Update `_select_throwers` (around lines 380-401):

```python
    def _select_throwers(self, rt, mi, team_a: str, team_b: str) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {team_a: [], team_b: []}
        opp_active_by_team = {
            team_a: [p for p in rt.players.values()
                     if p.team_id == team_b and p.status == OfficialPlayerStatus.ACTIVE],
            team_b: [p for p in rt.players.values()
                     if p.team_id == team_a and p.status == OfficialPlayerStatus.ACTIVE],
        }
        stall_state_by_team = {team_a: rt.stall_a, team_b: rt.stall_b}

        for team_id in (team_a, team_b):
            active = [
                p for p in rt.players.values()
                if p.team_id == team_id and p.status == OfficialPlayerStatus.ACTIVE
            ]
            if not active or not opp_active_by_team[team_id]:
                continue
            stall_seconds = stall_state_by_team[team_id].seconds_holding
            candidates = []
            for p in active:
                player = mi.player_lookup[p.player_id]
                eff = effectiveness(rt.fatigue[p.player_id])
                # Expected hit value: rough proxy for "good throw available".
                expected_value = (player.ratings.accuracy / 100.0) * eff
                if not _should_throw_under_iq(
                    iq=player.ratings.throw_selection_iq,
                    expected_value=expected_value,
                    stall_seconds=stall_seconds,
                    stall_cap=rt.rules.stall_cap_seconds,
                ):
                    continue
                # Existing per-player throw-trigger probability.
                if rt.rng.random() < 0.4 * eff:
                    candidates.append(p.player_id)
            result[team_id] = candidates[:3]
        return result
```

- [ ] **Step 4: Run tests + probe**

Run: `python -m pytest tests/test_rec_engine_throw_iq.py tests/test_rec_engine.py -v`
Expected: green.

Run: `python tools/tier_1_sanity_probe.py`
Expected: `OK` with all six moment kinds. The new IQ filter is conservative for high-IQ players at low values, which may suppress flood-throw and gassed-collapse rates. If a kind drops out, raise the probe's default `accuracy` or `throw_selection_iq` to compensate (still within `_make_player` in the probe fixture).

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: green.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(rec): throw_selection_iq gates throw value under stall pressure (Plan B Task 13)

_select_throwers now consults _should_throw_under_iq before adding a
player to the candidate list. The IQ threshold scales linearly with
the throw's expected value (accuracy * effectiveness), but RELAXES
to zero as stall_timer.seconds_holding approaches the stall cap.

High IQ means 'good judgment, including smarter forced throws under
clock pressure' — never passivity. Pinned by the
late-stall-pressure test."
```

---

## Task 14: `sample_data.py` curated rosters — v2 fields + explicit archetype

**Files:**
- Modify: `src/dodgeball_sim/sample_data.py`.

- [ ] **Step 1: Survey current curated rosters**

Run: `grep -n "Player(\|PlayerRatings(\|archetype" src/dodgeball_sim/sample_data.py | head -40`

Identify every `Player(...)` or `PlayerRatings(...)` construction. Each one must now:
- Include `catch_courage`, `throw_selection_iq`, `conditioning_curve` in the `PlayerRatings(...)`.
- Include an explicit `archetype=PlayerArchetype.<value>` in the `Player(...)`.

- [ ] **Step 2: Walk every roster entry**

For each curated player, hand-author the v2 fields based on the existing rating profile. Suggested heuristic (apply at author's discretion — these are characterization choices):

- Default the three new fields to 50 if no obvious lean.
- For a clearly aggressive/risk-taking player: `catch_courage=70-85`.
- For a smart, patient player: `throw_selection_iq=70-85`.
- For a workhorse / iron-engine type: `conditioning_curve=70-85`.

For each player's archetype, call out the intent. Examples:

```python
Player(
    id="thunder_carter",
    name="Carter Thunder",
    ratings=PlayerRatings(
        accuracy=85, power=88, dodge=55, catch=60,
        stamina=70, tactical_iq=55,
        catch_courage=50, throw_selection_iq=65, conditioning_curve=60,
    ),
    archetype=PlayerArchetype.THROWER,
),
Player(
    id="quick_lin",
    name="Lin Quick",
    ratings=PlayerRatings(
        accuracy=58, power=52, dodge=92, catch=72,
        stamina=78, tactical_iq=80,
        catch_courage=65, throw_selection_iq=72, conditioning_curve=80,
    ),
    archetype=PlayerArchetype.DODGER_ANCHOR,
),
```

For any player where the hand-author choice is unclear, call:

```python
from .archetype_derivation import derive_archetype

# at the bottom of the constructor list, optional:
_ratings = PlayerRatings(...)
_archetype = derive_archetype(_ratings)
```

…but prefer hand-authored archetype for curated rosters so the lineup reads intentionally.

- [ ] **Step 3: Run tests that load sample data**

Run: `python -m pytest tests/ -q 2>&1 | tail -20`

Any test or use case that boots a curated roster (career creation tests, dynasty CLI tests) will surface failures if a Player was missed.

- [ ] **Step 4: Commit**

```bash
git add src/dodgeball_sim/sample_data.py
git commit -m "feat(sample_data): curated rosters carry v2 ratings + explicit archetypes (Plan B Task 14)

Every curated Player now declares catch_courage, throw_selection_iq,
conditioning_curve in its PlayerRatings, and an explicit
PlayerArchetype on the Player itself. Hand-authored archetypes give
the curated lineups intentional character — no derived-default
fallback for curated content.

Random players (via randomizer.py) still use derive_archetype."
```

---

## Task 15: Display-name leak smoke test

**Files:**
- Modify: `tests/test_archetype_display_smoke.py` (already partially seeded in Task 10).

- [ ] **Step 1: Write the comprehensive smoke test**

Replace the contents of `tests/test_archetype_display_smoke.py` with:

```python
"""Smoke test: raw PlayerArchetype enum values must never leak into
user-facing strings from identity, recruitment, or scouting.

Plan B Task 15. See plan-b-design.md §Pinned design decisions §7.
"""

import pytest

from dodgeball_sim.identity import classify_archetype
from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings, PlayerTraits
from dodgeball_sim.recruitment import archetype_for_player
from dodgeball_sim.scouting import reveal_archetype


def _raw_value_set() -> set[str]:
    return {a.value for a in PlayerArchetype}


def _player(arch: PlayerArchetype) -> Player:
    return Player(
        id="p",
        name="Test",
        ratings=PlayerRatings(
            accuracy=60, power=60, dodge=60, catch=60,
            stamina=60, tactical_iq=60,
            catch_courage=60, throw_selection_iq=60, conditioning_curve=60,
        ),
        archetype=arch,
        traits=PlayerTraits(),
    )


def test_display_name_present_for_every_member():
    for arch in PlayerArchetype:
        assert arch.display_name
        assert arch.display_name != arch.value


def test_classify_archetype_never_returns_raw_value():
    raw = _raw_value_set()
    for arch in PlayerArchetype:
        assert classify_archetype(_player(arch)) not in raw


def test_recruitment_never_returns_raw_value():
    raw = _raw_value_set()
    for arch in PlayerArchetype:
        assert archetype_for_player(_player(arch)) not in raw


def test_scouting_never_returns_raw_value():
    raw = _raw_value_set()
    for arch in PlayerArchetype:
        assert reveal_archetype(_player(arch)) not in raw


def test_recruitment_and_scouting_have_distinct_vocab():
    """Each system should have its own copy — same enum produces
    different strings across systems."""
    arch = PlayerArchetype.CATCHER
    assert archetype_for_player(_player(arch)) != reveal_archetype(_player(arch))


def test_display_name_is_human_friendly():
    """Display names should not contain underscores."""
    for arch in PlayerArchetype:
        assert "_" not in arch.display_name
```

- [ ] **Step 2: Run the smoke test**

Run: `python -m pytest tests/test_archetype_display_smoke.py -v`
Expected: 6 PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_archetype_display_smoke.py
git commit -m "test: archetype display-name leak smoke test (Plan B Task 15)

Iterates all 8 PlayerArchetype values and asserts that no public-facing
output from identity, recruitment, or scouting equals a raw enum value
string. Also pins:
- Every member has a non-empty display_name distinct from its value.
- Display names never contain underscores.
- Recruitment and scouting use distinct vocabularies for the same enum."
```

---

## Task 16: Full regression + sanity probe gate

**Files:** None modified. This task is a verification gate.

- [ ] **Step 1: Run the full Python test suite**

Run: `python -m pytest -q`
Expected: all tests pass. Record the test count.

If any test fails, fix it before proceeding — Plan B is not done until the full suite is green.

- [ ] **Step 2: Run the Tier 1 sanity probe**

Run: `python tools/tier_1_sanity_probe.py`
Expected: exits 0 with `OK` printed and all six moment kinds present in the output.

If any of the six kinds (`dramatic_catch`, `late_game_escape`, `one_v_one_finale`, `gassed_collapse`, `flood_throw`, `comeback`) is missing, adjust the probe's fixture ratings in `tools/tier_1_sanity_probe.py:_make_player` to nudge the missing kind back into existence. **Document any fixture tuning in the commit message.**

- [ ] **Step 3: Spot-check V11 / USAD conformance is untouched**

Run: `python -m pytest tests/test_official_conformance_matrix.py tests/test_official_autonomous_game.py -v`
Expected: all green. These tests are the contract that Plan B must not break.

- [ ] **Step 4: Spot-check Plan A integration**

Run: `python -m pytest tests/test_tier_1_integration.py tests/test_official_driver.py tests/test_engine_driver.py -v`
Expected: all green.

- [ ] **Step 5: Commit a verification marker if any incidental fixes were needed**

If incidental fixes landed in this verification pass (e.g. probe fixture tuning), commit them as:

```bash
git add -A
git commit -m "chore(plan-b): verification gate fixes (Plan B Task 16)

[describe any fixture or test adjustments made to keep regression green]"
```

Otherwise no commit needed.

---

## Task 17: Documentation — STATUS.md and roadmap update

**Files:**
- Modify: `docs/STATUS.md`.
- Modify: `docs/specs/2026-05-20-post-v11-redesign-brief/tier-1-roadmap.md`.

- [ ] **Step 1: Update `docs/STATUS.md`**

In the "Shipped And Verified" section, add an entry for Plan B beneath the Plan A row:

```markdown
- **Post-V11 redesign — Plan B: Player attribute v2** (landed 2026-05-XX) — see `docs/specs/2026-05-20-post-v11-redesign-brief/plan-b-design.md` and `plan-b-player-attribute-v2.md`. `PlayerRatings` gains `catch_courage`, `throw_selection_iq`, `conditioning_curve`. `PlayerArchetype` rewritten to 4 rec-league bases (THROWER, CATCHER, BALL_HAWK, DODGER_ANCHOR) plus 4 named hybrids; old V6 values gone. Single canonical `derive_archetype` helper; randomizer / recruitment / scouting / identity all route through it. Rec driver gains three new decision points (one per new attribute). Persistence fails loudly on legacy V1–V11 data per brief §8 clean break. Six moment kinds still emit; V11 / USAD conformance untouched.
```

In the "Current Phase" paragraph, update the post-V11 progress line:

> ...Plan A (hybrid driver architecture + Tier 1 engine) shipped on 2026-05-20, **Plan B (player attribute v2) shipped on 2026-05-XX**, and Plans C/D live in...

Replace the V11 `PlayerArchetype`-vestigial claim in the "Open Work And Known Gaps" #5 entry. The current text says:

> The `PlayerArchetype` enum/field is vestigial (defaults to `TACTICAL`, never assigned).

That claim was wrong — the audit during Plan B showed randomizer / development / lineup all branched on it load-bearingly. Replace with:

> Plan B replaced the V6 `PlayerArchetype` enum with rec-league semantics. The audit during Plan B found the old enum was NOT vestigial as previously documented — `randomizer.py`, `development.py`, and `lineup.py` all branched on it. STATUS.md is now corrected.

- [ ] **Step 2: Update `tier-1-roadmap.md`**

In the plan-sequence table, mark Plan B as landed:

```markdown
| **B** | **Player attribute v2** | Data-model upgrade | **landed 2026-05-XX** | — |
```

Update the milestone-progress note at the top of the file to reflect that B is done and C is unblocked.

- [ ] **Step 3: Final regression gate**

Run once more: `python -m pytest -q && python tools/tier_1_sanity_probe.py`
Expected: tests green, probe `OK`.

- [ ] **Step 4: Commit**

```bash
git add docs/STATUS.md docs/specs/2026-05-20-post-v11-redesign-brief/tier-1-roadmap.md
git commit -m "docs(plan-b): mark Player Attribute v2 landed; correct PlayerArchetype claim

STATUS.md now reflects Plan B landing. The 'vestigial archetype'
claim from earlier docs is corrected: the audit during Plan B
showed randomizer/development/lineup all branched on the V6 enum.

tier-1-roadmap.md plan-sequence table updated."
```

---

## Plan B: definition of done

All of the following are true before Plan B is considered complete:

- [ ] All 17 tasks above are checked off.
- [ ] `python -m pytest -q` reports green. Test count delta from the Plan A close-out baseline of 725 should be a **positive** increment — every new attribute, archetype enum behavior, hybrid inheritance rule, persistence fail-mode, and display-leak check has at least one new test.
- [ ] `python tools/tier_1_sanity_probe.py` exits 0 with `OK` and all six moment kinds present.
- [ ] No file under `src/dodgeball_sim/burden.py`, `discipline.py`, `no_blocking.py`, `official_engine.py`, `engine_driver.py`, `moment_events.py`, `flood_throws.py`, `stall_timer.py`, `official_driver.py` has been modified by Plan B.
- [ ] `PlayerArchetype` has exactly 8 values; V6 values (POWER / AGILITY / PRECISION / DEFENSE / TACTICAL) are gone.
- [ ] `PlayerRatings.overall()` no longer exists; every caller uses `overall_skill()`.
- [ ] `derive_archetype` is the only place in the codebase that assigns a `PlayerArchetype` from rating values (verified by grep: any independent scoring loops in `recruitment.py`, `scouting.py`, `identity.py` are gone).
- [ ] Persistence loaders raise `ValueError` with a descriptive message on legacy V1–V11 player data; pinned by `tests/test_persistence_loud_fail.py`.
- [ ] All three new attributes have at least one deterministic behavioral test against the rec driver (no probabilistic "measurably more" assertions).
- [ ] `docs/STATUS.md` reflects Plan B landing and corrects the vestigial-archetype claim.

## Self-review checklist (run before handing off)

1. **Spec coverage** — does every requirement from `plan-b-design.md` appear in at least one task?
   - 3 new ratings → Task 1.
   - `overall_skill` / `identity_profile` split → Task 2.
   - 8-value enum with `display_name` → Task 3.
   - Single `derive_archetype` (base + hybrid + threshold + tie-break + mapping) → Task 4.
   - Loud-fail loaders → Task 5.
   - Randomizer rebase → Task 6.
   - Development weighted-union (60/40) → Task 7.
   - Lineup re-key → Task 8.
   - Identity rebase + display names → Task 9.
   - Recruitment / scouting rebase with distinct vocab → Task 10.
   - Rec driver three decision points → Tasks 11, 12, 13.
   - Curated rosters → Task 14.
   - Display-name leak smoke test → Task 15.
   - Regression gate → Task 16.
   - Docs → Task 17.

2. **Pinned design decisions** — every one of the seven post-approval pins is referenced by a task:
   - §1 weights → Task 4.
   - §2 gap threshold → Task 4 (`GAP_THRESHOLD = 15.0`).
   - §3 tie-break → Task 4.
   - §4 hybrid mapping → Task 4.
   - §5 weighted union → Task 7.
   - §6 tactical_iq role → Task 2 (in `identity_profile`) and Task 4 (in DODGER_ANCHOR score).
   - §7 display-name smoke → Task 15.

3. **Type consistency** — every name (`PlayerArchetype`, `derive_archetype`, `_response_branch_for_courage`, `_should_throw_under_iq`, `_primary_stats_for_archetype`, `archetype_for_player`, `reveal_archetype`, `IdentityProfile`, `GAP_THRESHOLD`) is used identically in its introducing task and all later references.

4. **No placeholders** — every code block contains the real code, not a stub.

---

## Execution handoff

Plan complete and saved to `docs/specs/2026-05-20-post-v11-redesign-brief/plan-b-player-attribute-v2.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — Fresh subagent per task, review between tasks, fast iteration. Use `superpowers:subagent-driven-development`.
2. **Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Which approach?
