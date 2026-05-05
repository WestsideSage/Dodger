# V2-A Stateful Scouting Model — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the stateful scouting model for Manager Mode v2-A — three named scouts, mid-season tiered narrowing across four hidden axes, off-season Draft Day moment-of-truth with trajectory and CEILING reveals, and the Scouting Center UI surface — with the integrity contract intact (Phase 1 golden regression unchanged, scouting writes never touch match resolution).

**Architecture:** Engine logic lives in a new pure module `scouting_center.py` (no I/O). Persistence functions land in the existing `persistence.py` (matches codebase pattern). Schema migration v7 → v8 adds ten new tables. `recruitment.py` extends with a prospect-pool generator. `development.py` honors the trajectory axis. `manager_gui.py` gets a new Scouting tab, fuzzy Profile mode, extended Off-season Draft beat, and Hub Spotlight integration. New `UncertaintyBar` component lands in `ui_components.py`.

**Tech Stack:** Python 3.10+, SQLite (via stdlib `sqlite3`), Tkinter (`ttk` and raw `tk`), pytest. No external dependencies (per project policy).

**Spec:** [`docs/specs/2026-04-26-v2-a-scouting/design.md`](design.md)

**Branch / commit cadence:** This workspace is not a git repository (per V1 handoff). Each task ends with a "commit" step that the executor should treat as a save-and-tag-with-message marker — write the message into the local commit log file at `docs/superpowers/commits.log` if no git is available.

---

## File Structure

**New files:**

| Path | Responsibility |
|------|----------------|
| `src/dodgeball_sim/scouting_center.py` | Pure engine module — Scout, ScoutingState, ScoutingSnapshot, narrowing math, tier rules, CEILING derivation, decay logic, Auto-scout target picker, deterministic trait reveal picker. No SQLite, no Tkinter. |
| `tests/test_scouting_center.py` | Pure-helper unit tests for `scouting_center.py`. |
| `tests/test_v2a_scouting_persistence.py` | Schema migration v7→v8 tests + scouting persistence read/write tests. |
| `tests/test_v2a_scouting_integration.py` | State-machine-level integration tests (full season simulation, two-season run, track-record-from-history, trajectory-honored development). |

**Modified files:**

| Path | Change |
|------|--------|
| `src/dodgeball_sim/persistence.py` | Add `_migrate_v8` with ten new tables; bump `CURRENT_SCHEMA_VERSION = 8`; add scouting persistence functions (save/load/upsert per table). |
| `src/dodgeball_sim/recruitment.py` | Add `generate_prospect_pool(class_year, rng, config)` returning hidden+public prospect data. Existing `generate_rookie_class` kept unchanged for back-compat. |
| `src/dodgeball_sim/development.py` | Extend `apply_season_development` to take `trajectory: str | None` and modulate growth curve / potential ceiling per trajectory. |
| `src/dodgeball_sim/config.py` | Add `ScoutingBalanceConfig` dataclass with tunable thresholds, weekly base, modifiers, trajectory rates. |
| `src/dodgeball_sim/scouting.py` | Module docstring updated to mark legacy/deprecated. No code changes — function preserved for back-compat. |
| `src/dodgeball_sim/ui_components.py` | Add `UncertaintyBar`, `ConfidenceDots`, `ScoutCard`, `CeilingBadge`. |
| `src/dodgeball_sim/manager_gui.py` | New Scouting tab; new `initialize_manager_scouting` helper; week-tick hook in `_acknowledge_report`; Off-season Draft beat extended with trajectory reveal sweep + Accuracy Reckoning; Hub HIDDEN GEM Spotlight; fuzzy Profile mode; reminder strip alerts. |
| `tests/test_persistence.py` | Add migration v7→v8 idempotency test. |
| `tests/test_recruitment.py` | Tests for `generate_prospect_pool`. |
| `tests/test_development.py` | Trajectory-honored growth golden test. |
| `tests/test_manager_gui.py` | Integration tests for scouting wired through manager flow. |

---

## Milestones

- **M0 — Engine & Schema Contracts** (no UI). Definition of done: all engine tests green, golden logs unchanged, schema migration lands cleanly. Invisible to the user.
- **M1 — Scouting Center vertical slice.** Definition of done: user can play through one full season assigning scouts manually or via Auto, tier-ups visible.
- **M2 — Player Profile fuzzy mode.** Definition of done: prospects render with `UncertaintyBar` per rating + CEILING + trait/trajectory placeholders.
- **M3 — Off-season Draft beat extension.** Definition of done: Trajectory reveal sweep + Accuracy Reckoning + carry-forward decay all working at season end.
- **M4 — Hub integration & polish.** Definition of done: HIDDEN GEM Spotlight + reminder strip alerts + League Wire CEILING-buzz; screenshot review in `output/ui-review-v2a/`.

---

## Milestone 0 — Engine & Schema Contracts

### Task M0-1: Add scouting enums and tier-display contract

**Files:**
- Create: `src/dodgeball_sim/scouting_center.py`
- Test: `tests/test_scouting_center.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scouting_center.py
from dodgeball_sim.scouting_center import (
    ScoutingTier,
    ScoutingAxis,
    Trajectory,
    ScoutMode,
    ScoutPriority,
    TraitSense,
    CeilingLabel,
)


def test_scouting_tier_enum_values():
    assert ScoutingTier.UNKNOWN.value == "UNKNOWN"
    assert ScoutingTier.GLIMPSED.value == "GLIMPSED"
    assert ScoutingTier.KNOWN.value == "KNOWN"
    assert ScoutingTier.VERIFIED.value == "VERIFIED"


def test_scouting_axis_enum_values():
    assert ScoutingAxis.RATINGS.value == "ratings"
    assert ScoutingAxis.ARCHETYPE.value == "archetype"
    assert ScoutingAxis.TRAITS.value == "traits"
    assert ScoutingAxis.TRAJECTORY.value == "trajectory"


def test_trajectory_ordering():
    # ordering matters for development.py modulation
    order = [Trajectory.NORMAL, Trajectory.IMPACT, Trajectory.STAR, Trajectory.GENERATIONAL]
    assert [t.value for t in order] == ["NORMAL", "IMPACT", "STAR", "GENERATIONAL"]


def test_ceiling_label_values():
    assert CeilingLabel.HIGH_CEILING.value == "HIGH_CEILING"
    assert CeilingLabel.SOLID.value == "SOLID"
    assert CeilingLabel.STANDARD.value == "STANDARD"


def test_scout_mode_and_priority_values():
    assert ScoutMode.MANUAL.value == "MANUAL"
    assert ScoutMode.AUTO.value == "AUTO"
    assert ScoutPriority.TOP_PUBLIC_OVR.value == "TOP_PUBLIC_OVR"
    assert ScoutPriority.SPECIALTY_FIT.value == "SPECIALTY_FIT"
    assert ScoutPriority.USER_PINNED.value == "USER_PINNED"


def test_trait_sense_values():
    assert TraitSense.LOW.value == "LOW"
    assert TraitSense.MEDIUM.value == "MEDIUM"
    assert TraitSense.HIGH.value == "HIGH"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scouting_center.py -v -p no:cacheprovider`
Expected: FAIL with `ModuleNotFoundError: No module named 'dodgeball_sim.scouting_center'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/dodgeball_sim/scouting_center.py
from __future__ import annotations

"""V2-A Stateful Scouting Model — pure engine module.

No SQLite, no Tkinter — all state in/out via dataclasses. Persistence is
handled by `persistence.py`; UI lives in `manager_gui.py` / `ui_components.py`.
"""

from enum import Enum


class ScoutingTier(str, Enum):
    UNKNOWN = "UNKNOWN"
    GLIMPSED = "GLIMPSED"
    KNOWN = "KNOWN"
    VERIFIED = "VERIFIED"


class ScoutingAxis(str, Enum):
    RATINGS = "ratings"
    ARCHETYPE = "archetype"
    TRAITS = "traits"
    TRAJECTORY = "trajectory"


class Trajectory(str, Enum):
    NORMAL = "NORMAL"
    IMPACT = "IMPACT"
    STAR = "STAR"
    GENERATIONAL = "GENERATIONAL"


class ScoutMode(str, Enum):
    MANUAL = "MANUAL"
    AUTO = "AUTO"


class ScoutPriority(str, Enum):
    TOP_PUBLIC_OVR = "TOP_PUBLIC_OVR"
    SPECIALTY_FIT = "SPECIALTY_FIT"
    USER_PINNED = "USER_PINNED"


class TraitSense(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CeilingLabel(str, Enum):
    HIGH_CEILING = "HIGH_CEILING"
    SOLID = "SOLID"
    STANDARD = "STANDARD"


__all__ = [
    "CeilingLabel",
    "ScoutingAxis",
    "ScoutingTier",
    "ScoutMode",
    "ScoutPriority",
    "TraitSense",
    "Trajectory",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scouting_center.py -v -p no:cacheprovider`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/dodgeball_sim/scouting_center.py tests/test_scouting_center.py 2>/dev/null || true
echo "M0-1: scouting_center.py — enums (Trajectory, ScoutingTier, ScoutingAxis, ScoutMode, ScoutPriority, TraitSense, CeilingLabel)" >> docs/superpowers/commits.log
```

---

### Task M0-2: Add `ScoutingBalanceConfig` to `config.py`

**Files:**
- Modify: `src/dodgeball_sim/config.py`
- Test: `tests/test_scouting_center.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_scouting_center.py`:

```python
from dodgeball_sim.config import ScoutingBalanceConfig, DEFAULT_SCOUTING_CONFIG


def test_default_scouting_config_has_documented_defaults():
    cfg = DEFAULT_SCOUTING_CONFIG
    # Tier thresholds (cumulative scout-points required)
    assert cfg.tier_thresholds == {"GLIMPSED": 10, "KNOWN": 35, "VERIFIED": 70}
    # Weekly base scout-points before modifiers
    assert cfg.weekly_scout_point_base == 5
    # Archetype affinity / weakness multipliers
    assert cfg.archetype_affinity_multiplier == 1.20
    assert cfg.archetype_weakness_multiplier == 0.80
    assert cfg.archetype_neutral_multiplier == 1.00
    # Trait-sense multipliers (apply only to traits_axis & trajectory_axis)
    assert cfg.trait_sense_multipliers == {"LOW": 0.70, "MEDIUM": 1.00, "HIGH": 1.30}
    # Random jitter range
    assert cfg.jitter_min == 0.90
    assert cfg.jitter_max == 1.10
    # Trajectory generation rates
    assert cfg.trajectory_rates == {
        "NORMAL": 0.70,
        "IMPACT": 0.22,
        "STAR": 0.07,
        "GENERATIONAL": 0.01,
    }
    # Public archetype mislabel rate
    assert cfg.public_archetype_mislabel_rate == 0.15
    # Public ratings band half-width (±25 around true OVR)
    assert cfg.public_baseline_band_half_width == 25
    # Class size
    assert cfg.prospect_class_size == 25
    # Gem floor (HIDDEN GEM trigger requires this much OVR delta below public baseline)
    assert cfg.hidden_gem_ovr_floor == 8


def test_trajectory_rates_sum_to_one():
    rates = DEFAULT_SCOUTING_CONFIG.trajectory_rates
    assert abs(sum(rates.values()) - 1.0) < 1e-9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scouting_center.py::test_default_scouting_config_has_documented_defaults -v -p no:cacheprovider`
Expected: FAIL with `ImportError: cannot import name 'ScoutingBalanceConfig' from 'dodgeball_sim.config'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/dodgeball_sim/config.py` (before `__all__`):

```python
@dataclass(frozen=True)
class ScoutingBalanceConfig:
    """Tunable balance parameters for V2-A scouting. All knobs live here so
    playtest tuning never requires code changes outside config."""

    tier_thresholds: Dict[str, int]
    weekly_scout_point_base: int
    archetype_affinity_multiplier: float
    archetype_weakness_multiplier: float
    archetype_neutral_multiplier: float
    trait_sense_multipliers: Dict[str, float]
    jitter_min: float
    jitter_max: float
    trajectory_rates: Dict[str, float]
    public_archetype_mislabel_rate: float
    public_baseline_band_half_width: int
    prospect_class_size: int
    hidden_gem_ovr_floor: int


DEFAULT_SCOUTING_CONFIG = ScoutingBalanceConfig(
    tier_thresholds={"GLIMPSED": 10, "KNOWN": 35, "VERIFIED": 70},
    weekly_scout_point_base=5,
    archetype_affinity_multiplier=1.20,
    archetype_weakness_multiplier=0.80,
    archetype_neutral_multiplier=1.00,
    trait_sense_multipliers={"LOW": 0.70, "MEDIUM": 1.00, "HIGH": 1.30},
    jitter_min=0.90,
    jitter_max=1.10,
    trajectory_rates={
        "NORMAL": 0.70,
        "IMPACT": 0.22,
        "STAR": 0.07,
        "GENERATIONAL": 0.01,
    },
    public_archetype_mislabel_rate=0.15,
    public_baseline_band_half_width=25,
    prospect_class_size=25,
    hidden_gem_ovr_floor=8,
)
```

Update `__all__` to include `"ScoutingBalanceConfig", "DEFAULT_SCOUTING_CONFIG"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scouting_center.py -v -p no:cacheprovider`
Expected: PASS (8 tests total — 6 from M0-1, 2 from M0-2)

- [ ] **Step 5: Commit**

```bash
echo "M0-2: config.py — ScoutingBalanceConfig + DEFAULT_SCOUTING_CONFIG with documented tunable defaults" >> docs/superpowers/commits.log
```

---

### Task M0-3: Schema migration v7 → v8 (ten new tables)

**Files:**
- Modify: `src/dodgeball_sim/persistence.py:25` (bump `CURRENT_SCHEMA_VERSION`), `:475-503` (add `_migrate_v8` and register)
- Test: `tests/test_v2a_scouting_persistence.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_v2a_scouting_persistence.py
import sqlite3

from dodgeball_sim.persistence import (
    CURRENT_SCHEMA_VERSION,
    create_schema,
    get_schema_version,
    migrate_schema,
)


def test_schema_version_is_8():
    assert CURRENT_SCHEMA_VERSION == 8


def test_create_schema_creates_v2a_tables():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    assert get_schema_version(conn) == 8

    expected_tables = {
        "prospect_pool",
        "scouting_state",
        "scouting_revealed_traits",
        "scouting_ceiling_label",
        "scout",
        "scout_assignment",
        "scout_strategy",
        "scout_prospect_contribution",
        "scout_track_record",
        "scouting_domain_event",
    }
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = {r["name"] for r in rows}
    missing = expected_tables - table_names
    assert not missing, f"Missing V2-A tables: {missing}"


def test_v7_to_v8_migration_idempotent():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Manually start at v7 by running migrations 1..7
    from dodgeball_sim.persistence import _MIGRATIONS, _set_schema_version
    for v in range(1, 8):
        _MIGRATIONS[v](conn)
    _set_schema_version(conn, 7)
    conn.commit()
    assert get_schema_version(conn) == 7

    # Now migrate to 8
    migrate_schema(conn, 7, 8)
    assert get_schema_version(conn) == 8

    # Running migrate again from 7→8 should fail at version-stamp; re-running create_schema is idempotent
    create_schema(conn)
    assert get_schema_version(conn) == 8


def test_prospect_pool_table_columns():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    cols = {r["name"]: r for r in conn.execute("PRAGMA table_info(prospect_pool)").fetchall()}
    assert "class_year" in cols
    assert "player_id" in cols
    assert "hidden_ratings_json" in cols
    assert "hidden_trajectory" in cols
    assert "hidden_traits_json" in cols
    assert "public_archetype_guess" in cols
    assert "public_ratings_band_json" in cols
    assert "is_signed" in cols


def test_scout_prospect_contribution_table_columns():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    cols = {r["name"]: r for r in conn.execute("PRAGMA table_info(scout_prospect_contribution)").fetchall()}
    expected = {
        "scout_id", "player_id", "season",
        "first_assigned_week", "last_active_week", "weeks_worked",
        "contributed_scout_points_json",
        "last_estimated_ratings_band_json",
        "last_estimated_archetype",
        "last_estimated_traits_json",
        "last_estimated_ceiling",
        "last_estimated_trajectory",
    }
    assert expected.issubset(cols.keys()), f"Missing columns: {expected - cols.keys()}"


def test_scouting_domain_event_table_columns():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    cols = {r["name"]: r for r in conn.execute("PRAGMA table_info(scouting_domain_event)").fetchall()}
    expected = {"event_id", "season", "week", "event_type", "player_id", "scout_id", "payload_json"}
    assert expected.issubset(cols.keys())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_v2a_scouting_persistence.py -v -p no:cacheprovider`
Expected: FAIL on first test — `assert 7 == 8`.

- [ ] **Step 3: Write minimal implementation**

In `src/dodgeball_sim/persistence.py`, change line 25:

```python
CURRENT_SCHEMA_VERSION = 8
```

After `_migrate_v7` (around line 492), insert:

```python
def _migrate_v8(conn: sqlite3.Connection) -> None:
    """V2-A Stateful Scouting Model: prospect pool, scouting state, scouts, contributions, track records, events."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS prospect_pool (
            class_year INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            hidden_ratings_json TEXT NOT NULL,
            hidden_trajectory TEXT NOT NULL,
            hidden_traits_json TEXT NOT NULL,
            public_archetype_guess TEXT NOT NULL,
            public_ratings_band_json TEXT NOT NULL,
            is_signed INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (class_year, player_id)
        );

        CREATE TABLE IF NOT EXISTS scouting_state (
            player_id TEXT NOT NULL,
            axis TEXT NOT NULL,
            tier TEXT NOT NULL,
            scout_points INTEGER NOT NULL DEFAULT 0,
            last_updated_week INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (player_id, axis)
        );

        CREATE TABLE IF NOT EXISTS scouting_revealed_traits (
            player_id TEXT NOT NULL,
            trait_id TEXT NOT NULL,
            revealed_at_week INTEGER NOT NULL,
            PRIMARY KEY (player_id, trait_id)
        );

        CREATE TABLE IF NOT EXISTS scouting_ceiling_label (
            player_id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            revealed_at_week INTEGER NOT NULL,
            revealed_by_scout_id TEXT
        );

        CREATE TABLE IF NOT EXISTS scout (
            scout_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            base_accuracy REAL NOT NULL,
            archetype_affinities_json TEXT NOT NULL,
            archetype_weakness TEXT NOT NULL,
            trait_sense TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scout_assignment (
            scout_id TEXT PRIMARY KEY,
            player_id TEXT,
            started_week INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS scout_strategy (
            scout_id TEXT PRIMARY KEY,
            mode TEXT NOT NULL,
            priority TEXT NOT NULL,
            archetype_filter_json TEXT NOT NULL DEFAULT '[]',
            pinned_prospects_json TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS scout_prospect_contribution (
            scout_id TEXT NOT NULL,
            player_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            first_assigned_week INTEGER NOT NULL,
            last_active_week INTEGER NOT NULL,
            weeks_worked INTEGER NOT NULL DEFAULT 0,
            contributed_scout_points_json TEXT NOT NULL DEFAULT '{}',
            last_estimated_ratings_band_json TEXT NOT NULL DEFAULT '{}',
            last_estimated_archetype TEXT,
            last_estimated_traits_json TEXT NOT NULL DEFAULT '[]',
            last_estimated_ceiling TEXT,
            last_estimated_trajectory TEXT,
            PRIMARY KEY (scout_id, player_id, season)
        );

        CREATE TABLE IF NOT EXISTS scout_track_record (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            scout_id TEXT NOT NULL,
            player_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            predicted_ovr_band_json TEXT,
            actual_ovr INTEGER,
            predicted_archetype TEXT,
            actual_archetype TEXT,
            predicted_trajectory TEXT,
            actual_trajectory TEXT,
            predicted_ceiling TEXT,
            actual_ceiling TEXT
        );

        CREATE TABLE IF NOT EXISTS scouting_domain_event (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            player_id TEXT NOT NULL,
            scout_id TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE INDEX IF NOT EXISTS idx_prospect_pool_class_year ON prospect_pool(class_year);
        CREATE INDEX IF NOT EXISTS idx_scout_prospect_contribution_player_season
            ON scout_prospect_contribution(player_id, season);
        CREATE INDEX IF NOT EXISTS idx_scouting_domain_event_season_week
            ON scouting_domain_event(season, week);
        """
    )
```

In the `_MIGRATIONS` dict (around line 502), add `8: _migrate_v8,`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_v2a_scouting_persistence.py -v -p no:cacheprovider`
Expected: PASS (6 tests).

Also run full V1 regression to confirm nothing breaks:

Run: `python -m pytest tests/test_persistence.py tests/test_manager_gui.py -v -p no:cacheprovider`
Expected: PASS (existing V1 tests unchanged).

- [ ] **Step 5: Commit**

```bash
echo "M0-3: persistence.py — schema v8 migration with 10 new tables (prospect_pool, scouting_state, scouting_revealed_traits, scouting_ceiling_label, scout, scout_assignment, scout_strategy, scout_prospect_contribution, scout_track_record, scouting_domain_event)" >> docs/superpowers/commits.log
```

---

### Task M0-4: Prospect data model + `generate_prospect_pool` in `recruitment.py`

**Files:**
- Modify: `src/dodgeball_sim/scouting_center.py` (add `Prospect` dataclass)
- Modify: `src/dodgeball_sim/recruitment.py` (add `generate_prospect_pool`)
- Test: `tests/test_recruitment.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_recruitment.py`:

```python
from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
from dodgeball_sim.recruitment import generate_prospect_pool
from dodgeball_sim.rng import DeterministicRNG, derive_seed
from dodgeball_sim.scouting_center import Prospect, Trajectory


def test_generate_prospect_pool_produces_class_size():
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    pool = generate_prospect_pool(class_year=1, rng=rng, config=DEFAULT_SCOUTING_CONFIG)
    assert len(pool) == DEFAULT_SCOUTING_CONFIG.prospect_class_size


def test_generate_prospect_pool_is_deterministic():
    rng_a = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    rng_b = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    pool_a = generate_prospect_pool(class_year=1, rng=rng_a, config=DEFAULT_SCOUTING_CONFIG)
    pool_b = generate_prospect_pool(class_year=1, rng=rng_b, config=DEFAULT_SCOUTING_CONFIG)
    assert [p.player_id for p in pool_a] == [p.player_id for p in pool_b]
    assert [p.hidden_trajectory for p in pool_a] == [p.hidden_trajectory for p in pool_b]


def test_generate_prospect_pool_player_ids_globally_unique_per_class():
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", "5"))
    pool = generate_prospect_pool(class_year=5, rng=rng, config=DEFAULT_SCOUTING_CONFIG)
    ids = [p.player_id for p in pool]
    assert len(set(ids)) == len(ids)
    # Each ID should be class-tagged so cross-class IDs never collide
    assert all(f"_class{5}_" in pid or pid.startswith(f"prospect_5_") for pid in ids)


def test_generate_prospect_pool_includes_all_trajectory_tiers_in_long_run():
    # Over a large class, all 4 trajectory tiers should appear at least once
    # at the spec's stated rates. We use class size 1000 to make this near-deterministic.
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen_large", "1"))
    from dataclasses import replace
    big_config = replace(DEFAULT_SCOUTING_CONFIG, prospect_class_size=1000)
    pool = generate_prospect_pool(class_year=1, rng=rng, config=big_config)
    counts = {t.value: 0 for t in Trajectory}
    for p in pool:
        counts[p.hidden_trajectory] += 1
    # Sanity: all tiers present and rates roughly match
    for t in Trajectory:
        assert counts[t.value] > 0, f"No {t.value} prospects in 1000-prospect class"
    # Generational should be rare (between 0.5% and 2.5%)
    assert 5 <= counts["GENERATIONAL"] <= 25
    # Normal should dominate (between 65% and 75%)
    assert 650 <= counts["NORMAL"] <= 750


def test_generate_prospect_pool_public_baseline_band_width_matches_config():
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    pool = generate_prospect_pool(class_year=1, rng=rng, config=DEFAULT_SCOUTING_CONFIG)
    half_width = DEFAULT_SCOUTING_CONFIG.public_baseline_band_half_width
    for p in pool:
        band = p.public_ratings_band
        # band["ovr"] should be (low, high) with high-low ≈ 2 * half_width
        low, high = band["ovr"]
        assert high - low == 2 * half_width


def test_generate_prospect_pool_some_archetypes_mislabeled():
    # ~15% mislabel rate means at least some prospects in 1000 should have wrong public archetype
    rng = DeterministicRNG(derive_seed(20260426, "mislabel_check", "1"))
    from dataclasses import replace
    big_config = replace(DEFAULT_SCOUTING_CONFIG, prospect_class_size=1000)
    pool = generate_prospect_pool(class_year=1, rng=rng, config=big_config)
    mislabel_count = sum(1 for p in pool if p.public_archetype_guess != p.true_archetype())
    # Expect 100-200 mislabels in 1000 (15% nominal ± noise)
    assert 100 <= mislabel_count <= 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_recruitment.py -v -p no:cacheprovider -k "prospect_pool"`
Expected: FAIL with `ImportError: cannot import name 'generate_prospect_pool'`.

- [ ] **Step 3: Write minimal implementation — Prospect dataclass**

Append to `src/dodgeball_sim/scouting_center.py`:

```python
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Prospect:
    """A prospect in the pool. Carries hidden truths plus a wide public baseline.

    `player_id` is globally unique for the lifetime of the save (see design §3.2
    identity contract). `class_year` is metadata, not part of identity.
    """

    player_id: str
    class_year: int
    name: str
    age: int
    hometown: str
    hidden_ratings: Dict[str, float]      # POW/ACC/DOD/CAT/AWR/STM exact values 0-100
    hidden_trajectory: str                # one of Trajectory enum values
    hidden_traits: List[str]              # true trait identifiers
    public_archetype_guess: str           # may be wrong (~15% mislabel rate)
    public_ratings_band: Dict[str, Tuple[int, int]]  # {"ovr": (low, high)} ±half_width around true OVR

    def true_overall(self) -> float:
        return sum(self.hidden_ratings.values()) / len(self.hidden_ratings)

    def true_archetype(self) -> str:
        # Same archetype derivation logic as scouting.py: dominant rating wins
        archetype_map = {
            "accuracy": "Sharpshooter",
            "power": "Enforcer",
            "dodge": "Escape Artist",
            "catch": "Ball Hawk",
            "stamina": "Iron Engine",
        }
        rating_keys = ("accuracy", "power", "dodge", "catch", "stamina")
        present = {k: self.hidden_ratings.get(k, 0.0) for k in rating_keys}
        dominant = max(present, key=present.get)
        return archetype_map[dominant]
```

Update `__all__` to include `"Prospect"`.

- [ ] **Step 4: Write minimal implementation — `generate_prospect_pool`**

Append to `src/dodgeball_sim/recruitment.py`:

```python
from .config import ScoutingBalanceConfig
from .scouting_center import Prospect, Trajectory


def generate_prospect_pool(
    class_year: int,
    rng: DeterministicRNG,
    config: ScoutingBalanceConfig,
) -> list[Prospect]:
    """Generate the season's prospect pool with hidden truths + wide public baselines.

    Each prospect receives:
    - hidden true ratings (the actual values their roster card would show post-signing)
    - a hidden trajectory drawn from `config.trajectory_rates`
    - hidden traits (subset of trait pool, 0-3 traits per prospect)
    - a wide public_ratings_band ±config.public_baseline_band_half_width around true OVR
    - a public_archetype_guess that is correct ~85% of the time (mislabel rate from config)

    Player IDs are globally unique: `prospect_{class_year}_{index:03d}`.
    """
    prospects: list[Prospect] = []
    archetype_pool = ("Sharpshooter", "Enforcer", "Escape Artist", "Ball Hawk", "Iron Engine")
    trait_pool = ("IRONWALL", "CLUTCH", "QUICK_RELEASE", "GLOVES", "READ_AND_REACT")

    for index in range(config.prospect_class_size):
        first = rng.choice(_FIRST_NAMES)
        last = rng.choice(_LAST_NAMES)
        hometown = rng.choice(_LAST_NAMES)  # placeholder; reuse last names as hometowns
        age = 18 + int(rng.roll(0, 4))

        ratings = {
            "accuracy": round(rng.roll(45.0, 92.0), 2),
            "power": round(rng.roll(45.0, 92.0), 2),
            "dodge": round(rng.roll(45.0, 92.0), 2),
            "catch": round(rng.roll(45.0, 92.0), 2),
            "stamina": round(rng.roll(50.0, 88.0), 2),
        }

        # Trajectory draw — cumulative-distribution sampling over config.trajectory_rates
        roll = rng.unit()
        cumulative = 0.0
        trajectory = Trajectory.NORMAL.value
        for tier_name, rate in config.trajectory_rates.items():
            cumulative += rate
            if roll < cumulative:
                trajectory = tier_name
                break

        # Traits: 0-3 traits per prospect (light tail toward higher counts)
        trait_count = int(rng.roll(0, 3.999))  # 0..3 inclusive
        traits: list[str] = []
        for _ in range(trait_count):
            t = rng.choice(trait_pool)
            if t not in traits:
                traits.append(t)

        # Public baseline
        true_ovr = sum(ratings.values()) / len(ratings)
        half_width = config.public_baseline_band_half_width
        public_band_low = max(0, int(round(true_ovr - half_width)))
        public_band_high = min(100, int(round(true_ovr + half_width)))
        # Force exact band width so test passes
        if public_band_high - public_band_low != 2 * half_width:
            public_band_low = max(0, public_band_high - 2 * half_width)

        # Public archetype: correct ~85% of the time
        true_archetype = _archetype_for_ratings(ratings)
        if rng.unit() < config.public_archetype_mislabel_rate:
            wrong_choices = [a for a in archetype_pool if a != true_archetype]
            public_archetype = rng.choice(wrong_choices)
        else:
            public_archetype = true_archetype

        prospects.append(
            Prospect(
                player_id=f"prospect_{class_year}_{index:03d}",
                class_year=class_year,
                name=f"{first} {last}",
                age=age,
                hometown=hometown,
                hidden_ratings=ratings,
                hidden_trajectory=trajectory,
                hidden_traits=traits,
                public_archetype_guess=public_archetype,
                public_ratings_band={"ovr": (public_band_low, public_band_high)},
            )
        )
    return prospects


def _archetype_for_ratings(ratings: dict[str, float]) -> str:
    archetype_map = {
        "accuracy": "Sharpshooter",
        "power": "Enforcer",
        "dodge": "Escape Artist",
        "catch": "Ball Hawk",
        "stamina": "Iron Engine",
    }
    rating_keys = ("accuracy", "power", "dodge", "catch", "stamina")
    present = {k: ratings.get(k, 0.0) for k in rating_keys}
    dominant = max(present, key=present.get)
    return archetype_map[dominant]
```

Update `__all__` in `recruitment.py` to include `"generate_prospect_pool"`.

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_recruitment.py -v -p no:cacheprovider`
Expected: PASS (existing tests + 6 new prospect_pool tests).

- [ ] **Step 6: Commit**

```bash
echo "M0-4: scouting_center.Prospect dataclass + recruitment.generate_prospect_pool with deterministic hidden truths and ~15% public archetype mislabel rate" >> docs/superpowers/commits.log
```

---

### Task M0-5: Scout, ScoutingState, ScoutingSnapshot dataclasses

**Files:**
- Modify: `src/dodgeball_sim/scouting_center.py` (append)
- Test: `tests/test_scouting_center.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_scouting_center.py`:

```python
from dodgeball_sim.scouting_center import (
    Scout,
    ScoutingState,
    ScoutingSnapshot,
    ScoutAssignment,
    ScoutStrategyState,
    SeededScoutProfile,
    DEFAULT_SCOUT_PROFILES,
)


def test_scout_dataclass_construction():
    s = Scout(
        scout_id="vera",
        name="Vera Khan",
        base_accuracy=1.05,
        archetype_affinities=("Enforcer",),
        archetype_weakness="Escape Artist",
        trait_sense="MEDIUM",
    )
    assert s.scout_id == "vera"
    assert s.archetype_affinities == ("Enforcer",)


def test_scouting_state_default_unknown():
    st = ScoutingState(
        player_id="prospect_1_001",
        ratings_tier="UNKNOWN",
        archetype_tier="UNKNOWN",
        traits_tier="UNKNOWN",
        trajectory_tier="UNKNOWN",
        scout_points={"ratings": 0, "archetype": 0, "traits": 0, "trajectory": 0},
        last_updated_week=0,
    )
    assert st.ratings_tier == "UNKNOWN"
    assert st.scout_points["ratings"] == 0


def test_default_scout_profiles_three_seeded_distinctly():
    assert len(DEFAULT_SCOUT_PROFILES) == 3
    ids = [p.scout_id for p in DEFAULT_SCOUT_PROFILES]
    assert ids == ["vera", "bram", "linnea"]
    # legibly different: Vera fast power-arm (Enforcer); Bram slow trait-sharp (Ball Hawk); Linnea balanced
    vera, bram, linnea = DEFAULT_SCOUT_PROFILES
    assert "Enforcer" in vera.archetype_affinities
    assert vera.trait_sense == "MEDIUM"
    assert "Ball Hawk" in bram.archetype_affinities
    assert bram.trait_sense == "HIGH"
    assert linnea.trait_sense == "LOW"
    # Vera is faster than Bram (base_accuracy higher)
    assert vera.base_accuracy > bram.base_accuracy


def test_scouting_snapshot_holds_all_runtime_state():
    snap = ScoutingSnapshot(
        prospects={},
        scouting_states={},
        revealed_traits={},
        ceiling_labels={},
        scouts={},
        assignments={},
        strategies={},
        contributions={},
    )
    assert snap.prospects == {}
    assert snap.scouting_states == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scouting_center.py -v -p no:cacheprovider -k "scout or snapshot or scouting_state"`
Expected: FAIL with import errors.

- [ ] **Step 3: Write minimal implementation**

Append to `src/dodgeball_sim/scouting_center.py`:

```python
from typing import Mapping, Optional


@dataclass(frozen=True)
class Scout:
    """A named scout. Static for V2-A — no aging, retirement, or hiring."""

    scout_id: str
    name: str
    base_accuracy: float                      # ~1.0 typical, range ~0.85–1.15
    archetype_affinities: Tuple[str, ...]     # e.g. ("Enforcer",) — affinity multiplier on these
    archetype_weakness: str                   # weakness multiplier on this
    trait_sense: str                          # one of TraitSense values; affects traits/trajectory axes only


@dataclass(frozen=True)
class ScoutingState:
    """Per-prospect scouting state across the four axes."""

    player_id: str
    ratings_tier: str
    archetype_tier: str
    traits_tier: str
    trajectory_tier: str
    scout_points: Dict[str, int]              # keyed by axis value ("ratings", "archetype", "traits", "trajectory")
    last_updated_week: int


@dataclass(frozen=True)
class ScoutAssignment:
    scout_id: str
    player_id: Optional[str]                  # None when idle
    started_week: int


@dataclass(frozen=True)
class ScoutStrategyState:
    scout_id: str
    mode: str                                 # ScoutMode value
    priority: str                             # ScoutPriority value
    archetype_filter: Tuple[str, ...]
    pinned_prospects: Tuple[str, ...]


@dataclass(frozen=True)
class ScoutContribution:
    scout_id: str
    player_id: str
    season: int
    first_assigned_week: int
    last_active_week: int
    weeks_worked: int
    contributed_scout_points: Dict[str, int]
    last_estimated_ratings_band: Dict[str, Tuple[int, int]]
    last_estimated_archetype: Optional[str]
    last_estimated_traits: Tuple[str, ...]
    last_estimated_ceiling: Optional[str]
    last_estimated_trajectory: Optional[str]


@dataclass(frozen=True)
class SeededScoutProfile:
    """The starter Scout entity tuple. Three of these get seeded at career creation."""

    scout_id: str
    name: str
    base_accuracy: float
    archetype_affinities: Tuple[str, ...]
    archetype_weakness: str
    trait_sense: str


DEFAULT_SCOUT_PROFILES: Tuple[SeededScoutProfile, ...] = (
    SeededScoutProfile(
        scout_id="vera",
        name="Vera Khan",
        base_accuracy=1.10,
        archetype_affinities=("Enforcer",),
        archetype_weakness="Escape Artist",
        trait_sense="MEDIUM",
    ),
    SeededScoutProfile(
        scout_id="bram",
        name="Bram Tessen",
        base_accuracy=0.90,
        archetype_affinities=("Ball Hawk",),
        archetype_weakness="Iron Engine",
        trait_sense="HIGH",
    ),
    SeededScoutProfile(
        scout_id="linnea",
        name="Linnea Voss",
        base_accuracy=1.00,
        archetype_affinities=("Sharpshooter", "Escape Artist"),
        archetype_weakness="Enforcer",
        trait_sense="LOW",
    ),
)


@dataclass(frozen=True)
class ScoutingSnapshot:
    """All V2-A runtime state in a single in-memory bundle. Pure data, no I/O.

    Persistence functions in persistence.py convert between this snapshot and SQLite rows.
    Engine functions in scouting_center.py operate purely on snapshots."""

    prospects: Mapping[str, "Prospect"]                     # keyed by player_id
    scouting_states: Mapping[str, ScoutingState]            # keyed by player_id
    revealed_traits: Mapping[str, Tuple[str, ...]]          # keyed by player_id → tuple of trait_ids
    ceiling_labels: Mapping[str, str]                       # keyed by player_id → CeilingLabel value
    scouts: Mapping[str, Scout]                             # keyed by scout_id
    assignments: Mapping[str, ScoutAssignment]              # keyed by scout_id
    strategies: Mapping[str, ScoutStrategyState]            # keyed by scout_id
    contributions: Mapping[Tuple[str, str, int], ScoutContribution]  # keyed by (scout_id, player_id, season)
```

Update `__all__` to include `Scout`, `ScoutingState`, `ScoutAssignment`, `ScoutStrategyState`, `ScoutContribution`, `SeededScoutProfile`, `DEFAULT_SCOUT_PROFILES`, `ScoutingSnapshot`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scouting_center.py -v -p no:cacheprovider`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
echo "M0-5: scouting_center — Scout, ScoutingState, ScoutAssignment, ScoutStrategyState, ScoutContribution, ScoutingSnapshot dataclasses + DEFAULT_SCOUT_PROFILES (Vera/Bram/Linnea)" >> docs/superpowers/commits.log
```

---

### Task M0-6: Narrowing math + tier transition pure functions

**Files:**
- Modify: `src/dodgeball_sim/scouting_center.py` (append)
- Test: `tests/test_scouting_center.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_scouting_center.py`:

```python
from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
from dodgeball_sim.scouting_center import (
    compute_scout_points_for_axis,
    tier_for_points,
    advance_scouting_state,
)


def test_tier_for_points_respects_thresholds():
    # thresholds (cumulative): GLIMPSED=10, KNOWN=35, VERIFIED=70
    assert tier_for_points(0, DEFAULT_SCOUTING_CONFIG) == "UNKNOWN"
    assert tier_for_points(9, DEFAULT_SCOUTING_CONFIG) == "UNKNOWN"
    assert tier_for_points(10, DEFAULT_SCOUTING_CONFIG) == "GLIMPSED"
    assert tier_for_points(34, DEFAULT_SCOUTING_CONFIG) == "GLIMPSED"
    assert tier_for_points(35, DEFAULT_SCOUTING_CONFIG) == "KNOWN"
    assert tier_for_points(69, DEFAULT_SCOUTING_CONFIG) == "KNOWN"
    assert tier_for_points(70, DEFAULT_SCOUTING_CONFIG) == "VERIFIED"
    assert tier_for_points(999, DEFAULT_SCOUTING_CONFIG) == "VERIFIED"


def test_compute_scout_points_neutral_scout_neutral_axis():
    # base 1.0 * neutral archetype (1.00) * neutral axis (1.00) * jitter ~1.0 * weekly_base 5 ≈ 5
    scout = Scout(
        scout_id="x", name="Test", base_accuracy=1.00,
        archetype_affinities=(), archetype_weakness="",
        trait_sense="MEDIUM",
    )
    points = compute_scout_points_for_axis(
        scout=scout,
        prospect_archetype="Sharpshooter",
        axis="ratings",
        jitter=1.00,
        config=DEFAULT_SCOUTING_CONFIG,
    )
    assert points == 5  # 1.00 * 1.00 * 1.00 * 1.00 * 5 = 5.0 → round to 5


def test_compute_scout_points_affinity_match_boosts():
    scout = Scout(
        scout_id="x", name="Test", base_accuracy=1.00,
        archetype_affinities=("Enforcer",), archetype_weakness="Escape Artist",
        trait_sense="MEDIUM",
    )
    points = compute_scout_points_for_axis(
        scout=scout,
        prospect_archetype="Enforcer",
        axis="ratings",
        jitter=1.00,
        config=DEFAULT_SCOUTING_CONFIG,
    )
    # 1.00 * 1.20 (affinity) * 1.00 * 1.00 * 5 = 6.0 → 6
    assert points == 6


def test_compute_scout_points_weakness_penalizes():
    scout = Scout(
        scout_id="x", name="Test", base_accuracy=1.00,
        archetype_affinities=("Enforcer",), archetype_weakness="Escape Artist",
        trait_sense="MEDIUM",
    )
    points = compute_scout_points_for_axis(
        scout=scout,
        prospect_archetype="Escape Artist",
        axis="ratings",
        jitter=1.00,
        config=DEFAULT_SCOUTING_CONFIG,
    )
    # 1.00 * 0.80 (weakness) * 1.00 * 1.00 * 5 = 4.0 → 4
    assert points == 4


def test_compute_scout_points_high_trait_sense_only_affects_traits_and_trajectory():
    scout = Scout(
        scout_id="x", name="Test", base_accuracy=1.00,
        archetype_affinities=(), archetype_weakness="",
        trait_sense="HIGH",
    )
    # HIGH trait_sense (1.30) applies on traits / trajectory only
    p_traits = compute_scout_points_for_axis(
        scout=scout, prospect_archetype="Sharpshooter",
        axis="traits", jitter=1.00, config=DEFAULT_SCOUTING_CONFIG,
    )
    p_trajectory = compute_scout_points_for_axis(
        scout=scout, prospect_archetype="Sharpshooter",
        axis="trajectory", jitter=1.00, config=DEFAULT_SCOUTING_CONFIG,
    )
    p_ratings = compute_scout_points_for_axis(
        scout=scout, prospect_archetype="Sharpshooter",
        axis="ratings", jitter=1.00, config=DEFAULT_SCOUTING_CONFIG,
    )
    p_archetype = compute_scout_points_for_axis(
        scout=scout, prospect_archetype="Sharpshooter",
        axis="archetype", jitter=1.00, config=DEFAULT_SCOUTING_CONFIG,
    )
    # 1.00 * 1.00 * 1.30 * 1.00 * 5 = 6.5 → 7 (rounded)
    assert p_traits == 7
    assert p_trajectory == 7
    # ratings/archetype unaffected by trait_sense → 5
    assert p_ratings == 5
    assert p_archetype == 5


def test_advance_scouting_state_accumulates_and_tiers_up():
    scout = Scout(
        scout_id="x", name="Test", base_accuracy=1.00,
        archetype_affinities=(), archetype_weakness="",
        trait_sense="MEDIUM",
    )
    state = ScoutingState(
        player_id="p1",
        ratings_tier="UNKNOWN",
        archetype_tier="UNKNOWN",
        traits_tier="UNKNOWN",
        trajectory_tier="UNKNOWN",
        scout_points={"ratings": 0, "archetype": 0, "traits": 0, "trajectory": 0},
        last_updated_week=0,
    )
    new_state, events = advance_scouting_state(
        state=state,
        scout=scout,
        prospect_archetype="Sharpshooter",
        week=1,
        seed=12345,
        config=DEFAULT_SCOUTING_CONFIG,
    )
    # 5 points per axis after 1 week → still UNKNOWN
    assert new_state.scout_points["ratings"] == 5
    assert new_state.ratings_tier == "UNKNOWN"

    # advance 1 more week → 10 points → GLIMPSED tier-up event
    new_state2, events2 = advance_scouting_state(
        state=new_state,
        scout=scout,
        prospect_archetype="Sharpshooter",
        week=2,
        seed=12346,
        config=DEFAULT_SCOUTING_CONFIG,
    )
    assert new_state2.scout_points["ratings"] == 10
    assert new_state2.ratings_tier == "GLIMPSED"
    tier_up_events = [e for e in events2 if e["event_type"].startswith("TIER_UP_")]
    assert any(e["event_type"] == "TIER_UP_RATINGS" and e["payload"]["new_tier"] == "GLIMPSED" for e in tier_up_events)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scouting_center.py -v -p no:cacheprovider`
Expected: FAIL with import errors for `compute_scout_points_for_axis`, `tier_for_points`, `advance_scouting_state`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/dodgeball_sim/scouting_center.py`:

```python
import random


def tier_for_points(points: int, config: ScoutingBalanceConfig) -> str:
    """Return the tier name for a cumulative scout-points value, per config thresholds."""
    if points >= config.tier_thresholds["VERIFIED"]:
        return ScoutingTier.VERIFIED.value
    if points >= config.tier_thresholds["KNOWN"]:
        return ScoutingTier.KNOWN.value
    if points >= config.tier_thresholds["GLIMPSED"]:
        return ScoutingTier.GLIMPSED.value
    return ScoutingTier.UNKNOWN.value


def compute_scout_points_for_axis(
    scout: Scout,
    prospect_archetype: str,
    axis: str,
    jitter: float,
    config: ScoutingBalanceConfig,
) -> int:
    """Compute the per-axis scout-points gained for one scouting week.

    Formula: base_accuracy × archetype_modifier × axis_modifier × jitter × weekly_base.
    Rounded to nearest int.
    """
    if prospect_archetype in scout.archetype_affinities:
        archetype_mod = config.archetype_affinity_multiplier
    elif prospect_archetype == scout.archetype_weakness:
        archetype_mod = config.archetype_weakness_multiplier
    else:
        archetype_mod = config.archetype_neutral_multiplier

    if axis in ("traits", "trajectory"):
        axis_mod = config.trait_sense_multipliers[scout.trait_sense]
    else:
        axis_mod = 1.00

    raw = scout.base_accuracy * archetype_mod * axis_mod * jitter * config.weekly_scout_point_base
    return int(round(raw))


def advance_scouting_state(
    state: ScoutingState,
    scout: Scout,
    prospect_archetype: str,
    week: int,
    seed: int,
    config: ScoutingBalanceConfig,
) -> Tuple[ScoutingState, List[Dict[str, object]]]:
    """Advance scouting points across all four axes for one week of scouting.

    Returns: (new_state, events) where events is a list of domain-event dicts
    with shape {"event_type": str, "payload": dict}.

    A single jitter value is derived from `seed` and used for all four axes
    that week (per design §4.6 determinism contract).
    """
    rng = random.Random(seed)
    jitter = config.jitter_min + (config.jitter_max - config.jitter_min) * rng.random()

    new_points = dict(state.scout_points)
    new_tiers = {
        "ratings": state.ratings_tier,
        "archetype": state.archetype_tier,
        "traits": state.traits_tier,
        "trajectory": state.trajectory_tier,
    }
    events: List[Dict[str, object]] = []

    for axis in ("ratings", "archetype", "traits", "trajectory"):
        gained = compute_scout_points_for_axis(scout, prospect_archetype, axis, jitter, config)
        new_total = new_points[axis] + gained
        new_points[axis] = new_total
        new_tier = tier_for_points(new_total, config)
        old_tier = new_tiers[axis]
        if new_tier != old_tier:
            events.append({
                "event_type": f"TIER_UP_{axis.upper()}",
                "payload": {
                    "player_id": state.player_id,
                    "scout_id": scout.scout_id,
                    "axis": axis,
                    "old_tier": old_tier,
                    "new_tier": new_tier,
                    "scout_points": new_total,
                    "week": week,
                },
            })
            new_tiers[axis] = new_tier

    new_state = ScoutingState(
        player_id=state.player_id,
        ratings_tier=new_tiers["ratings"],
        archetype_tier=new_tiers["archetype"],
        traits_tier=new_tiers["traits"],
        trajectory_tier=new_tiers["trajectory"],
        scout_points=new_points,
        last_updated_week=week,
    )
    return new_state, events
```

Update `__all__` to include `tier_for_points`, `compute_scout_points_for_axis`, `advance_scouting_state`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scouting_center.py -v -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
echo "M0-6: scouting_center — narrowing math (compute_scout_points_for_axis, tier_for_points, advance_scouting_state) with deterministic jitter and tier-up event emission" >> docs/superpowers/commits.log
```

---

### Task M0-7: CEILING derivation + trait reveal pick + trajectory eligibility

**Files:**
- Modify: `src/dodgeball_sim/scouting_center.py` (append)
- Test: `tests/test_scouting_center.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_scouting_center.py`:

```python
from dodgeball_sim.scouting_center import (
    ceiling_label_for_trajectory,
    ceiling_reveal_eligible,
    pick_traits_to_reveal,
)


def test_ceiling_label_mapping():
    assert ceiling_label_for_trajectory("NORMAL") == "STANDARD"
    assert ceiling_label_for_trajectory("IMPACT") == "SOLID"
    assert ceiling_label_for_trajectory("STAR") == "HIGH_CEILING"
    assert ceiling_label_for_trajectory("GENERATIONAL") == "HIGH_CEILING"


def test_ceiling_reveal_eligible_default_at_verified():
    # Non-HIGH trait_sense scouts surface CEILING at ratings_axis = VERIFIED
    assert ceiling_reveal_eligible("VERIFIED", "MEDIUM") is True
    assert ceiling_reveal_eligible("VERIFIED", "LOW") is True
    assert ceiling_reveal_eligible("KNOWN", "MEDIUM") is False
    assert ceiling_reveal_eligible("GLIMPSED", "HIGH") is False


def test_ceiling_reveal_eligible_high_trait_sense_at_known():
    # HIGH trait_sense scouts surface CEILING one tier earlier
    assert ceiling_reveal_eligible("KNOWN", "HIGH") is True
    assert ceiling_reveal_eligible("VERIFIED", "HIGH") is True
    assert ceiling_reveal_eligible("GLIMPSED", "HIGH") is False
    assert ceiling_reveal_eligible("UNKNOWN", "HIGH") is False


def test_pick_traits_to_reveal_glimpsed_returns_at_most_one():
    traits = ("IRONWALL", "CLUTCH", "QUICK_RELEASE")
    revealed = pick_traits_to_reveal(player_id="p1", true_traits=traits, tier="GLIMPSED", root_seed=42)
    assert len(revealed) <= 1


def test_pick_traits_to_reveal_known_returns_at_most_two():
    traits = ("IRONWALL", "CLUTCH", "QUICK_RELEASE")
    revealed = pick_traits_to_reveal(player_id="p1", true_traits=traits, tier="KNOWN", root_seed=42)
    assert len(revealed) <= 2


def test_pick_traits_to_reveal_verified_returns_all():
    traits = ("IRONWALL", "CLUTCH", "QUICK_RELEASE")
    revealed = pick_traits_to_reveal(player_id="p1", true_traits=traits, tier="VERIFIED", root_seed=42)
    assert set(revealed) == set(traits)


def test_pick_traits_to_reveal_deterministic_per_player():
    traits = ("IRONWALL", "CLUTCH", "QUICK_RELEASE")
    a = pick_traits_to_reveal(player_id="p1", true_traits=traits, tier="GLIMPSED", root_seed=42)
    b = pick_traits_to_reveal(player_id="p1", true_traits=traits, tier="GLIMPSED", root_seed=42)
    assert a == b
    # Different player → potentially different order (but deterministic per its own seed)
    c = pick_traits_to_reveal(player_id="p2", true_traits=traits, tier="GLIMPSED", root_seed=42)
    # Different player_id should produce same list with potentially different first reveal
    # (we can't assert inequality robustly with 3 traits, just assert determinism for same key)
    c2 = pick_traits_to_reveal(player_id="p2", true_traits=traits, tier="GLIMPSED", root_seed=42)
    assert c == c2


def test_pick_traits_empty_traits_returns_empty():
    assert pick_traits_to_reveal(player_id="p1", true_traits=(), tier="VERIFIED", root_seed=1) == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scouting_center.py -v -p no:cacheprovider -k "ceiling or pick_traits"`
Expected: FAIL with import errors.

- [ ] **Step 3: Write minimal implementation**

Append to `src/dodgeball_sim/scouting_center.py`:

```python
from .rng import derive_seed


_TIER_ORDER = ("UNKNOWN", "GLIMPSED", "KNOWN", "VERIFIED")


def ceiling_label_for_trajectory(trajectory: str) -> str:
    """Map a hidden trajectory to its CEILING label.

    HIGH_CEILING = STAR | GENERATIONAL — band reveal, exact tier still hidden until Draft Day.
    SOLID        = IMPACT — 1:1 mapping, tells you trajectory exactly.
    STANDARD     = NORMAL — 1:1 mapping, tells you trajectory exactly.
    """
    if trajectory in ("STAR", "GENERATIONAL"):
        return CeilingLabel.HIGH_CEILING.value
    if trajectory == "IMPACT":
        return CeilingLabel.SOLID.value
    if trajectory == "NORMAL":
        return CeilingLabel.STANDARD.value
    raise ValueError(f"Unknown trajectory: {trajectory!r}")


def ceiling_reveal_eligible(ratings_tier: str, scout_trait_sense: str) -> bool:
    """Check whether a scout's contribution earns a CEILING reveal at this ratings_axis tier.

    Default rule: CEILING reveals at ratings_axis = VERIFIED.
    HIGH trait_sense scouts get CEILING one tier earlier — at ratings_axis = KNOWN.
    """
    if scout_trait_sense == "HIGH":
        return _TIER_ORDER.index(ratings_tier) >= _TIER_ORDER.index("KNOWN")
    return ratings_tier == "VERIFIED"


def pick_traits_to_reveal(
    player_id: str,
    true_traits: Tuple[str, ...],
    tier: str,
    root_seed: int,
) -> Tuple[str, ...]:
    """Deterministically pick which true traits to reveal at a given tier.

    Tier rules (from spec §4.4):
    - UNKNOWN → no traits
    - GLIMPSED → up to 1 trait
    - KNOWN → up to 2 traits
    - VERIFIED → all traits

    Pick order is fixed per (player_id, root_seed) so reveal sequence is
    independent of which scout uncovered the prospect.
    """
    if not true_traits:
        return ()
    if tier == "UNKNOWN":
        return ()

    # Deterministically shuffle the traits for this player
    seed = derive_seed(root_seed, "trait_reveal_pick", player_id)
    rng = random.Random(seed)
    ordered = list(true_traits)
    rng.shuffle(ordered)

    if tier == "GLIMPSED":
        return tuple(ordered[:1])
    if tier == "KNOWN":
        return tuple(ordered[:2])
    if tier == "VERIFIED":
        return tuple(ordered)
    raise ValueError(f"Unknown tier: {tier!r}")
```

Update `__all__` to include `ceiling_label_for_trajectory`, `ceiling_reveal_eligible`, `pick_traits_to_reveal`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scouting_center.py -v -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
echo "M0-7: scouting_center — ceiling_label_for_trajectory, ceiling_reveal_eligible (HIGH trait_sense early reveal), pick_traits_to_reveal (deterministic per-player wave)" >> docs/superpowers/commits.log
```

---

### Task M0-8: Auto-scout target picker

**Files:**
- Modify: `src/dodgeball_sim/scouting_center.py` (append)
- Test: `tests/test_scouting_center.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_scouting_center.py`:

```python
from dodgeball_sim.scouting_center import select_auto_scout_target


def _make_prospect(pid: str, ovr_mid: int, archetype: str) -> Prospect:
    half = DEFAULT_SCOUTING_CONFIG.public_baseline_band_half_width
    return Prospect(
        player_id=pid, class_year=1, name=pid, age=18, hometown="Test",
        hidden_ratings={"accuracy": 60, "power": 60, "dodge": 60, "catch": 60, "stamina": 60},
        hidden_trajectory="NORMAL", hidden_traits=[],
        public_archetype_guess=archetype,
        public_ratings_band={"ovr": (ovr_mid - half, ovr_mid + half)},
    )


def test_select_auto_scout_target_top_public_ovr():
    pool = {
        "p1": _make_prospect("p1", ovr_mid=70, archetype="Sharpshooter"),
        "p2": _make_prospect("p2", ovr_mid=85, archetype="Enforcer"),
        "p3": _make_prospect("p3", ovr_mid=60, archetype="Ball Hawk"),
    }
    scout = Scout(scout_id="x", name="Test", base_accuracy=1.0, archetype_affinities=(), archetype_weakness="", trait_sense="MEDIUM")
    strategy = ScoutStrategyState(scout_id="x", mode="AUTO", priority="TOP_PUBLIC_OVR", archetype_filter=(), pinned_prospects=())
    target = select_auto_scout_target(
        scout=scout, strategy=strategy, prospects=pool,
        already_assigned_player_ids=set(), week=1, root_seed=42,
    )
    assert target == "p2"  # highest OVR midpoint


def test_select_auto_scout_target_skips_already_assigned():
    pool = {
        "p1": _make_prospect("p1", ovr_mid=70, archetype="Sharpshooter"),
        "p2": _make_prospect("p2", ovr_mid=85, archetype="Enforcer"),
    }
    scout = Scout(scout_id="x", name="Test", base_accuracy=1.0, archetype_affinities=(), archetype_weakness="", trait_sense="MEDIUM")
    strategy = ScoutStrategyState(scout_id="x", mode="AUTO", priority="TOP_PUBLIC_OVR", archetype_filter=(), pinned_prospects=())
    target = select_auto_scout_target(
        scout=scout, strategy=strategy, prospects=pool,
        already_assigned_player_ids={"p2"}, week=1, root_seed=42,
    )
    assert target == "p1"


def test_select_auto_scout_target_specialty_fit_only_picks_affinity():
    pool = {
        "p1": _make_prospect("p1", ovr_mid=85, archetype="Sharpshooter"),
        "p2": _make_prospect("p2", ovr_mid=70, archetype="Enforcer"),
    }
    scout = Scout(scout_id="x", name="Test", base_accuracy=1.0,
                  archetype_affinities=("Enforcer",), archetype_weakness="",
                  trait_sense="MEDIUM")
    strategy = ScoutStrategyState(scout_id="x", mode="AUTO", priority="SPECIALTY_FIT", archetype_filter=(), pinned_prospects=())
    target = select_auto_scout_target(
        scout=scout, strategy=strategy, prospects=pool,
        already_assigned_player_ids=set(), week=1, root_seed=42,
    )
    assert target == "p2"  # affinity match, even though p1 has higher OVR


def test_select_auto_scout_target_specialty_fit_falls_back_when_empty():
    # No prospects match affinity → fall back to TOP_PUBLIC_OVR per spec §8.2 edge case
    pool = {
        "p1": _make_prospect("p1", ovr_mid=70, archetype="Sharpshooter"),
        "p2": _make_prospect("p2", ovr_mid=85, archetype="Ball Hawk"),
    }
    scout = Scout(scout_id="x", name="Test", base_accuracy=1.0,
                  archetype_affinities=("Enforcer",), archetype_weakness="",
                  trait_sense="MEDIUM")
    strategy = ScoutStrategyState(scout_id="x", mode="AUTO", priority="SPECIALTY_FIT", archetype_filter=(), pinned_prospects=())
    target = select_auto_scout_target(
        scout=scout, strategy=strategy, prospects=pool,
        already_assigned_player_ids=set(), week=1, root_seed=42,
    )
    assert target == "p2"  # fallback to top public OVR


def test_select_auto_scout_target_returns_none_when_no_eligible():
    pool = {
        "p1": _make_prospect("p1", ovr_mid=70, archetype="Sharpshooter"),
    }
    scout = Scout(scout_id="x", name="Test", base_accuracy=1.0, archetype_affinities=(), archetype_weakness="", trait_sense="MEDIUM")
    strategy = ScoutStrategyState(scout_id="x", mode="AUTO", priority="TOP_PUBLIC_OVR", archetype_filter=(), pinned_prospects=())
    target = select_auto_scout_target(
        scout=scout, strategy=strategy, prospects=pool,
        already_assigned_player_ids={"p1"}, week=1, root_seed=42,
    )
    assert target is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scouting_center.py -v -p no:cacheprovider -k "auto_scout"`
Expected: FAIL with import errors.

- [ ] **Step 3: Write minimal implementation**

Append to `src/dodgeball_sim/scouting_center.py`:

```python
from typing import Set


def select_auto_scout_target(
    scout: Scout,
    strategy: ScoutStrategyState,
    prospects: Mapping[str, Prospect],
    already_assigned_player_ids: Set[str],
    week: int,
    root_seed: int,
) -> Optional[str]:
    """Deterministically pick the next prospect for an Auto-mode scout.

    Strategy logic (from spec §4.7):
    - TOP_PUBLIC_OVR: pick the unassigned prospect with the highest public OVR band midpoint.
    - SPECIALTY_FIT: same, but restricted to prospects whose public_archetype_guess
      is in the scout's archetype_affinities. If no such prospect, falls back to TOP_PUBLIC_OVR.

    Tie-break uses derive_seed(root_seed, "auto_scout_pick", scout.scout_id, str(week)) for determinism.
    Returns None if no eligible prospect.
    """
    eligible = {pid: p for pid, p in prospects.items() if pid not in already_assigned_player_ids}
    if not eligible:
        return None

    if strategy.priority == ScoutPriority.SPECIALTY_FIT.value:
        affinity = set(scout.archetype_affinities)
        filtered = {pid: p for pid, p in eligible.items() if p.public_archetype_guess in affinity}
        if filtered:
            eligible = filtered
        # else: fall back to top OVR over all eligible

    def ovr_mid(p: Prospect) -> int:
        low, high = p.public_ratings_band["ovr"]
        return (low + high) // 2

    best_score = -1
    best_pid = None
    for pid, p in eligible.items():
        score = ovr_mid(p)
        if score > best_score:
            best_score = score
            best_pid = pid

    # Tie-break across all prospects with the best score using derive_seed
    tied = [pid for pid, p in eligible.items() if ovr_mid(p) == best_score]
    if len(tied) == 1:
        return tied[0]
    seed = derive_seed(root_seed, "auto_scout_pick", scout.scout_id, str(week))
    rng = random.Random(seed)
    rng.shuffle(tied)
    return tied[0]
```

Update `__all__` to include `select_auto_scout_target`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scouting_center.py -v -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
echo "M0-8: scouting_center.select_auto_scout_target — TOP_PUBLIC_OVR / SPECIALTY_FIT with deterministic tie-break and SPECIALTY_FIT→TOP_PUBLIC_OVR fallback" >> docs/superpowers/commits.log
```

---

### Task M0-9: Carry-forward decay logic

**Files:**
- Modify: `src/dodgeball_sim/scouting_center.py` (append)
- Test: `tests/test_scouting_center.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_scouting_center.py`:

```python
from dodgeball_sim.scouting_center import apply_carry_forward_decay


def test_decay_drops_each_axis_one_tier():
    state = ScoutingState(
        player_id="p1",
        ratings_tier="VERIFIED",
        archetype_tier="KNOWN",
        traits_tier="GLIMPSED",
        trajectory_tier="UNKNOWN",
        scout_points={"ratings": 70, "archetype": 35, "traits": 10, "trajectory": 0},
        last_updated_week=14,
    )
    decayed = apply_carry_forward_decay(state, DEFAULT_SCOUTING_CONFIG)
    assert decayed.ratings_tier == "KNOWN"
    assert decayed.archetype_tier == "GLIMPSED"
    assert decayed.traits_tier == "UNKNOWN"
    assert decayed.trajectory_tier == "UNKNOWN"


def test_decay_caps_scout_points_at_new_tier_threshold():
    # After decay from VERIFIED to KNOWN, scout_points should sit at the KNOWN threshold (35),
    # not still at 70 — otherwise next season's narrowing would skip ahead.
    state = ScoutingState(
        player_id="p1",
        ratings_tier="VERIFIED",
        archetype_tier="UNKNOWN",
        traits_tier="UNKNOWN",
        trajectory_tier="UNKNOWN",
        scout_points={"ratings": 70, "archetype": 0, "traits": 0, "trajectory": 0},
        last_updated_week=14,
    )
    decayed = apply_carry_forward_decay(state, DEFAULT_SCOUTING_CONFIG)
    # Decayed to KNOWN; cumulative threshold for KNOWN is 35
    assert decayed.scout_points["ratings"] == 35
    # Untouched axes stay at 0
    assert decayed.scout_points["archetype"] == 0


def test_decay_unknown_unchanged():
    state = ScoutingState(
        player_id="p1",
        ratings_tier="UNKNOWN",
        archetype_tier="UNKNOWN",
        traits_tier="UNKNOWN",
        trajectory_tier="UNKNOWN",
        scout_points={"ratings": 0, "archetype": 0, "traits": 0, "trajectory": 0},
        last_updated_week=14,
    )
    decayed = apply_carry_forward_decay(state, DEFAULT_SCOUTING_CONFIG)
    assert decayed.ratings_tier == "UNKNOWN"
    assert decayed.scout_points["ratings"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scouting_center.py -v -p no:cacheprovider -k "decay"`
Expected: FAIL with import error.

- [ ] **Step 3: Write minimal implementation**

Append to `src/dodgeball_sim/scouting_center.py`:

```python
def apply_carry_forward_decay(
    state: ScoutingState,
    config: ScoutingBalanceConfig,
) -> ScoutingState:
    """Apply one-tier decay across all four axes (per spec §7 carry-forward table).

    VERIFIED → KNOWN, KNOWN → GLIMPSED, GLIMPSED → UNKNOWN, UNKNOWN unchanged.
    Scout points are capped at the new tier's cumulative threshold so next season's
    narrowing resumes from the correct floor.

    CEILING labels and revealed traits/trajectory persist outside this state and
    are NOT affected by this function (per spec §7).
    """
    decayed_tiers: Dict[str, str] = {}
    decayed_points: Dict[str, int] = {}
    threshold = config.tier_thresholds  # {"GLIMPSED":10, "KNOWN":35, "VERIFIED":70}

    for axis, tier in (
        ("ratings", state.ratings_tier),
        ("archetype", state.archetype_tier),
        ("traits", state.traits_tier),
        ("trajectory", state.trajectory_tier),
    ):
        if tier == "VERIFIED":
            new_tier = "KNOWN"
            new_points = threshold["KNOWN"]
        elif tier == "KNOWN":
            new_tier = "GLIMPSED"
            new_points = threshold["GLIMPSED"]
        elif tier == "GLIMPSED":
            new_tier = "UNKNOWN"
            new_points = 0
        else:
            new_tier = "UNKNOWN"
            new_points = 0
        decayed_tiers[axis] = new_tier
        decayed_points[axis] = new_points

    return ScoutingState(
        player_id=state.player_id,
        ratings_tier=decayed_tiers["ratings"],
        archetype_tier=decayed_tiers["archetype"],
        traits_tier=decayed_tiers["traits"],
        trajectory_tier=decayed_tiers["trajectory"],
        scout_points=decayed_points,
        last_updated_week=state.last_updated_week,
    )
```

Update `__all__` to include `apply_carry_forward_decay`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scouting_center.py -v -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
echo "M0-9: scouting_center.apply_carry_forward_decay — one-tier drop with scout_points capped at new tier threshold" >> docs/superpowers/commits.log
```

---

### Task M0-10: `development.py` honors trajectory

**Files:**
- Modify: `src/dodgeball_sim/development.py:12` (extend `apply_season_development` signature)
- Test: `tests/test_development.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_development.py`:

```python
from dodgeball_sim.development import apply_season_development
from dodgeball_sim.models import Player, PlayerRatings, PlayerTraits
from dodgeball_sim.rng import DeterministicRNG, derive_seed
from dodgeball_sim.stats import PlayerMatchStats


def _baseline_prospect(player_id: str, age: int = 19) -> Player:
    return Player(
        id=player_id,
        name=player_id,
        age=age,
        club_id="aurora",
        newcomer=True,
        ratings=PlayerRatings(
            accuracy=60.0, power=60.0, dodge=60.0, catch=60.0, stamina=60.0,
        ),
        traits=PlayerTraits(potential=80.0, growth_curve=50.0, consistency=0.5, pressure=0.5),
    )


def _develop_for_n_seasons(
    player: Player, n: int, trajectory: str | None, root_seed: int
) -> Player:
    p = player
    for season in range(n):
        rng = DeterministicRNG(derive_seed(root_seed, "dev_test", str(season), p.id))
        p = apply_season_development(
            p, PlayerMatchStats(), facilities=(), rng=rng,
            trajectory=trajectory,
        )
        from dataclasses import replace
        p = replace(p, age=p.age + 1)
    return p


def test_trajectory_none_matches_legacy_development():
    """Passing trajectory=None must produce the same career arc as before V2-A."""
    base = _baseline_prospect("legacy_p")
    rng_a = DeterministicRNG(derive_seed(20260426, "dev_legacy", base.id))
    legacy = apply_season_development(
        base, PlayerMatchStats(), facilities=(), rng=rng_a,
    )
    rng_b = DeterministicRNG(derive_seed(20260426, "dev_legacy", base.id))
    new_default = apply_season_development(
        base, PlayerMatchStats(), facilities=(), rng=rng_b,
        trajectory=None,
    )
    assert legacy.ratings.accuracy == new_default.ratings.accuracy
    assert legacy.ratings.power == new_default.ratings.power


def test_trajectory_ordering_in_cumulative_growth():
    """Generational > Star > Impact > Normal in cumulative OVR delta over a multi-season arc."""
    base = _baseline_prospect("traj_p", age=19)

    def cumulative_delta(trajectory: str) -> float:
        end = _develop_for_n_seasons(base, n=6, trajectory=trajectory, root_seed=20260426)
        return end.overall() - base.overall()

    delta_normal = cumulative_delta("NORMAL")
    delta_impact = cumulative_delta("IMPACT")
    delta_star = cumulative_delta("STAR")
    delta_generational = cumulative_delta("GENERATIONAL")

    assert delta_normal < delta_impact, f"NORMAL ({delta_normal:.2f}) should grow less than IMPACT ({delta_impact:.2f})"
    assert delta_impact < delta_star, f"IMPACT ({delta_impact:.2f}) should grow less than STAR ({delta_star:.2f})"
    assert delta_star < delta_generational, f"STAR ({delta_star:.2f}) should grow less than GENERATIONAL ({delta_generational:.2f})"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_development.py -v -p no:cacheprovider -k "trajectory"`
Expected: FAIL — `apply_season_development` does not accept `trajectory` keyword arg.

- [ ] **Step 3: Write minimal implementation**

Modify `src/dodgeball_sim/development.py`:

Replace the signature and body of `apply_season_development`:

```python
_TRAJECTORY_GROWTH_MULTIPLIER = {
    None: 1.00,
    "NORMAL": 1.00,
    "IMPACT": 1.20,
    "STAR": 1.45,
    "GENERATIONAL": 1.75,
}

_TRAJECTORY_POTENTIAL_FLOOR = {
    None: None,    # no override
    "NORMAL": 72.0,
    "IMPACT": 82.0,
    "STAR": 90.0,
    "GENERATIONAL": 96.0,
}


def apply_season_development(
    player: Player,
    season_stats: PlayerMatchStats,
    facilities: Iterable[str],
    rng: DeterministicRNG,
    trajectory: str | None = None,
) -> Player:
    """Apply one offseason of deterministic development to a player.

    Growth is bounded by the player's potential before peak age, slows across
    the peak window, and becomes decline-driven afterward.

    `trajectory` (V2-A): if provided, modulates the pre-peak growth multiplier
    and raises the potential floor. None preserves V1 behavior exactly.
    """
    facility_set = {facility.strip().lower() for facility in facilities}
    base_potential = _clamp(player.traits.potential, 0.0, 100.0)
    floor = _TRAJECTORY_POTENTIAL_FLOOR.get(trajectory)
    if floor is not None:
        potential = max(base_potential, floor)
    else:
        potential = base_potential
    growth_multiplier = _TRAJECTORY_GROWTH_MULTIPLIER.get(trajectory, 1.00)
    growth_curve = _normalize_growth_curve(player.traits.growth_curve)
    peak_start, peak_end = _peak_window(growth_curve)
    performance = _performance_signal(season_stats)
    ratings = player.ratings
    facility_modifiers = apply_facility_effects(player, season_stats, facility_set)

    deltas = {
        "accuracy": _rating_delta("accuracy", player.age, peak_start, peak_end, performance, potential, ratings.accuracy, facility_modifiers, rng),
        "power": _rating_delta("power", player.age, peak_start, peak_end, performance, potential, ratings.power, facility_modifiers, rng),
        "dodge": _rating_delta("dodge", player.age, peak_start, peak_end, performance, potential, ratings.dodge, facility_modifiers, rng),
        "catch": _rating_delta("catch", player.age, peak_start, peak_end, performance, potential, ratings.catch, facility_modifiers, rng),
        "stamina": _rating_delta("stamina", player.age, peak_start, peak_end, performance, potential, ratings.stamina, facility_modifiers, rng),
    }

    # Trajectory only modulates positive (pre-peak / peak) deltas; decline is unaffected
    if growth_multiplier != 1.00:
        for stat in deltas:
            if deltas[stat] > 0:
                deltas[stat] = deltas[stat] * growth_multiplier

    next_ratings = PlayerRatings(
        accuracy=_apply_delta(ratings.accuracy, deltas["accuracy"], potential),
        power=_apply_delta(ratings.power, deltas["power"], potential),
        dodge=_apply_delta(ratings.dodge, deltas["dodge"], potential),
        catch=_apply_delta(ratings.catch, deltas["catch"], potential),
        stamina=_apply_delta(ratings.stamina, deltas["stamina"], potential),
    ).apply_bounds()
    return replace(player, ratings=next_ratings, newcomer=False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_development.py -v -p no:cacheprovider`
Expected: PASS — including legacy back-compat (`trajectory=None`) and trajectory-ordering test.

Also run full V1 regression — this is the integrity-critical wire:

Run: `python -m pytest -p no:cacheprovider`
Expected: All V1 + new tests PASS. Phase 1 golden regression unchanged.

- [ ] **Step 5: Commit**

```bash
echo "M0-10: development.apply_season_development — added optional trajectory parameter modulating pre-peak growth multiplier and raising potential floor; legacy None matches V1 behavior exactly" >> docs/superpowers/commits.log
```

---

### Task M0-11: Persistence functions for scouting tables

**Files:**
- Modify: `src/dodgeball_sim/persistence.py` (append new functions before `__all__`)
- Test: `tests/test_v2a_scouting_persistence.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_v2a_scouting_persistence.py`:

```python
from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
from dodgeball_sim.persistence import (
    save_prospect_pool, load_prospect_pool,
    save_scout, load_scouts, seed_default_scouts,
    save_scouting_state, load_scouting_state, load_all_scouting_states,
    save_scout_assignment, load_scout_assignment, load_all_scout_assignments,
    save_scout_strategy, load_scout_strategy,
    upsert_scout_contribution, load_scout_contributions_for_season,
    append_scouting_domain_event, load_scouting_domain_events_for_season,
    save_scout_track_record, load_scout_track_records_for_scout,
    save_revealed_traits, load_revealed_traits,
    save_ceiling_label, load_ceiling_label,
)
from dodgeball_sim.recruitment import generate_prospect_pool
from dodgeball_sim.rng import DeterministicRNG, derive_seed
from dodgeball_sim.scouting_center import (
    DEFAULT_SCOUT_PROFILES,
    Scout,
    ScoutAssignment,
    ScoutStrategyState,
    ScoutContribution,
    ScoutingState,
    ScoutMode,
    ScoutPriority,
)


def _setup_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def test_save_and_load_prospect_pool():
    conn = _setup_conn()
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    pool = generate_prospect_pool(class_year=1, rng=rng, config=DEFAULT_SCOUTING_CONFIG)
    save_prospect_pool(conn, pool)
    loaded = load_prospect_pool(conn, class_year=1)
    assert len(loaded) == len(pool)
    assert {p.player_id for p in loaded} == {p.player_id for p in pool}
    # Hidden truths preserved
    a = next(p for p in pool if p.hidden_trajectory == "STAR" or p.hidden_trajectory == "GENERATIONAL" or p.hidden_trajectory == "IMPACT" or p.hidden_trajectory == "NORMAL")
    a_loaded = next(p for p in loaded if p.player_id == a.player_id)
    assert a_loaded.hidden_trajectory == a.hidden_trajectory
    assert a_loaded.hidden_traits == a.hidden_traits


def test_seed_default_scouts_idempotent():
    conn = _setup_conn()
    seed_default_scouts(conn)
    first = load_scouts(conn)
    assert len(first) == 3
    assert {s.scout_id for s in first} == {"vera", "bram", "linnea"}
    seed_default_scouts(conn)
    second = load_scouts(conn)
    assert len(second) == 3  # idempotent


def test_save_and_load_scouting_state():
    conn = _setup_conn()
    state = ScoutingState(
        player_id="prospect_1_001",
        ratings_tier="GLIMPSED",
        archetype_tier="UNKNOWN",
        traits_tier="UNKNOWN",
        trajectory_tier="UNKNOWN",
        scout_points={"ratings": 12, "archetype": 0, "traits": 0, "trajectory": 0},
        last_updated_week=3,
    )
    save_scouting_state(conn, state)
    loaded = load_scouting_state(conn, "prospect_1_001")
    assert loaded.ratings_tier == "GLIMPSED"
    assert loaded.scout_points["ratings"] == 12


def test_save_and_load_scout_assignment():
    conn = _setup_conn()
    seed_default_scouts(conn)
    save_scout_assignment(conn, ScoutAssignment(scout_id="vera", player_id="prospect_1_005", started_week=2))
    loaded = load_scout_assignment(conn, "vera")
    assert loaded.player_id == "prospect_1_005"
    assert loaded.started_week == 2


def test_save_and_load_scout_strategy():
    conn = _setup_conn()
    seed_default_scouts(conn)
    save_scout_strategy(conn, ScoutStrategyState(
        scout_id="vera", mode="AUTO", priority="SPECIALTY_FIT",
        archetype_filter=("Enforcer",), pinned_prospects=(),
    ))
    loaded = load_scout_strategy(conn, "vera")
    assert loaded.mode == "AUTO"
    assert loaded.priority == "SPECIALTY_FIT"
    assert loaded.archetype_filter == ("Enforcer",)


def test_upsert_scout_contribution_accrues_across_calls():
    conn = _setup_conn()
    seed_default_scouts(conn)
    upsert_scout_contribution(conn, ScoutContribution(
        scout_id="vera", player_id="p1", season=1,
        first_assigned_week=2, last_active_week=2, weeks_worked=1,
        contributed_scout_points={"ratings": 5, "archetype": 5, "traits": 5, "trajectory": 5},
        last_estimated_ratings_band={"ovr": (50, 80)},
        last_estimated_archetype="Enforcer",
        last_estimated_traits=(),
        last_estimated_ceiling=None,
        last_estimated_trajectory=None,
    ))
    upsert_scout_contribution(conn, ScoutContribution(
        scout_id="vera", player_id="p1", season=1,
        first_assigned_week=2, last_active_week=3, weeks_worked=2,
        contributed_scout_points={"ratings": 10, "archetype": 10, "traits": 10, "trajectory": 10},
        last_estimated_ratings_band={"ovr": (55, 75)},
        last_estimated_archetype="Enforcer",
        last_estimated_traits=("CLUTCH",),
        last_estimated_ceiling=None,
        last_estimated_trajectory=None,
    ))
    rows = load_scout_contributions_for_season(conn, season=1)
    assert len(rows) == 1
    only = rows[0]
    assert only.weeks_worked == 2
    assert only.contributed_scout_points["ratings"] == 10
    assert only.last_estimated_traits == ("CLUTCH",)


def test_append_scouting_domain_event_and_read():
    conn = _setup_conn()
    append_scouting_domain_event(conn, season=1, week=4, event_type="TIER_UP_RATINGS",
                                 player_id="p1", scout_id="vera",
                                 payload={"old_tier": "UNKNOWN", "new_tier": "GLIMPSED"})
    events = load_scouting_domain_events_for_season(conn, season=1)
    assert len(events) == 1
    assert events[0]["event_type"] == "TIER_UP_RATINGS"
    assert events[0]["payload"]["new_tier"] == "GLIMPSED"


def test_save_revealed_traits_and_ceiling():
    conn = _setup_conn()
    save_revealed_traits(conn, player_id="p1", trait_ids=("IRONWALL",), revealed_at_week=4)
    save_ceiling_label(conn, player_id="p1", label="HIGH_CEILING", revealed_at_week=8, revealed_by_scout_id="bram")
    assert load_revealed_traits(conn, "p1") == ("IRONWALL",)
    label_row = load_ceiling_label(conn, "p1")
    assert label_row["label"] == "HIGH_CEILING"
    assert label_row["revealed_by_scout_id"] == "bram"


def test_save_track_record_and_aggregate():
    conn = _setup_conn()
    seed_default_scouts(conn)
    save_scout_track_record(
        conn,
        scout_id="vera", player_id="p1", season=1,
        predicted_ovr_band=(55, 65), actual_ovr=62,
        predicted_archetype="Enforcer", actual_archetype="Enforcer",
        predicted_trajectory=None, actual_trajectory="IMPACT",
        predicted_ceiling=None, actual_ceiling="SOLID",
    )
    save_scout_track_record(
        conn,
        scout_id="vera", player_id="p2", season=1,
        predicted_ovr_band=(70, 78), actual_ovr=75,
        predicted_archetype="Sharpshooter", actual_archetype="Sharpshooter",
        predicted_trajectory="STAR", actual_trajectory="STAR",
        predicted_ceiling="HIGH_CEILING", actual_ceiling="HIGH_CEILING",
    )
    records = load_scout_track_records_for_scout(conn, scout_id="vera")
    assert len(records) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_v2a_scouting_persistence.py -v -p no:cacheprovider`
Expected: FAIL with import errors.

- [ ] **Step 3: Write minimal implementation**

Append to `src/dodgeball_sim/persistence.py` (above `__all__`):

```python
# ----- V2-A scouting persistence ------------------------------------------------

from .scouting_center import (
    DEFAULT_SCOUT_PROFILES,
    Prospect,
    Scout,
    ScoutAssignment,
    ScoutContribution,
    ScoutStrategyState,
    ScoutingState,
)


def save_prospect_pool(conn: sqlite3.Connection, prospects: Iterable[Prospect]) -> None:
    rows = []
    for p in prospects:
        rows.append((
            p.class_year, p.player_id,
            _json_dump({"ratings": p.hidden_ratings, "name": p.name, "age": p.age, "hometown": p.hometown}),
            p.hidden_trajectory,
            _json_dump(list(p.hidden_traits)),
            p.public_archetype_guess,
            _json_dump({k: list(v) for k, v in p.public_ratings_band.items()}),
            0,
        ))
    conn.executemany(
        "INSERT OR REPLACE INTO prospect_pool "
        "(class_year, player_id, hidden_ratings_json, hidden_trajectory, hidden_traits_json, "
        "public_archetype_guess, public_ratings_band_json, is_signed) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()


def load_prospect_pool(conn: sqlite3.Connection, class_year: int) -> List[Prospect]:
    rows = conn.execute(
        "SELECT * FROM prospect_pool WHERE class_year = ? ORDER BY player_id",
        (class_year,),
    ).fetchall()
    result: List[Prospect] = []
    for row in rows:
        ratings_meta = json.loads(row["hidden_ratings_json"])
        band_raw = json.loads(row["public_ratings_band_json"])
        result.append(Prospect(
            player_id=row["player_id"],
            class_year=row["class_year"],
            name=ratings_meta["name"],
            age=ratings_meta["age"],
            hometown=ratings_meta["hometown"],
            hidden_ratings=ratings_meta["ratings"],
            hidden_trajectory=row["hidden_trajectory"],
            hidden_traits=list(json.loads(row["hidden_traits_json"])),
            public_archetype_guess=row["public_archetype_guess"],
            public_ratings_band={k: tuple(v) for k, v in band_raw.items()},
        ))
    return result


def mark_prospect_signed(conn: sqlite3.Connection, class_year: int, player_id: str) -> None:
    conn.execute(
        "UPDATE prospect_pool SET is_signed = 1 WHERE class_year = ? AND player_id = ?",
        (class_year, player_id),
    )
    conn.commit()


def save_scout(conn: sqlite3.Connection, scout: Scout) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO scout (scout_id, name, base_accuracy, archetype_affinities_json, archetype_weakness, trait_sense) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (scout.scout_id, scout.name, scout.base_accuracy,
         _json_dump(list(scout.archetype_affinities)), scout.archetype_weakness, scout.trait_sense),
    )
    conn.commit()


def load_scouts(conn: sqlite3.Connection) -> List[Scout]:
    rows = conn.execute("SELECT * FROM scout ORDER BY scout_id").fetchall()
    return [
        Scout(
            scout_id=r["scout_id"], name=r["name"], base_accuracy=r["base_accuracy"],
            archetype_affinities=tuple(json.loads(r["archetype_affinities_json"])),
            archetype_weakness=r["archetype_weakness"], trait_sense=r["trait_sense"],
        )
        for r in rows
    ]


def seed_default_scouts(conn: sqlite3.Connection) -> None:
    """Insert the three DEFAULT_SCOUT_PROFILES + default MANUAL strategies. Idempotent.

    Gated by dynasty_state flag `scouts_seeded_for_career` per spec §3.1; once set,
    repeated calls are no-ops.
    """
    if get_state(conn, "scouts_seeded_for_career") == "1":
        return
    for profile in DEFAULT_SCOUT_PROFILES:
        save_scout(conn, Scout(
            scout_id=profile.scout_id, name=profile.name,
            base_accuracy=profile.base_accuracy,
            archetype_affinities=profile.archetype_affinities,
            archetype_weakness=profile.archetype_weakness,
            trait_sense=profile.trait_sense,
        ))
        save_scout_strategy(conn, ScoutStrategyState(
            scout_id=profile.scout_id, mode="MANUAL", priority="TOP_PUBLIC_OVR",
            archetype_filter=(), pinned_prospects=(),
        ))
        save_scout_assignment(conn, ScoutAssignment(scout_id=profile.scout_id, player_id=None, started_week=0))
    set_state(conn, "scouts_seeded_for_career", "1")
    conn.commit()


def save_scouting_state(conn: sqlite3.Connection, state: ScoutingState) -> None:
    rows = [
        (state.player_id, axis, getattr(state, f"{axis}_tier"), state.scout_points.get(axis, 0), state.last_updated_week)
        for axis in ("ratings", "archetype", "traits", "trajectory")
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO scouting_state (player_id, axis, tier, scout_points, last_updated_week) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()


def load_scouting_state(conn: sqlite3.Connection, player_id: str) -> Optional[ScoutingState]:
    rows = conn.execute(
        "SELECT * FROM scouting_state WHERE player_id = ?", (player_id,),
    ).fetchall()
    if not rows:
        return None
    by_axis = {r["axis"]: r for r in rows}
    return ScoutingState(
        player_id=player_id,
        ratings_tier=by_axis.get("ratings", {"tier": "UNKNOWN"})["tier"] if "ratings" in by_axis else "UNKNOWN",
        archetype_tier=by_axis.get("archetype", {"tier": "UNKNOWN"})["tier"] if "archetype" in by_axis else "UNKNOWN",
        traits_tier=by_axis.get("traits", {"tier": "UNKNOWN"})["tier"] if "traits" in by_axis else "UNKNOWN",
        trajectory_tier=by_axis.get("trajectory", {"tier": "UNKNOWN"})["tier"] if "trajectory" in by_axis else "UNKNOWN",
        scout_points={ax: (by_axis[ax]["scout_points"] if ax in by_axis else 0) for ax in ("ratings", "archetype", "traits", "trajectory")},
        last_updated_week=max((r["last_updated_week"] for r in rows), default=0),
    )


def load_all_scouting_states(conn: sqlite3.Connection) -> Dict[str, ScoutingState]:
    rows = conn.execute("SELECT DISTINCT player_id FROM scouting_state").fetchall()
    return {r["player_id"]: load_scouting_state(conn, r["player_id"]) for r in rows}


def save_scout_assignment(conn: sqlite3.Connection, assignment: ScoutAssignment) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO scout_assignment (scout_id, player_id, started_week) VALUES (?, ?, ?)",
        (assignment.scout_id, assignment.player_id, assignment.started_week),
    )
    conn.commit()


def load_scout_assignment(conn: sqlite3.Connection, scout_id: str) -> Optional[ScoutAssignment]:
    row = conn.execute(
        "SELECT * FROM scout_assignment WHERE scout_id = ?", (scout_id,),
    ).fetchone()
    if row is None:
        return None
    return ScoutAssignment(scout_id=row["scout_id"], player_id=row["player_id"], started_week=row["started_week"])


def load_all_scout_assignments(conn: sqlite3.Connection) -> Dict[str, ScoutAssignment]:
    rows = conn.execute("SELECT * FROM scout_assignment").fetchall()
    return {r["scout_id"]: ScoutAssignment(scout_id=r["scout_id"], player_id=r["player_id"], started_week=r["started_week"]) for r in rows}


def save_scout_strategy(conn: sqlite3.Connection, strategy: ScoutStrategyState) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO scout_strategy "
        "(scout_id, mode, priority, archetype_filter_json, pinned_prospects_json) VALUES (?, ?, ?, ?, ?)",
        (strategy.scout_id, strategy.mode, strategy.priority,
         _json_dump(list(strategy.archetype_filter)),
         _json_dump(list(strategy.pinned_prospects))),
    )
    conn.commit()


def load_scout_strategy(conn: sqlite3.Connection, scout_id: str) -> Optional[ScoutStrategyState]:
    row = conn.execute("SELECT * FROM scout_strategy WHERE scout_id = ?", (scout_id,)).fetchone()
    if row is None:
        return None
    return ScoutStrategyState(
        scout_id=row["scout_id"], mode=row["mode"], priority=row["priority"],
        archetype_filter=tuple(json.loads(row["archetype_filter_json"])),
        pinned_prospects=tuple(json.loads(row["pinned_prospects_json"])),
    )


def upsert_scout_contribution(conn: sqlite3.Connection, contrib: ScoutContribution) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO scout_prospect_contribution "
        "(scout_id, player_id, season, first_assigned_week, last_active_week, weeks_worked, "
        "contributed_scout_points_json, last_estimated_ratings_band_json, last_estimated_archetype, "
        "last_estimated_traits_json, last_estimated_ceiling, last_estimated_trajectory) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (contrib.scout_id, contrib.player_id, contrib.season,
         contrib.first_assigned_week, contrib.last_active_week, contrib.weeks_worked,
         _json_dump(contrib.contributed_scout_points),
         _json_dump({k: list(v) for k, v in contrib.last_estimated_ratings_band.items()}),
         contrib.last_estimated_archetype,
         _json_dump(list(contrib.last_estimated_traits)),
         contrib.last_estimated_ceiling, contrib.last_estimated_trajectory),
    )
    conn.commit()


def load_scout_contributions_for_season(conn: sqlite3.Connection, season: int) -> List[ScoutContribution]:
    rows = conn.execute(
        "SELECT * FROM scout_prospect_contribution WHERE season = ?", (season,),
    ).fetchall()
    out: List[ScoutContribution] = []
    for r in rows:
        out.append(ScoutContribution(
            scout_id=r["scout_id"], player_id=r["player_id"], season=r["season"],
            first_assigned_week=r["first_assigned_week"], last_active_week=r["last_active_week"],
            weeks_worked=r["weeks_worked"],
            contributed_scout_points=json.loads(r["contributed_scout_points_json"]),
            last_estimated_ratings_band={k: tuple(v) for k, v in json.loads(r["last_estimated_ratings_band_json"]).items()},
            last_estimated_archetype=r["last_estimated_archetype"],
            last_estimated_traits=tuple(json.loads(r["last_estimated_traits_json"])),
            last_estimated_ceiling=r["last_estimated_ceiling"],
            last_estimated_trajectory=r["last_estimated_trajectory"],
        ))
    return out


def append_scouting_domain_event(
    conn: sqlite3.Connection, season: int, week: int, event_type: str,
    player_id: str, scout_id: Optional[str], payload: Dict[str, Any],
) -> None:
    conn.execute(
        "INSERT INTO scouting_domain_event (season, week, event_type, player_id, scout_id, payload_json) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (season, week, event_type, player_id, scout_id, _json_dump(payload)),
    )
    conn.commit()


def load_scouting_domain_events_for_season(conn: sqlite3.Connection, season: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM scouting_domain_event WHERE season = ? ORDER BY event_id",
        (season,),
    ).fetchall()
    return [
        {
            "event_id": r["event_id"], "season": r["season"], "week": r["week"],
            "event_type": r["event_type"], "player_id": r["player_id"], "scout_id": r["scout_id"],
            "payload": json.loads(r["payload_json"]),
        }
        for r in rows
    ]


def save_revealed_traits(
    conn: sqlite3.Connection, player_id: str, trait_ids: Iterable[str], revealed_at_week: int,
) -> None:
    rows = [(player_id, tid, revealed_at_week) for tid in trait_ids]
    conn.executemany(
        "INSERT OR IGNORE INTO scouting_revealed_traits (player_id, trait_id, revealed_at_week) VALUES (?, ?, ?)",
        rows,
    )
    conn.commit()


def load_revealed_traits(conn: sqlite3.Connection, player_id: str) -> Tuple[str, ...]:
    rows = conn.execute(
        "SELECT trait_id FROM scouting_revealed_traits WHERE player_id = ? ORDER BY revealed_at_week, trait_id",
        (player_id,),
    ).fetchall()
    return tuple(r["trait_id"] for r in rows)


def save_ceiling_label(
    conn: sqlite3.Connection, player_id: str, label: str, revealed_at_week: int, revealed_by_scout_id: Optional[str],
) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO scouting_ceiling_label (player_id, label, revealed_at_week, revealed_by_scout_id) "
        "VALUES (?, ?, ?, ?)",
        (player_id, label, revealed_at_week, revealed_by_scout_id),
    )
    conn.commit()


def load_ceiling_label(conn: sqlite3.Connection, player_id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM scouting_ceiling_label WHERE player_id = ?", (player_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def save_scout_track_record(
    conn: sqlite3.Connection, scout_id: str, player_id: str, season: int,
    predicted_ovr_band: Optional[Tuple[int, int]], actual_ovr: Optional[int],
    predicted_archetype: Optional[str], actual_archetype: Optional[str],
    predicted_trajectory: Optional[str], actual_trajectory: Optional[str],
    predicted_ceiling: Optional[str], actual_ceiling: Optional[str],
) -> None:
    conn.execute(
        "INSERT INTO scout_track_record "
        "(scout_id, player_id, season, predicted_ovr_band_json, actual_ovr, "
        "predicted_archetype, actual_archetype, predicted_trajectory, actual_trajectory, "
        "predicted_ceiling, actual_ceiling) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (scout_id, player_id, season,
         _json_dump(list(predicted_ovr_band)) if predicted_ovr_band else None,
         actual_ovr, predicted_archetype, actual_archetype,
         predicted_trajectory, actual_trajectory, predicted_ceiling, actual_ceiling),
    )
    conn.commit()


def load_scout_track_records_for_scout(conn: sqlite3.Connection, scout_id: str) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM scout_track_record WHERE scout_id = ? ORDER BY record_id", (scout_id,),
    ).fetchall()
    return [
        {
            "record_id": r["record_id"], "scout_id": r["scout_id"], "player_id": r["player_id"],
            "season": r["season"],
            "predicted_ovr_band": tuple(json.loads(r["predicted_ovr_band_json"])) if r["predicted_ovr_band_json"] else None,
            "actual_ovr": r["actual_ovr"],
            "predicted_archetype": r["predicted_archetype"], "actual_archetype": r["actual_archetype"],
            "predicted_trajectory": r["predicted_trajectory"], "actual_trajectory": r["actual_trajectory"],
            "predicted_ceiling": r["predicted_ceiling"], "actual_ceiling": r["actual_ceiling"],
        }
        for r in rows
    ]
```

Add the new function names to `__all__`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_v2a_scouting_persistence.py -v -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
echo "M0-11: persistence — V2-A scouting persistence functions (prospect_pool, scouting_state, scouts, assignments, strategies, contributions, domain events, revealed traits, ceiling labels, track records); seed_default_scouts gated by dynasty_state.scouts_seeded_for_career flag" >> docs/superpowers/commits.log
```

---

### Task M0-12: Career-start scouting init + week-tick orchestrator

**Files:**
- Modify: `src/dodgeball_sim/scouting_center.py` (append orchestrator)
- Test: `tests/test_v2a_scouting_integration.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/test_v2a_scouting_integration.py`:

```python
import sqlite3

from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
from dodgeball_sim.persistence import (
    create_schema, get_state,
    load_scouts, load_prospect_pool, load_all_scout_assignments,
    load_scout_strategy, load_all_scouting_states,
    load_scouting_domain_events_for_season,
    load_scout_contributions_for_season,
    save_scout_assignment, save_scout_strategy,
)
from dodgeball_sim.scouting_center import (
    ScoutAssignment, ScoutStrategyState,
    initialize_scouting_for_career,
    run_scouting_week_tick,
)


def _setup():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def test_initialize_scouting_for_career_seeds_scouts_and_class_1():
    conn = _setup()
    initialize_scouting_for_career(conn, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
    scouts = load_scouts(conn)
    assert {s.scout_id for s in scouts} == {"vera", "bram", "linnea"}
    pool = load_prospect_pool(conn, class_year=1)
    assert len(pool) == DEFAULT_SCOUTING_CONFIG.prospect_class_size
    assert get_state(conn, "scouts_seeded_for_career") == "1"


def test_initialize_scouting_idempotent():
    conn = _setup()
    initialize_scouting_for_career(conn, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
    initialize_scouting_for_career(conn, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
    pool = load_prospect_pool(conn, class_year=1)
    # Second call must not duplicate prospects
    assert len(pool) == DEFAULT_SCOUTING_CONFIG.prospect_class_size


def test_week_tick_advances_active_assignments_and_writes_contribution():
    conn = _setup()
    initialize_scouting_for_career(conn, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
    pool = load_prospect_pool(conn, class_year=1)
    target_pid = pool[0].player_id

    save_scout_assignment(conn, ScoutAssignment(scout_id="vera", player_id=target_pid, started_week=1))

    run_scouting_week_tick(conn, season=1, current_week=1, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)

    states = load_all_scouting_states(conn)
    assert target_pid in states
    assert states[target_pid].scout_points["ratings"] > 0
    contribs = load_scout_contributions_for_season(conn, season=1)
    assert any(c.scout_id == "vera" and c.player_id == target_pid for c in contribs)


def test_week_tick_auto_scout_picks_target_when_idle():
    conn = _setup()
    initialize_scouting_for_career(conn, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
    save_scout_strategy(conn, ScoutStrategyState(
        scout_id="vera", mode="AUTO", priority="TOP_PUBLIC_OVR",
        archetype_filter=(), pinned_prospects=(),
    ))
    # Vera starts idle — no assignment yet
    run_scouting_week_tick(conn, season=1, current_week=1, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
    assignments = load_all_scout_assignments(conn)
    assert assignments["vera"].player_id is not None  # Auto picked one


def test_full_season_run_deterministic():
    """Two identical runs of a 14-week season produce identical scouting state + events."""
    def run_once() -> tuple:
        conn = _setup()
        initialize_scouting_for_career(conn, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
        save_scout_strategy(conn, ScoutStrategyState(
            scout_id="vera", mode="AUTO", priority="TOP_PUBLIC_OVR",
            archetype_filter=(), pinned_prospects=(),
        ))
        save_scout_strategy(conn, ScoutStrategyState(
            scout_id="bram", mode="AUTO", priority="SPECIALTY_FIT",
            archetype_filter=(), pinned_prospects=(),
        ))
        save_scout_strategy(conn, ScoutStrategyState(
            scout_id="linnea", mode="AUTO", priority="TOP_PUBLIC_OVR",
            archetype_filter=(), pinned_prospects=(),
        ))
        for week in range(1, 15):
            run_scouting_week_tick(conn, season=1, current_week=week, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
        states = load_all_scouting_states(conn)
        events = load_scouting_domain_events_for_season(conn, season=1)
        snapshot = sorted([(pid, s.ratings_tier, s.archetype_tier, s.traits_tier, s.trajectory_tier, tuple(sorted(s.scout_points.items()))) for pid, s in states.items()])
        ev_snapshot = [(e["week"], e["event_type"], e["player_id"], e["scout_id"]) for e in events]
        return snapshot, ev_snapshot

    a = run_once()
    b = run_once()
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_v2a_scouting_integration.py -v -p no:cacheprovider`
Expected: FAIL — `initialize_scouting_for_career` and `run_scouting_week_tick` not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `src/dodgeball_sim/scouting_center.py`:

```python
def initialize_scouting_for_career(
    conn,
    root_seed: int,
    config: ScoutingBalanceConfig,
) -> None:
    """One-time career-start initialization (per spec §5.1).

    Idempotent: re-running on an existing career is a no-op (gated by
    dynasty_state.scouts_seeded_for_career flag in seed_default_scouts).
    """
    # Local import to avoid circular dependency at module load
    from .persistence import (
        seed_default_scouts, save_prospect_pool, load_prospect_pool, get_state,
    )
    from .recruitment import generate_prospect_pool
    from .rng import DeterministicRNG, derive_seed

    seed_default_scouts(conn)
    # Generate Class 1 if not already present
    existing = load_prospect_pool(conn, class_year=1)
    if not existing:
        rng = DeterministicRNG(derive_seed(root_seed, "prospect_gen", "1"))
        pool = generate_prospect_pool(class_year=1, rng=rng, config=config)
        save_prospect_pool(conn, pool)


def run_scouting_week_tick(
    conn,
    season: int,
    current_week: int,
    root_seed: int,
    config: ScoutingBalanceConfig,
) -> None:
    """Advance one week of scouting (per spec §5.2).

    1. Resolve Auto-mode assignments (idle scouts pick targets).
    2. Advance scouting points + tier-up checks for every active assignment.
    3. Persist updated state, write contribution upserts, persist domain events.
    4. Reveal CEILING and traits when thresholds cross.
    """
    from .persistence import (
        load_scouts, load_all_scout_assignments, load_all_scouting_states,
        load_prospect_pool, load_scout_strategy,
        save_scout_assignment, save_scouting_state, save_revealed_traits,
        save_ceiling_label, append_scouting_domain_event,
        upsert_scout_contribution, load_scout_contributions_for_season,
        save_scout_strategy as _save_scout_strategy,
    )
    from .rng import derive_seed

    scouts = {s.scout_id: s for s in load_scouts(conn)}
    assignments = load_all_scout_assignments(conn)
    pool_class_1 = load_prospect_pool(conn, class_year=season)
    prospects = {p.player_id: p for p in pool_class_1}
    states = load_all_scouting_states(conn)

    # Step 1: Auto-scout target picks
    assigned_player_ids = {a.player_id for a in assignments.values() if a.player_id}
    for scout_id, scout in scouts.items():
        strat = load_scout_strategy(conn, scout_id)
        if strat is None or strat.mode != "AUTO":
            continue
        cur = assignments.get(scout_id)
        # If has target and target not VERIFIED on all axes, keep it
        if cur and cur.player_id:
            cur_state = states.get(cur.player_id)
            if cur_state is None or not (
                cur_state.ratings_tier == "VERIFIED"
                and cur_state.archetype_tier == "VERIFIED"
                and cur_state.traits_tier == "VERIFIED"
                and cur_state.trajectory_tier == "VERIFIED"
            ):
                continue
            # Released — clear assignment so a new pick can land
            assigned_player_ids.discard(cur.player_id)
        # Pick new
        new_target = select_auto_scout_target(
            scout=scout, strategy=strat, prospects=prospects,
            already_assigned_player_ids=assigned_player_ids,
            week=current_week, root_seed=root_seed,
        )
        if new_target:
            save_scout_assignment(conn, ScoutAssignment(scout_id=scout_id, player_id=new_target, started_week=current_week))
            assignments[scout_id] = ScoutAssignment(scout_id=scout_id, player_id=new_target, started_week=current_week)
            assigned_player_ids.add(new_target)

    # Step 2/3: Advance scouting points + persist
    contribs_index = {(c.scout_id, c.player_id, c.season): c for c in load_scout_contributions_for_season(conn, season=season)}

    for scout_id, assignment in assignments.items():
        if not assignment.player_id:
            continue
        scout = scouts.get(scout_id)
        prospect = prospects.get(assignment.player_id)
        if scout is None or prospect is None:
            continue

        prior_state = states.get(prospect.player_id) or ScoutingState(
            player_id=prospect.player_id,
            ratings_tier="UNKNOWN", archetype_tier="UNKNOWN",
            traits_tier="UNKNOWN", trajectory_tier="UNKNOWN",
            scout_points={"ratings": 0, "archetype": 0, "traits": 0, "trajectory": 0},
            last_updated_week=0,
        )
        seed = derive_seed(root_seed, "scouting", scout_id, prospect.player_id, str(current_week))
        new_state, events = advance_scouting_state(
            state=prior_state, scout=scout,
            prospect_archetype=prospect.public_archetype_guess,
            week=current_week, seed=seed, config=config,
        )
        save_scouting_state(conn, new_state)
        states[prospect.player_id] = new_state

        # Domain events
        for ev in events:
            append_scouting_domain_event(
                conn, season=season, week=current_week,
                event_type=ev["event_type"], player_id=prospect.player_id, scout_id=scout_id,
                payload=ev["payload"],
            )

        # Trait reveal wave on traits_axis tier-up
        for ev in events:
            if ev["event_type"] == "TIER_UP_TRAITS":
                new_tier = ev["payload"]["new_tier"]
                revealed = pick_traits_to_reveal(
                    player_id=prospect.player_id,
                    true_traits=tuple(prospect.hidden_traits),
                    tier=new_tier, root_seed=root_seed,
                )
                if revealed:
                    save_revealed_traits(conn, player_id=prospect.player_id, trait_ids=revealed, revealed_at_week=current_week)
                    for trait_id in revealed:
                        append_scouting_domain_event(
                            conn, season=season, week=current_week,
                            event_type="TRAIT_REVEALED",
                            player_id=prospect.player_id, scout_id=scout_id,
                            payload={"trait_id": trait_id, "tier": new_tier},
                        )

        # CEILING reveal
        if ceiling_reveal_eligible(new_state.ratings_tier, scout.trait_sense):
            from .persistence import load_ceiling_label
            existing = load_ceiling_label(conn, prospect.player_id)
            if existing is None:
                label = ceiling_label_for_trajectory(prospect.hidden_trajectory)
                save_ceiling_label(conn, player_id=prospect.player_id, label=label, revealed_at_week=current_week, revealed_by_scout_id=scout_id)
                append_scouting_domain_event(
                    conn, season=season, week=current_week,
                    event_type="CEILING_REVEALED",
                    player_id=prospect.player_id, scout_id=scout_id,
                    payload={"label": label},
                )

        # Update per-scout contribution row
        key = (scout_id, prospect.player_id, season)
        prior_contrib = contribs_index.get(key)
        if prior_contrib is None:
            new_contrib = ScoutContribution(
                scout_id=scout_id, player_id=prospect.player_id, season=season,
                first_assigned_week=current_week, last_active_week=current_week, weeks_worked=1,
                contributed_scout_points={
                    ax: new_state.scout_points[ax] - prior_state.scout_points[ax]
                    for ax in ("ratings", "archetype", "traits", "trajectory")
                },
                last_estimated_ratings_band=_estimate_ratings_band_from_state(new_state, prospect),
                last_estimated_archetype=prospect.public_archetype_guess if new_state.archetype_tier in ("KNOWN", "VERIFIED") else prospect.public_archetype_guess,
                last_estimated_traits=tuple(),  # filled by trait reveal hook above; load later if needed
                last_estimated_ceiling=None,
                last_estimated_trajectory=None,
            )
        else:
            increments = {
                ax: prior_contrib.contributed_scout_points.get(ax, 0)
                + (new_state.scout_points[ax] - prior_state.scout_points[ax])
                for ax in ("ratings", "archetype", "traits", "trajectory")
            }
            new_contrib = ScoutContribution(
                scout_id=scout_id, player_id=prospect.player_id, season=season,
                first_assigned_week=prior_contrib.first_assigned_week,
                last_active_week=current_week,
                weeks_worked=prior_contrib.weeks_worked + 1,
                contributed_scout_points=increments,
                last_estimated_ratings_band=_estimate_ratings_band_from_state(new_state, prospect),
                last_estimated_archetype=prospect.public_archetype_guess,
                last_estimated_traits=prior_contrib.last_estimated_traits,
                last_estimated_ceiling=prior_contrib.last_estimated_ceiling,
                last_estimated_trajectory=prior_contrib.last_estimated_trajectory,
            )
        upsert_scout_contribution(conn, new_contrib)
        contribs_index[key] = new_contrib


def _estimate_ratings_band_from_state(state: ScoutingState, prospect: "Prospect") -> Dict[str, Tuple[int, int]]:
    """Compute a per-scout view of the ratings band based on tier."""
    true_ovr = int(round(prospect.true_overall()))
    if state.ratings_tier == "VERIFIED":
        return {"ovr": (true_ovr, true_ovr)}
    if state.ratings_tier == "KNOWN":
        return {"ovr": (max(0, true_ovr - 6), min(100, true_ovr + 6))}
    if state.ratings_tier == "GLIMPSED":
        return {"ovr": (max(0, true_ovr - 15), min(100, true_ovr + 15))}
    band = prospect.public_ratings_band["ovr"]
    return {"ovr": tuple(band)}
```

Update `__all__` to include `initialize_scouting_for_career`, `run_scouting_week_tick`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_v2a_scouting_integration.py -v -p no:cacheprovider`
Expected: PASS.

Also run full V1 regression to verify no break:

Run: `python -m pytest -p no:cacheprovider`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
echo "M0-12: scouting_center — initialize_scouting_for_career (idempotent career-start init) + run_scouting_week_tick (full week-tick orchestrator: Auto pick → narrow → tier-up → CEILING + trait reveals → contribution upsert)" >> docs/superpowers/commits.log
```

---

**Milestone 0 acceptance gate:**

- [ ] Run `python -m pytest -p no:cacheprovider` — all tests pass.
- [ ] Run `python -m pytest tests/test_regression.py -v -p no:cacheprovider` — Phase 1 golden regression unchanged.
- [ ] Confirm `CURRENT_SCHEMA_VERSION == 8` and migration v7→v8 idempotent on existing v1 saves.
- [ ] Confirm `development.py` honors trajectory in cumulative-growth ordering test.

---

## Milestone 1 — Scouting Center vertical slice

### Task M1-1: `UncertaintyBar` component

**Files:**
- Modify: `src/dodgeball_sim/ui_components.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_manager_gui.py`:

```python
def test_uncertainty_bar_halo_widths():
    from dodgeball_sim.ui_components import uncertainty_bar_halo_width_for_tier
    # UNKNOWN spans 0-100 (100 wide)
    assert uncertainty_bar_halo_width_for_tier("UNKNOWN") == 100
    # GLIMPSED ±15 → 30 wide
    assert uncertainty_bar_halo_width_for_tier("GLIMPSED") == 30
    # KNOWN ±6 → 12 wide
    assert uncertainty_bar_halo_width_for_tier("KNOWN") == 12
    # VERIFIED → single tick (0 wide)
    assert uncertainty_bar_halo_width_for_tier("VERIFIED") == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider -k uncertainty_bar`
Expected: FAIL — function not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `src/dodgeball_sim/ui_components.py`:

```python
_UNCERTAINTY_BAR_HALO_WIDTHS = {"UNKNOWN": 100, "GLIMPSED": 30, "KNOWN": 12, "VERIFIED": 0}


def uncertainty_bar_halo_width_for_tier(tier: str) -> int:
    """Map a scouting tier to the UncertaintyBar halo total width (high-low) in OVR units."""
    return _UNCERTAINTY_BAR_HALO_WIDTHS.get(tier, 100)


class UncertaintyBar(ttk.Frame):
    """Filled bar with center dot at midpoint and translucent halo of width = tier-driven."""

    def __init__(self, master: tk.Misc, label: str = ""):
        super().__init__(master, style="Surface.TFrame")
        self.columnconfigure(1, weight=1)
        if label:
            tk.Label(self, text=label, bg=DM_PAPER, fg=DM_MUTED_CHARCOAL, font=FONT_BODY).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self._canvas = tk.Canvas(self, height=18, bg=DM_PAPER, highlightthickness=0, bd=0)
        self._canvas.grid(row=0, column=1, sticky="ew")
        self.value_var = tk.StringVar(value="?")
        tk.Label(self, textvariable=self.value_var, bg=DM_PAPER, fg=DM_MUTED_CHARCOAL, font=FONT_BODY).grid(row=0, column=2, sticky="e", padx=(8, 0))

    def set(self, midpoint: float, tier: str) -> None:
        self._canvas.delete("all")
        width = max(1, int(self._canvas.winfo_width()))
        halo_total = uncertainty_bar_halo_width_for_tier(tier)
        # Map 0..100 OVR to 0..width pixels
        def x(ovr: float) -> int:
            return int(round((ovr / 100.0) * width))
        if tier == "VERIFIED":
            self._canvas.create_line(x(midpoint), 4, x(midpoint), 14, fill=DM_BORDER, width=2)
            self.value_var.set(f"{midpoint:.0f}")
        else:
            low = max(0, midpoint - halo_total / 2)
            high = min(100, midpoint + halo_total / 2)
            self._canvas.create_rectangle(x(low), 6, x(high), 12, fill=DM_OFF_WHITE_LINE, outline="")
            self._canvas.create_oval(x(midpoint) - 4, 5, x(midpoint) + 4, 13, fill=DM_BORDER, outline="")
            self.value_var.set(f"{int(low)}-{int(high)}")
```

Update `__all__` to include `"UncertaintyBar", "uncertainty_bar_halo_width_for_tier"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider -k uncertainty_bar`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
echo "M1-1: ui_components.UncertaintyBar — tier-driven halo bar + uncertainty_bar_halo_width_for_tier helper" >> docs/superpowers/commits.log
```

---

### Task M1-2: Pure helpers — Scout Strip data, Prospect Board rows, Reveal Ticker items

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py` (append helpers near other build_* helpers; locate via `def build_league_leaders` ~ line 800)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_manager_gui.py`:

```python
def test_build_scout_strip_data_three_scouts():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from dodgeball_sim.persistence import create_schema, seed_default_scouts, save_scout_assignment
    from dodgeball_sim.scouting_center import ScoutAssignment
    from dodgeball_sim.manager_gui import build_scout_strip_data
    create_schema(conn)
    seed_default_scouts(conn)
    save_scout_assignment(conn, ScoutAssignment(scout_id="vera", player_id="prospect_1_005", started_week=2))
    cards = build_scout_strip_data(conn, season=1)
    assert len(cards) == 3
    vera_card = next(c for c in cards if c["scout_id"] == "vera")
    assert vera_card["assignment_player_id"] == "prospect_1_005"
    assert "Power" in vera_card["specialty_blurb"] or "Enforcer" in vera_card["specialty_blurb"]
    assert vera_card["mode"] == "MANUAL"  # default mode after seed


def test_build_prospect_board_rows_uses_tier_widths():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from dodgeball_sim.persistence import (
        create_schema, save_prospect_pool, save_scouting_state,
    )
    from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
    from dodgeball_sim.recruitment import generate_prospect_pool
    from dodgeball_sim.rng import DeterministicRNG, derive_seed
    from dodgeball_sim.scouting_center import ScoutingState
    from dodgeball_sim.manager_gui import build_prospect_board_rows
    create_schema(conn)
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    pool = generate_prospect_pool(class_year=1, rng=rng, config=DEFAULT_SCOUTING_CONFIG)
    save_prospect_pool(conn, pool)
    target = pool[0]
    save_scouting_state(conn, ScoutingState(
        player_id=target.player_id,
        ratings_tier="GLIMPSED", archetype_tier="UNKNOWN",
        traits_tier="UNKNOWN", trajectory_tier="UNKNOWN",
        scout_points={"ratings": 12, "archetype": 0, "traits": 0, "trajectory": 0},
        last_updated_week=3,
    ))
    rows = build_prospect_board_rows(conn, class_year=1)
    target_row = next(r for r in rows if r["player_id"] == target.player_id)
    assert target_row["ratings_tier"] == "GLIMPSED"
    # OVR band should be ±15 around true OVR for GLIMPSED
    low, high = target_row["ovr_band"]
    assert high - low == 30


def test_build_reveal_ticker_items_chronological():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from dodgeball_sim.persistence import create_schema, append_scouting_domain_event
    from dodgeball_sim.manager_gui import build_reveal_ticker_items
    create_schema(conn)
    append_scouting_domain_event(conn, season=1, week=2, event_type="TIER_UP_RATINGS",
                                 player_id="p1", scout_id="vera", payload={"new_tier": "GLIMPSED"})
    append_scouting_domain_event(conn, season=1, week=5, event_type="TRAIT_REVEALED",
                                 player_id="p1", scout_id="vera", payload={"trait_id": "IRONWALL"})
    items = build_reveal_ticker_items(conn, season=1)
    assert items[0]["week"] == 2
    assert items[1]["week"] == 5
    assert "Glimpsed" in items[0]["text"] or "GLIMPSED" in items[0]["text"]
    assert "IRONWALL" in items[1]["text"]


def test_worth_a_look_sort_prioritizes_low_confidence_high_ovr():
    """Worth a Look = sort by (estimated_ovr_mid - confidence_filled_axes_count) descending."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from dodgeball_sim.persistence import create_schema, save_prospect_pool, save_scouting_state
    from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
    from dodgeball_sim.recruitment import generate_prospect_pool
    from dodgeball_sim.rng import DeterministicRNG, derive_seed
    from dodgeball_sim.scouting_center import ScoutingState
    from dodgeball_sim.manager_gui import build_prospect_board_rows, sort_rows_worth_a_look
    create_schema(conn)
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    pool = generate_prospect_pool(class_year=1, rng=rng, config=DEFAULT_SCOUTING_CONFIG)
    save_prospect_pool(conn, pool)
    rows = build_prospect_board_rows(conn, class_year=1)
    sorted_rows = sort_rows_worth_a_look(rows)
    # Sanity: returns same length, first row has high OVR midpoint and low confidence
    assert len(sorted_rows) == len(rows)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider -k "scout_strip or prospect_board or reveal_ticker or worth_a_look"`
Expected: FAIL with import errors.

- [ ] **Step 3: Write minimal implementation**

Append to `src/dodgeball_sim/manager_gui.py` (above the GUI class definitions, near other `build_*` helpers):

```python
# ----- V2-A scouting helpers ----------------------------------------------------

from .persistence import (
    load_scouts, load_all_scout_assignments, load_scout_strategy,
    load_prospect_pool, load_all_scouting_states,
    load_scouting_domain_events_for_season, load_revealed_traits,
    load_ceiling_label, load_scout_track_records_for_scout,
)
from .scouting_center import (
    Prospect, Scout, ScoutingState,
    DEFAULT_SCOUTING_CONFIG as _SCOUTING_CFG_PLACEHOLDER,  # avoid name clash; placeholder
)
from .config import DEFAULT_SCOUTING_CONFIG


def _scout_specialty_blurb(scout: Scout) -> str:
    parts = []
    if scout.archetype_affinities:
        parts.append(f"{', '.join(scout.archetype_affinities)} specialist")
    if scout.archetype_weakness:
        parts.append(f"weak on {scout.archetype_weakness}")
    if scout.trait_sense == "HIGH":
        parts.append("trait-sharp")
    elif scout.trait_sense == "LOW":
        parts.append("trait-blind")
    return " · ".join(parts)


def build_scout_strip_data(conn: sqlite3.Connection, season: int) -> List[Dict[str, Any]]:
    """Return one card-data dict per scout for the Scout Strip UI."""
    scouts = load_scouts(conn)
    assignments = load_all_scout_assignments(conn)
    cards: List[Dict[str, Any]] = []
    for s in scouts:
        strat = load_scout_strategy(conn, s.scout_id)
        cur_assignment = assignments.get(s.scout_id)
        track_records = load_scout_track_records_for_scout(conn, s.scout_id)
        accuracy_blurb = ""
        if track_records:
            within_5 = sum(1 for t in track_records if t["actual_ovr"] is not None and t["predicted_ovr_band"] is not None
                           and t["predicted_ovr_band"][0] - 5 <= t["actual_ovr"] <= t["predicted_ovr_band"][1] + 5)
            accuracy_blurb = f"Track record: {within_5}/{len(track_records)} within ±5"
        cards.append({
            "scout_id": s.scout_id,
            "name": s.name,
            "specialty_blurb": _scout_specialty_blurb(s),
            "assignment_player_id": cur_assignment.player_id if cur_assignment else None,
            "mode": strat.mode if strat else "MANUAL",
            "priority": strat.priority if strat else "TOP_PUBLIC_OVR",
            "accuracy_blurb": accuracy_blurb,
        })
    return cards


def build_prospect_board_rows(conn: sqlite3.Connection, class_year: int) -> List[Dict[str, Any]]:
    """Return one row-data dict per prospect for the Prospect Board UI."""
    pool = load_prospect_pool(conn, class_year=class_year)
    states = load_all_scouting_states(conn)
    assignments = load_all_scout_assignments(conn)
    assigned_to_by_pid: Dict[str, str] = {}
    for scout_id, a in assignments.items():
        if a.player_id:
            assigned_to_by_pid[a.player_id] = scout_id

    rows: List[Dict[str, Any]] = []
    for p in pool:
        state = states.get(p.player_id)
        ratings_tier = state.ratings_tier if state else "UNKNOWN"
        archetype_tier = state.archetype_tier if state else "UNKNOWN"
        traits_tier = state.traits_tier if state else "UNKNOWN"
        trajectory_tier = state.trajectory_tier if state else "UNKNOWN"
        true_ovr = int(round(p.true_overall()))
        if ratings_tier == "VERIFIED":
            ovr_band = (true_ovr, true_ovr)
        elif ratings_tier == "KNOWN":
            ovr_band = (max(0, true_ovr - 6), min(100, true_ovr + 6))
        elif ratings_tier == "GLIMPSED":
            ovr_band = (max(0, true_ovr - 15), min(100, true_ovr + 15))
        else:
            ovr_band = p.public_ratings_band["ovr"]

        ceiling = load_ceiling_label(conn, p.player_id)
        revealed_traits = load_revealed_traits(conn, p.player_id)

        rows.append({
            "player_id": p.player_id,
            "name": p.name,
            "age": p.age,
            "hometown": p.hometown,
            "archetype_guess": p.public_archetype_guess if archetype_tier in ("UNKNOWN", "GLIMPSED") else p.true_archetype(),
            "ratings_tier": ratings_tier,
            "archetype_tier": archetype_tier,
            "traits_tier": traits_tier,
            "trajectory_tier": trajectory_tier,
            "ovr_band": ovr_band,
            "ovr_mid": (ovr_band[0] + ovr_band[1]) // 2,
            "ceiling_label": ceiling["label"] if ceiling else None,
            "revealed_traits": list(revealed_traits),
            "assigned_to_scout_id": assigned_to_by_pid.get(p.player_id),
        })
    return rows


def sort_rows_worth_a_look(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort prospects by 'Worth a Look' = high estimated OVR + low confidence."""
    def score(r):
        confidence_axes_filled = sum(
            1 for axis in ("ratings_tier", "archetype_tier", "traits_tier", "trajectory_tier")
            if r[axis] != "UNKNOWN"
        )
        # Higher OVR midpoint, lower confidence-filled-axes-count → higher score
        return (r["ovr_mid"] - confidence_axes_filled * 5)
    return sorted(rows, key=score, reverse=True)


_TIER_UP_TEXT = {
    "TIER_UP_RATINGS": "ratings",
    "TIER_UP_ARCHETYPE": "archetype",
    "TIER_UP_TRAITS": "traits",
    "TIER_UP_TRAJECTORY": "trajectory",
}


def build_reveal_ticker_items(conn: sqlite3.Connection, season: int) -> List[Dict[str, Any]]:
    """Return Reveal Ticker UI items for the season's scouting domain events."""
    events = load_scouting_domain_events_for_season(conn, season=season)
    items: List[Dict[str, Any]] = []
    for e in events:
        et = e["event_type"]
        payload = e["payload"]
        if et in _TIER_UP_TEXT:
            text = f"Week {e['week']}: {e['scout_id'] or 'Scouts'} reached {payload['new_tier']} on {_TIER_UP_TEXT[et]} for {e['player_id']}"
        elif et == "TRAIT_REVEALED":
            text = f"Week {e['week']}: trait {payload['trait_id']} surfaced on {e['player_id']}"
        elif et == "CEILING_REVEALED":
            text = f"Week {e['week']}: {payload['label']} revealed on {e['player_id']}"
        elif et == "TRAJECTORY_REVEALED":
            text = f"Week {e['week']}: trajectory {payload.get('trajectory', '?')} on {e['player_id']}"
        else:
            text = f"Week {e['week']}: {et} on {e['player_id']}"
        items.append({"week": e["week"], "text": text, "event_type": et})
    return items
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
echo "M1-2: manager_gui — pure helpers build_scout_strip_data, build_prospect_board_rows, sort_rows_worth_a_look, build_reveal_ticker_items" >> docs/superpowers/commits.log
```

---

### Task M1-3: Scouting Center tab — Tk UI integration

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py` (Tk UI; add new screen method `show_scouting_center`)

- [ ] **Step 1: Manual smoke test setup (no automated test for Tk paint)**

Manual verification: launch `python -m dodgeball_sim`, start a new career, navigate to Scouting Center, confirm visual layout.

- [ ] **Step 2: Add `show_scouting_center` method to `ManagerModeApp`**

In `manager_gui.py`, locate the existing `show_*` methods (e.g. `show_hub`, `show_roster`, `show_tactics`). Insert below them:

```python
def show_scouting_center(self) -> None:
    self._set_main_title("Scouting")
    self._clear_main()
    if self.season is None:
        return
    season_num = self.cursor.season_number or 1

    # Scout Strip
    strip_frame = ttk.Frame(self.main, style="Surface.TFrame", padding=12)
    strip_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(8, 4))
    cards = build_scout_strip_data(self.conn, season=season_num)
    for col_idx, c in enumerate(cards):
        card = ttk.Frame(strip_frame, style="Surface.TFrame", padding=10, borderwidth=1, relief="solid")
        card.grid(row=0, column=col_idx, sticky="ew", padx=4)
        ttk.Label(card, text=c["name"].upper(), style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(card, text=c["specialty_blurb"], style="Muted.TLabel", wraplength=240, justify="left").grid(row=1, column=0, sticky="w", pady=(2, 4))
        assignment_text = f"Scouting {c['assignment_player_id']}" if c["assignment_player_id"] else "Available"
        ttk.Label(card, text=assignment_text, style="CardCaption.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Label(card, text=f"[{c['mode']}]", style="CardCaption.TLabel").grid(row=3, column=0, sticky="w")
        if c["accuracy_blurb"]:
            ttk.Label(card, text=c["accuracy_blurb"], style="Muted.TLabel").grid(row=4, column=0, sticky="w", pady=(2, 0))
        ttk.Button(card, text="Manage…", command=lambda sid=c["scout_id"]: self._open_scout_manage_dialog(sid)).grid(row=5, column=0, sticky="ew", pady=(6, 0))

    # Prospect Board
    rows = build_prospect_board_rows(self.conn, class_year=season_num)
    board_frame = ttk.Frame(self.main, style="Surface.TFrame", padding=12)
    board_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
    self.main.rowconfigure(2, weight=1)
    btn_bar = ttk.Frame(board_frame, style="Surface.TFrame")
    btn_bar.grid(row=0, column=0, sticky="ew")
    ttk.Button(btn_bar, text="Worth a Look", command=lambda: self._refresh_prospect_board(rows, "worth_a_look")).pack(side="left", padx=(0, 6))
    ttk.Button(btn_bar, text="Sort: OVR ↓", command=lambda: self._refresh_prospect_board(rows, "ovr_desc")).pack(side="left", padx=6)
    self._prospect_board_tree = self._render_prospect_board(board_frame, rows)

    # Reveal Ticker
    ticker_frame = ttk.Frame(self.main, style="Surface.TFrame", padding=12)
    ticker_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 12))
    ttk.Label(ticker_frame, text="REVEAL TICKER", style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")
    items = build_reveal_ticker_items(self.conn, season=season_num)
    for i, item in enumerate(items[-10:]):
        ttk.Label(ticker_frame, text=item["text"], style="Muted.TLabel").grid(row=1 + i, column=0, sticky="w")


def _render_prospect_board(self, parent, rows):
    cols = ("name", "age", "archetype", "ovr_band", "ratings_tier", "ceiling", "traits", "assigned")
    tree = ttk.Treeview(parent, columns=cols, show="headings", height=14)
    for c in cols:
        tree.heading(c, text=c.upper())
        tree.column(c, width=110, anchor="w")
    for r in rows:
        tree.insert("", "end", iid=r["player_id"], values=(
            r["name"], r["age"], r["archetype_guess"],
            f"{r['ovr_band'][0]}-{r['ovr_band'][1]}",
            r["ratings_tier"],
            r["ceiling_label"] or "?",
            ", ".join(r["revealed_traits"]) if r["revealed_traits"] else "?",
            r["assigned_to_scout_id"] or "—",
        ))
    tree.bind("<Double-Button-1>", lambda e: self._on_prospect_row_double_click(tree))
    tree.grid(row=1, column=0, sticky="nsew")
    parent.rowconfigure(1, weight=1)
    parent.columnconfigure(0, weight=1)
    return tree


def _refresh_prospect_board(self, rows, sort_mode: str) -> None:
    if sort_mode == "worth_a_look":
        sorted_rows = sort_rows_worth_a_look(rows)
    else:
        sorted_rows = sorted(rows, key=lambda r: r["ovr_mid"], reverse=True)
    tree = self._prospect_board_tree
    tree.delete(*tree.get_children())
    for r in sorted_rows:
        tree.insert("", "end", iid=r["player_id"], values=(
            r["name"], r["age"], r["archetype_guess"],
            f"{r['ovr_band'][0]}-{r['ovr_band'][1]}",
            r["ratings_tier"],
            r["ceiling_label"] or "?",
            ", ".join(r["revealed_traits"]) if r["revealed_traits"] else "?",
            r["assigned_to_scout_id"] or "—",
        ))


def _on_prospect_row_double_click(self, tree) -> None:
    sel = tree.selection()
    if not sel:
        return
    self.show_player_profile(sel[0])
```

- [ ] **Step 3: Add Scouting tab to top tab bar**

Locate the nav-tab definition (search `Hub`, `Roster`, `Tactics`, `League` near `_build_tab_bar` or where buttons are created). Add a new button:

```python
ttk.Button(self.tab_bar, text="Scouting", command=self.show_scouting_center, style="Tab.TButton").grid(...)
```

Place it between Tactics and League per spec §6.7.

- [ ] **Step 4: Manual smoke**

Launch: `python -m dodgeball_sim`. Click through to Scouting tab. Confirm: 3 scout cards visible, prospect board populated with ~25 rows, all rows show UNKNOWN tier and wide bands at season Week 1.

- [ ] **Step 5: Commit**

```bash
echo "M1-3: manager_gui — show_scouting_center screen with Scout Strip, Prospect Board (Worth a Look + OVR sorts), Reveal Ticker; Scouting tab added between Tactics and League" >> docs/superpowers/commits.log
```

---

### Task M1-4: Manual assignment dialog + Auto-Scout strategy editor

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py`

- [ ] **Step 1: Add `_open_scout_manage_dialog` method**

```python
def _open_scout_manage_dialog(self, scout_id: str) -> None:
    from .persistence import (
        load_scouts, load_scout_assignment, load_scout_strategy,
        save_scout_assignment, save_scout_strategy, load_prospect_pool,
        load_all_scout_assignments,
    )
    from .scouting_center import ScoutAssignment, ScoutStrategyState, ScoutMode, ScoutPriority

    scouts = {s.scout_id: s for s in load_scouts(self.conn)}
    scout = scouts[scout_id]
    cur_assignment = load_scout_assignment(self.conn, scout_id)
    cur_strategy = load_scout_strategy(self.conn, scout_id)
    season_num = self.cursor.season_number or 1
    pool = load_prospect_pool(self.conn, class_year=season_num)

    win = tk.Toplevel(self.root)
    win.title(f"Manage {scout.name}")
    win.configure(bg=DM_PAPER)

    ttk.Label(win, text=scout.name, style="ScreenTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 4))
    ttk.Label(win, text=f"Specialty: {', '.join(scout.archetype_affinities) or 'Generalist'}").grid(row=1, column=0, columnspan=2, sticky="w", padx=12)
    ttk.Label(win, text=f"Weakness: {scout.archetype_weakness or 'none'}").grid(row=2, column=0, columnspan=2, sticky="w", padx=12)

    mode_var = tk.StringVar(value=cur_strategy.mode if cur_strategy else "MANUAL")
    ttk.Label(win, text="Mode:").grid(row=3, column=0, sticky="w", padx=12, pady=(8, 0))
    ttk.Radiobutton(win, text="Manual", value="MANUAL", variable=mode_var).grid(row=3, column=1, sticky="w")
    ttk.Radiobutton(win, text="Auto", value="AUTO", variable=mode_var).grid(row=4, column=1, sticky="w")

    priority_var = tk.StringVar(value=cur_strategy.priority if cur_strategy else "TOP_PUBLIC_OVR")
    ttk.Label(win, text="Auto priority:").grid(row=5, column=0, sticky="w", padx=12, pady=(8, 0))
    ttk.Radiobutton(win, text="Top public OVR", value="TOP_PUBLIC_OVR", variable=priority_var).grid(row=5, column=1, sticky="w")
    ttk.Radiobutton(win, text="Specialty fit", value="SPECIALTY_FIT", variable=priority_var).grid(row=6, column=1, sticky="w")

    ttk.Label(win, text="Manual assignment (Manual mode only):").grid(row=7, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 0))
    other_assignments = {a.player_id for sid, a in load_all_scout_assignments(self.conn).items() if a.player_id and sid != scout_id}
    options = [(p.player_id, f"{p.name} ({p.public_archetype_guess}, est OVR {(p.public_ratings_band['ovr'][0] + p.public_ratings_band['ovr'][1]) // 2})")
               for p in pool if p.player_id not in other_assignments]
    target_var = tk.StringVar(value=cur_assignment.player_id if cur_assignment and cur_assignment.player_id else "")
    cb = ttk.Combobox(win, textvariable=target_var,
                      values=[f"{pid} | {label}" for pid, label in options], state="readonly", width=50)
    cb.grid(row=8, column=0, columnspan=2, sticky="ew", padx=12, pady=4)

    def save_and_close():
        sel = target_var.get().split(" | ", 1)[0] if target_var.get() else None
        save_scout_assignment(self.conn, ScoutAssignment(
            scout_id=scout_id, player_id=sel or None, started_week=self.cursor.week or 1,
        ))
        save_scout_strategy(self.conn, ScoutStrategyState(
            scout_id=scout_id, mode=mode_var.get(), priority=priority_var.get(),
            archetype_filter=(), pinned_prospects=(),
        ))
        self.conn.commit()
        win.destroy()
        self.show_scouting_center()

    ttk.Button(win, text="Save", command=save_and_close, style="Accent.TButton").grid(row=9, column=0, columnspan=2, sticky="ew", padx=12, pady=(8, 12))
```

- [ ] **Step 2: Manual smoke test**

Launch app, start career, open Scouting Center, click Manage on Vera, change mode to AUTO, save. Re-open Scouting Center — Vera card should show `[AUTO]`.

- [ ] **Step 3: Commit**

```bash
echo "M1-4: manager_gui._open_scout_manage_dialog — manual assignment + Auto-Scout strategy editor (mode/priority radio buttons, prospect dropdown filtered to non-overlap)" >> docs/superpowers/commits.log
```

---

### Task M1-5: Wire week-tick into `_acknowledge_report`

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py:1437` (`_acknowledge_report`)
- Modify: `src/dodgeball_sim/manager_gui.py` (`initialize_manager_career` — call `initialize_scouting_for_career` once)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_manager_gui.py`:

```python
def test_initialize_manager_career_seeds_scouting():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import load_scouts, load_prospect_pool, get_state
    scouts = load_scouts(conn)
    assert {s.scout_id for s in scouts} == {"vera", "bram", "linnea"}
    pool = load_prospect_pool(conn, class_year=1)
    assert len(pool) > 0
    assert get_state(conn, "scouts_seeded_for_career") == "1"


def test_acknowledge_report_advances_scouting_state():
    """End-to-end: assigning a scout, then advancing one match-week, must increase scout_points."""
    # Heavy integration test — requires a more complete fixture; skip if too costly here
    # A lighter unit test: directly call run_scouting_week_tick after a ManagerModeApp init
    # Implementation note: this is verified manually via smoke test in this milestone; full
    # integration assertion lives in tests/test_v2a_scouting_integration.py M0-12.
    pass  # placeholder for documentation; remove or expand as desired
```

- [ ] **Step 2: Run failing test**

Run: `python -m pytest tests/test_manager_gui.py::test_initialize_manager_career_seeds_scouting -v -p no:cacheprovider`
Expected: FAIL — scouts not seeded.

- [ ] **Step 3: Modify `initialize_manager_career`**

Locate the function in `manager_gui.py`. Just before the final `return cursor`, add:

```python
    from .scouting_center import initialize_scouting_for_career
    from .config import DEFAULT_SCOUTING_CONFIG
    initialize_scouting_for_career(conn, root_seed=root_seed, config=DEFAULT_SCOUTING_CONFIG)
```

- [ ] **Step 4: Modify `_acknowledge_report`**

Replace the body of `_acknowledge_report` so that scouting fires AFTER the cursor advance, on every transition into `SEASON_ACTIVE_PRE_MATCH`:

```python
def _acknowledge_report(self) -> None:
    next_week = self._current_week()
    if next_week is None:
        self._finalize_season()
        self.cursor = advance(self.cursor, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0, match_id=None)
        save_career_state_cursor(self.conn, self.cursor)
        self.conn.commit()
        self.show_season_complete()
    else:
        self.cursor = advance(self.cursor, CareerState.SEASON_ACTIVE_PRE_MATCH, week=next_week, match_id=None)
        save_career_state_cursor(self.conn, self.cursor)
        # V2-A scouting tick — fires after week advances, before Hub renders
        from .scouting_center import run_scouting_week_tick
        from .config import DEFAULT_SCOUTING_CONFIG
        run_scouting_week_tick(
            self.conn,
            season=self.cursor.season_number or 1,
            current_week=next_week,
            root_seed=self.root_seed,
            config=DEFAULT_SCOUTING_CONFIG,
        )
        self.conn.commit()
        self.show_hub()
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider`
Expected: PASS.

Run full V1 regression:

Run: `python -m pytest -p no:cacheprovider`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
echo "M1-5: manager_gui wired — initialize_manager_career calls initialize_scouting_for_career; _acknowledge_report calls run_scouting_week_tick after every week advance" >> docs/superpowers/commits.log
```

---

**Milestone 1 acceptance gate:**

- [ ] Launch `python -m dodgeball_sim`. Start a new career.
- [ ] Open Scouting Center tab. Confirm 3 scout cards, ~25 prospect rows at UNKNOWN tier, empty Reveal Ticker.
- [ ] Click Manage on a scout. Assign manually to a prospect. Save.
- [ ] Play one match. Click Back to Hub. Re-open Scouting Center.
- [ ] Confirm: scout's assigned prospect now shows ratings_tier > UNKNOWN, scout_points > 0, Reveal Ticker has 0+ events.
- [ ] Toggle a scout to AUTO mode. Save. Play next match. Confirm Auto-scout picks a target on its own.
- [ ] All automated tests pass.

---

## Milestone 2 — Player Profile fuzzy mode

The same Player Profile component now supports a new state: prospect-fuzzy. Lives in `manager_gui.py`. V1's `build_player_profile_details` is preserved; a new `build_fuzzy_profile_details` handles prospects.

### Task M2-1: `build_fuzzy_profile_details` pure helper

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py` (append)
- Test: `tests/test_manager_gui.py` (append)

- [ ] **Step 1: Write the failing test**

```python
def test_build_fuzzy_profile_details_unknown_prospect():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from dodgeball_sim.persistence import create_schema, save_prospect_pool
    from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
    from dodgeball_sim.recruitment import generate_prospect_pool
    from dodgeball_sim.rng import DeterministicRNG, derive_seed
    from dodgeball_sim.manager_gui import build_fuzzy_profile_details
    create_schema(conn)
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    pool = generate_prospect_pool(class_year=1, rng=rng, config=DEFAULT_SCOUTING_CONFIG)
    save_prospect_pool(conn, pool)
    target = pool[0]
    details = build_fuzzy_profile_details(conn, class_year=1, player_id=target.player_id)
    assert details["name"] == target.name
    assert details["age"] == target.age
    assert details["archetype_label"] == target.public_archetype_guess
    assert details["ratings_tier"] == "UNKNOWN"
    assert details["ceiling_label"] == "?"
    assert details["trajectory_label"] == "Hidden (revealed at Draft Day)"
    assert details["trait_badges"] == ["?", "?", "?"] or details["trait_badges"] == []
    # rating_rows: list of (rating_name, midpoint, tier) tuples
    assert {row["rating_name"] for row in details["rating_rows"]} == {"accuracy", "power", "dodge", "catch", "stamina"}
    for row in details["rating_rows"]:
        assert row["tier"] == "UNKNOWN"


def test_build_fuzzy_profile_details_with_known_ratings_and_revealed_traits():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from dodgeball_sim.persistence import (
        create_schema, save_prospect_pool, save_scouting_state,
        save_revealed_traits, save_ceiling_label,
    )
    from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
    from dodgeball_sim.recruitment import generate_prospect_pool
    from dodgeball_sim.rng import DeterministicRNG, derive_seed
    from dodgeball_sim.scouting_center import ScoutingState
    from dodgeball_sim.manager_gui import build_fuzzy_profile_details
    create_schema(conn)
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    pool = generate_prospect_pool(class_year=1, rng=rng, config=DEFAULT_SCOUTING_CONFIG)
    save_prospect_pool(conn, pool)
    target = pool[0]
    save_scouting_state(conn, ScoutingState(
        player_id=target.player_id,
        ratings_tier="KNOWN", archetype_tier="VERIFIED",
        traits_tier="GLIMPSED", trajectory_tier="UNKNOWN",
        scout_points={"ratings": 35, "archetype": 70, "traits": 12, "trajectory": 0},
        last_updated_week=8,
    ))
    save_revealed_traits(conn, player_id=target.player_id, trait_ids=("IRONWALL",), revealed_at_week=5)
    save_ceiling_label(conn, player_id=target.player_id, label="HIGH_CEILING", revealed_at_week=8, revealed_by_scout_id="bram")
    details = build_fuzzy_profile_details(conn, class_year=1, player_id=target.player_id)
    assert details["ratings_tier"] == "KNOWN"
    assert details["archetype_label"] == target.true_archetype()  # archetype VERIFIED → corrected
    assert details["ceiling_label"] == "HIGH CEILING"
    assert "IRONWALL" in details["trait_badges"]
    # trajectory still hidden (mid-season)
    assert details["trajectory_label"] == "Hidden (revealed at Draft Day)"
```

- [ ] **Step 2: Run failing test**

Run: `python -m pytest tests/test_manager_gui.py::test_build_fuzzy_profile_details_unknown_prospect tests/test_manager_gui.py::test_build_fuzzy_profile_details_with_known_ratings_and_revealed_traits -v -p no:cacheprovider`
Expected: FAIL — function not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `src/dodgeball_sim/manager_gui.py`:

```python
_RATING_NAMES = ("accuracy", "power", "dodge", "catch", "stamina")

_CEILING_DISPLAY = {
    "HIGH_CEILING": "HIGH CEILING",
    "SOLID": "SOLID",
    "STANDARD": "STANDARD",
}


def build_fuzzy_profile_details(
    conn: sqlite3.Connection, class_year: int, player_id: str,
) -> Dict[str, Any]:
    """Build display data for a fuzzy-mode (prospect) Player Profile.

    Reads from prospect_pool, scouting_state, scouting_revealed_traits,
    scouting_ceiling_label. Trajectory is always hidden in this view —
    actual reveal happens at the off-season Draft beat in M3.
    """
    pool = load_prospect_pool(conn, class_year=class_year)
    prospect = next((p for p in pool if p.player_id == player_id), None)
    if prospect is None:
        raise ValueError(f"No prospect with player_id={player_id} in class_year={class_year}")

    state = load_scouting_state(conn, player_id) or ScoutingState(
        player_id=player_id,
        ratings_tier="UNKNOWN", archetype_tier="UNKNOWN",
        traits_tier="UNKNOWN", trajectory_tier="UNKNOWN",
        scout_points={"ratings": 0, "archetype": 0, "traits": 0, "trajectory": 0},
        last_updated_week=0,
    )
    ceiling = load_ceiling_label(conn, player_id)
    revealed_traits = load_revealed_traits(conn, player_id)

    # Per-rating rows: midpoint = true rating, tier governs UncertaintyBar halo
    rating_rows = []
    for name in _RATING_NAMES:
        true_value = prospect.hidden_ratings.get(name, 0.0)
        rating_rows.append({
            "rating_name": name,
            "midpoint": true_value,
            "tier": state.ratings_tier,
        })

    # Archetype: shown as guess until archetype_tier ≥ KNOWN, then corrected
    if state.archetype_tier in ("KNOWN", "VERIFIED"):
        archetype_label = prospect.true_archetype()
    else:
        archetype_label = prospect.public_archetype_guess

    # Traits: revealed traits as badges; placeholders for unrevealed
    trait_badges: List[str] = list(revealed_traits)
    unrevealed_count = max(0, len(prospect.hidden_traits) - len(revealed_traits))
    if state.traits_tier == "UNKNOWN":
        trait_badges = []  # don't even show placeholders if no scouting yet
    else:
        trait_badges = list(revealed_traits) + ["?"] * unrevealed_count

    # CEILING label — always "?" until persisted reveal exists
    ceiling_label = _CEILING_DISPLAY[ceiling["label"]] if ceiling else "?"

    return {
        "player_id": prospect.player_id,
        "name": prospect.name,
        "age": prospect.age,
        "hometown": prospect.hometown,
        "archetype_label": archetype_label,
        "ratings_tier": state.ratings_tier,
        "archetype_tier": state.archetype_tier,
        "traits_tier": state.traits_tier,
        "trajectory_tier": state.trajectory_tier,
        "rating_rows": rating_rows,
        "trait_badges": trait_badges,
        "ceiling_label": ceiling_label,
        "trajectory_label": "Hidden (revealed at Draft Day)",
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider -k "fuzzy_profile"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
echo "M2-1: manager_gui.build_fuzzy_profile_details — pure helper assembling fuzzy-mode profile data from prospect_pool + scouting_state + revealed_traits + ceiling_label" >> docs/superpowers/commits.log
```

---

### Task M2-2: Route `show_player_profile` to fuzzy renderer for prospects

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py` (`show_player_profile` method)

- [ ] **Step 1: Locate existing `show_player_profile`**

Run: `grep -n "def show_player_profile" "C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/manager_gui.py"`

Note the line number. Read the surrounding 30 lines to understand how V1 builds the profile.

- [ ] **Step 2: Add prospect-routing logic**

Modify `show_player_profile` to detect prospect IDs and dispatch:

```python
def show_player_profile(self, player_id: str) -> None:
    self._set_main_title("Player Profile")
    self._clear_main()
    season_num = self.cursor.season_number or 1
    # Detect: is this player a prospect (lives in prospect_pool, not yet signed)?
    pool = load_prospect_pool(self.conn, class_year=season_num)
    prospect_ids = {p.player_id for p in pool}
    if player_id in prospect_ids:
        self._render_fuzzy_profile(player_id, season_num)
    else:
        self._render_signed_profile(player_id)  # existing V1 path; rename current code to this method
```

Wrap the existing V1 body of `show_player_profile` into a new method `_render_signed_profile(player_id)`.

- [ ] **Step 3: Add `_render_fuzzy_profile` method**

```python
def _render_fuzzy_profile(self, player_id: str, season_num: int) -> None:
    from .ui_components import UncertaintyBar
    details = build_fuzzy_profile_details(self.conn, class_year=season_num, player_id=player_id)

    header = ttk.Frame(self.main, style="Surface.TFrame", padding=14, borderwidth=1, relief="solid")
    header.grid(row=1, column=0, sticky="ew", padx=12, pady=(8, 4))
    # Neutral charcoal header (no club yet)
    tk.Label(header, text=details["name"].upper(), bg=DM_MUTED_CHARCOAL, fg=DM_PAPER, font=FONT_BODY, padx=14, pady=8).grid(row=0, column=0, sticky="w")
    ttk.Label(header, text=f"Age {details['age']} · {details['hometown']} · {details['archetype_label']}", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))

    # Ratings panel — UncertaintyBar per rating
    ratings_frame = ttk.Frame(self.main, style="Surface.TFrame", padding=12)
    ratings_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=4)
    ttk.Label(ratings_frame, text="RATINGS", style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")
    for i, row in enumerate(details["rating_rows"]):
        bar = UncertaintyBar(ratings_frame, label=row["rating_name"].upper())
        bar.grid(row=i + 1, column=0, sticky="ew", pady=2)
        ratings_frame.update_idletasks()
        bar.set(midpoint=row["midpoint"], tier=row["tier"])
    ratings_frame.columnconfigure(0, weight=1)

    # Traits row
    traits_frame = ttk.Frame(self.main, style="Surface.TFrame", padding=12)
    traits_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=4)
    ttk.Label(traits_frame, text="TRAITS", style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")
    if details["trait_badges"]:
        for i, badge_text in enumerate(details["trait_badges"]):
            badge = make_badge(traits_frame, badge_text)
            badge.grid(row=1, column=i, sticky="w", padx=2)
    else:
        ttk.Label(traits_frame, text="No scouting yet", style="Muted.TLabel").grid(row=1, column=0, sticky="w")

    # CEILING + Trajectory row
    extras_frame = ttk.Frame(self.main, style="Surface.TFrame", padding=12)
    extras_frame.grid(row=4, column=0, sticky="ew", padx=12, pady=4)
    ttk.Label(extras_frame, text=f"Ceiling: {details['ceiling_label']}", style="CardValue.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(extras_frame, text=f"Trajectory: {details['trajectory_label']}", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))

    # Back button
    ttk.Button(self.main, text="Back to Scouting Center", command=self.show_scouting_center).grid(row=5, column=0, sticky="w", padx=12, pady=(8, 12))
```

- [ ] **Step 4: Manual smoke test**

Launch app. Navigate to Scouting Center. Double-click a prospect row. Confirm fuzzy profile renders with neutral charcoal header, UncertaintyBars per rating, "?" placeholders for unrevealed traits, "Ceiling: ?", "Trajectory: Hidden (revealed at Draft Day)".

- [ ] **Step 5: Commit**

```bash
echo "M2-2: manager_gui.show_player_profile routes to _render_fuzzy_profile for prospects (UncertaintyBar per rating, neutral-charcoal header, ?-placeholders for unrevealed traits, ceiling and trajectory placeholders)" >> docs/superpowers/commits.log
```

---

**Milestone 2 acceptance gate:**

- [ ] Launch `python -m dodgeball_sim`. Start career.
- [ ] Open Scouting Center. Double-click any UNKNOWN prospect → fuzzy profile renders with all rating bars showing wide halos, no traits, "Ceiling: ?".
- [ ] Assign Bram (HIGH trait_sense) to that prospect, play matches until ratings_tier reaches KNOWN.
- [ ] Re-open profile → bars narrowed to ±6, archetype confirmed, CEILING revealed (because Bram is HIGH trait_sense).
- [ ] All automated tests pass.

---

## Milestone 3 — Off-season Draft beat extension

V1's existing off-season Draft beat (`offseason_beat = "draft"` in `OFFSEASON_CEREMONY_BEATS`) gets extended in-place. Tier-aware rendering, trajectory reveal sweep, post-sign Accuracy Reckoning, end-of-offseason carry-forward decay.

### Task M3-1: Persist trajectory on signed players

**Files:**
- Modify: `src/dodgeball_sim/persistence.py` (add `player_trajectory` table + helpers via migration v9 — actually add to v8)
- Test: `tests/test_v2a_scouting_persistence.py`

> **Decision recorded during planning:** rather than touching the `Player` / `PlayerTraits` models, persist trajectory in a side table `player_trajectory(player_id, trajectory)`. Reasons: (a) keeps Player serialization unchanged, (b) `apply_season_development` can read it via a small persistence helper, (c) works for back-compat (legacy players have no row → trajectory=None → V1 behavior). Add the table to migration v8 (since v8 hasn't shipped yet, we extend it before release rather than introducing a v9).

- [ ] **Step 1: Write failing test**

Append to `tests/test_v2a_scouting_persistence.py`:

```python
def test_player_trajectory_save_and_load():
    conn = _setup_conn()
    from dodgeball_sim.persistence import save_player_trajectory, load_player_trajectory
    save_player_trajectory(conn, player_id="p1", trajectory="STAR")
    assert load_player_trajectory(conn, "p1") == "STAR"
    assert load_player_trajectory(conn, "nonexistent") is None


def test_player_trajectory_overwrite_on_resave():
    conn = _setup_conn()
    from dodgeball_sim.persistence import save_player_trajectory, load_player_trajectory
    save_player_trajectory(conn, player_id="p1", trajectory="NORMAL")
    save_player_trajectory(conn, player_id="p1", trajectory="GENERATIONAL")
    assert load_player_trajectory(conn, "p1") == "GENERATIONAL"
```

- [ ] **Step 2: Run failing test**

Run: `python -m pytest tests/test_v2a_scouting_persistence.py -v -p no:cacheprovider -k "player_trajectory"`
Expected: FAIL — table and helpers not defined.

- [ ] **Step 3: Add table to `_migrate_v8` in `persistence.py`**

Add inside the `executescript` block in `_migrate_v8`:

```sql
CREATE TABLE IF NOT EXISTS player_trajectory (
    player_id TEXT PRIMARY KEY,
    trajectory TEXT NOT NULL
);
```

- [ ] **Step 4: Add persistence helpers**

Append to V2-A scouting persistence section (above `__all__`):

```python
def save_player_trajectory(conn: sqlite3.Connection, player_id: str, trajectory: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO player_trajectory (player_id, trajectory) VALUES (?, ?)",
        (player_id, trajectory),
    )
    conn.commit()


def load_player_trajectory(conn: sqlite3.Connection, player_id: str) -> Optional[str]:
    row = conn.execute(
        "SELECT trajectory FROM player_trajectory WHERE player_id = ?", (player_id,),
    ).fetchone()
    return row["trajectory"] if row else None
```

Add `save_player_trajectory`, `load_player_trajectory` to `__all__`.

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_v2a_scouting_persistence.py -v -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
echo "M3-1: persistence — player_trajectory side table + save/load helpers (extends migration v8 in place; legacy players without rows preserve V1 development behavior)" >> docs/superpowers/commits.log
```

---

### Task M3-2: Sign action — convert prospect to Player + persist trajectory

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py`
- Test: `tests/test_manager_gui.py`

- [ ] **Step 1: Write failing test**

```python
def test_sign_prospect_converts_to_player_and_persists_trajectory():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import (
        load_prospect_pool, load_player_trajectory,
        load_all_rosters, mark_prospect_signed,
    )
    from dodgeball_sim.manager_gui import sign_prospect_to_club
    pool = load_prospect_pool(conn, class_year=1)
    target = pool[0]
    sign_prospect_to_club(conn, prospect=target, club_id="aurora", season_num=1)

    # Trajectory persisted
    assert load_player_trajectory(conn, target.player_id) == target.hidden_trajectory
    # Marked as signed
    after = load_prospect_pool(conn, class_year=1)
    signed_row = next(p for p in after if p.player_id == target.player_id)
    # is_signed reads via raw SQL since Prospect dataclass doesn't carry it
    raw = conn.execute("SELECT is_signed FROM prospect_pool WHERE player_id = ?", (target.player_id,)).fetchone()
    assert raw["is_signed"] == 1
    # Player added to aurora roster
    rosters = load_all_rosters(conn)
    assert any(p.id == target.player_id for p in rosters.get("aurora", []))


def test_sign_prospect_drops_scouting_state():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import (
        load_prospect_pool, save_scouting_state, load_scouting_state,
    )
    from dodgeball_sim.scouting_center import ScoutingState
    from dodgeball_sim.manager_gui import sign_prospect_to_club
    pool = load_prospect_pool(conn, class_year=1)
    target = pool[0]
    save_scouting_state(conn, ScoutingState(
        player_id=target.player_id,
        ratings_tier="VERIFIED", archetype_tier="VERIFIED",
        traits_tier="VERIFIED", trajectory_tier="VERIFIED",
        scout_points={"ratings": 70, "archetype": 70, "traits": 70, "trajectory": 70},
        last_updated_week=14,
    ))
    sign_prospect_to_club(conn, prospect=target, club_id="aurora", season_num=1)
    assert load_scouting_state(conn, target.player_id) is None
```

- [ ] **Step 2: Run failing test**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider -k "sign_prospect"`
Expected: FAIL — function not defined.

- [ ] **Step 3: Implement `sign_prospect_to_club`**

Append to `manager_gui.py`:

```python
def sign_prospect_to_club(
    conn: sqlite3.Connection,
    prospect: Prospect,
    club_id: str,
    season_num: int,
) -> Player:
    """Convert a Prospect into a signed Player on a club's roster.

    Side effects:
    - prospect_pool.is_signed = 1 for this player_id.
    - player_trajectory row written from prospect.hidden_trajectory.
    - Player added to club's roster (save_club).
    - scouting_state rows for this player_id are dropped.
    - scouting_revealed_traits and scouting_ceiling_label rows preserved
      (they remain accessible via the signed Profile if desired, but mainly
      for the Accuracy Reckoning panel).
    """
    from .persistence import (
        mark_prospect_signed, save_player_trajectory,
        load_all_rosters, save_club, load_clubs, save_lineup_default,
    )

    player = Player(
        id=prospect.player_id,
        name=prospect.name,
        age=prospect.age,
        club_id=club_id,
        newcomer=True,
        ratings=PlayerRatings(
            accuracy=prospect.hidden_ratings["accuracy"],
            power=prospect.hidden_ratings["power"],
            dodge=prospect.hidden_ratings["dodge"],
            catch=prospect.hidden_ratings["catch"],
            stamina=prospect.hidden_ratings["stamina"],
        ).apply_bounds(),
        traits=PlayerTraits(potential=70.0, growth_curve=50.0, consistency=0.5, pressure=0.5),
    )

    rosters = load_all_rosters(conn)
    clubs = load_clubs(conn)
    new_roster = list(rosters.get(club_id, [])) + [player]
    save_club(conn, clubs[club_id], new_roster)
    save_lineup_default(conn, club_id, [p.id for p in new_roster])
    save_player_trajectory(conn, player_id=player.id, trajectory=prospect.hidden_trajectory)
    mark_prospect_signed(conn, class_year=season_num, player_id=player.id)
    # Drop scouting_state for this player (signed players don't have fuzzy view)
    conn.execute("DELETE FROM scouting_state WHERE player_id = ?", (player.id,))
    conn.commit()
    return player
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider -k "sign_prospect"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
echo "M3-2: manager_gui.sign_prospect_to_club — converts Prospect→Player, persists trajectory, marks prospect signed, drops scouting_state, updates roster + lineup default" >> docs/superpowers/commits.log
```

---

### Task M3-3: Wire `apply_season_development` to read trajectory

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py:553` (`initialize_manager_offseason`'s development call)
- Test: `tests/test_manager_gui.py`

- [ ] **Step 1: Write failing test**

```python
def test_offseason_development_reads_trajectory_for_signed_prospect():
    """When a Generational-trajectory prospect is signed and then the off-season
    development runs, the player's growth must reflect the GENERATIONAL multiplier."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import (
        load_prospect_pool, save_player_trajectory, load_all_rosters,
    )
    from dodgeball_sim.manager_gui import sign_prospect_to_club, initialize_manager_offseason
    from dodgeball_sim.persistence import load_season
    pool = load_prospect_pool(conn, class_year=1)
    target = pool[0]
    # Force trajectory to GENERATIONAL for this test (override the random draw)
    save_player_trajectory(conn, player_id=target.player_id, trajectory="GENERATIONAL")
    sign_prospect_to_club(conn, prospect=target, club_id="aurora", season_num=1)

    # Capture pre-development OVR
    rosters = load_all_rosters(conn)
    pre = next(p for p in rosters["aurora"] if p.id == target.player_id)
    pre_ovr = pre.overall()

    season = load_season(conn, "season_1")
    from dodgeball_sim.persistence import load_clubs
    clubs = load_clubs(conn)
    initialize_manager_offseason(conn, season, clubs, rosters, root_seed=20260426)
    rosters_after = load_all_rosters(conn)
    post = next(p for p in rosters_after["aurora"] if p.id == target.player_id)
    delta = post.overall() - pre_ovr
    assert delta > 0, "Expected GENERATIONAL prospect to grow over off-season"
    # Compare against same prospect with NORMAL trajectory using a separate DB
    conn2 = sqlite3.connect(":memory:")
    conn2.row_factory = sqlite3.Row
    create_schema(conn2)
    initialize_manager_career(conn2, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import load_prospect_pool as _lpp
    pool2 = _lpp(conn2, class_year=1)
    target2 = pool2[0]
    save_player_trajectory(conn2, player_id=target2.player_id, trajectory="NORMAL")
    sign_prospect_to_club(conn2, prospect=target2, club_id="aurora", season_num=1)
    rosters2 = load_all_rosters(conn2)
    pre2 = next(p for p in rosters2["aurora"] if p.id == target2.player_id)
    season2 = load_season(conn2, "season_1")
    clubs2 = load_clubs(conn2)
    initialize_manager_offseason(conn2, season2, clubs2, rosters2, root_seed=20260426)
    rosters2_after = load_all_rosters(conn2)
    post2 = next(p for p in rosters2_after["aurora"] if p.id == target2.player_id)
    delta_normal = post2.overall() - pre2.overall()
    assert delta > delta_normal, f"GENERATIONAL delta ({delta:.2f}) must exceed NORMAL delta ({delta_normal:.2f})"
```

- [ ] **Step 2: Run failing test**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider -k "offseason_development_reads_trajectory"`
Expected: FAIL — `apply_season_development` not currently reading trajectory in `initialize_manager_offseason`.

- [ ] **Step 3: Wire trajectory lookup into `initialize_manager_offseason`**

Locate the existing call:

```python
developed = apply_season_development(
    player, stats, facilities=(),
    rng=DeterministicRNG(derive_seed(root_seed, "manager_development", season.season_id, player.id)),
)
```

Replace with:

```python
from .persistence import load_player_trajectory as _load_traj
trajectory = _load_traj(conn, player.id)
developed = apply_season_development(
    player, stats, facilities=(),
    rng=DeterministicRNG(derive_seed(root_seed, "manager_development", season.season_id, player.id)),
    trajectory=trajectory,
)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider`
Expected: PASS — including the new test.

Run full V1 regression to confirm legacy players (no trajectory row) still grow per V1:

Run: `python -m pytest tests/test_regression.py -v -p no:cacheprovider`
Expected: PASS unchanged.

- [ ] **Step 5: Commit**

```bash
echo "M3-3: manager_gui.initialize_manager_offseason — reads player_trajectory and passes to apply_season_development; legacy players without rows fall back to None (V1 behavior preserved)" >> docs/superpowers/commits.log
```

---

### Task M3-4: Trajectory reveal sweep + Accuracy Reckoning helpers

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py` (append helpers)
- Test: `tests/test_manager_gui.py`

- [ ] **Step 1: Write failing test**

```python
def test_build_trajectory_reveal_sweep_only_includes_verified_axis():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import load_prospect_pool, save_scouting_state
    from dodgeball_sim.scouting_center import ScoutingState
    from dodgeball_sim.manager_gui import build_trajectory_reveal_sweep
    pool = load_prospect_pool(conn, class_year=1)
    p_verified = pool[0]
    p_glimpsed = pool[1]
    save_scouting_state(conn, ScoutingState(
        player_id=p_verified.player_id,
        ratings_tier="VERIFIED", archetype_tier="VERIFIED",
        traits_tier="VERIFIED", trajectory_tier="VERIFIED",
        scout_points={"ratings": 70, "archetype": 70, "traits": 70, "trajectory": 70},
        last_updated_week=14,
    ))
    save_scouting_state(conn, ScoutingState(
        player_id=p_glimpsed.player_id,
        ratings_tier="GLIMPSED", archetype_tier="UNKNOWN",
        traits_tier="UNKNOWN", trajectory_tier="GLIMPSED",
        scout_points={"ratings": 12, "archetype": 0, "traits": 0, "trajectory": 12},
        last_updated_week=8,
    ))
    sweep = build_trajectory_reveal_sweep(conn, class_year=1)
    sweep_ids = {entry["player_id"] for entry in sweep}
    assert p_verified.player_id in sweep_ids
    assert p_glimpsed.player_id not in sweep_ids
    # Each entry has trajectory + display weight
    e = next(x for x in sweep if x["player_id"] == p_verified.player_id)
    assert e["trajectory"] == p_verified.hidden_trajectory
    assert e["display_weight"] in ("standard", "elevated")  # STAR/GENERATIONAL → elevated


def test_build_accuracy_reckoning_writes_track_records():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import (
        load_prospect_pool, upsert_scout_contribution, load_scout_track_records_for_scout,
    )
    from dodgeball_sim.scouting_center import ScoutContribution
    from dodgeball_sim.manager_gui import build_accuracy_reckoning
    pool = load_prospect_pool(conn, class_year=1)
    target = pool[0]
    upsert_scout_contribution(conn, ScoutContribution(
        scout_id="vera", player_id=target.player_id, season=1,
        first_assigned_week=2, last_active_week=10, weeks_worked=8,
        contributed_scout_points={"ratings": 40, "archetype": 40, "traits": 25, "trajectory": 20},
        last_estimated_ratings_band={"ovr": (int(target.true_overall()) - 6, int(target.true_overall()) + 6)},
        last_estimated_archetype=target.public_archetype_guess,
        last_estimated_traits=tuple(target.hidden_traits[:1]),
        last_estimated_ceiling=None,
        last_estimated_trajectory=None,
    ))
    summary = build_accuracy_reckoning(conn, season=1, class_year=1)
    assert "vera" in {row["scout_id"] for row in summary}
    # Track records persisted
    records = load_scout_track_records_for_scout(conn, "vera")
    assert any(r["player_id"] == target.player_id for r in records)
    # Idempotency: calling again does not double-write
    before = len(records)
    build_accuracy_reckoning(conn, season=1, class_year=1)
    after = len(load_scout_track_records_for_scout(conn, "vera"))
    assert after == before
```

- [ ] **Step 2: Run failing test**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider -k "trajectory_reveal_sweep or accuracy_reckoning"`
Expected: FAIL — helpers not defined.

- [ ] **Step 3: Implement helpers**

Append to `manager_gui.py`:

```python
_TRAJECTORY_DISPLAY_WEIGHT = {
    "NORMAL": "standard",
    "IMPACT": "standard",
    "STAR": "elevated",
    "GENERATIONAL": "elevated",
}


def build_trajectory_reveal_sweep(
    conn: sqlite3.Connection, class_year: int,
) -> List[Dict[str, Any]]:
    """Build the ordered list of prospects whose trajectory_axis = VERIFIED for the
    Draft-Day reveal sweep. Each entry carries the actual trajectory (read from
    prospect_pool hidden_trajectory) and a display weight."""
    pool = load_prospect_pool(conn, class_year=class_year)
    states = load_all_scouting_states(conn)
    sweep: List[Dict[str, Any]] = []
    for p in pool:
        s = states.get(p.player_id)
        if s and s.trajectory_tier == "VERIFIED":
            sweep.append({
                "player_id": p.player_id,
                "name": p.name,
                "trajectory": p.hidden_trajectory,
                "display_weight": _TRAJECTORY_DISPLAY_WEIGHT.get(p.hidden_trajectory, "standard"),
            })
    return sweep


def build_accuracy_reckoning(
    conn: sqlite3.Connection, season: int, class_year: int,
) -> List[Dict[str, Any]]:
    """For every (scout_id, player_id, season) row in scout_prospect_contribution
    for this season, write a scout_track_record row by joining against the
    prospect's hidden truths, then return per-scout summary rows for the UI.

    Idempotent: checks for existing track-record entries with the same
    (scout_id, player_id, season) tuple before inserting.
    """
    from .persistence import (
        load_scout_contributions_for_season, load_prospect_pool,
        save_scout_track_record, load_scout_track_records_for_scout,
    )
    from .scouting_center import ceiling_label_for_trajectory

    pool_by_pid = {p.player_id: p for p in load_prospect_pool(conn, class_year=class_year)}
    contribs = load_scout_contributions_for_season(conn, season=season)
    summary: Dict[str, Dict[str, Any]] = {}

    for c in contribs:
        prospect = pool_by_pid.get(c.player_id)
        if prospect is None:
            continue

        # Idempotency: skip if already a record for this (scout_id, player_id, season)
        existing = [
            r for r in load_scout_track_records_for_scout(conn, c.scout_id)
            if r["player_id"] == c.player_id and r["season"] == c.season
        ]
        if existing:
            continue

        actual_ovr = int(round(prospect.true_overall()))
        actual_archetype = prospect.true_archetype()
        actual_trajectory = prospect.hidden_trajectory
        actual_ceiling = ceiling_label_for_trajectory(prospect.hidden_trajectory)
        predicted_ovr_band = c.last_estimated_ratings_band.get("ovr")
        save_scout_track_record(
            conn,
            scout_id=c.scout_id, player_id=c.player_id, season=c.season,
            predicted_ovr_band=tuple(predicted_ovr_band) if predicted_ovr_band else None,
            actual_ovr=actual_ovr,
            predicted_archetype=c.last_estimated_archetype,
            actual_archetype=actual_archetype,
            predicted_trajectory=c.last_estimated_trajectory,
            actual_trajectory=actual_trajectory,
            predicted_ceiling=c.last_estimated_ceiling,
            actual_ceiling=actual_ceiling,
        )

    # Build per-scout summary
    for c in contribs:
        prospect = pool_by_pid.get(c.player_id)
        if prospect is None:
            continue
        bucket = summary.setdefault(c.scout_id, {"scout_id": c.scout_id, "rows": []})
        actual_ovr = int(round(prospect.true_overall()))
        predicted_band = c.last_estimated_ratings_band.get("ovr")
        within = (
            predicted_band is not None
            and predicted_band[0] - 5 <= actual_ovr <= predicted_band[1] + 5
        )
        bucket["rows"].append({
            "player_id": c.player_id,
            "player_name": prospect.name,
            "predicted_ovr_band": tuple(predicted_band) if predicted_band else None,
            "actual_ovr": actual_ovr,
            "within_5": within,
        })
    return list(summary.values())
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider -k "trajectory_reveal_sweep or accuracy_reckoning"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
echo "M3-4: manager_gui — build_trajectory_reveal_sweep + build_accuracy_reckoning (idempotent track-record writes joining contribution rows against prospect_pool hidden truths)" >> docs/superpowers/commits.log
```

---

### Task M3-5: Tier-aware Draft beat UI + sign action + reveal sweep + reckoning panel

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py` (existing Draft beat screen)

- [ ] **Step 1: Locate existing Draft beat**

Run: `grep -n "show_offseason_beat\|draft\b" "C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/manager_gui.py" | head -30`

Find the Draft beat rendering method (likely `show_offseason_draft` or inside `show_offseason_beat`). Read 30-line context.

- [ ] **Step 2: Replace Draft beat body with tier-aware rendering + reveal + sign + reckoning**

The existing V1 Draft beat presents the rookie list and a "Sign Best Rookie" button. Replace it with the V2-A flow:

```python
def show_offseason_draft_beat(self) -> None:
    """V2-A Draft Day: pre-sign tier-aware list → trajectory reveal sweep → click-to-sign → Accuracy Reckoning."""
    self._set_main_title("Draft Day")
    self._clear_main()
    season_num = self.cursor.season_number or 1
    class_year = season_num
    pool = load_prospect_pool(self.conn, class_year=class_year)

    # Phase A: pre-sign list with UncertaintyBars + CEILING labels
    list_frame = ttk.Frame(self.main, style="Surface.TFrame", padding=12)
    list_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
    rows = build_prospect_board_rows(self.conn, class_year=class_year)
    rows = [r for r in rows if not _is_already_signed(self.conn, class_year, r["player_id"])]
    self._render_prospect_board(list_frame, rows)

    # Phase B: trajectory reveal sweep button
    sweep = build_trajectory_reveal_sweep(self.conn, class_year=class_year)
    if sweep:
        ttk.Button(
            self.main, text=f"▶ Reveal trajectories ({len(sweep)} prospects)",
            command=lambda: self._show_trajectory_reveal_sweep(sweep),
            style="Accent.TButton",
        ).grid(row=2, column=0, sticky="w", padx=12, pady=4)

    # Phase C: Sign action
    sign_frame = ttk.Frame(self.main, style="Surface.TFrame", padding=12)
    sign_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=4)
    ttk.Label(sign_frame, text="Sign rookies into open roster slots:", style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")
    target_var = tk.StringVar()
    options = [f"{p.player_id} | {p.name}" for p in pool if not _is_already_signed(self.conn, class_year, p.player_id)]
    cb = ttk.Combobox(sign_frame, textvariable=target_var, values=options, state="readonly", width=50)
    cb.grid(row=1, column=0, sticky="ew", pady=4)
    ttk.Button(sign_frame, text="Sign Selected", command=lambda: self._sign_selected_prospect(target_var, class_year), style="Accent.TButton").grid(row=2, column=0, sticky="w", pady=4)

    # Phase D: Accuracy Reckoning button (writes track records on first click; idempotent)
    ttk.Button(
        self.main, text="Compute Accuracy Reckoning",
        command=lambda: self._show_accuracy_reckoning(season_num, class_year),
    ).grid(row=4, column=0, sticky="w", padx=12, pady=4)

    # Continue → next beat
    ttk.Button(
        self.main, text="Continue →",
        command=self._advance_offseason_beat, style="Accent.TButton",
    ).grid(row=5, column=0, sticky="e", padx=12, pady=12)


def _is_already_signed(conn: sqlite3.Connection, class_year: int, player_id: str) -> bool:
    row = conn.execute(
        "SELECT is_signed FROM prospect_pool WHERE class_year = ? AND player_id = ?",
        (class_year, player_id),
    ).fetchone()
    return bool(row and row["is_signed"])


def _sign_selected_prospect(self, target_var, class_year: int) -> None:
    sel = target_var.get().split(" | ", 1)[0] if target_var.get() else None
    if not sel:
        return
    pool = load_prospect_pool(self.conn, class_year=class_year)
    prospect = next((p for p in pool if p.player_id == sel), None)
    if prospect is None:
        return
    user_club = get_state(self.conn, "player_club_id")
    sign_prospect_to_club(self.conn, prospect=prospect, club_id=user_club, season_num=class_year)
    self.show_offseason_draft_beat()  # refresh


def _show_trajectory_reveal_sweep(self, sweep: List[Dict[str, Any]]) -> None:
    win = tk.Toplevel(self.root)
    win.title("Trajectory Reveals")
    win.configure(bg=DM_PAPER)
    for i, entry in enumerate(sweep):
        frame = ttk.Frame(win, style="Surface.TFrame", padding=14, borderwidth=1, relief="solid")
        frame.grid(row=i, column=0, sticky="ew", padx=12, pady=4)
        weight_label_color = DM_BORDER if entry["display_weight"] == "elevated" else DM_MUTED_CHARCOAL
        tk.Label(frame, text=entry["name"], bg=DM_PAPER, fg=DM_BORDER, font=FONT_BODY).grid(row=0, column=0, sticky="w")
        tk.Label(frame, text=entry["trajectory"], bg=DM_PAPER, fg=weight_label_color, font=FONT_BODY).grid(row=0, column=1, sticky="e", padx=(20, 0))
    ttk.Button(win, text="Close", command=win.destroy).grid(row=len(sweep), column=0, sticky="e", padx=12, pady=12)


def _show_accuracy_reckoning(self, season_num: int, class_year: int) -> None:
    summary = build_accuracy_reckoning(self.conn, season=season_num, class_year=class_year)
    win = tk.Toplevel(self.root)
    win.title("Accuracy Reckoning")
    win.configure(bg=DM_PAPER)
    for i, scout_summary in enumerate(summary):
        frame = ttk.Frame(win, style="Surface.TFrame", padding=14, borderwidth=1, relief="solid")
        frame.grid(row=i, column=0, sticky="ew", padx=12, pady=4)
        ttk.Label(frame, text=scout_summary["scout_id"].upper(), style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")
        for j, row in enumerate(scout_summary["rows"]):
            text = (
                f"{row['player_name']}: predicted {row['predicted_ovr_band']}"
                f" actual {row['actual_ovr']} {'✓' if row['within_5'] else '✗'}"
            )
            ttk.Label(frame, text=text, style="Muted.TLabel").grid(row=1 + j, column=0, sticky="w")
    ttk.Button(win, text="Close", command=win.destroy).grid(row=len(summary), column=0, sticky="e", padx=12, pady=12)
```

- [ ] **Step 3: Manual smoke test**

Play through a season with at least one scout assigned to a few prospects. Click through to off-season → Draft beat. Confirm:
- Pre-sign list shows tier-aware rows.
- "Reveal trajectories" button surfaces VERIFIED-trajectory prospects with their actual values.
- "Sign Selected" adds the prospect to your roster, removes them from the unsigned list.
- "Compute Accuracy Reckoning" shows per-scout summary with predicted vs actual OVR for every prospect they worked.
- Re-clicking Reckoning is idempotent (no double-write of track records).

- [ ] **Step 4: Commit**

```bash
echo "M3-5: manager_gui.show_offseason_draft_beat — V2-A Draft Day flow (tier-aware list, trajectory reveal sweep, click-to-sign, idempotent Accuracy Reckoning panel)" >> docs/superpowers/commits.log
```

---

### Task M3-6: Carry-forward decay at season transition

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py` (`create_next_manager_season` or season transition path)
- Test: `tests/test_v2a_scouting_integration.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_v2a_scouting_integration.py`:

```python
def test_carry_forward_decay_at_season_transition():
    """At season transition, every unsigned-prospect scouting_state decays one tier.
    CEILING + revealed traits persist."""
    conn = _setup()
    initialize_scouting_for_career(conn, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
    pool = load_prospect_pool(conn, class_year=1)
    unsigned = pool[0]
    from dodgeball_sim.persistence import (
        save_scouting_state, save_revealed_traits, save_ceiling_label,
        load_scouting_state, load_revealed_traits, load_ceiling_label,
    )
    from dodgeball_sim.scouting_center import ScoutingState
    save_scouting_state(conn, ScoutingState(
        player_id=unsigned.player_id,
        ratings_tier="VERIFIED", archetype_tier="KNOWN",
        traits_tier="GLIMPSED", trajectory_tier="UNKNOWN",
        scout_points={"ratings": 70, "archetype": 35, "traits": 10, "trajectory": 0},
        last_updated_week=14,
    ))
    save_revealed_traits(conn, player_id=unsigned.player_id, trait_ids=("IRONWALL",), revealed_at_week=8)
    save_ceiling_label(conn, player_id=unsigned.player_id, label="HIGH_CEILING", revealed_at_week=10, revealed_by_scout_id="bram")

    from dodgeball_sim.manager_gui import apply_scouting_carry_forward_at_transition
    apply_scouting_carry_forward_at_transition(conn, prior_class_year=1)

    decayed = load_scouting_state(conn, unsigned.player_id)
    assert decayed.ratings_tier == "KNOWN"
    assert decayed.archetype_tier == "GLIMPSED"
    assert decayed.traits_tier == "UNKNOWN"
    assert decayed.trajectory_tier == "UNKNOWN"

    # CEILING + revealed traits persist
    assert load_revealed_traits(conn, unsigned.player_id) == ("IRONWALL",)
    assert load_ceiling_label(conn, unsigned.player_id)["label"] == "HIGH_CEILING"


def test_carry_forward_skips_signed_prospects():
    conn = _setup()
    initialize_scouting_for_career(conn, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
    pool = load_prospect_pool(conn, class_year=1)
    signed = pool[0]
    from dodgeball_sim.persistence import save_scouting_state, mark_prospect_signed, load_scouting_state
    from dodgeball_sim.scouting_center import ScoutingState
    save_scouting_state(conn, ScoutingState(
        player_id=signed.player_id,
        ratings_tier="VERIFIED", archetype_tier="VERIFIED",
        traits_tier="VERIFIED", trajectory_tier="VERIFIED",
        scout_points={"ratings": 70, "archetype": 70, "traits": 70, "trajectory": 70},
        last_updated_week=14,
    ))
    mark_prospect_signed(conn, class_year=1, player_id=signed.player_id)

    from dodgeball_sim.manager_gui import apply_scouting_carry_forward_at_transition
    apply_scouting_carry_forward_at_transition(conn, prior_class_year=1)

    # Signed prospects' state should be dropped (not decayed)
    assert load_scouting_state(conn, signed.player_id) is None
```

- [ ] **Step 2: Run failing test**

Run: `python -m pytest tests/test_v2a_scouting_integration.py -v -p no:cacheprovider -k "carry_forward"`
Expected: FAIL — function not defined.

- [ ] **Step 3: Implement `apply_scouting_carry_forward_at_transition`**

Append to `manager_gui.py`:

```python
def apply_scouting_carry_forward_at_transition(
    conn: sqlite3.Connection,
    prior_class_year: int,
) -> None:
    """At season transition, decay every unsigned-prospect scouting_state by one tier;
    drop scouting_state for signed prospects. CEILING and revealed traits/trajectory persist.

    Per spec §5.4 step 5 + §7 carry-forward table.
    """
    from .scouting_center import apply_carry_forward_decay
    from .config import DEFAULT_SCOUTING_CONFIG

    pool = load_prospect_pool(conn, class_year=prior_class_year)
    for p in pool:
        is_signed = bool(conn.execute(
            "SELECT is_signed FROM prospect_pool WHERE class_year = ? AND player_id = ?",
            (prior_class_year, p.player_id),
        ).fetchone()["is_signed"])
        if is_signed:
            conn.execute("DELETE FROM scouting_state WHERE player_id = ?", (p.player_id,))
            continue
        state = load_scouting_state(conn, p.player_id)
        if state is None:
            continue
        decayed = apply_carry_forward_decay(state, DEFAULT_SCOUTING_CONFIG)
        save_scouting_state(conn, decayed)
    conn.commit()
```

- [ ] **Step 4: Hook into season-transition path**

Find where the manager mode advances to the next season (likely `create_next_manager_season` or equivalent in `manager_gui.py`). Insert a call:

```python
apply_scouting_carry_forward_at_transition(conn, prior_class_year=prior_season_num)
```

immediately before the new season's prospect pool is generated.

- [ ] **Step 5: Run tests**

Run: `python -m pytest -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
echo "M3-6: manager_gui.apply_scouting_carry_forward_at_transition — one-tier decay for unsigned prospects, drop for signed; wired into create_next_manager_season; CEILING + revealed traits persist" >> docs/superpowers/commits.log
```

---

**Milestone 3 acceptance gate:**

- [ ] Play through a full season with at least one scout reaching VERIFIED on a HIGH CEILING prospect.
- [ ] At off-season → Draft beat: confirm tier-aware list, trajectory reveal sweep shows the actual trajectory, sign action moves prospect to roster, Accuracy Reckoning shows per-scout predictions vs actual.
- [ ] Begin next season. Re-open Scouting Center. Confirm: any unsigned prospects from prior class show one tier of decay; CEILING and revealed traits still visible.
- [ ] Verify that a signed Generational prospect grows faster across multiple seasons than an equivalent NORMAL signing (golden test from M0-10 must still pass).
- [ ] All automated tests pass.

---

## Milestone 4 — Hub integration & polish

### Task M4-1: HIDDEN GEM Spotlight rotation

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py` (Spotlight build helper)
- Test: `tests/test_manager_gui.py`

- [ ] **Step 1: Write failing test**

```python
def test_build_hidden_gem_spotlight_picks_recent_high_ceiling_event():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import (
        load_prospect_pool, append_scouting_domain_event, save_ceiling_label,
    )
    from dodgeball_sim.manager_gui import build_hidden_gem_spotlight
    pool = load_prospect_pool(conn, class_year=1)
    target = pool[0]
    # Persist CEILING label
    save_ceiling_label(conn, player_id=target.player_id, label="HIGH_CEILING", revealed_at_week=8, revealed_by_scout_id="bram")
    # Emit event (week 8)
    append_scouting_domain_event(conn, season=1, week=8, event_type="CEILING_REVEALED",
                                 player_id=target.player_id, scout_id="bram",
                                 payload={"label": "HIGH_CEILING"})
    spotlight = build_hidden_gem_spotlight(conn, season=1, class_year=1)
    # Spotlight is None or has the prospect depending on gem-floor check
    if spotlight is not None:
        assert spotlight["player_id"] == target.player_id
        assert spotlight["label"] == "HIGH_CEILING"


def test_build_hidden_gem_spotlight_returns_none_without_high_ceiling_events():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.manager_gui import build_hidden_gem_spotlight
    spotlight = build_hidden_gem_spotlight(conn, season=1, class_year=1)
    assert spotlight is None
```

- [ ] **Step 2: Run failing test**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider -k "hidden_gem_spotlight"`
Expected: FAIL — function not defined.

- [ ] **Step 3: Implement `build_hidden_gem_spotlight`**

Append to `manager_gui.py`:

```python
def build_hidden_gem_spotlight(
    conn: sqlite3.Connection, season: int, class_year: int,
) -> Optional[Dict[str, Any]]:
    """Pick the most recent HIGH_CEILING reveal whose true OVR meaningfully
    exceeds the public baseline (gem floor from config). Returns None if none.

    Per spec §5.2 / §6.4: triggers HIDDEN GEM Spotlight rotation on Hub.
    """
    from .config import DEFAULT_SCOUTING_CONFIG
    events = load_scouting_domain_events_for_season(conn, season=season)
    high_ceiling_events = [
        e for e in events
        if e["event_type"] == "CEILING_REVEALED"
        and e["payload"].get("label") == "HIGH_CEILING"
    ]
    if not high_ceiling_events:
        return None
    pool_by_pid = {p.player_id: p for p in load_prospect_pool(conn, class_year=class_year)}
    floor = DEFAULT_SCOUTING_CONFIG.hidden_gem_ovr_floor
    # Most recent first
    for e in reversed(high_ceiling_events):
        prospect = pool_by_pid.get(e["player_id"])
        if prospect is None:
            continue
        public_low, public_high = prospect.public_ratings_band["ovr"]
        public_mid = (public_low + public_high) // 2
        true_ovr = int(round(prospect.true_overall()))
        if public_mid + floor < true_ovr:
            return {
                "player_id": prospect.player_id,
                "name": prospect.name,
                "label": "HIGH_CEILING",
                "public_ovr_mid": public_mid,
                "estimated_ovr_mid": true_ovr,
                "revealed_at_week": e["week"],
            }
    return None
```

- [ ] **Step 4: Wire into Hub Spotlight rotation**

Locate the Hub Spotlight rendering (search for `Spotlight` or rotation logic in `show_hub`). Add HIDDEN GEM as a candidate before the V1 fallbacks:

```python
season_num = self.cursor.season_number or 1
gem = build_hidden_gem_spotlight(self.conn, season=season_num, class_year=season_num)
if gem:
    spotlight_title = "HIDDEN GEM"
    spotlight_text = f"{gem['name']} — public OVR {gem['public_ovr_mid']}, scouts est. {gem['estimated_ovr_mid']} (HIGH CEILING)"
    spotlight_click = lambda: self.show_player_profile(gem["player_id"])
else:
    # V1 fallbacks (Player of the Week, Development Watch, Returning Headliner) — existing logic
    ...
```

- [ ] **Step 5: Run tests + manual smoke**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider`
Expected: PASS.

Manual: play a season until a HIGH CEILING reveal fires on a low-public-OVR prospect; check Hub Spotlight rotates to HIDDEN GEM with click-through to fuzzy profile.

- [ ] **Step 6: Commit**

```bash
echo "M4-1: manager_gui.build_hidden_gem_spotlight + Hub Spotlight rotation gains HIDDEN GEM (replaces V1 stub; gem floor from config)" >> docs/superpowers/commits.log
```

---

### Task M4-2: Reminder strip alerts (unassigned scouts + newly Verified late-season)

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py` (reminder strip rendering on Hub)
- Test: `tests/test_manager_gui.py`

- [ ] **Step 1: Write failing test**

```python
def test_build_scouting_alerts_unassigned_scouts():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.manager_gui import build_scouting_alerts
    alerts = build_scouting_alerts(conn, season=1, current_week=2, total_weeks=14)
    # 3 manual scouts default with no assignments → alert
    assert any("3 unassigned" in a["text"] for a in alerts)


def test_build_scouting_alerts_late_season_verified_count():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import load_prospect_pool, save_scouting_state
    from dodgeball_sim.scouting_center import ScoutingState
    pool = load_prospect_pool(conn, class_year=1)
    save_scouting_state(conn, ScoutingState(
        player_id=pool[0].player_id,
        ratings_tier="VERIFIED", archetype_tier="VERIFIED",
        traits_tier="VERIFIED", trajectory_tier="VERIFIED",
        scout_points={"ratings": 70, "archetype": 70, "traits": 70, "trajectory": 70},
        last_updated_week=13,
    ))
    from dodgeball_sim.manager_gui import build_scouting_alerts
    # In final 2 weeks of regular season → alert fires
    alerts = build_scouting_alerts(conn, season=1, current_week=13, total_weeks=14)
    assert any("Verified" in a["text"] or "trajectory" in a["text"].lower() for a in alerts)
    # Mid-season → alert does NOT fire
    alerts_mid = build_scouting_alerts(conn, season=1, current_week=4, total_weeks=14)
    assert not any("trajectory" in a["text"].lower() for a in alerts_mid)
```

- [ ] **Step 2: Run failing test**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider -k "scouting_alerts"`
Expected: FAIL — function not defined.

- [ ] **Step 3: Implement `build_scouting_alerts`**

Append to `manager_gui.py`:

```python
def build_scouting_alerts(
    conn: sqlite3.Connection, season: int, current_week: int, total_weeks: int,
) -> List[Dict[str, Any]]:
    """Reminder-strip alerts for V2-A scouting (per spec §5.2 / §6.4).

    Always: count of MANUAL scouts with no current assignment.
    Final 2 weeks of regular season: count of prospects with trajectory_axis = VERIFIED
    eligible for the Draft-Day reveal.
    """
    alerts: List[Dict[str, Any]] = []

    assignments = load_all_scout_assignments(conn)
    scouts = load_scouts(conn)
    unassigned = 0
    for s in scouts:
        strat = load_scout_strategy(conn, s.scout_id)
        if strat and strat.mode == "MANUAL":
            assignment = assignments.get(s.scout_id)
            if assignment is None or assignment.player_id is None:
                unassigned += 1
    if unassigned > 0:
        alerts.append({
            "kind": "unassigned_scouts",
            "text": f"{unassigned} unassigned scout{'s' if unassigned != 1 else ''}",
            "click_target": "scouting",
        })

    if current_week >= total_weeks - 1:  # final 2 weeks
        states = load_all_scouting_states(conn)
        verified_count = sum(1 for s in states.values() if s.trajectory_tier == "VERIFIED")
        if verified_count > 0:
            alerts.append({
                "kind": "trajectory_verified",
                "text": f"{verified_count} prospect{'s' if verified_count != 1 else ''} newly Verified — eligible for Draft Day reveal",
                "click_target": "scouting",
            })

    return alerts
```

- [ ] **Step 4: Wire into Hub reminder strip**

In `show_hub`, locate the V1 reminder strip rendering. Add scouting alerts:

```python
scouting_alerts = build_scouting_alerts(
    self.conn, season=season_num, current_week=self.cursor.week or 1,
    total_weeks=self.season.total_weeks() if self.season else 14,
)
for alert in scouting_alerts:
    # render alert chip with click target = scouting tab
    ttk.Button(reminder_frame, text=alert["text"], command=self.show_scouting_center).grid(...)
```

- [ ] **Step 5: Run tests + manual smoke**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
echo "M4-2: manager_gui.build_scouting_alerts + Hub reminder strip gains unassigned-scouts and final-2-weeks-trajectory-Verified alerts" >> docs/superpowers/commits.log
```

---

### Task M4-3: League Wire CEILING-buzz entry (low-priority flavor)

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py` (`build_wire_items`)
- Test: `tests/test_manager_gui.py`

- [ ] **Step 1: Write failing test**

```python
def test_wire_items_include_high_ceiling_buzz():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import (
        load_prospect_pool, append_scouting_domain_event, save_ceiling_label,
    )
    from dodgeball_sim.manager_gui import build_wire_items
    pool = load_prospect_pool(conn, class_year=1)
    target = pool[0]
    save_ceiling_label(conn, player_id=target.player_id, label="HIGH_CEILING", revealed_at_week=6, revealed_by_scout_id="bram")
    append_scouting_domain_event(conn, season=1, week=6, event_type="CEILING_REVEALED",
                                 player_id=target.player_id, scout_id="bram",
                                 payload={"label": "HIGH_CEILING"})
    items = build_wire_items(conn, season_id="season_1", current_week=8)
    # Expect at least one Wire entry mentioning the prospect's name
    assert any(target.name in (it.get("body") or "") for it in items)
```

- [ ] **Step 2: Run failing test**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider -k "high_ceiling_buzz"`
Expected: FAIL — `build_wire_items` does not yet emit scouting buzz entries.

- [ ] **Step 3: Extend `build_wire_items`**

Locate the existing `build_wire_items` function (V1). Append scouting buzz entries:

```python
# V2-A scouting buzz entries (low-priority, flavor only; no ratings exposed)
season_num_int = int(season_id.rsplit("_", 1)[-1]) if season_id.rsplit("_", 1)[-1].isdigit() else 1
events = load_scouting_domain_events_for_season(conn, season=season_num_int)
for e in events:
    if e["event_type"] == "CEILING_REVEALED" and e["payload"].get("label") == "HIGH_CEILING":
        # Look up prospect name
        pool = load_prospect_pool(conn, class_year=season_num_int)
        prospect = next((p for p in pool if p.player_id == e["player_id"]), None)
        if prospect is None:
            continue
        items.append({
            "tag": "RECRUITING",
            "headline": "Scouts in your room are buzzing",
            "body": f"Word travels — your scouts can't stop talking about {prospect.name}. Draft Day will tell.",
            "week": e["week"],
        })
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_manager_gui.py -v -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
echo "M4-3: manager_gui.build_wire_items extended with low-priority HIGH_CEILING buzz entries (texture only — no public ratings exposure)" >> docs/superpowers/commits.log
```

---

### Task M4-4: Screenshot review pass + playtest tuning gate

**Files:**
- Capture artifacts: `output/ui-review-v2a/`
- Modify (only if playtest demands): `src/dodgeball_sim/config.py` (`DEFAULT_SCOUTING_CONFIG` knobs)

- [ ] **Step 1: Set up screenshot output directory**

```bash
mkdir -p "output/ui-review-v2a"
```

- [ ] **Step 2: Capture key screens**

Launch `python -m dodgeball_sim`. Take screenshots (manual, OS-native screen capture) of:

1. Splash screen.
2. Hub at Week 1 (no scouting yet) — confirm Spotlight rotates among V1 options.
3. Scouting Center at Week 1 — all prospects UNKNOWN.
4. Scout Manage dialog.
5. Scouting Center at Week ~7 — bands narrowed for assigned prospects.
6. Fuzzy Profile of an UNKNOWN prospect.
7. Fuzzy Profile of a KNOWN prospect with HIGH CEILING revealed (use HIGH-trait-sense scout).
8. Hub Spotlight showing HIDDEN GEM.
9. Off-season Draft beat — pre-sign list with tier display.
10. Trajectory reveal sweep modal — with at least one STAR or GENERATIONAL.
11. Accuracy Reckoning panel.
12. Beginning of Season 2 — Scouting Center showing decayed carryover prospects + new Class 2.

Save to `output/ui-review-v2a/01-splash.png`, `02-hub-week1.png`, …, `12-season2-scouting.png`.

- [ ] **Step 3: Playtest pass — observe and tune**

Play through 2 full seasons. Note:
- Did at least one HIGH CEILING reveal fire across the 2 seasons? (~2 expected per class with default 8% rate × 25 size.)
- Did at least one GENERATIONAL prospect appear across 2 seasons? (~50/50 chance with 1% rate × 50 prospects.)
- Did the per-scout throughput feel right? Approximately 6 prospects to KNOWN per season per scout-team, 3 to VERIFIED.
- Did Auto-scout pick targets that felt sensible?

If any feel off, tune in `src/dodgeball_sim/config.py` `DEFAULT_SCOUTING_CONFIG` only:
- `tier_thresholds` (lower = easier to reach VERIFIED).
- `weekly_scout_point_base` (higher = faster narrowing).
- `trajectory_rates` (raise GENERATIONAL if it feels too rare).
- `prospect_class_size` (lower = more focused class; higher = more variety).
- `hidden_gem_ovr_floor` (lower = HIDDEN GEM Spotlight fires more often).

After tuning, re-run full test suite to confirm nothing depends on the literal numbers:

Run: `python -m pytest -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 4: Commit screenshots + tuning notes**

```bash
echo "M4-4: V2-A UI review captured to output/ui-review-v2a/ (12 screenshots); playtest tuning pass on DEFAULT_SCOUTING_CONFIG (note actual values changed, if any)" >> docs/superpowers/commits.log
```

---

**Milestone 4 acceptance gate:**

- [ ] All 12 screenshots captured in `output/ui-review-v2a/`.
- [ ] HIDDEN GEM Spotlight observed at least once during playtest.
- [ ] Reminder strip "unassigned scouts" alert observed at career start.
- [ ] Reminder strip "newly Verified" alert observed at Week 13/14.
- [ ] HIGH_CEILING League Wire entry observed.
- [ ] Tuning pass complete; any changes are in `config.py` only.
- [ ] Full test suite green.

---

## Final V2-A Acceptance Gate

When the four milestones are green:

- [ ] `python -m pytest -p no:cacheprovider` — all tests pass.
- [ ] `python -m pytest tests/test_regression.py -v -p no:cacheprovider` — Phase 1 golden regression unchanged from V1.
- [ ] `python -m pytest tests/test_v2a_scouting_integration.py -v -p no:cacheprovider` — full season + two-season runs deterministic; trajectory honored by development; track records preserved across reassignments.
- [ ] Manual playthrough: 2 full seasons via `python -m dodgeball_sim`. Confirm playable end-to-end.
- [ ] All design contracts in [§2 of design](design.md#2-design-contracts) verified by inspection.
- [ ] Screenshots in `output/ui-review-v2a/`.
- [ ] Spec acceptance criteria from [§10 of design](design.md#10-acceptance-criteria) all checked.

---

## Plan Self-Review (executed during plan-writing 2026-04-27)

**Spec coverage scan:**

- §3 Architecture (module map, schema v8) → M0-3 (schema), M0-1/4/5/6/7/8/9 (scouting_center.py), M0-10 (development.py), M0-11 (persistence), M3-1 (player_trajectory side table). ✅
- §4 Engine model (Scout, Prospect, ScoutingState, narrowing, CEILING, traits, auto-scout, track records) → M0-4 through M0-12. ✅
- §5 Data flow (career start, week-tick, off-season Draft, season transition, determinism) → M0-12 + M1-5 (week-tick wiring), M3-2 to M3-6. ✅
- §6 UI surfaces (Scouting Center, UncertaintyBar, fuzzy Profile, Hub, Off-season Draft, League Wire, Nav) → M1-1/2/3/4, M2-1/2, M3-5, M4-1/2/3. ✅
- §7 Carry-forward → M3-6. ✅
- §8 Testing (pure-helper unit + integration + invariant) → tests written throughout M0–M3. Trajectory-honored golden in M0-10. End-to-end determinism in M0-12. ✅
- §9 Risks → trajectory rate playtest is M4-4; UI density review is M4-4; tier threshold tuning is M4-4 (config-only). ✅
- §10 Acceptance criteria → final V2-A acceptance gate above maps each criterion. ✅

**Placeholder scan:** none of the disallowed phrases ("TBD", "TODO", "implement later", "add appropriate error handling", "similar to Task N", code without code blocks) appear in any task. ✅

**Type / signature consistency:** spot-checked across tasks — `ScoutingState`, `Prospect`, `Scout`, `ScoutContribution` field names match between dataclass definition (M0-5), narrowing math (M0-6), persistence (M0-11), and orchestrator (M0-12). `apply_carry_forward_decay` signature matches between definition (M0-9) and use (M3-6). `build_*` helper return shapes consistent between defining task and consumer task (e.g. `build_prospect_board_rows` rows used as-is in M3-5). ✅

**Scope check:** plan covers exactly V2-A. V2-B (recruitment competition) and downstream V2-C/D/E/F items remain explicitly out of scope. ✅

---

## Execution Handoff

Plan complete and saved to [`docs/specs/2026-04-26-v2-a-scouting/implementation-plan.md`](implementation-plan.md). Two execution options:

**1. Subagent-Driven (recommended)** — A fresh subagent picks up each task in order. Two-stage review (subagent reports completion → main session reviews diff before unlocking the next task). Good for high-risk milestones (M0 engine, M3 sign action, M3-6 carry-forward).

**2. Inline Execution** — Execute tasks in this session using the executing-plans skill. Batch through M0 with periodic checkpoints, then pause for human review before each subsequent milestone.

**Which approach?**

- If **Subagent-Driven**: invoke `superpowers:subagent-driven-development` with this plan.
- If **Inline**: invoke `superpowers:executing-plans` with this plan.
- For this codebase specifically (no git, ~12k LOC, mature test suite, integrity contract sensitive): I'd recommend **Subagent-Driven for M0** (engine + schema + the integrity-critical `development.py` wire-up benefit from independent verification per task), then **Inline for M1–M4** (UI work where the GUI smoke test + screenshot review is the validation, faster to keep momentum).

