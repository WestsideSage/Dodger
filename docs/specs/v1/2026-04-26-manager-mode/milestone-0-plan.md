# Manager Mode — Milestone 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land all engine and state contracts that the Manager Mode v1 UI will consume. **No UI work in this milestone.** UI implementation in M1+ does not begin until M0 is reviewed and approved as a separate gate.

**Architecture:** Six independent engine deliverables. Each is a small set of pure modules + new tests + (where applicable) an additive SQLite migration. Existing engine behavior must not shift; the Phase 1 golden log (`tests/golden_logs/phase1_baseline.json`) must remain unchanged. Where a deliverable touches a code path the engine consumes (e.g. `franchise.simulate_match`), the change is a strict refactor that yields the same output by default.

**Tech Stack:** Python 3.10+, SQLite via stdlib `sqlite3`, pytest, no external dependencies. Test patterns mirror the existing repo: `tests/factories.py` helpers, in-memory SQLite for unit tests (`sqlite3.connect(":memory:")`), `pytest.tmp_path` for file-backed tests.

**Reference docs:**
- Spec: [docs/specs/2026-04-26-manager-mode/design.md](./design.md) — read §2.5 (Engine Dependencies) and §12.6 (Career State Machine) before starting any task.
- Engineering invariants: [docs/specs/AGENTS.md](../AGENTS.md) — §1 (invariants), §7 (integrity harness), §8 (config versioning).

---

## File Structure

**New modules:**
- `src/dodgeball_sim/win_probability.py` — post-hoc retrospective WP analyzer (Task 3).
- `src/dodgeball_sim/lineup.py` — `LineupResolver` and lineup contract (Task 4).
- `src/dodgeball_sim/career_state.py` — career state machine enum + cursor + transitions (Task 5).

**New test files:**
- `tests/test_win_probability.py`
- `tests/test_lineup.py`
- `tests/test_career_state.py`

**Modified modules:**
- `src/dodgeball_sim/league.py` — extend `Club` with identity fields (Task 1).
- `src/dodgeball_sim/persistence.py` — `_migrate_v6` (Club identity columns), `_migrate_v7` (lineup tables); update `save_club` / `load_clubs` to round-trip new fields; add `save_lineup_default` / `load_lineup_default` / `save_match_lineup_override` / `load_match_lineup_override` / `save_career_state_cursor` / `load_career_state_cursor` (Tasks 1, 4, 5).
- `src/dodgeball_sim/sample_data.py` — repopulate the curated cast (Task 1).
- `src/dodgeball_sim/awards.py` — add `compute_match_mvp` reusing existing `_mvp_score` (Task 2).
- `src/dodgeball_sim/franchise.py` — `simulate_match` consumes `LineupResolver` instead of using raw roster order (Task 4).
- `src/dodgeball_sim/scheduler.py` — module docstring documenting v1 status; small `season_format_summary()` helper (Task 6).

**Modified test files:**
- `tests/test_persistence.py` — round-trip tests for new persistence functions.
- `tests/test_dynasty_persistence.py` — extend Club construction calls with new fields (or rely on defaults).
- `tests/test_awards.py` — match-MVP test.
- `tests/test_scheduler.py` — round-robin format verification.
- `tests/test_stats.py`, `tests/test_season.py` — extend Club construction calls if positional args break (or rely on defaults).

**Spec doc update:**
- `docs/specs/2026-04-26-manager-mode/design.md` — mark §2.5.7 (match-MVP) and §2.5.8 (playoffs) verification results.

---

## Task 1: Club Identity Extension + Migration v6 + Sample Data Repopulation

**Spec ref:** §2.5.1, §3.2.

**Files:**
- Modify: `src/dodgeball_sim/league.py:9-17`
- Modify: `src/dodgeball_sim/persistence.py` — add `_migrate_v6`, register in `_MIGRATIONS`, update `save_club` and `load_clubs`. Bump `CURRENT_SCHEMA_VERSION` to `6`.
- Modify: `src/dodgeball_sim/sample_data.py` — replace 2-team fixture with the v1 curated cast of 6 clubs.
- Test: `tests/test_persistence.py` — migration v6 + Club round-trip with new fields.
- Test: `tests/test_sample_data.py` (new) — sanity-check curated cast shape.

### Sub-tasks

- [ ] **1.1: Run the existing test suite as a clean baseline**

```bash
cd "C:/GPT5-Projects/Dodgeball Simulator"
python -m pytest -q
```

Expected: all tests pass. Record the count for later comparison. If anything fails on a clean checkout, stop and resolve before continuing.

- [ ] **1.2: Write failing test for extended `Club` model**

Add to `tests/test_persistence.py` (top of file is fine):

```python
from dodgeball_sim.league import Club
from dodgeball_sim.models import CoachPolicy


def test_club_has_identity_fields():
    club = Club(
        club_id="aurora",
        name="Aurora Pilots",
        colors="teal/charcoal",
        home_region="Northwest",
        founded_year=1998,
        coach_policy=CoachPolicy(),
        primary_color="#2E5E5C",
        secondary_color="#1F2933",
        venue_name="Aurora Field House",
        tagline="Power-arm aggression, deep scouting tradition",
    )
    assert club.primary_color == "#2E5E5C"
    assert club.secondary_color == "#1F2933"
    assert club.venue_name == "Aurora Field House"
    assert club.tagline == "Power-arm aggression, deep scouting tradition"


def test_club_identity_fields_default_to_empty():
    """Backwards-compat: existing positional construction must still work."""
    club = Club("legacy", "Legacy Club", "red/white", "North", 2020, CoachPolicy())
    assert club.primary_color == ""
    assert club.secondary_color == ""
    assert club.venue_name == ""
    assert club.tagline == ""
```

- [ ] **1.3: Run failing test to confirm it fails**

```bash
python -m pytest tests/test_persistence.py::test_club_has_identity_fields -v
```

Expected: FAIL with `TypeError: Club.__init__() got an unexpected keyword argument 'primary_color'`.

- [ ] **1.4: Extend the `Club` dataclass**

Edit `src/dodgeball_sim/league.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from .models import CoachPolicy


@dataclass(frozen=True)
class Club:
    """Persistent franchise entity. Distinct from Team (match snapshot)."""
    club_id: str
    name: str
    colors: str          # legacy single-string e.g. "red/black"; kept for backward compat
    home_region: str
    founded_year: int
    coach_policy: CoachPolicy = field(default_factory=CoachPolicy)
    primary_color: str = ""    # hex, e.g. "#2E5E5C" — new in v6
    secondary_color: str = ""  # hex, e.g. "#1F2933" — new in v6
    venue_name: str = ""       # human-readable venue name — new in v6
    tagline: str = ""          # one-line identity blurb — new in v6


@dataclass(frozen=True)
class Conference:
    conference_id: str
    name: str
    club_ids: Tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "club_ids", tuple(self.club_ids))


@dataclass(frozen=True)
class League:
    league_id: str
    name: str
    conferences: Tuple[Conference, ...]
    season_ids: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "conferences", tuple(self.conferences))
        object.__setattr__(self, "season_ids", tuple(self.season_ids))

    def all_club_ids(self) -> List[str]:
        ids: List[str] = []
        for conf in self.conferences:
            ids.extend(conf.club_ids)
        return ids


__all__ = ["Club", "Conference", "League"]
```

- [ ] **1.5: Run the model tests**

```bash
python -m pytest tests/test_persistence.py::test_club_has_identity_fields tests/test_persistence.py::test_club_identity_fields_default_to_empty -v
```

Expected: PASS.

- [ ] **1.6: Run the full suite to confirm no positional-arg call site broke**

```bash
python -m pytest -q
```

Expected: PASS at the same count as 1.1. The defaulted new fields should not affect existing call sites that pass 6 positional args (`Club(id, name, colors, region, year, policy)`).

- [ ] **1.7: Write failing test for migration v6 column adds**

Add to `tests/test_persistence.py`:

```python
import sqlite3

from dodgeball_sim.persistence import (
    create_schema,
    get_schema_version,
)


def test_v6_adds_club_identity_columns():
    """Schema after create_schema() must include the v6 identity columns.
    Note: the canonical CURRENT_SCHEMA_VERSION assertion is added in Task 4.5
    once the v7 migration also lands; we don't double-update it here."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    cursor = conn.execute("PRAGMA table_info(clubs)")
    column_names = {row["name"] for row in cursor.fetchall()}
    assert "primary_color" in column_names
    assert "secondary_color" in column_names
    assert "venue_name" in column_names
    assert "tagline" in column_names
    assert get_schema_version(conn) >= 6
```

- [ ] **1.8: Run failing migration test**

```bash
python -m pytest tests/test_persistence.py::test_v6_adds_club_identity_columns -v
```

Expected: FAIL — columns missing.

- [ ] **1.9: Add `_migrate_v6` and bump `CURRENT_SCHEMA_VERSION`**

Edit `src/dodgeball_sim/persistence.py`. At the constant declaration:

```python
# Increment when new migrations are added.
CURRENT_SCHEMA_VERSION = 6
```

After the existing `_migrate_v5` function (around line 458), add:

```python
def _migrate_v6(conn: sqlite3.Connection) -> None:
    """Manager Mode M0: extend clubs with identity fields (primary/secondary
    color, venue name, tagline). Existing rows get empty strings."""
    conn.executescript(
        """
        ALTER TABLE clubs ADD COLUMN primary_color TEXT NOT NULL DEFAULT '';
        ALTER TABLE clubs ADD COLUMN secondary_color TEXT NOT NULL DEFAULT '';
        ALTER TABLE clubs ADD COLUMN venue_name TEXT NOT NULL DEFAULT '';
        ALTER TABLE clubs ADD COLUMN tagline TEXT NOT NULL DEFAULT '';
        """
    )
```

Update the `_MIGRATIONS` registry (around line 460):

```python
_MIGRATIONS: Dict[int, Any] = {
    1: _migrate_v1,
    2: _migrate_v2,
    3: _migrate_v3,
    4: _migrate_v4,
    5: _migrate_v5,
    6: _migrate_v6,
}
```

- [ ] **1.10: Run migration test**

```bash
python -m pytest tests/test_persistence.py::test_v6_adds_club_identity_columns -v
```

Expected: PASS.

- [ ] **1.11: Write failing test for `save_club` / `load_clubs` round-trip with new fields**

Add to `tests/test_persistence.py`:

```python
from dodgeball_sim.persistence import (
    load_clubs,
    save_club,
)


def test_save_load_club_roundtrip_includes_identity_fields():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    club = Club(
        club_id="aurora",
        name="Aurora Pilots",
        colors="teal/charcoal",
        home_region="Northwest",
        founded_year=1998,
        coach_policy=CoachPolicy(),
        primary_color="#2E5E5C",
        secondary_color="#1F2933",
        venue_name="Aurora Field House",
        tagline="Power-arm aggression, deep scouting tradition",
    )
    save_club(conn, club, roster=[])

    loaded = load_clubs(conn)["aurora"]
    assert loaded.primary_color == "#2E5E5C"
    assert loaded.secondary_color == "#1F2933"
    assert loaded.venue_name == "Aurora Field House"
    assert loaded.tagline == "Power-arm aggression, deep scouting tradition"
```

- [ ] **1.12: Run failing round-trip test**

```bash
python -m pytest tests/test_persistence.py::test_save_load_club_roundtrip_includes_identity_fields -v
```

Expected: FAIL — `save_club` doesn't write the new columns; `load_clubs` doesn't read them.

- [ ] **1.13: Update `save_club` to write the new columns**

In `src/dodgeball_sim/persistence.py`, replace the `save_club` function (around line 665):

```python
def save_club(conn: sqlite3.Connection, club: Club, roster: List[Player]) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO clubs
            (club_id, name, colors, home_region, founded_year, coach_policy_json,
             primary_color, secondary_color, venue_name, tagline)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            club.club_id, club.name, club.colors, club.home_region,
            club.founded_year, _json_dump(club.coach_policy.as_dict()),
            club.primary_color, club.secondary_color, club.venue_name, club.tagline,
        ),
    )
    conn.execute(
        "INSERT OR REPLACE INTO club_rosters (club_id, players_json) VALUES (?, ?)",
        (club.club_id, _json_dump([_player_to_dict(p) for p in roster])),
    )
```

- [ ] **1.14: Update `load_clubs` to read the new columns**

In `src/dodgeball_sim/persistence.py`, replace the `load_clubs` function (around line 683):

```python
def load_clubs(conn: sqlite3.Connection) -> Dict[str, "Club"]:
    cursor = conn.execute("SELECT * FROM clubs")
    clubs: Dict[str, Club] = {}
    for row in cursor.fetchall():
        cp_dict = json.loads(row["coach_policy_json"])
        keys = row.keys()
        clubs[row["club_id"]] = Club(
            club_id=row["club_id"],
            name=row["name"],
            colors=row["colors"],
            home_region=row["home_region"],
            founded_year=row["founded_year"],
            coach_policy=CoachPolicy(**{k: v for k, v in cp_dict.items() if k in CoachPolicy.__dataclass_fields__}),
            primary_color=row["primary_color"] if "primary_color" in keys else "",
            secondary_color=row["secondary_color"] if "secondary_color" in keys else "",
            venue_name=row["venue_name"] if "venue_name" in keys else "",
            tagline=row["tagline"] if "tagline" in keys else "",
        )
    return clubs
```

(Defensive `if X in keys` checks let pre-v6 in-memory rows still load; on real DBs the migration will have added the columns.)

- [ ] **1.15: Run round-trip test**

```bash
python -m pytest tests/test_persistence.py::test_save_load_club_roundtrip_includes_identity_fields -v
```

Expected: PASS.

- [ ] **1.16: Write failing tests for the v1 curated cast in `sample_data.py`**

Create `tests/test_sample_data.py`:

```python
from dodgeball_sim.sample_data import sample_match_setup, curated_clubs


def test_curated_cast_size():
    """v1 ships 6 hand-tuned curated clubs."""
    clubs = curated_clubs()
    assert len(clubs) == 6


def test_every_curated_club_has_full_identity():
    for club in curated_clubs():
        assert club.primary_color, f"{club.club_id} missing primary_color"
        assert club.secondary_color, f"{club.club_id} missing secondary_color"
        assert club.venue_name, f"{club.club_id} missing venue_name"
        assert club.tagline, f"{club.club_id} missing tagline"


def test_sample_match_setup_still_works():
    """sample_match_setup() must keep returning the Aurora vs Lunar matchup
    so existing demos and the legacy GUI path do not break."""
    setup = sample_match_setup()
    assert setup.team_a.id == "aurora"
    assert setup.team_b.id == "lunar"
    assert len(setup.team_a.players) >= 3
    assert len(setup.team_b.players) >= 3
```

- [ ] **1.17: Run failing sample-data tests**

```bash
python -m pytest tests/test_sample_data.py -v
```

Expected: FAIL — `curated_clubs` does not exist.

- [ ] **1.18: Repopulate `sample_data.py` with the curated cast**

Replace the contents of `src/dodgeball_sim/sample_data.py`:

```python
from __future__ import annotations

from typing import List

from .league import Club
from .models import CoachPolicy, MatchSetup, Player, PlayerRatings, PlayerTraits, Team
from .setup_loader import describe_matchup


def _player(
    player_id: str,
    name: str,
    *,
    accuracy: float,
    power: float,
    dodge: float,
    catch: float,
    stamina: float = 60.0,
) -> Player:
    ratings = PlayerRatings(
        accuracy=accuracy,
        power=power,
        dodge=dodge,
        catch=catch,
        stamina=stamina,
    ).apply_bounds()
    return Player(id=player_id, name=name, ratings=ratings, traits=PlayerTraits())


def _team(
    team_id: str,
    name: str,
    players: List[Player],
    *,
    policy: CoachPolicy,
    chemistry: float,
) -> Team:
    return Team(id=team_id, name=name, players=tuple(players), coach_policy=policy, chemistry=chemistry)


# ---------------------------------------------------------------------------
# v1 curated cast — 6 fictional clubs with full identity (Manager Mode M0)
# ---------------------------------------------------------------------------

_AURORA = Club(
    club_id="aurora",
    name="Aurora Pilots",
    colors="teal/charcoal",
    home_region="Northwest",
    founded_year=1998,
    coach_policy=CoachPolicy(target_stars=0.7, risk_tolerance=0.55, sync_throws=0.25, tempo=0.5, rush_frequency=0.45),
    primary_color="#2E5E5C",
    secondary_color="#1F2933",
    venue_name="Aurora Field House",
    tagline="Power-arm aggression, deep scouting tradition",
)

_LUNAR = Club(
    club_id="lunar",
    name="Lunar Arcs",
    colors="silver/navy",
    home_region="Northeast",
    founded_year=2002,
    coach_policy=CoachPolicy(target_stars=0.65, risk_tolerance=0.45, sync_throws=0.35, tempo=0.42, rush_frequency=0.5),
    primary_color="#5C6F8A",
    secondary_color="#0F1A2E",
    venue_name="Arc Pavilion",
    tagline="Catch-heavy attrition, patient defensive system",
)

_NORTHWOOD = Club(
    club_id="northwood",
    name="Northwood Wreckers",
    colors="brick/cream",
    home_region="Midwest",
    founded_year=1985,
    coach_policy=CoachPolicy(target_stars=0.8, risk_tolerance=0.7, sync_throws=0.4, tempo=0.65, rush_frequency=0.6),
    primary_color="#B75A3A",
    secondary_color="#F4F1EA",
    venue_name="Wrecker Yard",
    tagline="High-tempo power throwing, target the stars",
)

_HARBOR = Club(
    club_id="harbor",
    name="Harbor Anchors",
    colors="navy/gold",
    home_region="Coastal",
    founded_year=1990,
    coach_policy=CoachPolicy(target_stars=0.55, risk_tolerance=0.4, sync_throws=0.3, tempo=0.4, rush_frequency=0.35),
    primary_color="#1F3A5F",
    secondary_color="#D6A23A",
    venue_name="Anchorage Hall",
    tagline="Defensive grind, league's best catchers",
)

_GRANITE = Club(
    club_id="granite",
    name="Granite Foxes",
    colors="sage/charcoal",
    home_region="Mountain",
    founded_year=2010,
    coach_policy=CoachPolicy(target_stars=0.6, risk_tolerance=0.5, sync_throws=0.5, tempo=0.55, rush_frequency=0.55),
    primary_color="#8FA87E",
    secondary_color="#242428",
    venue_name="Granite Arena",
    tagline="Swarm and overload, balanced rotation depth",
)

_SOLSTICE = Club(
    club_id="solstice",
    name="Solstice Embers",
    colors="mustard/black",
    home_region="South",
    founded_year=2005,
    coach_policy=CoachPolicy(target_stars=0.75, risk_tolerance=0.6, sync_throws=0.45, tempo=0.6, rush_frequency=0.5),
    primary_color="#D6A23A",
    secondary_color="#242428",
    venue_name="Ember Court",
    tagline="Sniper control, accuracy-focused recruiting",
)


def curated_clubs() -> List[Club]:
    """Return the v1 curated cast in display order."""
    return [_AURORA, _LUNAR, _NORTHWOOD, _HARBOR, _GRANITE, _SOLSTICE]


# ---------------------------------------------------------------------------
# Legacy single-matchup helper (preserved so existing demos / GUI keep working)
# ---------------------------------------------------------------------------

_TEAM_A = _team(
    "aurora",
    "Aurora Pilots",
    [
        _player("aurora_captain", "Aurora Captain", accuracy=78, power=72, dodge=60, catch=55),
        _player("aurora_scout", "Aurora Scout", accuracy=68, power=52, dodge=64, catch=58),
        _player("aurora_rookie", "Aurora Rookie", accuracy=60, power=50, dodge=52, catch=65),
    ],
    policy=_AURORA.coach_policy,
    chemistry=0.58,
)

_TEAM_B = _team(
    "lunar",
    "Lunar Arcs",
    [
        _player("lunar_captain", "Lunar Captain", accuracy=75, power=70, dodge=57, catch=50),
        _player("lunar_anchor", "Lunar Anchor", accuracy=65, power=60, dodge=62, catch=70),
        _player("lunar_spotter", "Lunar Spotter", accuracy=55, power=48, dodge=58, catch=60),
    ],
    policy=_LUNAR.coach_policy,
    chemistry=0.52,
)


def sample_match_setup() -> MatchSetup:
    """Return the canonical sample matchup for demos/CLI/legacy GUI."""
    return MatchSetup(team_a=_TEAM_A, team_b=_TEAM_B, config_version="phase1.v1")


def describe_sample_matchup() -> str:
    return describe_matchup(sample_match_setup())


__all__ = [
    "curated_clubs",
    "sample_match_setup",
    "describe_sample_matchup",
]
```

- [ ] **1.19: Run sample-data tests**

```bash
python -m pytest tests/test_sample_data.py -v
```

Expected: PASS.

- [ ] **1.20: Run the regression / golden-log test to confirm engine output is unchanged**

```bash
python -m pytest tests/test_regression.py -v
```

Expected: PASS. Sample-data changes only added curated clubs and preserved the original `_TEAM_A`/`_TEAM_B` ratings, so the engine output for the canonical matchup must remain bit-identical.

If this fails, the engine output has shifted. Investigate which player/policy field changed before continuing — do not regenerate the golden log without an explicit AGENTS.md §1 change-note.

- [ ] **1.21: Run the full suite**

```bash
python -m pytest -q
```

Expected: all tests pass at a count equal to the 1.1 baseline + the new tests added in 1.2 / 1.7 / 1.11 / 1.16.

- [ ] **1.22: Commit Task 1**

```bash
git add src/dodgeball_sim/league.py src/dodgeball_sim/persistence.py src/dodgeball_sim/sample_data.py tests/test_persistence.py tests/test_sample_data.py
git commit -m "$(cat <<'EOF'
feat(m0): extend Club with identity fields + repopulate curated cast

Manager Mode Milestone 0 deliverable §2.5.1: add primary_color,
secondary_color, venue_name, tagline to Club. Schema v6 ALTER TABLE
adds the columns with empty-string defaults so existing rows keep
loading. save_club / load_clubs round-trip the new fields.

sample_data.py now exposes curated_clubs() returning the v1 6-club
cast (Aurora, Lunar, Northwood, Harbor, Granite, Solstice). The
legacy sample_match_setup() helper is preserved bit-for-bit so the
phase1 golden log is unchanged.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Match-MVP Function

**Spec ref:** §2.5.7.

**Files:**
- Modify: `src/dodgeball_sim/awards.py` — add `compute_match_mvp` reusing existing `_mvp_score`.
- Test: `tests/test_awards.py` — match-MVP behavior + tiebreak determinism + empty-input contract.
- Modify: `docs/specs/2026-04-26-manager-mode/design.md` — mark §2.5.7 verified.

### Sub-tasks

- [ ] **2.1: Confirm there is no existing match-MVP function**

```bash
python -c "from dodgeball_sim import awards; print([n for n in dir(awards) if 'mvp' in n.lower() or 'match' in n.lower()])"
```

Expected: shows no `compute_match_mvp` (only `compute_season_awards` and the private `_mvp_score`). If a `compute_match_mvp` already exists, stop and adapt this task to verify rather than implement.

- [ ] **2.2: Write failing test for `compute_match_mvp`**

Add to `tests/test_awards.py`:

```python
from dodgeball_sim.awards import compute_match_mvp
from dodgeball_sim.stats import PlayerMatchStats


def test_compute_match_mvp_picks_highest_score():
    stats = {
        "alice": PlayerMatchStats(eliminations_by_throw=4, catches_made=1),
        "bob":   PlayerMatchStats(eliminations_by_throw=2, catches_made=2),
        "carol": PlayerMatchStats(eliminations_by_throw=1, catches_made=0),
    }
    # Score formula (from awards._mvp_score):
    #   alice: 4*3 + 1*4 = 16
    #   bob:   2*3 + 2*4 = 14
    #   carol: 1*3 + 0   = 3
    assert compute_match_mvp(stats) == "alice"


def test_compute_match_mvp_deterministic_tiebreak():
    """Tied players resolve in stable order (lexicographic player_id)."""
    stats = {
        "zeta":  PlayerMatchStats(eliminations_by_throw=2),
        "alpha": PlayerMatchStats(eliminations_by_throw=2),
    }
    assert compute_match_mvp(stats) == "zeta"  # max() with secondary key keeps last lex


def test_compute_match_mvp_empty_returns_none():
    assert compute_match_mvp({}) is None
```

- [ ] **2.3: Run failing tests**

```bash
python -m pytest tests/test_awards.py::test_compute_match_mvp_picks_highest_score tests/test_awards.py::test_compute_match_mvp_deterministic_tiebreak tests/test_awards.py::test_compute_match_mvp_empty_returns_none -v
```

Expected: FAIL — `compute_match_mvp` not defined.

- [ ] **2.4: Implement `compute_match_mvp`**

Add to `src/dodgeball_sim/awards.py` (after `compute_season_awards`):

```python
def compute_match_mvp(player_match_stats: Dict[str, PlayerMatchStats]) -> Optional[str]:
    """Return the player_id of the match MVP, or None if there are no stats.

    Uses the same _mvp_score formula as compute_season_awards. Tiebreaks
    deterministically by player_id (lexicographic, max wins) so the same
    stat set always produces the same MVP.
    """
    if not player_match_stats:
        return None
    return max(
        player_match_stats,
        key=lambda pid: (_mvp_score(player_match_stats[pid]), pid),
    )
```

Also export it. Update `__all__` at the bottom of the file:

```python
__all__ = [
    "SeasonAward",
    "compute_match_mvp",
    "compute_season_awards",
    "aggregate_season_stats",
]
```

- [ ] **2.5: Run match-MVP tests**

```bash
python -m pytest tests/test_awards.py -v
```

Expected: PASS, including the existing `compute_season_awards` tests untouched.

- [ ] **2.6: Mark §2.5.7 verified in the design spec**

Edit `docs/specs/2026-04-26-manager-mode/design.md`. Find §2.5.7 (around the line starting `### 2.5.7 Match-MVP function`) and replace its body:

```markdown
### 2.5.7 Match-MVP function

**Status (M0 verified):** No `compute_match_mvp` existed in `awards.py`; only `compute_season_awards`. Added in M0 — `awards.compute_match_mvp(player_match_stats: Dict[str, PlayerMatchStats]) -> Optional[str]` reusing the existing `_mvp_score` formula with a deterministic player_id tiebreak. Empty input returns `None`.
```

- [ ] **2.7: Commit Task 2**

```bash
git add src/dodgeball_sim/awards.py tests/test_awards.py docs/specs/2026-04-26-manager-mode/design.md
git commit -m "$(cat <<'EOF'
feat(m0): add compute_match_mvp for Match Report consumption

Manager Mode Milestone 0 deliverable §2.5.7. Reuses awards._mvp_score
so match MVP and season MVP rank players consistently. Deterministic
tiebreak by player_id. Empty input returns None.

Marks §2.5.7 verified in the design spec.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Win-Probability Analyzer

**Spec ref:** §2.5.4, §8.3.

**Architecture decision:** the analyzer is **post-hoc retrospective leverage**, not a live predictor. Two functions:

1. `pre_match_expected_outcome(team_a, team_b) -> float` — sigmoid on the OVR-difference of the two team rosters. Returns p(team_a wins) ∈ [0, 1]. Used post-match only, to flag UPSET when actual deviates from expected beyond a documented threshold.
2. `per_event_wp_delta(events, team_a_id, team_b_id, team_a_player_ids, team_b_player_ids) -> List[float]` — for each event in the resolved log, compute a survivor-count-based WP before and after the event; return the per-event delta from team_a's perspective. Sums approximately reflect the match outcome direction.

The survivor-count WP model: `wp_a = sigmoid(K * (alive_a - alive_b))` where K is a small constant (e.g., 0.6) tuned so an even split sits at 0.5 and a 1-survivor-vs-3 advantage reads roughly 80/20. This is intentionally simple — the model's job is to mark moments of high leverage, not to predict.

**Files:**
- Create: `src/dodgeball_sim/win_probability.py`.
- Create: `tests/test_win_probability.py`.
- Modify: `docs/specs/2026-04-26-manager-mode/design.md` — note implementation details.

### Sub-tasks

- [ ] **3.1: Write failing tests for `pre_match_expected_outcome`**

Create `tests/test_win_probability.py`:

```python
from dodgeball_sim.models import CoachPolicy, Player, PlayerRatings, PlayerTraits, Team
from dodgeball_sim.win_probability import pre_match_expected_outcome


def _player(pid: str, ovr: float) -> Player:
    return Player(
        id=pid,
        name=pid.title(),
        ratings=PlayerRatings(accuracy=ovr, power=ovr, dodge=ovr, catch=ovr, stamina=ovr),
        traits=PlayerTraits(),
    )


def _team(tid: str, ovr: float, n: int = 6) -> Team:
    return Team(
        id=tid,
        name=tid.title(),
        players=tuple(_player(f"{tid}_{i}", ovr) for i in range(n)),
        coach_policy=CoachPolicy(),
        chemistry=0.5,
    )


def test_pre_match_expected_outcome_equal_teams_is_half():
    a = _team("a", 70)
    b = _team("b", 70)
    p = pre_match_expected_outcome(a, b)
    assert abs(p - 0.5) < 1e-9


def test_pre_match_expected_outcome_in_unit_interval():
    a = _team("a", 50)
    b = _team("b", 90)
    p = pre_match_expected_outcome(a, b)
    assert 0.0 <= p <= 1.0


def test_pre_match_expected_outcome_monotonicity():
    """Strictly stronger A → strictly higher p."""
    weak_a = _team("a", 50)
    strong_a = _team("a", 80)
    b = _team("b", 65)
    p_weak = pre_match_expected_outcome(weak_a, b)
    p_strong = pre_match_expected_outcome(strong_a, b)
    assert p_strong > p_weak


def test_pre_match_expected_outcome_symmetry():
    """Swapping teams returns 1 - p."""
    a = _team("a", 60)
    b = _team("b", 80)
    p_ab = pre_match_expected_outcome(a, b)
    p_ba = pre_match_expected_outcome(b, a)
    assert abs((p_ab + p_ba) - 1.0) < 1e-9


def test_pre_match_expected_outcome_deterministic():
    a = _team("a", 70)
    b = _team("b", 75)
    assert pre_match_expected_outcome(a, b) == pre_match_expected_outcome(a, b)
```

- [ ] **3.2: Run failing tests**

```bash
python -m pytest tests/test_win_probability.py -v
```

Expected: FAIL — module does not exist.

- [ ] **3.3: Implement `pre_match_expected_outcome`**

Create `src/dodgeball_sim/win_probability.py`:

```python
from __future__ import annotations

"""Post-hoc retrospective win-probability analyzer.

These functions are RETROSPECTIVE LEVERAGE ESTIMATES, not live predictions.
They are consumed post-match by Match Report (Turning Points, UPSET tag)
to explain what happened. The pre-match Match Preview screen MUST NOT
display these numbers — that constraint is part of the integrity contract
(see docs/specs/2026-04-26-manager-mode/design.md §6.4 and §8.3).

Model — pre_match_expected_outcome:
  Sigmoid on the average-rating difference between team A and team B
  rosters. Symmetric, monotonic, deterministic. The constant K is chosen
  so a 10-OVR gap reads roughly 65/35.

Model — per_event_wp_delta:
  Survivor-count-based WP. After each event we compute
    wp_a = sigmoid(K_SURV * (alive_a - alive_b))
  and emit the change vs the previous event. This is an intentionally
  simple model; its job is to mark moments of high leverage, not to
  predict outcomes precisely.
"""

import math
from typing import Iterable, List

from .events import MatchEvent
from .models import Team

_K_OVR = 0.06    # OVR-diff sensitivity for pre-match expected outcome
_K_SURV = 0.6   # survivor-diff sensitivity for in-match WP


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _team_average_overall(team: Team) -> float:
    if not team.players:
        return 0.0
    return sum(p.overall() for p in team.players) / len(team.players)


def pre_match_expected_outcome(team_a: Team, team_b: Team) -> float:
    """Return p(team_a wins), as a retrospective leverage baseline.

    NOT for live pre-match display. Only the post-match Report consumes this
    (to flag upsets).
    """
    diff = _team_average_overall(team_a) - _team_average_overall(team_b)
    return _sigmoid(_K_OVR * diff)


__all__ = ["pre_match_expected_outcome"]
```

- [ ] **3.4: Run pre-match tests**

```bash
python -m pytest tests/test_win_probability.py -v
```

Expected: all 5 pre-match tests PASS.

- [ ] **3.5: Write failing tests for `per_event_wp_delta`**

Add to `tests/test_win_probability.py`:

```python
from dodgeball_sim.events import MatchEvent
from dodgeball_sim.win_probability import per_event_wp_delta


def _throw_event(
    event_id: int,
    thrower: str,
    target: str,
    resolution: str,
    *,
    out_player: str | None = None,
    out_team: str | None = None,
) -> MatchEvent:
    """Build a minimal throw event for WP tests."""
    state_diff = {}
    if out_player and out_team:
        state_diff["player_out"] = {"player_id": out_player, "team": out_team}
    return MatchEvent(
        event_id=event_id,
        tick=event_id,
        seed=0,
        event_type="throw",
        phase="volley",
        actors={"thrower": thrower, "target": target},
        context={},
        probabilities={},
        rolls={},
        outcome={"resolution": resolution},
        state_diff=state_diff,
    )


def test_per_event_wp_delta_length_matches_events():
    events = [
        _throw_event(1, "a1", "b1", "miss"),
        _throw_event(2, "b1", "a1", "miss"),
    ]
    deltas = per_event_wp_delta(
        events,
        team_a_id="A",
        team_b_id="B",
        team_a_player_ids=["a1", "a2", "a3"],
        team_b_player_ids=["b1", "b2", "b3"],
    )
    assert len(deltas) == len(events)


def test_hit_against_team_a_lowers_a_wp():
    """An on-target hit that eliminates an A player should produce a
    negative delta from A's perspective."""
    events = [
        _throw_event(1, "b1", "a1", "hit", out_player="a1", out_team="A"),
    ]
    deltas = per_event_wp_delta(
        events,
        team_a_id="A",
        team_b_id="B",
        team_a_player_ids=["a1", "a2", "a3"],
        team_b_player_ids=["b1", "b2", "b3"],
    )
    assert deltas[0] < 0.0


def test_hit_against_team_b_raises_a_wp():
    events = [
        _throw_event(1, "a1", "b1", "hit", out_player="b1", out_team="B"),
    ]
    deltas = per_event_wp_delta(
        events,
        team_a_id="A",
        team_b_id="B",
        team_a_player_ids=["a1", "a2", "a3"],
        team_b_player_ids=["b1", "b2", "b3"],
    )
    assert deltas[0] > 0.0


def test_catch_by_a_raises_a_wp():
    """A catches B's throw — B's thrower (b1) is the eliminated player."""
    events = [
        _throw_event(1, "b1", "a1", "catch", out_player="b1", out_team="B"),
    ]
    deltas = per_event_wp_delta(
        events,
        team_a_id="A",
        team_b_id="B",
        team_a_player_ids=["a1", "a2", "a3"],
        team_b_player_ids=["b1", "b2", "b3"],
    )
    assert deltas[0] > 0.0


def test_per_event_wp_delta_deterministic():
    events = [
        _throw_event(1, "b1", "a1", "hit", out_player="a1", out_team="A"),
        _throw_event(2, "a2", "b1", "hit", out_player="b1", out_team="B"),
    ]
    args = dict(
        team_a_id="A",
        team_b_id="B",
        team_a_player_ids=["a1", "a2", "a3"],
        team_b_player_ids=["b1", "b2", "b3"],
    )
    assert per_event_wp_delta(events, **args) == per_event_wp_delta(events, **args)


def test_per_event_wp_delta_symmetry():
    """Same physical event, but evaluated from B's perspective, must produce
    deltas with flipped signs."""
    events = [
        _throw_event(1, "b1", "a1", "hit", out_player="a1", out_team="A"),
    ]
    a_view = per_event_wp_delta(
        events,
        team_a_id="A",
        team_b_id="B",
        team_a_player_ids=["a1", "a2", "a3"],
        team_b_player_ids=["b1", "b2", "b3"],
    )
    b_view = per_event_wp_delta(
        events,
        team_a_id="B",
        team_b_id="A",
        team_a_player_ids=["b1", "b2", "b3"],
        team_b_player_ids=["a1", "a2", "a3"],
    )
    assert abs(a_view[0] + b_view[0]) < 1e-9
```

- [ ] **3.6: Run failing per-event tests**

```bash
python -m pytest tests/test_win_probability.py -v
```

Expected: 6 new tests FAIL — `per_event_wp_delta` not defined.

- [ ] **3.7: Implement `per_event_wp_delta`**

Add to `src/dodgeball_sim/win_probability.py` (after `pre_match_expected_outcome`):

```python
def per_event_wp_delta(
    events: Iterable[MatchEvent],
    team_a_id: str,
    team_b_id: str,
    team_a_player_ids: List[str],
    team_b_player_ids: List[str],
) -> List[float]:
    """Return the per-event WP delta from team_a's perspective.

    Survivor-count-based: after each event, recompute
      wp_a = sigmoid(K_SURV * (alive_a - alive_b))
    and emit (wp_a_after - wp_a_before).

    Length of the returned list equals len(events).
    """
    alive_a = set(team_a_player_ids)
    alive_b = set(team_b_player_ids)

    def _wp_a() -> float:
        return _sigmoid(_K_SURV * (len(alive_a) - len(alive_b)))

    deltas: List[float] = []
    wp_before = _wp_a()
    for event in events:
        elim = event.state_diff.get("player_out")
        if elim:
            pid = elim.get("player_id")
            team = elim.get("team")
            if team == team_a_id:
                alive_a.discard(pid)
            elif team == team_b_id:
                alive_b.discard(pid)
        wp_after = _wp_a()
        deltas.append(wp_after - wp_before)
        wp_before = wp_after
    return deltas
```

Update `__all__`:

```python
__all__ = ["pre_match_expected_outcome", "per_event_wp_delta"]
```

- [ ] **3.8: Run per-event tests**

```bash
python -m pytest tests/test_win_probability.py -v
```

Expected: all 11 tests PASS.

- [ ] **3.9: Run full suite to confirm no regression**

```bash
python -m pytest -q
```

Expected: PASS at the prior baseline + new tests count.

- [ ] **3.10: Commit Task 3**

```bash
git add src/dodgeball_sim/win_probability.py tests/test_win_probability.py
git commit -m "$(cat <<'EOF'
feat(m0): add post-hoc win-probability analyzer

Manager Mode Milestone 0 deliverable §2.5.4. New module
win_probability.py exposes:

  pre_match_expected_outcome(team_a, team_b) -> float
    Sigmoid on average-OVR difference. Used POST-MATCH only, by
    Match Report's UPSET tag. Pre-match Match Preview never reads
    this — that's the integrity contract.

  per_event_wp_delta(events, ...) -> List[float]
    Survivor-count-based per-event leverage. Sums approximately
    reflect outcome direction.

Tests cover monotonicity, symmetry, determinism, and direction-of-
swing for hits and catches, matching AGENTS.md §1 invariants.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Lineup Persistence + LineupResolver + Match-Builder Integration

**Spec ref:** §2.5.3.

**Lineup contract (locked here for v1):**
- A lineup is an **ordered list of player IDs** for a club.
- The first `STARTERS_COUNT` (default 6) are starters; the rest is bench. The engine match snapshot uses the full ordered list (today's behavior); the starters/bench split is a UI concern. The contract reserves the rule so future engine work can act on it without renegotiating.
- A club has at most one **default lineup** (`lineup_default`).
- Each match can have at most one **per-match override** (`match_lineup_override`).
- **Resolution order:** override → default → "highest-OVR remaining roster" backfill.
- **Invalid players** (in the lineup but no longer on the roster — retired, released) are silently dropped on resolution. The resolver returns the remaining valid IDs in original order, then back-fills from highest-OVR roster players not yet listed until the lineup reaches `len(roster)` or `STARTERS_COUNT`, whichever applies.

**Files:**
- Create: `src/dodgeball_sim/lineup.py`.
- Modify: `src/dodgeball_sim/persistence.py` — add `_migrate_v7`, register it, bump `CURRENT_SCHEMA_VERSION` to `7`. Add `save_lineup_default`, `load_lineup_default`, `save_match_lineup_override`, `load_match_lineup_override`.
- Modify: `src/dodgeball_sim/franchise.py:101-165` — `simulate_match` calls `LineupResolver.resolve(...)` instead of using `[p.id for p in roster]` directly.
- Create: `tests/test_lineup.py`.
- Modify: `tests/test_persistence.py` — round-trip tests for new persistence functions + v7 migration.

### Sub-tasks

- [ ] **4.1: Write failing tests for `LineupResolver`**

Create `tests/test_lineup.py`:

```python
from dodgeball_sim.lineup import STARTERS_COUNT, LineupResolver
from dodgeball_sim.models import Player, PlayerRatings, PlayerTraits


def _p(pid: str, ovr: float = 60.0) -> Player:
    return Player(
        id=pid,
        name=pid.title(),
        ratings=PlayerRatings(accuracy=ovr, power=ovr, dodge=ovr, catch=ovr, stamina=ovr),
        traits=PlayerTraits(),
    )


def test_resolve_default_falls_back_to_roster_order_when_no_default():
    roster = [_p("a"), _p("b"), _p("c")]
    resolver = LineupResolver()
    assert resolver.resolve(roster=roster, default=None, override=None) == ["a", "b", "c"]


def test_resolve_uses_default_when_no_override():
    roster = [_p("a"), _p("b"), _p("c")]
    resolver = LineupResolver()
    assert resolver.resolve(roster=roster, default=["b", "a", "c"], override=None) == ["b", "a", "c"]


def test_resolve_override_beats_default():
    roster = [_p("a"), _p("b"), _p("c")]
    resolver = LineupResolver()
    assert resolver.resolve(
        roster=roster,
        default=["b", "a", "c"],
        override=["c", "a", "b"],
    ) == ["c", "a", "b"]


def test_resolve_drops_invalid_player_ids_silently():
    """A retired/released player ID in the default must be dropped, then
    backfilled from the highest-OVR remaining roster member."""
    roster = [_p("a", 70), _p("b", 80), _p("c", 50), _p("d", 90)]
    resolver = LineupResolver()
    # Default mentions "ghost" who is no longer on the roster. The resolver
    # drops "ghost", keeps "a", "c" in order, then backfills with the
    # highest-OVR remaining (d, then b).
    result = resolver.resolve(
        roster=roster,
        default=["ghost", "a", "c"],
        override=None,
    )
    assert result[:2] == ["a", "c"]
    assert result[2:] == ["d", "b"]  # backfill order: d (90) then b (80)


def test_resolve_returns_invalid_flag_when_default_was_partially_invalid():
    """The resolver also reports whether it had to drop invalid IDs, so the
    UI can flag 'lineup default needs attention'."""
    roster = [_p("a"), _p("b")]
    resolver = LineupResolver()
    out = resolver.resolve_with_diagnostics(
        roster=roster,
        default=["ghost", "a", "b"],
        override=None,
    )
    assert out.lineup == ["a", "b"]
    assert out.dropped_ids == ["ghost"]


def test_starters_count_is_six():
    """Documented v1 default. UI starter/bench split uses this."""
    assert STARTERS_COUNT == 6
```

- [ ] **4.2: Run failing lineup tests**

```bash
python -m pytest tests/test_lineup.py -v
```

Expected: FAIL — module does not exist.

- [ ] **4.3: Implement `LineupResolver`**

Create `src/dodgeball_sim/lineup.py`:

```python
from __future__ import annotations

"""Lineup resolution for Manager Mode.

A lineup is an ordered list of player IDs. The engine consumes the full
ordered list when building a match snapshot. The starter/bench split
(STARTERS_COUNT) is a UI presentation concern; the contract reserves
the rule so future engine logic can act on it without renegotiating.

Resolution order:
  override (per-match) → default (per-club) → roster order
Invalid IDs (no longer on the roster — retired/released) are dropped
silently in original order, then back-filled from the highest-OVR
remaining roster members.

Manager Mode Milestone 0 deliverable §2.5.3.
"""

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .models import Player

STARTERS_COUNT = 6


@dataclass(frozen=True)
class ResolvedLineup:
    """Lineup with diagnostics about what was dropped during resolution."""
    lineup: List[str]
    dropped_ids: List[str]


class LineupResolver:
    """Resolve a club's effective lineup for a match.

    Use ``resolve`` for the simple "give me the IDs" path. Use
    ``resolve_with_diagnostics`` when the UI needs to know that the
    default lineup contained invalid players (so it can surface a
    "default needs attention" reminder on the Hub).
    """

    def resolve(
        self,
        roster: Sequence[Player],
        default: Optional[Sequence[str]],
        override: Optional[Sequence[str]],
    ) -> List[str]:
        return self.resolve_with_diagnostics(roster, default, override).lineup

    def resolve_with_diagnostics(
        self,
        roster: Sequence[Player],
        default: Optional[Sequence[str]],
        override: Optional[Sequence[str]],
    ) -> ResolvedLineup:
        roster_ids = {p.id for p in roster}
        roster_by_id = {p.id: p for p in roster}

        chosen: Sequence[str]
        if override is not None:
            chosen = override
        elif default is not None:
            chosen = default
        else:
            chosen = [p.id for p in roster]

        kept: List[str] = []
        dropped: List[str] = []
        seen: set[str] = set()
        for pid in chosen:
            if pid in roster_ids and pid not in seen:
                kept.append(pid)
                seen.add(pid)
            else:
                if pid not in roster_ids:
                    dropped.append(pid)

        if len(kept) < len(roster):
            remaining = [p for p in roster if p.id not in seen]
            remaining.sort(key=lambda p: (-p.overall(), p.id))
            for p in remaining:
                kept.append(p.id)
                seen.add(p.id)

        return ResolvedLineup(lineup=kept, dropped_ids=dropped)


__all__ = ["STARTERS_COUNT", "LineupResolver", "ResolvedLineup"]
```

- [ ] **4.4: Run lineup tests**

```bash
python -m pytest tests/test_lineup.py -v
```

Expected: all 6 tests PASS.

- [ ] **4.5: Write failing tests for v7 migration + lineup persistence**

Add to `tests/test_persistence.py`:

```python
from dodgeball_sim.persistence import (
    load_lineup_default,
    load_match_lineup_override,
    save_lineup_default,
    save_match_lineup_override,
)


def test_current_schema_version_is_seven():
    assert CURRENT_SCHEMA_VERSION == 7


def test_v7_creates_lineup_tables():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name IN ('lineup_default', 'match_lineup_override')"
    )
    names = {row["name"] for row in cursor.fetchall()}
    assert names == {"lineup_default", "match_lineup_override"}


def test_save_load_lineup_default_roundtrip():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    save_lineup_default(conn, "aurora", ["p3", "p1", "p4", "p1"])  # dup p1 should still serialize
    loaded = load_lineup_default(conn, "aurora")
    assert loaded == ["p3", "p1", "p4", "p1"]


def test_load_lineup_default_returns_none_when_absent():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    assert load_lineup_default(conn, "no_such_club") is None


def test_save_load_match_lineup_override_roundtrip():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    save_match_lineup_override(conn, "match_42", "aurora", ["p2", "p1"])
    loaded = load_match_lineup_override(conn, "match_42", "aurora")
    assert loaded == ["p2", "p1"]


def test_load_match_lineup_override_returns_none_when_absent():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    assert load_match_lineup_override(conn, "match_99", "aurora") is None
```

- [ ] **4.6: Run failing lineup persistence tests**

```bash
python -m pytest tests/test_persistence.py::test_current_schema_version_is_seven tests/test_persistence.py::test_v7_creates_lineup_tables -v
```

Expected: FAIL — `CURRENT_SCHEMA_VERSION == 6`, lineup tables don't exist, `load_lineup_default` not exported.

- [ ] **4.7: Add `_migrate_v7` and bump `CURRENT_SCHEMA_VERSION` to 7**

In `src/dodgeball_sim/persistence.py`:

```python
CURRENT_SCHEMA_VERSION = 7
```

After `_migrate_v6`, add:

```python
def _migrate_v7(conn: sqlite3.Connection) -> None:
    """Manager Mode M0: lineup persistence — per-club default and per-match override."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS lineup_default (
            club_id TEXT PRIMARY KEY,
            ordered_player_ids_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS match_lineup_override (
            match_id TEXT NOT NULL,
            club_id TEXT NOT NULL,
            ordered_player_ids_json TEXT NOT NULL,
            PRIMARY KEY (match_id, club_id)
        );
        """
    )
```

Register in `_MIGRATIONS`:

```python
_MIGRATIONS: Dict[int, Any] = {
    1: _migrate_v1,
    2: _migrate_v2,
    3: _migrate_v3,
    4: _migrate_v4,
    5: _migrate_v5,
    6: _migrate_v6,
    7: _migrate_v7,
}
```

- [ ] **4.8: Add lineup save/load functions**

In `src/dodgeball_sim/persistence.py`, after the existing `load_all_rosters` function (around line 715), add:

```python
def save_lineup_default(
    conn: sqlite3.Connection,
    club_id: str,
    ordered_player_ids: List[str],
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO lineup_default
            (club_id, ordered_player_ids_json, updated_at)
        VALUES (?, ?, ?)
        """,
        (club_id, _json_dump(list(ordered_player_ids)), _utcnow_iso()),
    )


def load_lineup_default(
    conn: sqlite3.Connection,
    club_id: str,
) -> Optional[List[str]]:
    row = conn.execute(
        "SELECT ordered_player_ids_json FROM lineup_default WHERE club_id = ?",
        (club_id,),
    ).fetchone()
    if row is None:
        return None
    return list(json.loads(row["ordered_player_ids_json"]))


def save_match_lineup_override(
    conn: sqlite3.Connection,
    match_id: str,
    club_id: str,
    ordered_player_ids: List[str],
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO match_lineup_override
            (match_id, club_id, ordered_player_ids_json)
        VALUES (?, ?, ?)
        """,
        (match_id, club_id, _json_dump(list(ordered_player_ids))),
    )


def load_match_lineup_override(
    conn: sqlite3.Connection,
    match_id: str,
    club_id: str,
) -> Optional[List[str]]:
    row = conn.execute(
        """
        SELECT ordered_player_ids_json FROM match_lineup_override
        WHERE match_id = ? AND club_id = ?
        """,
        (match_id, club_id),
    ).fetchone()
    if row is None:
        return None
    return list(json.loads(row["ordered_player_ids_json"]))
```

Add the four function names to the `__all__` list at the bottom of `persistence.py`.

- [ ] **4.9: Run lineup persistence tests**

```bash
python -m pytest tests/test_persistence.py -v
```

Expected: all PASS, including the v7 migration tests.

- [ ] **4.10: Wire `LineupResolver` into `franchise.simulate_match`**

In `src/dodgeball_sim/franchise.py`, replace the `simulate_match` function so it accepts optional `home_lineup_default`, `away_lineup_default`, `home_lineup_override`, `away_lineup_override` arguments and uses `LineupResolver`.

Replace lines 101–165 (the `simulate_match` function) with:

```python
def simulate_match(
    scheduled: ScheduledMatch,
    home_club: Club,
    away_club: Club,
    home_roster: List[Player],
    away_roster: List[Player],
    root_seed: int,
    config_version: str = "phase1.v1",
    difficulty: str = "pro",
    meta_patch: MetaPatch | None = None,
    home_lineup_default: Optional[List[str]] = None,
    away_lineup_default: Optional[List[str]] = None,
    home_lineup_override: Optional[List[str]] = None,
    away_lineup_override: Optional[List[str]] = None,
) -> Tuple[MatchRecord, SeasonResult]:
    """Run one match and produce a MatchRecord + SeasonResult. Pure computation.

    Lineup resolution: override → default → roster order. When all four
    lineup args are None, the result is identical to pre-M0 behavior
    (full roster in roster order), so existing callers and the Phase 1
    golden log are unaffected.
    """
    from .lineup import LineupResolver  # local import to avoid cycle on cold imports

    resolver = LineupResolver()
    home_lineup = resolver.resolve(home_roster, home_lineup_default, home_lineup_override)
    away_lineup = resolver.resolve(away_roster, away_lineup_default, away_lineup_override)

    match_seed = derive_seed(root_seed, "match", scheduled.match_id)

    home_team = build_match_team_snapshot(home_club, home_roster, home_lineup)
    away_team = build_match_team_snapshot(away_club, away_roster, away_lineup)

    setup = MatchSetup(team_a=home_team, team_b=away_team, config_version=config_version)
    engine = MatchEngine()
    result = engine.run(setup, seed=match_seed, difficulty=difficulty, meta_patch=meta_patch)

    home_hash = _hash_players(home_roster)
    away_hash = _hash_players(away_roster)
    event_hash = _hash_events(result)
    final_hash = hashlib.sha256(
        json.dumps(result.box_score, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()[:16]

    box = result.box_score["teams"]
    home_survivors = box[home_club.club_id]["totals"]["living"]
    away_survivors = box[away_club.club_id]["totals"]["living"]
    winner_club_id = result.winner_team_id

    record = MatchRecord(
        match_id=scheduled.match_id,
        season_id=scheduled.season_id,
        week=scheduled.week,
        home_club_id=scheduled.home_club_id,
        away_club_id=scheduled.away_club_id,
        home_roster_hash=home_hash,
        away_roster_hash=away_hash,
        config_version=config_version,
        ruleset_version="default.v1",
        meta_patch_id=None if meta_patch is None else meta_patch.patch_id,
        seed=match_seed,
        event_log_hash=event_hash,
        final_state_hash=final_hash,
        engine_match_id=None,
        result=result,
    )

    season_result = SeasonResult(
        match_id=scheduled.match_id,
        season_id=scheduled.season_id,
        week=scheduled.week,
        home_club_id=scheduled.home_club_id,
        away_club_id=scheduled.away_club_id,
        home_survivors=home_survivors,
        away_survivors=away_survivors,
        winner_club_id=winner_club_id,
        seed=match_seed,
    )

    return record, season_result
```

Note: leave `simulate_matchday` and `simulate_full_season` calls unchanged for now; they will keep using the no-lineup path (full roster). UI integration in M1 will pass lineups through.

- [ ] **4.11: Run regression test to confirm engine output is unchanged**

```bash
python -m pytest tests/test_regression.py -v
```

Expected: PASS. Default-arg behavior produces `[p.id for p in roster]` lineup, which matches pre-M0 behavior.

- [ ] **4.12: Run dynasty persistence tests**

```bash
python -m pytest tests/test_dynasty_persistence.py tests/test_phase3_persistence.py -v
```

Expected: PASS — `simulate_match` callers in those tests use only the required args.

- [ ] **4.13: Add a lineup-aware integration test**

Add to `tests/test_lineup.py`:

```python
def test_resolver_invalid_then_backfill_round_trip():
    """End-to-end: a default with an invalid ID still produces a usable
    lineup ordered with the invalid ID dropped and the highest-OVR
    backfill appended."""
    roster = [_p("a", 70), _p("b", 80), _p("c", 50), _p("d", 90)]
    resolver = LineupResolver()
    out = resolver.resolve_with_diagnostics(
        roster=roster,
        default=["a", "ghost"],
        override=None,
    )
    assert out.lineup == ["a", "d", "b", "c"]
    assert out.dropped_ids == ["ghost"]
```

```bash
python -m pytest tests/test_lineup.py::test_resolver_invalid_then_backfill_round_trip -v
```

Expected: PASS.

- [ ] **4.14: Run full suite**

```bash
python -m pytest -q
```

Expected: PASS at the prior baseline + new tests.

- [ ] **4.15: Commit Task 4**

```bash
git add src/dodgeball_sim/lineup.py src/dodgeball_sim/persistence.py src/dodgeball_sim/franchise.py tests/test_lineup.py tests/test_persistence.py
git commit -m "$(cat <<'EOF'
feat(m0): lineup persistence + LineupResolver + simulate_match wiring

Manager Mode Milestone 0 deliverable §2.5.3. Adds:

- src/dodgeball_sim/lineup.py: LineupResolver with override → default →
  roster-order resolution, invalid-ID drop + highest-OVR backfill,
  ResolvedLineup diagnostic for UI 'lineup needs attention' flag.
  STARTERS_COUNT = 6 (UI-only contract for v1; engine still uses
  full ordered list in match snapshot).
- Schema v7 migration adds lineup_default and match_lineup_override
  tables. save/load helpers for both.
- franchise.simulate_match accepts optional lineup args and routes
  through LineupResolver. Default behavior with all-None lineup args
  is bit-identical to pre-M0; phase1 golden log unchanged.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Career State Machine

**Spec ref:** §12.6.

**Architecture decision:** the state machine lives in a new module `career_state.py`. State persistence reuses the existing `dynasty_state` key-value table from migration v2 (single key `career_state_cursor`, JSON value). No new migration required.

**Files:**
- Create: `src/dodgeball_sim/career_state.py`.
- Modify: `src/dodgeball_sim/persistence.py` — add `save_career_state_cursor` / `load_career_state_cursor` (reusing the `dynasty_state` table).
- Create: `tests/test_career_state.py`.

### Sub-tasks

- [ ] **5.1: Write failing tests for `CareerState` enum and `CareerStateCursor` dataclass**

Create `tests/test_career_state.py`:

```python
import pytest

from dodgeball_sim.career_state import (
    CareerState,
    CareerStateCursor,
    InvalidTransitionError,
    advance,
)


def test_career_state_enum_has_all_seven_states():
    expected = {
        "splash",
        "season_active_pre_match",
        "season_active_in_match",
        "season_active_match_report_pending",
        "season_complete_offseason_beat",
        "season_complete_recruitment_pending",
        "next_season_ready",
    }
    assert {s.value for s in CareerState} == expected


def test_cursor_defaults():
    cursor = CareerStateCursor(state=CareerState.SPLASH)
    assert cursor.state == CareerState.SPLASH
    assert cursor.season_number == 0
    assert cursor.week == 0
    assert cursor.offseason_beat_index == 0
    assert cursor.match_id is None
```

- [ ] **5.2: Run failing tests**

```bash
python -m pytest tests/test_career_state.py -v
```

Expected: FAIL — module does not exist.

- [ ] **5.3: Implement `CareerState` enum and `CareerStateCursor`**

Create `src/dodgeball_sim/career_state.py`:

```python
from __future__ import annotations

"""Career state machine for Manager Mode.

Centralizes the save/resume contract so screens never need ad-hoc state
checks. Every UI surface reads (state, payload) from a CareerStateCursor.

Spec: docs/specs/2026-04-26-manager-mode/design.md §12.6.

States and transitions are defined in TRANSITIONS below. Use advance()
to move forward; it raises InvalidTransitionError if the requested
transition is not in the table.
"""

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Optional, Set, Tuple


class CareerState(str, Enum):
    SPLASH = "splash"
    SEASON_ACTIVE_PRE_MATCH = "season_active_pre_match"
    SEASON_ACTIVE_IN_MATCH = "season_active_in_match"
    SEASON_ACTIVE_MATCH_REPORT_PENDING = "season_active_match_report_pending"
    SEASON_COMPLETE_OFFSEASON_BEAT = "season_complete_offseason_beat"
    SEASON_COMPLETE_RECRUITMENT_PENDING = "season_complete_recruitment_pending"
    NEXT_SEASON_READY = "next_season_ready"


@dataclass(frozen=True)
class CareerStateCursor:
    """Persisted career position. Stored as JSON in the dynasty_state KV table."""
    state: CareerState
    season_number: int = 0           # 0 before any career has started; 1+ in a career
    week: int = 0                    # current week within the season; 0 between seasons
    offseason_beat_index: int = 0    # 0..N-1 across the v1 7-beat ceremony
    match_id: Optional[str] = None   # set when in IN_MATCH or REPORT_PENDING


class InvalidTransitionError(RuntimeError):
    pass


# (from_state, to_state) → True iff transition is allowed
_ALLOWED: Set[Tuple[CareerState, CareerState]] = {
    (CareerState.SPLASH, CareerState.SEASON_ACTIVE_PRE_MATCH),
    (CareerState.SEASON_ACTIVE_PRE_MATCH, CareerState.SEASON_ACTIVE_IN_MATCH),
    (CareerState.SEASON_ACTIVE_IN_MATCH, CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING),
    (CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING, CareerState.SEASON_ACTIVE_PRE_MATCH),
    (CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT),
    (CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT),
    (CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING),
    (CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING, CareerState.NEXT_SEASON_READY),
    (CareerState.NEXT_SEASON_READY, CareerState.SEASON_ACTIVE_PRE_MATCH),
}


def can_transition(from_state: CareerState, to_state: CareerState) -> bool:
    return (from_state, to_state) in _ALLOWED


def advance(cursor: CareerStateCursor, to_state: CareerState, **payload_updates) -> CareerStateCursor:
    """Return a new cursor at to_state with payload updates applied.

    Raises InvalidTransitionError if (cursor.state, to_state) is not in
    the allowed transition table.
    """
    if not can_transition(cursor.state, to_state):
        raise InvalidTransitionError(
            f"Cannot transition {cursor.state.value} → {to_state.value}"
        )
    return replace(cursor, state=to_state, **payload_updates)


__all__ = [
    "CareerState",
    "CareerStateCursor",
    "InvalidTransitionError",
    "advance",
    "can_transition",
]
```

- [ ] **5.4: Run enum/cursor tests**

```bash
python -m pytest tests/test_career_state.py -v
```

Expected: PASS.

- [ ] **5.5: Write failing tests for valid transitions**

Add to `tests/test_career_state.py`:

```python
@pytest.mark.parametrize(
    "from_state,to_state",
    [
        (CareerState.SPLASH, CareerState.SEASON_ACTIVE_PRE_MATCH),
        (CareerState.SEASON_ACTIVE_PRE_MATCH, CareerState.SEASON_ACTIVE_IN_MATCH),
        (CareerState.SEASON_ACTIVE_IN_MATCH, CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING),
        (CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING, CareerState.SEASON_ACTIVE_PRE_MATCH),
        (CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT),
        (CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT),
        (CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING),
        (CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING, CareerState.NEXT_SEASON_READY),
        (CareerState.NEXT_SEASON_READY, CareerState.SEASON_ACTIVE_PRE_MATCH),
    ],
)
def test_allowed_transitions(from_state, to_state):
    cursor = CareerStateCursor(state=from_state)
    new_cursor = advance(cursor, to_state)
    assert new_cursor.state == to_state


def test_disallowed_transition_raises():
    cursor = CareerStateCursor(state=CareerState.SPLASH)
    with pytest.raises(InvalidTransitionError):
        advance(cursor, CareerState.SEASON_ACTIVE_IN_MATCH)


def test_advance_applies_payload_updates():
    cursor = CareerStateCursor(state=CareerState.SEASON_ACTIVE_PRE_MATCH, week=3)
    new_cursor = advance(
        cursor,
        CareerState.SEASON_ACTIVE_IN_MATCH,
        match_id="s1_w3_aurora_vs_lunar",
    )
    assert new_cursor.match_id == "s1_w3_aurora_vs_lunar"
    assert new_cursor.week == 3  # unchanged


def test_advance_match_report_to_pre_match_advances_week():
    """Caller is responsible for bumping week when crossing
    REPORT_PENDING → PRE_MATCH (the transition is allowed; the cursor
    bookkeeping is the caller's concern, demonstrated here)."""
    cursor = CareerStateCursor(
        state=CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING, week=3,
    )
    new_cursor = advance(
        cursor,
        CareerState.SEASON_ACTIVE_PRE_MATCH,
        week=cursor.week + 1,
        match_id=None,
    )
    assert new_cursor.week == 4
    assert new_cursor.match_id is None
```

- [ ] **5.6: Run transition tests**

```bash
python -m pytest tests/test_career_state.py -v
```

Expected: PASS — all transitions resolve correctly, disallowed one raises.

- [ ] **5.7: Write failing tests for cursor persistence**

Add to `tests/test_career_state.py`:

```python
import sqlite3

from dodgeball_sim.persistence import (
    create_schema,
    load_career_state_cursor,
    save_career_state_cursor,
)


def test_career_state_cursor_roundtrip():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    cursor = CareerStateCursor(
        state=CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING,
        season_number=2,
        week=7,
        offseason_beat_index=0,
        match_id="s2_w7_aurora_vs_lunar",
    )
    save_career_state_cursor(conn, cursor)
    loaded = load_career_state_cursor(conn)

    assert loaded == cursor


def test_load_career_state_cursor_returns_splash_when_absent():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    loaded = load_career_state_cursor(conn)
    assert loaded.state == CareerState.SPLASH
    assert loaded.season_number == 0
```

- [ ] **5.8: Run failing persistence tests**

```bash
python -m pytest tests/test_career_state.py::test_career_state_cursor_roundtrip tests/test_career_state.py::test_load_career_state_cursor_returns_splash_when_absent -v
```

Expected: FAIL — `save_career_state_cursor` / `load_career_state_cursor` not exported.

- [ ] **5.9: Add cursor save/load to `persistence.py`**

In `src/dodgeball_sim/persistence.py`, add at the bottom (before `__all__`):

```python
# ---------------------------------------------------------------------------
# Career state cursor (Manager Mode M0) — stored in dynasty_state KV table
# ---------------------------------------------------------------------------

_CAREER_STATE_KEY = "career_state_cursor"


def save_career_state_cursor(conn: sqlite3.Connection, cursor: "CareerStateCursor") -> None:
    """Persist the career state cursor as JSON in the dynasty_state KV row."""
    payload = {
        "state": cursor.state.value,
        "season_number": cursor.season_number,
        "week": cursor.week,
        "offseason_beat_index": cursor.offseason_beat_index,
        "match_id": cursor.match_id,
    }
    conn.execute(
        "INSERT OR REPLACE INTO dynasty_state (key, value) VALUES (?, ?)",
        (_CAREER_STATE_KEY, _json_dump(payload)),
    )


def load_career_state_cursor(conn: sqlite3.Connection) -> "CareerStateCursor":
    """Load the cursor. Returns a SPLASH cursor if no state is persisted yet."""
    from .career_state import CareerState, CareerStateCursor

    row = conn.execute(
        "SELECT value FROM dynasty_state WHERE key = ?",
        (_CAREER_STATE_KEY,),
    ).fetchone()
    if row is None:
        return CareerStateCursor(state=CareerState.SPLASH)
    payload = json.loads(row["value"])
    return CareerStateCursor(
        state=CareerState(payload["state"]),
        season_number=payload.get("season_number", 0),
        week=payload.get("week", 0),
        offseason_beat_index=payload.get("offseason_beat_index", 0),
        match_id=payload.get("match_id"),
    )
```

Also add a `TYPE_CHECKING` import for the type-hint ergonomics (optional but cleaner):

At the top of `persistence.py`, in the existing `from typing import` line, ensure `TYPE_CHECKING` is imported, then add:

```python
if TYPE_CHECKING:
    from .career_state import CareerStateCursor
```

Add the new function names to the `__all__` list.

- [ ] **5.10: Run cursor persistence tests**

```bash
python -m pytest tests/test_career_state.py -v
```

Expected: all PASS.

- [ ] **5.11: Run full suite**

```bash
python -m pytest -q
```

Expected: PASS.

- [ ] **5.12: Commit Task 5**

```bash
git add src/dodgeball_sim/career_state.py src/dodgeball_sim/persistence.py tests/test_career_state.py
git commit -m "$(cat <<'EOF'
feat(m0): career state machine + cursor persistence

Manager Mode Milestone 0 deliverable §12.6. Adds:

- src/dodgeball_sim/career_state.py: CareerState (7 states),
  CareerStateCursor (frozen dataclass payload), advance() with
  whitelisted transitions table, InvalidTransitionError on disallowed
  moves. Replace-style cursor updates so persisted state is immutable.
- save_career_state_cursor / load_career_state_cursor in persistence.py,
  reusing the dynasty_state KV table from schema v2 (no migration).
  load_career_state_cursor returns a SPLASH cursor on a fresh DB so
  every screen has a defined starting position.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Scheduler Verification + v1 Fallback Documentation

**Spec ref:** §2.5.8.

This deliverable is verification + documentation, not implementation. The current `scheduler.py` exposes only `generate_round_robin`; there is no playoff bracket function. v1 will ship with regular-season-by-record champion.

**Files:**
- Modify: `src/dodgeball_sim/scheduler.py` — module-level docstring documenting v1 status; small `season_format_summary()` helper for UI consumption.
- Modify: `tests/test_scheduler.py` — add a test asserting the format produced (round-robin, no playoffs).
- Modify: `docs/specs/2026-04-26-manager-mode/design.md` — mark §2.5.8 verified.

### Sub-tasks

- [ ] **6.1: Inspect `scheduler.py` for any playoff/bracket code**

```bash
grep -n "playoff\|bracket\|elimination\|final" "C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/scheduler.py"
```

Expected: no matches. The module is round-robin only.

- [ ] **6.2: Write failing test for `season_format_summary`**

Add to `tests/test_scheduler.py`:

```python
from dodgeball_sim.scheduler import season_format_summary


def test_season_format_summary_documents_round_robin_only():
    summary = season_format_summary()
    assert summary["format"] == "round_robin"
    assert summary["playoffs"] is False
    assert summary["champion_rule"] == "best_regular_season_record"
```

- [ ] **6.3: Run failing test**

```bash
python -m pytest tests/test_scheduler.py::test_season_format_summary_documents_round_robin_only -v
```

Expected: FAIL — `season_format_summary` not exported.

- [ ] **6.4: Add `season_format_summary` and update the module docstring**

Edit `src/dodgeball_sim/scheduler.py`. Replace the top of the file (above `from __future__`):

```python
"""Season scheduling.

v1 status (Manager Mode Milestone 0, verified 2026-04-26):
  - Single round-robin only (every club plays every other club exactly once).
  - No playoffs. No elimination bracket. No tiebreaker games.
  - Season champion = best regular-season record (handled by Match Report
    standings logic, not the scheduler).
  - Odd club counts get a bye round (currently unimplemented per the
    generate_round_robin caller contract — caller ensures even counts).

If a future milestone adds playoffs, extend this module with a separate
playoff bracket function plus tests and update season_format_summary().
"""
from __future__ import annotations
```

Then add this function near the bottom, before `__all__`:

```python
def season_format_summary() -> Dict[str, Any]:
    """Return a small dict describing the v1 season format for UI consumption.

    UI screens (Schedule, Standings) call this to label things correctly,
    so when the format ever changes the UI updates without separate edits.
    """
    return {
        "format": "round_robin",
        "playoffs": False,
        "champion_rule": "best_regular_season_record",
    }
```

Add the import at the top of the file:

```python
from typing import Any, Dict, List
```

(Keep the existing `List` import — replace the existing `from typing import List` line.)

Update `__all__`:

```python
__all__ = ["ScheduledMatch", "generate_round_robin", "season_format_summary"]
```

- [ ] **6.5: Run scheduler tests**

```bash
python -m pytest tests/test_scheduler.py -v
```

Expected: PASS, including any pre-existing tests untouched.

- [ ] **6.6: Mark §2.5.8 verified in the design spec**

Edit `docs/specs/2026-04-26-manager-mode/design.md`. Find §2.5.8 and replace its body:

```markdown
### 2.5.8 Playoff support in `scheduler.py`

**Status (M0 verified):** No playoff support. `scheduler.py` exposes only `generate_round_robin`. v1 ships regular-season-by-record champion. The module's top-level docstring now documents this status, and `season_format_summary()` returns a UI-consumable dict (`{"format": "round_robin", "playoffs": False, "champion_rule": "best_regular_season_record"}`) that the Schedule and Standings screens read so the labeling stays accurate when playoffs eventually land.
```

- [ ] **6.7: Run full suite**

```bash
python -m pytest -q
```

Expected: PASS.

- [ ] **6.8: Commit Task 6**

```bash
git add src/dodgeball_sim/scheduler.py tests/test_scheduler.py docs/specs/2026-04-26-manager-mode/design.md
git commit -m "$(cat <<'EOF'
docs(m0): document scheduler v1 format + add season_format_summary

Manager Mode Milestone 0 deliverable §2.5.8. Verified scheduler.py
has no playoff support — single round-robin only. Module docstring
documents v1 status. New season_format_summary() helper returns a
UI-consumable dict so future playoff support can update one place
and have the UI labeling follow.

Marks §2.5.8 verified in the design spec.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Milestone 0 Closeout

**Files:**
- Modify: `docs/specs/2026-04-26-manager-mode/design.md` — flip §2.5 summary table statuses to ✅ for the v1-required rows.

### Sub-tasks

- [ ] **7.1: Update the §2.5.9 summary table**

Edit `docs/specs/2026-04-26-manager-mode/design.md`. Find the summary table in §2.5.9 and update the v1 status column for the M0 deliverables:

```markdown
| Dependency | Size | v1 status | v2+ status |
|---|---|---|---|
| `Club` color/venue/tagline fields | Small | ✅ Landed (M0) | — |
| `CoachPolicy` expanded fields | Medium | Deferred (v1 uses existing 5) | Optional |
| Lineup persistence + resolver | Medium | ✅ Landed (M0) | — |
| Win-probability analyzer | Medium | ✅ Landed (M0) | — |
| Scouting model (stateful) | Large | Deferred (full Center is v2) | Required |
| Recruitment domain model | Large | Deferred (v1 ships simple Draft only) | Required |
| Match-MVP function | Small | ✅ Landed (M0) | — |
| Playoff support | Medium | ✅ Verified absent (M0); v1 ships regular-season-by-record | Optional |
```

- [ ] **7.2: Run the full suite one more time**

```bash
python -m pytest -q
```

Expected: PASS — record the count and compare to the 1.1 baseline + the M0 additions:
- Task 1: ~6 new tests
- Task 2: 3 new tests
- Task 3: 11 new tests
- Task 4: ~12 new tests
- Task 5: ~13 new tests
- Task 6: 1 new test

Total expected: baseline + ~46 new tests, all passing.

- [ ] **7.3: Run regression test alone, one more time, as the gate**

```bash
python -m pytest tests/test_regression.py -v
```

Expected: PASS. The Phase 1 golden log is the integrity contract from AGENTS.md §7. If it fails, **stop**: an M0 task accidentally shifted engine output. Investigate which task is responsible (likely lineup wiring or sample data) before declaring M0 done.

- [ ] **7.4: Commit closeout**

```bash
git add docs/specs/2026-04-26-manager-mode/design.md
git commit -m "$(cat <<'EOF'
docs(m0): mark Milestone 0 deliverables landed in spec status table

All v1-required Manager Mode engine dependencies are now in place:
Club identity fields, lineup resolver, win-probability analyzer,
match-MVP function, career state machine, scheduler verification.

Phase 1 golden log unchanged. M1 UI work can begin pending separate
M0 review/approval.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

- [ ] **7.5: Self-report the M0 completion summary**

After the commit lands, post a short summary covering:
- All 7 task groups complete, all tests passing.
- New modules: `win_probability.py`, `lineup.py`, `career_state.py`.
- Schema migrations: v6 (Club identity), v7 (lineup tables). `CURRENT_SCHEMA_VERSION = 7`.
- Phase 1 golden log unchanged.
- Spec §2.5 summary table flipped to landed/verified for v1-required deliverables.
- M1 UI implementation plan is the next deliverable, but only after M0 review is approved.

---

## Definition of Done (Milestone 0)

All of the following must be true before M0 is reviewed:

1. ✅ All seven task groups complete; every sub-task checkbox checked.
2. ✅ `python -m pytest -q` passes.
3. ✅ `python -m pytest tests/test_regression.py -v` passes — Phase 1 golden log unchanged.
4. ✅ `CURRENT_SCHEMA_VERSION == 7` and both new migrations (v6, v7) registered in `_MIGRATIONS`.
5. ✅ New modules `win_probability.py`, `lineup.py`, `career_state.py` exist and are imported only by other engine modules and tests — **no UI module imports them in this milestone.**
6. ✅ `docs/specs/2026-04-26-manager-mode/design.md` §2.5 summary table reflects landed status for the four M0-required rows + verified status for §2.5.7 and §2.5.8.
7. ✅ No file under `src/dodgeball_sim/gui.py`, `src/dodgeball_sim/ui_*.py`, or `src/dodgeball_sim/court_renderer.py` modified during this milestone (sanity check):

```bash
git diff --name-only $(git log --reverse --format=%H | head -1)..HEAD -- "src/dodgeball_sim/gui.py" "src/dodgeball_sim/ui_*.py" "src/dodgeball_sim/court_renderer.py"
```

Expected: empty output.

If all seven hold, M0 is ready for review. **Do not start M1 until M0 review is explicitly approved.**
