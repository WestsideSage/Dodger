# Browser Bug Blitz Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 16 browser-reported bugs from a full playthrough of Dodgeball Manager.

**Architecture:** Fixes span `src/dodgeball_sim/` (Python backend) and `frontend/src/` (React/TypeScript). Each task is narrowly scoped to one root cause — no refactors, no scope creep.

**Tech Stack:** FastAPI + SQLite (backend), React 18 + TypeScript (frontend), Vite build

---

## Root Cause Summary

| Bug | File(s) | Root Cause |
|-----|---------|-----------|
| BUG-01 | App.tsx | `screen` state set once on mount; never transitions game→offseason after final match |
| BUG-02 | replay_service.py, KeyPlayersPanel.tsx | `top_performers` has no `club_name`; panel shows no team label |
| BUG-03 | Roster.tsx | `fetchPlan` has no `.catch()`; crashes silently during offseason; investigate nav interception |
| BUG-04 | save_service.py | `list_saves_payload` returns every `.db` with no test-save filter |
| BUG-05 | use_cases.py | `_build_aftermath` always returns `standings_shift: []` |
| BUG-06/13/14 | voice_aftermath.py | One template pool for wins and losses; ambiguous pronoun + recurring-loss template |
| BUG-07 | command_center.py | `"Balanced"` not in `INTENTS`; backend silently falls back to "Win Now" |
| BUG-08 | StartingRecruitmentStep.tsx | `toggleProspect` reads stale `rosterIds` — should use functional setState |
| BUG-09 | SaveMenu.tsx | Already fixed in current code (mode choice shown before club picker) |
| BUG-10 | offseason_service.py, offseason_presentation.py | After signing, cursor skips to `schedule_reveal` — recruitment beat never shown |
| BUG-11 | web_status_service.py, App.tsx | Year hardcoded as `2026`; status API never exposes `season_year` |
| BUG-12 | offseason_presentation.py | Awards not sorted dramatically; MVP first, but should be last (big reveal) |
| BUG-15 | offseason_beats.py | `source == "legacy_free_agents"` fires on fresh saves with empty prospect pool |
| BUG-16 | replay_service.py | `top_performers` sorted by score desc but no floor; 0-score players included |

---

## Task 1: BUG-06/13/14 — Voice aftermath narrative by result

**Files:**
- Modify: `src/dodgeball_sim/voice_aftermath.py`

- [ ] **Step 1: Replace the single template pool with win/loss pools**

```python
from .rng import DeterministicRNG

_WIN_TEMPLATES = [
    "A decisive Win for the squad.",
    "The team secures a hard-fought Win.",
    "An impressive Win that sends a message.",
    "They walk away with a Win this week.",
    "The final whistle seals a Win.",
    "A Win that shifts the momentum.",
    "The scoreboard reflects a Win.",
    "Fans react to a stunning Win.",
    "A Win for the history books.",
    "They earned this Win on the court.",
    "The post-match mood is defined by this Win.",
    "A Win that nobody saw coming.",
    "The expected Win materializes.",
    "A gritty, unpolished Win.",
    "The Win speaks for itself.",
    "They ground out a Win.",
    "A textbook Win from start to finish.",
    "An emotional Win for the locker room.",
    "A Win built on pure effort.",
    "The Win leaves the league buzzing.",
    "A Win driven by late execution.",
    "The Win confirms their status.",
    "A Win that changes the narrative.",
    "They pull off a stunning Win.",
    "A methodical Win executed perfectly.",
    "A Win that defines the season.",
    "The ultimate Win to close the week.",
]

_LOSS_TEMPLATES = [
    "A tough Loss the squad will want to forget.",
    "The team falls to a hard Loss.",
    "A costly Loss that raises questions.",
    "They drop this one — a Loss that stings.",
    "The final whistle seals a damaging Loss.",
    "A Loss that shifts the momentum the wrong way.",
    "The scoreboard reflects a difficult Loss.",
    "A Loss the coaching staff will review carefully.",
    "They come up short — a clear Loss.",
    "The post-match mood is heavy after this Loss.",
    "An unexpected Loss shakes the program.",
    "A Loss that was building all match.",
    "A grinding, painful Loss.",
    "The Loss speaks for itself.",
    "They couldn't hold on — a Loss.",
    "A Loss from start to finish.",
    "An emotional Loss for the locker room.",
    "A Loss built on missed opportunities.",
    "The Loss leaves questions in the league.",
    "A Loss driven by late mistakes.",
    "The Loss puts pressure on the season.",
    "A Loss that changes the narrative.",
    "They couldn't pull it off — a Loss.",
    "A Loss that will sting for days.",
    "The Loss confirms the challengers ahead.",
    "A Loss that defines the stakes.",
    "The final Loss to close a hard week.",
]


def render_headline(result: str, context: str, rng: DeterministicRNG, **kwargs) -> str:
    templates = _WIN_TEMPLATES if result == "Win" else _LOSS_TEMPLATES
    return rng.choice(templates)
```

- [ ] **Step 2: Run existing tests to confirm no regressions**

```
python -m pytest tests/ -q -x
```

- [ ] **Step 3: Commit**

```
git add src/dodgeball_sim/voice_aftermath.py
git commit -m "fix: split win/loss headline templates (BUG-06, BUG-13, BUG-14)"
```

---

## Task 2: BUG-07 — Balanced tactic recognized by backend

**Files:**
- Modify: `src/dodgeball_sim/command_center.py`

- [ ] **Step 1: Add "Balanced" to INTENTS and handle it in policy function**

In `command_center.py`, change line:
```python
INTENTS = ("Win Now", "Develop Youth", "Preserve Health", "Evaluate Lineup", "Prepare For Playoffs")
```
to:
```python
INTENTS = ("Balanced", "Win Now", "Develop Youth", "Preserve Health", "Evaluate Lineup", "Prepare For Playoffs")
```

In `_policy_for_intent`, the existing `if/elif` chain falls through for "Balanced" — that's correct (no adjustments = balanced). No other change needed.

- [ ] **Step 2: Confirm the save plan endpoint accepts Balanced**

```
python -m pytest tests/ -q -x
```

- [ ] **Step 3: Commit**

```
git add src/dodgeball_sim/command_center.py
git commit -m "fix: add Balanced to recognized intents (BUG-07)"
```

---

## Task 3: BUG-05 — Compute standings shift in aftermath

**Files:**
- Modify: `src/dodgeball_sim/use_cases.py`

- [ ] **Step 1: Capture standings before sim, compute diff after**

In `use_cases.py`, in `simulate_week`, load standings BEFORE simulating matches, then diff after. Replace the `_build_aftermath` call site:

In `_build_aftermath`, add `standings_before` and `standings_after` params:

```python
def _build_aftermath(
    conn,
    dashboard: dict[str, Any],
    record,
    season_id: str,
    standings_before: list,
    standings_after: list,
    clubs: dict,
) -> dict[str, Any]:
    from dodgeball_sim.rng import DeterministicRNG, derive_seed
    from dodgeball_sim.voice_aftermath import render_headline

    root_seed_val = get_state(conn, "root_seed") or "1"
    rng = DeterministicRNG(derive_seed(int(root_seed_val), "headline", season_id, str(record.week)))
    headline = render_headline(dashboard["result"], "expected", rng)
    box = record.result.box_score["teams"]
    home_survivors = int(box[record.home_club_id]["totals"]["living"])
    away_survivors = int(box[record.away_club_id]["totals"]["living"])

    # Compute standings shift
    before_by_id = {row.club_id: (i + 1) for i, row in enumerate(standings_before)}
    after_by_id = {row.club_id: (i + 1) for i, row in enumerate(standings_after)}
    standings_shift = []
    for club_id, new_rank in after_by_id.items():
        old_rank = before_by_id.get(club_id, new_rank)
        if old_rank != new_rank:
            club = clubs.get(club_id)
            standings_shift.append({
                "club_id": club_id,
                "club_name": club.name if club else club_id,
                "old_rank": old_rank,
                "new_rank": new_rank,
            })
    standings_shift.sort(key=lambda item: item["new_rank"])

    return {
        "headline": headline,
        "match_card": {
            "home_club_id": record.home_club_id,
            "away_club_id": record.away_club_id,
            "winner_club_id": record.result.winner_team_id,
            "home_survivors": home_survivors,
            "away_survivors": away_survivors,
        },
        "player_growth_deltas": [],
        "standings_shift": standings_shift,
        "recruit_reactions": [],
    }
```

In `simulate_week`, capture standings before match simulation and pass them:

```python
# Before simulate_scheduled_match loop:
from .persistence import load_standings as _load_standings
standings_before = _load_standings(conn, season_id)

records = [simulate_scheduled_match(...) for week_match in week_matches]
record = next(item for item in records if item.match_id == scheduled.match_id)
recompute_regular_season_standings(conn, season)

standings_after = _load_standings(conn, season_id)
# sort both the same way as standings_with_all_clubs
clubs_map = clubs  # already loaded above
standings_before_sorted = sorted(standings_before, key=lambda r: (-r.points, -r.elimination_differential, r.club_id))
standings_after_sorted = sorted(standings_after, key=lambda r: (-r.points, -r.elimination_differential, r.club_id))

dashboard = build_post_week_dashboard(conn, plan, record)
...
aftermath = _build_aftermath(conn, dashboard, record, season_id, standings_before_sorted, standings_after_sorted, clubs_map)
```

- [ ] **Step 2: Run tests**

```
python -m pytest tests/ -q -x
```

- [ ] **Step 3: Commit**

```
git add src/dodgeball_sim/use_cases.py
git commit -m "fix: compute real standings shift in match aftermath (BUG-05)"
```

---

## Task 4: BUG-02 / BUG-16 — Key performers: team attribution + 0-impact filter

**Files:**
- Modify: `src/dodgeball_sim/replay_service.py`
- Modify: `frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx`

- [ ] **Step 1: Add club_name to top_performers, filter 0-score players**

In `replay_service.py`, after building `snapshots`, create a `player_club_map` from snapshots:

```python
# Build player→club map from roster snapshots
player_club_map: dict[str, str] = {}
for club_id_key, players in snapshots.items():
    for player in players:
        player_club_map[str(player.get("id", ""))] = club_id_key
```

Then update `top_performers` construction:

```python
top = sorted(stats.items(), key=lambda item: (-score_player(item[1]), item[0]))[:6]
top_performers = [
    {
        "player_id": player_id,
        "player_name": name_map.get(player_id, player_id),
        "club_name": clubs.get(player_club_map.get(player_id, ""), {}).name if clubs.get(player_club_map.get(player_id, "")) else "",
        "score": round(score_player(stat), 1),
        "eliminations_by_throw": stat.eliminations_by_throw,
        "catches_made": stat.catches_made,
        "dodges_successful": stat.dodges_successful,
    }
    for player_id, stat in top
    if score_player(stat) > 0  # BUG-16: exclude zero-impact players
]
```

- [ ] **Step 2: Update KeyPlayersPanel to show team label**

In `KeyPlayersPanel.tsx`, update the article rendering:

```tsx
<article key={player.player_id} className="command-key-player">
  <span>{index + 1}</span>
  <div>
    <strong>{player.player_name}</strong>
    {player.club_name && (
      <span style={{ fontSize: '0.7rem', color: '#64748b', marginLeft: '0.35rem' }}>
        {player.club_name}
      </span>
    )}
    <p>{statLine(player)}</p>
  </div>
</article>
```

Also update the `TopPerformer` type in `frontend/src/types.ts` to add `club_name?: string`.

- [ ] **Step 3: Run tests**

```
python -m pytest tests/ -q -x
```

- [ ] **Step 4: Commit**

```
git add src/dodgeball_sim/replay_service.py frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx frontend/src/types.ts
git commit -m "fix: add team attribution to key performers, filter 0-impact (BUG-02, BUG-16)"
```

---

## Task 5: BUG-04 — Filter test saves from Load Game menu

**Files:**
- Modify: `src/dodgeball_sim/save_service.py`

- [ ] **Step 1: Add test-save filter in list_saves_payload**

```python
_TEST_SAVE_PREFIXES = ("e2e-", "e2e_", "command-aftermath", "codex")

def _is_test_save(path: Path) -> bool:
    stem = path.stem.lower()
    return any(stem.startswith(prefix) for prefix in _TEST_SAVE_PREFIXES)


def list_saves_payload(saves_dir: Path, default_db_path: Path, active_save_path: Path | None) -> dict[str, Any]:
    saves_dir.mkdir(exist_ok=True)
    saves = [
        read_save_meta(db_file)
        for db_file in sorted(saves_dir.glob("*.db"))
        if not _is_test_save(db_file)
    ]
    if default_db_path.exists():
        saves.append(read_save_meta(default_db_path))
    return {"saves": saves, "active_path": str(active_save_path) if active_save_path else None}
```

- [ ] **Step 2: Run tests**

```
python -m pytest tests/ -q -x
```

- [ ] **Step 3: Commit**

```
git add src/dodgeball_sim/save_service.py
git commit -m "fix: hide test/e2e saves from Load Game menu (BUG-04)"
```

---

## Task 6: BUG-10 — Signing Day shows signed player before advancing

**Files:**
- Modify: `src/dodgeball_sim/offseason_service.py`
- Modify: `src/dodgeball_sim/offseason_presentation.py`

- [ ] **Step 1: Keep beat at recruitment index after signing**

In `offseason_service.py::recruit_offseason_payload`, change:
```python
cursor = state_advance(cursor, CareerState.NEXT_SEASON_READY, offseason_beat_index=SCHEDULE_REVEAL_INDEX)
```
to:
```python
recruitment_index = OFFSEASON_CEREMONY_BEATS.index("recruitment")
cursor = state_advance(cursor, CareerState.NEXT_SEASON_READY, offseason_beat_index=recruitment_index)
```

- [ ] **Step 2: Allow can_advance from NEXT_SEASON_READY on non-last beats**

In `offseason_presentation.py::build_beat_response`, change `can_advance`:
```python
"can_advance": (
    (
        cursor.state == CareerState.SEASON_COMPLETE_OFFSEASON_BEAT
        and not is_last
        and not is_recruitment
    )
    or (
        cursor.state == CareerState.NEXT_SEASON_READY
        and not is_last
    )
),
```

- [ ] **Step 3: Run tests**

```
python -m pytest tests/ -q -x
```

- [ ] **Step 4: Commit**

```
git add src/dodgeball_sim/offseason_service.py src/dodgeball_sim/offseason_presentation.py
git commit -m "fix: show signed player on Signing Day before advancing (BUG-10)"
```

---

## Task 7: BUG-12 — Awards sorted for dramatic reveal (MVP last)

**Files:**
- Modify: `src/dodgeball_sim/offseason_presentation.py`

- [ ] **Step 1: Sort awards so MVP/championship are revealed last**

In `build_beat_payload` for `beat_key == "awards"`, after building `result`, sort it:

```python
AWARD_PRESTIGE = {"mvp": 10, "championship": 9, "top_rookie": 3, "best_defender": 2, "best_thrower": 2, "best_catcher": 2, "most_improved": 1}

result.sort(key=lambda award: AWARD_PRESTIGE.get(award["award_type"], 0))
return {"awards": result}
```

This shows lesser awards first (building anticipation) and MVP last (dramatic finale).

- [ ] **Step 2: Run tests**

```
python -m pytest tests/ -q -x
```

- [ ] **Step 3: Commit**

```
git add src/dodgeball_sim/offseason_presentation.py
git commit -m "fix: sort awards by prestige for dramatic reveal, MVP last (BUG-12)"
```

---

## Task 8: BUG-15 — Remove misleading "Legacy save" message

**Files:**
- Modify: `src/dodgeball_sim/offseason_ceremony.py`

- [ ] **Step 1: Remove the legacy-save warning from rookie class preview**

In `offseason_ceremony.py` around line 716, remove the block:
```python
if source == "legacy_free_agents":
    lines.append("")
    lines.append("(Legacy save: showing free-agent fallback only.)")
```

Replace with no-op (just delete those 3 lines). The free-agent fallback is valid for modern saves that haven't generated a prospect pool yet.

- [ ] **Step 2: Run tests**

```
python -m pytest tests/ -q -x
```

- [ ] **Step 3: Commit**

```
git add src/dodgeball_sim/offseason_ceremony.py
git commit -m "fix: remove false-positive legacy save warning in rookie preview (BUG-15)"
```

---

## Task 9: BUG-11 — Dynamic year counter in header

**Files:**
- Modify: `src/dodgeball_sim/web_status_service.py`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add season_year to status API context**

In `web_status_service.py::build_status_payload`:

```python
def build_status_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    cursor = load_career_state_cursor(conn)
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    clubs = load_clubs(conn) if player_club_id else {}
    player_club = clubs.get(player_club_id) if player_club_id else None
    season = load_season(conn, season_id) if season_id else None
    return {
        "status": "ok",
        "state": career_state_payload(cursor),
        "context": {
            "season_id": season_id,
            "player_club_id": player_club_id,
            "player_club_name": player_club.name if player_club else player_club_id,
            "season_year": season.year if season else 2026,
        },
    }
```

- [ ] **Step 2: Store and display year in App.tsx**

Add state:
```tsx
const [seasonYear, setSeasonYear] = useState<number>(2026);
```

In the status fetch:
```tsx
return careerApi.status().then(status => {
  const state = status?.state?.state ?? '';
  setSeasonYear((status?.context as any)?.season_year ?? 2026);
  setScreen(OFFSEASON_STATES.has(state) ? 'offseason' : 'game');
});
```

Replace the hardcoded year on line 137:
```tsx
<p style={...}>{seasonYear}</p>
```

- [ ] **Step 3: Run tests and build**

```
python -m pytest tests/ -q -x
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```
git add src/dodgeball_sim/web_status_service.py frontend/src/App.tsx
git commit -m "fix: display dynamic season year in header (BUG-11)"
```

---

## Task 10: BUG-01 — Season end transitions to offseason

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Detect offseason next_state in onAdvanceWeek**

In `App.tsx`, update the `onAdvanceWeek` callback inside MatchWeek props. Since `postSimResult` holds the last sim result (available as closure), check `next_state` on advance:

```tsx
onAdvanceWeek={() => {
  const isOffseason = OFFSEASON_STATES.has(postSimResult?.next_state ?? '');
  setPostSimResult(null);
  setPostSimThisSession(false);
  if (isOffseason) {
    // Re-fetch status to properly transition to offseason screen
    careerApi.status().then(status => {
      const state = status?.state?.state ?? '';
      setSeasonYear((status?.context as any)?.season_year ?? 2026);
      setScreen(OFFSEASON_STATES.has(state) ? 'offseason' : 'game');
    }).catch(() => window.location.reload());
  }
}}
```

Note: `OFFSEASON_STATES` already contains the string values. `postSimResult?.next_state` is a string like `"season_complete_offseason_beat"`.

- [ ] **Step 2: Verify build compiles**

```
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```
git add frontend/src/App.tsx
git commit -m "fix: transition to offseason screen after final match (BUG-01)"
```

---

## Task 11: BUG-08 — Multi-select stale state fix

**Files:**
- Modify: `frontend/src/components/new-game/StartingRecruitmentStep.tsx`

- [ ] **Step 1: Use functional setState in toggleProspect**

Change:
```tsx
const toggleProspect = (id: string) => {
  const next = new Set(rosterIds);
  if (next.has(id)) next.delete(id);
  else if (next.size < 10) next.add(id);
  setRosterIds(next);
};
```
to:
```tsx
const toggleProspect = (id: string) => {
  setRosterIds(prev => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id);
    else if (next.size < 10) next.add(id);
    return next;
  });
};
```

- [ ] **Step 2: Build frontend**

```
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```
git add frontend/src/components/new-game/StartingRecruitmentStep.tsx
git commit -m "fix: use functional setState for multi-select to prevent stale state (BUG-08)"
```

---

## Task 12: BUG-03 — Navigation from Roster (investigate + fix)

**Files:**
- Modify: `frontend/src/components/Roster.tsx`
- Potentially modify: `frontend/src/components/MatchWeek.tsx`

- [ ] **Step 1: Add error handling to fetchPlan in Roster**

Change:
```tsx
const fetchPlan = () => {
  fetch('/api/command-center')
    .then(r => r.json())
    .then((d: CommandCenterResponse) => setPlanContext({...}));
};
```
to:
```tsx
const fetchPlan = () => {
  fetch('/api/command-center')
    .then(r => r.ok ? r.json() : Promise.reject(r))
    .then((d: CommandCenterResponse) => setPlanContext({
      intent: d.plan.intent,
      dev_focus: d.plan.department_orders?.dev_focus ?? 'BALANCED',
    }))
    .catch(() => { /* non-blocking: plan context just stays null */ });
};
```

- [ ] **Step 2: Scope the post-sim click skip listener to content div only**

In `MatchWeek.tsx`, the `window.addEventListener('click', skip)` fires on ALL clicks including nav buttons. Scope it to the content container instead:

Change in the post-sim skip useEffect:
```tsx
useEffect(() => {
  if (mode !== 'post-sim') return;
  const skip = (e: KeyboardEvent | MouseEvent) => {
    if (e.type === 'keydown' && (e as KeyboardEvent).code !== 'Space') return;
    setRevealStage(4);
  };
  window.addEventListener('keydown', skip);
  const contentEl = document.querySelector('.dm-content');
  if (contentEl) contentEl.addEventListener('click', skip);
  return () => {
    window.removeEventListener('keydown', skip);
    if (contentEl) contentEl.removeEventListener('click', skip);
  };
}, [mode]);
```

- [ ] **Step 3: Build frontend**

```
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```
git add frontend/src/components/Roster.tsx frontend/src/components/MatchWeek.tsx
git commit -m "fix: add error handling to fetchPlan, scope click-skip to content area (BUG-03)"
```

---

## Task 13: Final verification

- [ ] **Step 1: Run full Python test suite**

```
python -m pytest -q
```

- [ ] **Step 2: Build frontend**

```
cd frontend && npm run build
```

- [ ] **Step 3: BUG-09 status note**

BUG-09 (new game flow ordering) is already fixed in the current `SaveMenu.tsx` — the mode choice screen (`view === 'new'`) is shown BEFORE the club picker (`view === 'takeover'`). No code change needed.

---

## Execution Order

Tasks 1–8 are all independent backend/frontend changes that can be done in parallel. Tasks 9–12 touch App.tsx and should be sequenced (9 before 10 since Task 10 uses `setSeasonYear`). Task 13 is the final verification.
