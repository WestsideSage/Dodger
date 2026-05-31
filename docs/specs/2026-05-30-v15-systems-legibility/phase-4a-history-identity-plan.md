# V15 Phase 4a — History & Identity: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the legibility toolkit to the History and Identity surfaces — de-jargon the hero card, demote the Avg OVR headline, make Program Identity discoverable and explained, replace placeholder empty-states with honest `EmptyState` primitives, add `ProofChip` to milestone descriptions, fold Banner Shelf and Alumni Lineage into tabs (interim), remove the Trajectory Log display section, and apply the same honest-legibility pass to League History / `ProgramModal`.

**Architecture:** Presentation + honest payload-plumbing only. No engine changes, no new dependencies, no routing change. One new backend payload field (award holder + stat proof in timeline events), one backend test, then four independent frontend tasks against existing components. `ProgramModal` is a thin wrapper over `MyProgramView`; fixing the view content automatically fixes both the self-view and the league-modal view.

**Tech Stack:** Python 3 backend (`src/dodgeball_sim/`), pytest; React + Vite + TypeScript frontend (`frontend/`). Verification: `python -m pytest -q` · `npm run build` · `npm run lint` · `npm run e2e` (root).

> **Pre-flight:**
> - Phase 1 (toolkit) must be merged before starting: `import { TermTip, ProofChip, EmptyState } from '../../../legibility'` must resolve.
> - Branch: `git checkout -b feat/v15-phase4a-history-identity` off `main` (after Phase 1 merge).
> - Verify baseline green: `python -m pytest -q` and `npm run build && npm run lint`.
> - `MilestoneTree.tsx` is **not wired into `MyProgramView.tsx`** and is **not touched by this phase** — it is territory of the deferred archive-tree spec.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `src/dodgeball_sim/server.py` | Extend `get_history_my_program` award timeline entries with `holder_name` + `proof_stat` | 1 |
| `tests/test_history_server.py` (new) | Backend unit: award timeline carries holder/stat proof | 1 |
| `frontend/src/components/dynasty/history/MyProgramView.tsx` | Hero card de-jargon, Avg OVR demote, Identity discoverability + TermTip, honest EmptyState for banners/alumni/glance cells, remove Trajectory Log section + orphaned helper, fold BannerShelf+Alumni into tabs, ProofChip for award timeline entries | 2, 3, 4 |
| `frontend/src/components/dynasty/history/BannerShelf.tsx` | Replace inline empty note with `EmptyState` | 2 |
| `frontend/src/components/dynasty/history/AlumniLineage.tsx` | Replace inline empty note with `EmptyState` | 2 |
| `frontend/src/components/dynasty/history/LeagueView.tsx` | Apply honest `EmptyState` to all `do-hist-card-note` fallbacks; tighten glance copy | 5 |
| `tests/e2e/v15-history-identity.spec.ts` (new) | Playwright smoke: fresh-save path (empty banners/alumni EmptyState, identity TermTip, glance card copy) | 6 |

Each task is independently committable. Tasks 1 (backend) → 2–4 (frontend components) → 5 (LeagueView) → 6 (e2e).

---

## Task 1: Backend — award timeline proof (holder name + stat)

**Context:** `get_history_my_program` (server.py ~1080–1098) emits award timeline events with only a label string ("Best Newcomer", "MVP Award"). `season_awards` already stores `player_id` and `award_score`. `player_season_stats` stores per-player per-season `total_eliminations`, `total_catches_made`, and `matches`. This task joins those tables to populate `holder_name` and `proof_stat` alongside each award entry. The HoF name-resolution pattern (~1122–1131) already shows the correct approach. If a join yields no player row, both fields are `null` — the frontend uses `EmptyState`/omit, never invents text.

**Files:**
- Modify: `src/dodgeball_sim/server.py`
- Create: `tests/test_history_server.py`

- [ ] **Step 1: Build a helper inside `get_history_my_program` to resolve award holder info**

Locate the `award_rows` loop at approximately line 1081 in `server.py`. Replace the loop body as shown below. The existing import context (no new imports needed — `load_all_rosters` and `retired_rows` are already in scope) is used.

**Before (existing):**
```python
    award_rows = conn.execute(
        "SELECT season_id, award_type, player_id, club_id, award_score FROM season_awards WHERE club_id = ?",
        (club_id,),
    ).fetchall()
    for row in award_rows:
        label_map = {
            "mvp": "MVP Award",
            "best_thrower": "Best Thrower",
            "best_catcher": "Best Catcher",
            "best_newcomer": "Best Newcomer",
        }
        timeline.append({
            "season": row["season_id"],
            "week": None,
            "event_type": "award",
            "label": label_map.get(row["award_type"], row["award_type"]),
            "weight": "award",
        })
```

> **Note:** the existing `SELECT` omits `award_score`; confirm the actual column set by running `git grep -n "SELECT.*season_awards" -- src/dodgeball_sim/server.py`. If `award_score` is already included, no change needed to the SELECT. If only `season_id, award_type, player_id, club_id` are fetched, expand to include `award_score`.

**After:**
```python
    award_rows = conn.execute(
        "SELECT season_id, award_type, player_id, club_id, award_score FROM season_awards WHERE club_id = ?",
        (club_id,),
    ).fetchall()

    # Build a quick player-name lookup for award proof: check active roster first,
    # then retired players (same pattern as HoF name resolution above).
    def _player_display_name(player_id: str) -> str | None:
        for p in current_roster:
            if p.id == player_id:
                return p.name
        for r in retired_rows:
            if r["player_id"] == player_id and r.get("player"):
                return r["player"].name
        return None

    # Build a quick stat lookup: total_eliminations for the award season.
    def _award_proof_stat(player_id: str, season_id: str, award_type: str) -> str | None:
        row = conn.execute(
            """
            SELECT total_eliminations, total_catches_made, matches
            FROM player_season_stats
            WHERE player_id = ? AND season_id = ?
            """,
            (player_id, season_id),
        ).fetchone()
        if row is None:
            return None
        elims = row["total_eliminations"]
        catches = row["total_catches_made"]
        games = row["matches"]
        if award_type in ("best_newcomer", "mvp", "best_thrower"):
            return f"{elims} elims across {games} match{'es' if games != 1 else ''} that season."
        if award_type == "best_catcher":
            return f"{catches} catches across {games} match{'es' if games != 1 else ''} that season."
        return f"{elims} elims across {games} match{'es' if games != 1 else ''} that season."

    award_label_map = {
        "mvp": "MVP Award",
        "best_thrower": "Best Thrower",
        "best_catcher": "Best Catcher",
        "best_newcomer": "Best Newcomer",
    }

    for row in award_rows:
        holder_name = _player_display_name(row["player_id"])
        proof_stat = _award_proof_stat(row["player_id"], row["season_id"], row["award_type"])
        timeline.append({
            "season": row["season_id"],
            "week": None,
            "event_type": "award",
            "label": award_label_map.get(row["award_type"], row["award_type"]),
            "weight": "award",
            "holder_name": holder_name,   # str | None — None = player no longer traceable
            "proof_stat": proof_stat,     # str | None — None = stats not logged
        })
```

- [ ] **Step 2: Update the TypeScript interface in `MyProgramView.tsx`**

Add two optional fields to `TimelineEvent` (they are optional because championship/record/hof entries will not carry them):

```tsx
interface TimelineEvent {
  season: string;
  week: number | null;
  event_type: string;
  label: string;
  weight: string;
  holder_name?: string | null;   // present on 'award' entries only
  proof_stat?: string | null;    // present on 'award' entries only
}
```

And extend `DisplayEntry`:

```tsx
type DisplayEntry = {
  bucket: Exclude<ProgramFilter, 'all'>;
  copy: string;
  id: string;
  kicker: string;
  tag: string;
  tick: string;
  title: string;
  tone: 'amber' | 'cyan' | 'emerald' | 'rose' | 'violet';
  typeLabel: string;
  holderName?: string | null;
  proofStat?: string | null;
};
```

Propagate into `buildEntry` for the `'award'` case (see Task 3 Step 1 for full updated `buildEntry`).

- [ ] **Step 3: Write a backend test**

Create `tests/test_history_server.py`:

```python
"""Tests for /api/history/my-program award proof fields."""
import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from dodgeball_sim.server import app
from dodgeball_sim.persistence import init_db


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    init_db(conn)

    # Minimal data: one club, one player, one season_awards row, one player_season_stats row
    conn.execute(
        "INSERT OR IGNORE INTO clubs "
        "(club_id, name, city, primary_color, secondary_color, program_archetype) "
        "VALUES ('club_a', 'Testside', 'Testville', '#fff', '#000', 'Balanced Rebuild')"
    )
    conn.execute(
        "INSERT OR IGNORE INTO season_awards "
        "(season_id, award_type, player_id, club_id, award_score) "
        "VALUES ('season_1', 'best_newcomer', 'player_1', 'club_a', 55.0)"
    )
    conn.execute(
        "INSERT OR IGNORE INTO player_season_stats "
        "(player_id, season_id, club_id, matches, total_eliminations, total_catches_made, "
        " total_throws_attempted, total_dodges_successful, total_times_eliminated, newcomer) "
        "VALUES ('player_1', 'season_1', 'club_a', 8, 34, 5, 60, 12, 10, 1)"
    )
    conn.commit()

    import dodgeball_sim.server as server_module
    monkeypatch.setattr(server_module, "_DB_PATH", str(db_path))

    yield TestClient(app)

    conn.close()


def test_award_timeline_carries_proof_fields(client):
    resp = client.get("/api/history/my-program?club_id=club_a")
    assert resp.status_code == 200
    body = resp.json()
    award_events = [e for e in body["timeline"] if e["event_type"] == "award"]
    assert len(award_events) == 1
    evt = award_events[0]
    assert evt["label"] == "Best Newcomer"
    # proof_stat is a real payload string, not None
    assert evt["proof_stat"] is not None
    assert "34 elims" in evt["proof_stat"]
    assert "8 matches" in evt["proof_stat"]


def test_award_no_stats_row_returns_none_proof(client):
    """If player_season_stats is absent, proof_stat is None — not invented."""
    # Insert award for a player with no stats row
    import sqlite3 as sl
    from dodgeball_sim import server as sv
    conn2 = sl.connect(sv._DB_PATH)
    conn2.row_factory = sl.Row
    conn2.execute(
        "INSERT OR IGNORE INTO season_awards "
        "(season_id, award_type, player_id, club_id, award_score) "
        "VALUES ('season_2', 'mvp', 'player_ghost', 'club_a', 0.0)"
    )
    conn2.commit()
    conn2.close()

    resp = client.get("/api/history/my-program?club_id=club_a")
    assert resp.status_code == 200
    body = resp.json()
    ghost = next((e for e in body["timeline"] if e.get("holder_name") is None and e["event_type"] == "award" and e["label"] == "MVP Award"), None)
    # ghost player has no stats row — proof_stat must be None, not invented text
    assert ghost is not None
    assert ghost["proof_stat"] is None
```

> **Note on monkeypatching:** confirm the correct attribute name by running `grep -n "_DB_PATH\|get_db\|DATABASE_URL" src/dodgeball_sim/server.py`. If the DB path is injected via FastAPI Depends (not a module-level `_DB_PATH`), adapt the fixture to use the `override_dependency` pattern the existing tests use — check the existing test files for the established pattern.

- [ ] **Step 4: Run backend tests**

```bash
python -m pytest tests/test_history_server.py -q
python -m pytest -q
```

Expected: all green.

- [ ] **Step 5: Engine-health probe (confirm no drift)**

```bash
python tools/tier_engine_health_probe.py --driver official --trials 50
```

Expected: identical output to pre-task baseline (read-only payload change).

- [ ] **Step 6: Commit**

```bash
git add src/dodgeball_sim/server.py tests/test_history_server.py
git commit -m "feat(v15-p4a): award timeline proof — holder name + stat field

Add holder_name and proof_stat to award timeline entries in
get_history_my_program. Payload-backed: player_season_stats join;
null when data is absent (no invented claims). Backend test confirms
non-null proof for a logged stat and null for a ghost player.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Empty states — BannerShelf, AlumniLineage, glance cells

**Context:** The current fallbacks are `<p className="do-hist-card-note">` bare text — not announced as status, and not visually distinct from body copy. Replace with the toolkit `EmptyState`. The `showNextPlaceholder` "Open Slot" banner in `BannerShelf` is a synthetic placeholder — replace with an honest `EmptyState` when `banners.length === 0`.

**Files:**
- Modify: `frontend/src/components/dynasty/history/BannerShelf.tsx`
- Modify: `frontend/src/components/dynasty/history/AlumniLineage.tsx`
- Modify: `frontend/src/components/dynasty/history/MyProgramView.tsx` (glance cell copy only in this task)

- [ ] **Step 1: Rewrite `BannerShelf.tsx`**

```tsx
import { EmptyState } from '../../../legibility';
import { formatSeasonLabel } from './formatters';

interface BannerEntry {
  type: string;
  season: string;
  label: string;
}

export function BannerShelf({
  banners,
  showNextPlaceholder,
}: {
  banners: BannerEntry[];
  showNextPlaceholder?: boolean;
}) {
  if (banners.length === 0) {
    return (
      <EmptyState
        title="No banners yet"
        body={
          showNextPlaceholder
            ? 'Win a championship or earn a season award to raise your first banner. It will hang here forever.'
            : 'This program has not logged a championship or season award yet.'
        }
        icon="🏳️"
      />
    );
  }

  return (
    <div className="do-hist-banners">
      {banners.map((banner, index) => (
        <div
          key={`${banner.type}-${banner.season}-${index}`}
          className={`do-hist-banner ${banner.type === 'championship' ? 'is-title' : 'is-award'}`}
        >
          <span className="do-hist-banner-type">{banner.type === 'championship' ? 'Title' : 'Award'}</span>
          <strong className="do-hist-banner-label">{banner.label}</strong>
          <span className="do-hist-banner-season">{formatSeasonLabel(banner.season)}</span>
        </div>
      ))}
    </div>
  );
}
```

> **Rationale:** The "Open Slot" synthetic banner was fabricated UI content. The `EmptyState` is honest and explains what earns a banner. The `icon` prop is `React.ReactNode`; a plain string emoji is valid.

- [ ] **Step 2: Rewrite `AlumniLineage.tsx`**

```tsx
import { EmptyState } from '../../../legibility';

interface AlumnusEntry {
  id: string;
  name: string;
  seasons_played: number;
  career_elims: number;
  championships: number;
  ovr_final: number;
  potential_tier: string;
}

const TIER_TONE: Record<string, string> = {
  Elite: 'dm-badge-emerald',
  High: 'dm-badge-cyan',
  Limited: 'dm-badge-slate',
  Solid: 'dm-badge-violet',
  Unknown: 'dm-badge-slate',
};

export function AlumniLineage({ alumni }: { alumni: AlumnusEntry[] }) {
  if (alumni.length === 0) {
    return (
      <EmptyState
        title="No departed players yet"
        body="Players who leave or retire after contributing here will appear in this lineage. Your first alumni season is still ahead."
        icon="👤"
      />
    );
  }

  return (
    <div className="do-hist-list">
      {alumni.map((entry) => (
        <div key={entry.id} className="do-hist-list-row">
          <div className="main">
            <strong>{entry.name}</strong>
            <span className="meta">
              {entry.seasons_played} season{entry.seasons_played === 1 ? '' : 's'} · {entry.career_elims} career elims
            </span>
          </div>
          <div className="side">
            <span className={`dm-badge ${TIER_TONE[entry.potential_tier] ?? 'dm-badge-slate'}`}>
              {entry.potential_tier}
            </span>
            <span className="note">
              {entry.championships} title{entry.championships === 1 ? '' : 's'} · Final OVR {entry.ovr_final}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Update glance cell copy in `MyProgramView.tsx` (copy only — layout unchanged)**

Find the `do-hist-glance` block (~line 253–293). Replace the `Championship Banners` and `Alumni Lineage` cells with honest copy that does not invent a denomination. The full updated glance block is in Task 3 Step 2 (the hero card rewrite handles this area in one pass to keep the diffs clean); **skip this step and let Task 3 own the full glance rewrite** — they are sequential, not parallel.

- [ ] **Step 4: Compile + lint**

```bash
# from frontend/
npm run build && npm run lint
```

Expected: PASS. (Confirm `EmptyState` is importable from `'../../../legibility'`; if the Phase 1 barrel export hasn't landed yet this gate will fail — this is the correct Phase 1 dependency.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dynasty/history/BannerShelf.tsx frontend/src/components/dynasty/history/AlumniLineage.tsx
git commit -m "feat(v15-p4a): honest EmptyState for BannerShelf + AlumniLineage

Replace synthetic 'Open Slot' placeholder and bare card-note text
with toolkit EmptyState primitives — no fabricated history.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `MyProgramView.tsx` — hero card, identity, Trajectory Log removal, ProofChip on awards

This is the largest task. It makes five targeted changes to `MyProgramView.tsx`:

1. De-jargon the glance hero card ("Archive Through Season 4" → plain label; "3 tracked archive moments" → plain sub-label).
2. Demote Avg OVR from headline stat — replace with season-span label in both the glance cell and the `HeroCard` component.
3. Make Program Identity discoverable: wrap `identityLabel` in `TermTip term="identity.intent"`, and add a one-line provenance note explaining where "Intent Balanced" comes from.
4. Remove the Trajectory Log display section (`<section>` ~lines 374–403) and the now-orphaned `trajectoryGradeTone` helper — **preserving** the `latestTrajectory`/`dominant_intent` derivation feeding the identity cell (lines 240–249), which must stay.
5. Add `ProofChip` to award timeline entries when `holderName` and `proofStat` are non-null.
6. Fold Banner Shelf and Alumni Lineage into inline tabs (interim — the future archive-tree spec will re-home them).

**Files:**
- Modify: `frontend/src/components/dynasty/history/MyProgramView.tsx`

- [ ] **Step 1: Updated imports at top of file**

```tsx
import { useState } from 'react';
import { useApiResource } from '../../../hooks/useApiResource';
import { StatusMessage } from '../../ui';
import { EmptyState, ProofChip, TermTip } from '../../../legibility';
import { AlumniLineage } from './AlumniLineage';
import { BannerShelf } from './BannerShelf';
import { formatSeasonLabel, formatTimelineLabel, humanizeHistoryToken } from './formatters';
```

- [ ] **Step 2: Remove `trajectoryGradeTone` helper; update `TimelineEvent` and `DisplayEntry`**

Delete the entire `trajectoryGradeTone` function (lines 114–119):

```tsx
// DELETE THIS BLOCK — no longer needed after Trajectory Log section removal:
// function trajectoryGradeTone(value: string) { ... }
```

Update `TimelineEvent` to include the new proof fields from Task 1:

```tsx
interface TimelineEvent {
  season: string;
  week: number | null;
  event_type: string;
  label: string;
  weight: string;
  holder_name?: string | null;
  proof_stat?: string | null;
}
```

Update `DisplayEntry` to carry the proof fields through:

```tsx
type DisplayEntry = {
  bucket: Exclude<ProgramFilter, 'all'>;
  copy: string;
  id: string;
  kicker: string;
  tag: string;
  tick: string;
  title: string;
  tone: 'amber' | 'cyan' | 'emerald' | 'rose' | 'violet';
  typeLabel: string;
  holderName?: string | null;
  proofStat?: string | null;
};
```

- [ ] **Step 3: Updated `buildEntry` — propagate proof fields on award case**

Replace the full `buildEntry` function:

```tsx
function buildEntry(event: TimelineEvent): DisplayEntry {
  const seasonLabel = formatSeasonLabel(event.season);
  const title = formatTimelineLabel(event.label);

  switch (event.event_type) {
    case 'championship':
      return {
        bucket: 'titles',
        copy: `${seasonLabel} ended with a title run for this program.`,
        id: `${event.season}-${event.event_type}-${event.label}`,
        kicker: seasonLabel,
        tag: 'Champions',
        tick: seasonTick(event.season, event.week),
        title,
        tone: 'amber',
        typeLabel: 'Title',
      };
    case 'award':
      return {
        bucket: 'awards',
        copy: event.holder_name
          ? `${event.holder_name} won ${title} in ${seasonLabel}.`
          : `${title} was claimed by a player from this program in ${seasonLabel}.`,
        id: `${event.season}-${event.event_type}-${event.label}`,
        kicker: seasonLabel,
        tag: 'Award',
        tick: seasonTick(event.season, event.week),
        title,
        tone: 'emerald',
        typeLabel: 'Award',
        holderName: event.holder_name,
        proofStat: event.proof_stat,
      };
    case 'record':
      return {
        bucket: 'records',
        copy: `${title} became a league mark for this program in ${seasonLabel}.`,
        id: `${event.season}-${event.event_type}-${event.label}`,
        kicker: seasonLabel,
        tag: 'League record',
        tick: seasonTick(event.season, event.week),
        title,
        tone: 'cyan',
        typeLabel: 'Record',
      };
    case 'hof':
      return {
        bucket: 'legacy',
        copy: `${title} entered the Hall of Fame in ${seasonLabel}.`,
        id: `${event.season}-${event.event_type}-${event.label}`,
        kicker: seasonLabel,
        tag: 'Hall of Fame',
        tick: seasonTick(event.season, event.week),
        title,
        tone: 'violet',
        typeLabel: 'Legacy',
      };
    default:
      return {
        bucket: 'legacy',
        copy:
          event.week !== null
            ? `Logged in ${seasonLabel}, Week ${String(event.week).padStart(2, '0')}.`
            : `Logged in ${seasonLabel}.`,
        id: `${event.season}-${event.event_type}-${event.label}`,
        kicker: seasonLabel,
        tag: event.week !== null ? `Week ${String(event.week).padStart(2, '0')}` : 'Program milestone',
        tick: seasonTick(event.season, event.week),
        title,
        tone: 'rose',
        typeLabel: 'Milestone',
      };
  }
}
```

- [ ] **Step 4: Updated `HeroCard` — demote Avg OVR**

Replace the `HeroCard` component:

```tsx
function HeroCard({ data, highlight, label }: { data: HeroSeason; highlight?: boolean; label: string }) {
  return (
    <div className={`do-hist-hero-card ${highlight ? 'is-current' : ''}`}>
      <span className="do-hist-hero-label">{label}</span>
      <span className="do-hist-hero-season">{formatSeasonLabel(data.season_label)}</span>
      <span className="do-hist-hero-record">
        {data.wins}-{data.losses}-{data.draws}
      </span>
      <div className="do-hist-hero-meta">
        {data.championships ? (
          <span>{data.championships} title{data.championships === 1 ? '' : 's'}</span>
        ) : null}
      </div>
    </div>
  );
}
```

> **Rationale:** Avg OVR was computed from the current live roster (not from the archived season), making it a misleading headline for historical cards. Removing it from both positions (glance + hero card) leaves only data that is honest about that season.

- [ ] **Step 5: Tabs state for Banner Shelf / Alumni Lineage**

Add a tab state variable and a simple tab button helper below the existing `filter`/`setFilter` state inside `MyProgramView`:

```tsx
const [shelfTab, setShelfTab] = useState<'banners' | 'alumni'>('banners');
```

- [ ] **Step 6: Updated `MyProgramView` render — full replacement**

Replace the `return` block of `MyProgramView` in full:

```tsx
  return (
    <div className="do-tab-content">
      {/* Glance strip — de-jargoned copy */}
      <div className="do-hist-glance">
        <div className="cell">
          <span className="lbl">Season Range</span>
          <span className="val">
            {currentHero ? formatSeasonLabel(currentHero.season_label) : 'Season 1'}
          </span>
          <span className="trend">
            {entries.length === 1 && entries[0].id === 'history-baseline'
              ? 'Archive is live — no milestones logged yet'
              : `${entries.length} milestone${entries.length === 1 ? '' : 's'} logged`}
          </span>
        </div>
        <div className="cell">
          <span className="lbl">All-Time Record</span>
          <span className="val">
            {currentHero ? `${currentHero.wins}-${currentHero.losses}-${currentHero.draws}` : '—'}
          </span>
          <span className="trend">
            {currentHero ? 'Across completed seasons' : 'First completed season will appear here'}
          </span>
        </div>
        <div className="cell">
          <span className="lbl">
            <TermTip term="identity.intent">Program Identity</TermTip>
          </span>
          <span className="val">{identityLabel}</span>
          <span className="trend">
            {latestTrajectory
              ? `Lean: ${humanizeHistoryToken(latestTrajectory.dominant_intent)} — shaped by your season tactics`
              : 'Set at club creation · evolves from your season-by-season choices'}
          </span>
        </div>
        <div className="cell">
          <span className="lbl">Championship Banners</span>
          <span className="val">{championshipCount}</span>
          <span className={`trend ${championshipCount > 0 ? 'ok' : ''}`}>
            {championshipCount > 0
              ? `${championshipCount} title${championshipCount === 1 ? '' : 's'} in the archive`
              : 'First banner still ahead'}
          </span>
        </div>
        <div className="cell">
          <span className="lbl">Alumni</span>
          <span className="val">{data.alumni.length}</span>
          <span className="trend">
            {data.alumni.length > 0
              ? `${data.alumni.length} player${data.alumni.length === 1 ? '' : 's'} who shaped this program`
              : isSelf ? 'Your first alumni season is ahead' : 'No departed players yet'}
          </span>
        </div>
      </div>

      {/* Timeline filter + list */}
      <div className="do-hist-filters">
        <div className="filters">
          {FILTERS.map((item) => {
            const count =
              item.id === 'all'
                ? entries.length
                : entries.filter((entry) => entry.bucket === item.id).length;
            return (
              <button
                key={item.id}
                className={`do-board-filter ${filter === item.id ? 'is-active' : ''}`}
                onClick={() => setFilter(item.id)}
                type="button"
              >
                {item.label}
                <span className="n">{count}</span>
              </button>
            );
          })}
        </div>
        <span className="do-board-meta">
          {isSelf ? 'Program archive' : `${clubId.toUpperCase()} archive`}
        </span>
      </div>

      <div className="do-hist-timeline">
        <div className="rail" />
        {visibleEntries.length > 0 ? (
          visibleEntries.map((entry) => (
            <article key={entry.id} className={`do-hist-entry tone-${entry.tone}`}>
              <div className="do-hist-wk">
                <span className="wk-num">{entry.tick}</span>
                <span className="dot" />
              </div>
              <div className="do-hist-body">
                <header>
                  <span className={`dm-badge ${badgeToneClass(entry.tone)}`}>{entry.typeLabel}</span>
                  <span className="kicker">{entry.kicker}</span>
                  <span className="tag">{entry.tag}</span>
                </header>
                <h4 className="title">{entry.title}</h4>
                <p className="copy">{entry.copy}</p>
                {entry.proofStat && entry.holderName ? (
                  <ProofChip
                    label={entry.holderName}
                    source={entry.proofStat}
                  />
                ) : entry.proofStat ? (
                  <ProofChip
                    label="View proof"
                    source={entry.proofStat}
                  />
                ) : null}
              </div>
            </article>
          ))
        ) : (
          <article className="do-hist-entry tone-cyan">
            <div className="do-hist-wk">
              <span className="wk-num">NONE</span>
              <span className="dot" />
            </div>
            <div className="do-hist-body">
              <header>
                <span className="dm-badge dm-badge-cyan">Filter</span>
                <span className="kicker">No matching entries</span>
                <span className="tag">Clear filter</span>
              </header>
              <h4 className="title">No archive items in this lane</h4>
              <p className="copy">Switch back to All to see the full program archive.</p>
            </div>
          </article>
        )}
      </div>

      {/* Program Arc — kept, Avg OVR removed from HeroCard */}
      <div className="do-hist-grid">
        <section className="dm-panel do-hist-card">
          <div className="do-hist-card-head">
            <span className="dm-kicker">Program Arc</span>
            <h3>How it started vs today</h3>
          </div>
          {firstHero || currentHero ? (
            <div className="do-hist-hero-grid">
              {firstHero ? <HeroCard data={firstHero} label="Opening season" /> : null}
              {currentHero ? <HeroCard data={currentHero} label="Current snapshot" highlight /> : null}
            </div>
          ) : (
            <EmptyState
              title="No completed season archived yet"
              body="Your first full season record will appear here after the offseason ceremony."
            />
          )}
        </section>

        {/* Trajectory Log section REMOVED. Its data (dominant_intent) is still
            used in the glance strip above. MilestoneTree.tsx is untouched —
            it is the deferred archive-tree spec's territory. */}

        {/* Banner Shelf + Alumni Lineage folded into tabs (interim).
            The future archive-tree spec will re-home these into the dynamic tree. */}
        <section className="dm-panel do-hist-card">
          <div className="do-hist-card-head">
            <span className="dm-kicker">
              {shelfTab === 'banners' ? 'Banner Shelf' : 'Alumni Lineage'}
            </span>
            <div style={{ display: 'flex', gap: '0.4rem' }}>
              <button
                type="button"
                className={`do-board-filter${shelfTab === 'banners' ? ' is-active' : ''}`}
                onClick={() => setShelfTab('banners')}
              >
                Banners
              </button>
              <button
                type="button"
                className={`do-board-filter${shelfTab === 'alumni' ? ' is-active' : ''}`}
                onClick={() => setShelfTab('alumni')}
              >
                Alumni
              </button>
            </div>
          </div>
          {shelfTab === 'banners' ? (
            <BannerShelf banners={data.banners} showNextPlaceholder={isSelf} />
          ) : (
            <AlumniLineage alumni={data.alumni} />
          )}
        </section>
      </div>
    </div>
  );
```

> **Key removal note:** The Trajectory Log `<section>` (former lines 374–403) is intentionally gone. The `latestTrajectory` and `dominant_intent` derivation (lines 240–249 in the original) is intentionally kept for the glance Identity cell. The `trajectoryGradeTone` helper is intentionally removed; lint will confirm no dangling reference.

- [ ] **Step 7: Compile + lint**

```bash
npm run build && npm run lint
```

Expected: PASS. In particular lint must not flag `trajectoryGradeTone` as unused (it is gone), must not flag `program_trajectories` derivation as unused (it feeds `latestTrajectory`/`identityTrend`), and must not flag the new imports.

If lint flags `import type { ReactNode }` missing for the `icon` prop of `EmptyState`, check how other components in the repo import React types and match.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/dynasty/history/MyProgramView.tsx
git commit -m "feat(v15-p4a): history legibility — de-jargon, identity TermTip, ProofChip awards, Trajectory Log removed, tabs

- Hero card: 'Archive Through Season N' -> 'Season Range'; 'N tracked
  archive moments' -> plain milestone count
- Avg OVR demoted from glance cell and HeroCard (current-roster value
  was never honest for a historical snapshot)
- Program Identity wrapped in TermTip(identity.intent); provenance note
  explains it is set at creation and shaped by season tactics — NOT by
  Program Settings (which controls department orders, not archetype)
- Trajectory Log display section removed; dominant_intent derivation
  preserved for Identity cell; trajectoryGradeTone helper deleted
- Award timeline entries render ProofChip when holder_name + proof_stat
  are non-null (payload-backed from Task 1 backend change)
- BannerShelf + AlumniLineage folded into interim tabs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: `ProgramModal.tsx` — content legibility pass

**Context:** `ProgramModal` wraps `MyProgramView` with `isSelf={false}`, so all content fixes from Task 3 are automatically inherited. This task's only responsibility is adjusting the modal header copy to match the legibility standard (the kicker "League Archive" is fine; the body note is passive/jargony) and confirming the modal's aria/accessibility is solid. No open/route logic is touched — Phase 2d owns the row-click wiring.

**Files:**
- Modify: `frontend/src/components/dynasty/history/ProgramModal.tsx`

- [ ] **Step 1: Update modal header copy**

Replace the `do-hist-modal-header` block:

```tsx
        <div className="do-hist-modal-header">
          <span className="dm-kicker">League Archive</span>
          <h2 className="do-hist-modal-title">{clubName}</h2>
          <p className="do-hist-card-note">
            Viewing {clubName}'s program archive — titles, alumni, and milestones logged across their history.
          </p>
        </div>
```

- [ ] **Step 2: Confirm aria on the overlay**

The existing overlay uses `onClick={onClose}` on the backdrop and `Escape` via `useEffect`. Add `role="dialog"` and `aria-label` to the body panel so screen readers announce context:

```tsx
        <div
          className="command-policy-overlay-body do-hist-modal-body"
          onClick={(event) => event.stopPropagation()}
          role="dialog"
          aria-label={`${clubName} — Program Archive`}
          aria-modal="true"
        >
```

- [ ] **Step 3: Compile + lint**

```bash
npm run build && npm run lint
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/dynasty/history/ProgramModal.tsx
git commit -m "feat(v15-p4a): ProgramModal — plain header copy + aria dialog

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: `LeagueView.tsx` — honest empty states and glance copy

**Context:** `LeagueView` has four `<p className="do-hist-card-note">` bare-text fallbacks (Dynasty Rankings, All-Time Records, Hall of Fame, Rivalries) and glance cells with passive copy. Apply the same EmptyState pass. No new data is needed — this is copy + component substitution only.

**Files:**
- Modify: `frontend/src/components/dynasty/history/LeagueView.tsx`

- [ ] **Step 1: Add `EmptyState` import**

```tsx
import { EmptyState } from '../../../legibility';
```

- [ ] **Step 2: Replace all four bare-text fallbacks with `EmptyState`**

**Dynasty Rankings — before:**
```tsx
            <p className="do-hist-card-note">No dynasty ranking data has been logged yet.</p>
```
**After:**
```tsx
            <EmptyState
              title="No dynasty rankings yet"
              body="Rankings appear after the first championship is claimed. Win the league to start the board."
            />
```

**All-Time Records — before:**
```tsx
              <p className="do-hist-card-note">No league records have been set yet.</p>
```
**After:**
```tsx
              <EmptyState
                title="No league records set"
                body="Individual season-stat records are logged here once the league has enough history to establish a mark."
              />
```

**Hall of Fame — before:**
```tsx
              <p className="do-hist-card-note">The Hall of Fame is still empty.</p>
```
**After:**
```tsx
              <EmptyState
                title="Hall of Fame is empty"
                body="Players inducted after distinguished careers will appear here. The first class is still being earned."
                icon="🏛️"
              />
```

**Rivalries — before:**
```tsx
              <p className="do-hist-card-note">Rivalries will appear after repeated meetings.</p>
```
**After:**
```tsx
              <EmptyState
                title="No rivalries tracked yet"
                body="Club pairings that meet repeatedly rise to the top. A few more seasons will surface the heat maps."
              />
```

- [ ] **Step 3: Tighten glance copy that implies data that may not exist**

In the glance strip, `dynasty_rankings[0]` could be null (first season). The existing code handles null, but the trend copy `'No championship archive yet'` can be improved to match the EmptyState tone without being separate:

```tsx
          <span className={`trend ${topDynasty && topDynasty.championships > 0 ? 'ok' : ''}`}>
            {topDynasty
              ? `${topDynasty.championships} title${topDynasty.championships === 1 ? '' : 's'} · longest streak ${topDynasty.longest_win_streak}`
              : 'First champion has not been crowned yet'}
          </span>
```

And for Records logged:
```tsx
          <span className="trend">
            {data.records.length > 0
              ? 'League marks are being tracked'
              : 'Records will appear after the first stat milestones'}
          </span>
```

And Hall of Fame:
```tsx
          <span className="trend">
            {data.hof.length > 0 ? 'Legacy lane is active' : 'First inductee class is still being earned'}
          </span>
```

- [ ] **Step 4: Compile + lint**

```bash
npm run build && npm run lint
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dynasty/history/LeagueView.tsx
git commit -m "feat(v15-p4a): LeagueView honest EmptyState pass + glance copy

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Playwright e2e smoke

**Context:** The fresh-save path yields an empty save (no banners, no alumni, one offseason ceremony maximum). This is the reliable e2e path. The populated-history proof path (4-season save with a Best Newcomer logged) requires a seeded multi-season DB — check `tests/e2e/` for an existing dynasty fixture before committing to it. If no fixture exists, scope assertions to the fresh-save path; leave populated-history assertions as manual verification (note this explicitly in the test file).

**Files:**
- Create: `tests/e2e/v15-history-identity.spec.ts`

- [ ] **Step 1: Check for an existing dynasty/history e2e fixture**

```bash
grep -rn "dynasty\|history\|alumni\|banners\|season_2\|offseason" tests/e2e/ --include="*.ts" -l
```

If a multi-season fixture exists, extend the relevant test. Otherwise use fresh-save only.

- [ ] **Step 2: Create the e2e spec**

```ts
import { test, expect } from '@playwright/test';

// Verifies the History & Identity legibility changes on a fresh save.
// Populated-history proof (Best Newcomer ProofChip on a 4-season save)
// requires a seeded multi-season DB — test manually via the Dynasty Office
// History tab after running the fast-forward playtest (docs/playtest_output/).
test.describe('V15 Phase 4a — History & Identity', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the Dynasty Office History tab on a fresh or existing save.
    // Adjust selectors to match the app's actual navigation structure.
    await page.goto('/');
    // Wait for the app to be ready (save list or command center).
    await page.waitForSelector('[data-testid="app-root"], .command-center, .save-list', { timeout: 10000 });
  });

  test('Program Identity glance cell contains TermTip trigger', async ({ page }) => {
    // Navigate to the History tab inside Dynasty Office.
    // The exact navigation depends on whether a save is already loaded.
    // This selector targets the Dynasty Office tab and then History sub-tab.
    const dynastyBtn = page.getByRole('button', { name: /dynasty|history|office/i }).first();
    if (await dynastyBtn.isVisible()) {
      await dynastyBtn.click();
    }
    const historyTab = page.getByRole('button', { name: /history/i }).first();
    if (await historyTab.isVisible()) {
      await historyTab.click();
    }

    // The Program Identity cell should have a TermTip — a button with aria-label "What is Program Identity?"
    const tip = page.getByRole('button', { name: /What is Program Identity\?/i });
    await expect(tip).toBeVisible({ timeout: 5000 });

    // Activate the tooltip and confirm it explains flavor nature.
    await tip.focus();
    const tooltip = page.getByRole('tooltip');
    await expect(tooltip).toBeVisible();
    await expect(tooltip).toContainText(/flavor|strategic lean|tactical/i);
  });

  test('Empty BannerShelf renders honest EmptyState', async ({ page }) => {
    // On a fresh save or early-season save, banners.length === 0.
    const emptyStatus = page.getByRole('status').filter({ hasText: /no banners yet/i });
    if (await emptyStatus.isVisible()) {
      await expect(emptyStatus).toContainText(/championship or earn a season award/i);
    }
    // If a banner exists (loaded save), this branch is skipped — not a failure.
  });

  test('Empty AlumniLineage renders honest EmptyState (via Alumni tab)', async ({ page }) => {
    // Switch to the Alumni tab in the Banner Shelf + Alumni Lineage section.
    const alumniTab = page.getByRole('button', { name: /alumni/i });
    if (await alumniTab.isVisible()) {
      await alumniTab.click();
      const emptyStatus = page.getByRole('status').filter({ hasText: /no departed players yet/i });
      if (await emptyStatus.isVisible()) {
        await expect(emptyStatus).toContainText(/first alumni season/i);
      }
    }
  });

  test('Glance strip does not contain "Archive Through" jargon', async ({ page }) => {
    // Confirm the old jargon label is gone.
    await expect(page.getByText(/archive through/i)).not.toBeVisible();
    // Confirm the replacement label is present.
    await expect(page.getByText(/season range/i)).toBeVisible();
  });

  test('No horizontal overflow at 390px', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const overflow = await page.evaluate(() => document.body.scrollWidth > document.body.clientWidth);
    expect(overflow).toBe(false);
  });
});
```

> **Playwright config check:** confirm `playwright.config.ts` `baseURL` matches the dev server URL and that `webServer` is configured, or that the suite runs against a built preview. Run `cat playwright.config.ts | head -40` to verify.

- [ ] **Step 3: Run the e2e suite**

```bash
# from repo root:
npm run e2e -- v15-history-identity
```

Expected: all assertions pass on a fresh-save load. Any conditional (`if (await x.isVisible())`) branches that don't fire on the test save are not failures.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/v15-history-identity.spec.ts
git commit -m "feat(v15-p4a): Playwright smoke — History & Identity legibility

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 4a Exit Gates

- [ ] `python -m pytest -q` — green (incl. new `tests/test_history_server.py`).
- [ ] From `frontend/`: `npm run build && npm run lint` — clean. In particular:
  - `trajectoryGradeTone` must not appear anywhere in `MyProgramView.tsx` (deleted).
  - `TermTip`, `ProofChip`, `EmptyState` must all resolve from `'../../../legibility'` (no orphan imports).
  - No `as const satisfies` error from terms.ts (confirm `identity.intent` is already seeded — it is, from Phase 1 Task 2).
- [ ] From repo root: `npm run e2e -- v15-history-identity` — green.
- [ ] `python tools/tier_engine_health_probe.py --driver official --trials 50` — output identical to pre-phase baseline (no sim drift; this phase is presentation + one read-only payload join).
- [ ] Manual 390×844 browser check: History tab in Dynasty Office — no horizontal overflow, no console errors. Confirm:
  - "Season Range" label appears (replaces "Archive Through").
  - "Program Identity" label has a dotted-underline TermTip trigger; clicking it reveals a tooltip.
  - Empty banners → `EmptyState` (not "Open Slot" synthetic banner).
  - Empty alumni → `EmptyState` (via Alumni tab click).
  - On a 4-season save: award timeline entries show a named `ProofChip` with stat text; championship/record entries have no chip.
  - Trajectory Log section is absent; the Identity glance cell still shows the correct `dominant_intent` label.
  - `ProgramModal` opened from League History directory has `role="dialog"` and plain header copy.

---

## Hand-off Notes

**ProgramModal + Phase 2d overlap:** `ProgramModal.tsx` is opened by the Phase 2d Standings row-click wiring. This phase owns the modal's **content** (`role="dialog"`, aria, header copy); Phase 2d owns the **trigger** (row-click and the open/close call-site). The files do not conflict: Phase 2d will call `setModal({ clubId, clubName })` in a different component (`LeagueContext.tsx` or wherever standings live); that call-site does not touch `ProgramModal.tsx` itself.

**MilestoneTree.tsx is untouched:** The file exists at `frontend/src/components/dynasty/history/MilestoneTree.tsx`. It is not imported by `MyProgramView.tsx` and is not rendered anywhere in this phase. It belongs to the deferred archive-tree spec. Do not remove or extend it.

**terms.ts stays append-only:** `identity.intent` is already seeded in Phase 1 (`kind: 'flavor'`). No new term keys are needed by this phase. If any future phase 4a extension needs a new term (e.g. `history.banner` for a championship explainer), add it to the `TERMS` object as an append — do not rewrite existing entries.

**No new backend payload fields beyond `holder_name`/`proof_stat`:** avg_ovr is demoted on the frontend only (the backend still computes and returns it; removing the backend field is needless churn and would break any future consumer).

**Avg OVR removal rationale (for future reference):** The field is computed from the *current live roster*, not from the archived season roster — making it misleading as a historical headline. It is demoted in display only.
