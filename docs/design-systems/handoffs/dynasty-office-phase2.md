# Dynasty Office Phase 2: Stabilize the Shell

**Depends on:** Phase 1 complete (RecruitBoard, RecruitFilterPanel, RecruitingSlotsCard exist)

**Design system reference:** `docs/design-systems/Dynasty-Office-Design-System.md`, sections 3, 5

---

## Goal

Give the Dynasty Office page a stable identity shell — a program header and proper tabs — so the Recruit and History workspaces feel like siblings under one roof instead of two unrelated pages.

---

## What exists today

`frontend/src/components/DynastyOffice.tsx` (173 lines) renders:

- `PageHeader` with eyebrow "Dynasty Office", title "Program HQ"
- Two inline tab buttons (`recruit` / `history`) styled as raw buttons
- Tab content: recruit tab shows the Phase 1 recruit board layout; history tab shows `MyProgramView` and `LeagueView`

**Current gaps:**
- No program identity in the header (no club name, season, week)
- Tab switching uses raw `<button>` elements with no active-tab visual treatment
- The recruit and history tabs share no visual shell — they feel disconnected
- `CommandCenterResponse` (available via `/api/command-center`) has `player_club_name` and season/week context, but DynastyOffice doesn't fetch it

---

## What to build

### 1. `DynastyOfficeHeader`

**New file:** `frontend/src/components/dynasty/DynastyOfficeHeader.tsx`

Replaces the current `PageHeader` with program identity context.

**Props:**
```ts
{
  programName: string;
  season: number;
  week: number;
}
```

**Layout:**
```
DYNASTY OFFICE
AUTOPSY COMETS
Season 1 · Week 3
```

**Rules:**
- "DYNASTY OFFICE" is the `dm-kicker` eyebrow
- Program name is large (`text-2xl`, `font-display`, `font-bold`)
- Season/week is secondary text
- Uses `dm-panel` background
- No settings button yet — keep it simple

**Data source:** The program name comes from `DynastyOfficeResponse` — but that response doesn't include season/week. Two options:

**Option A (recommended):** Fetch `/api/command-center` on mount to get `player_club_name` and derive season/week from `current_state`. This endpoint is already used by other screens.

**Option B:** Add season/week to the `DynastyOfficeResponse`. Cleaner long-term but requires backend work.

### 2. `DynastyTabs`

**New file:** `frontend/src/components/dynasty/DynastyTabs.tsx`

Proper tab bar with active-tab styling.

**Props:**
```ts
{
  activeTab: 'recruit' | 'history';
  onTabChange: (tab: 'recruit' | 'history') => void;
}
```

**Layout:**
```
[ Recruit ]  [ History ]
```

**Rules:**
- Active tab gets a cyan bottom border (`border-bottom: 2px solid #22d3ee`) and cyan text
- Inactive tab uses muted text (`text-secondary`)
- Tab bar sits directly below the header with no gap
- Use `dm-kicker` typography for tab labels
- Tabs are buttons, not links (no route change — same component, different content)

### 3. Update `DynastyOffice.tsx` layout

**Edit:** `frontend/src/components/DynastyOffice.tsx`

Replace the current `PageHeader` and inline tab buttons with the new components:

```tsx
<div>
  <DynastyOfficeHeader
    programName={programName}
    season={season}
    week={week}
  />
  <DynastyTabs activeTab={activeTab} onTabChange={setActiveTab} />

  <div style={{ padding: '1.25rem 0' }}>
    {activeTab === 'recruit' && (
      // Phase 1 recruit board layout
    )}
    {activeTab === 'history' && (
      // existing history tab content
    )}
  </div>
</div>
```

Add a fetch for command-center context:

```ts
const [shellContext, setShellContext] = useState<{ name: string; season: number; week: number } | null>(null);

useEffect(() => {
  fetch('/api/command-center')
    .then(r => r.json())
    .then((d: any) => setShellContext({
      name: d.player_club_name,
      season: d.current_state?.season ?? 1,
      week: d.current_state?.week ?? 0,
    }));
}, []);
```

---

## Files to touch

| File | Action |
| ---- | ------ |
| `frontend/src/components/dynasty/DynastyOfficeHeader.tsx` | Create |
| `frontend/src/components/dynasty/DynastyTabs.tsx` | Create |
| `frontend/src/components/DynastyOffice.tsx` | Edit — replace PageHeader and tab buttons, add context fetch |

---

## What NOT to build

- Program settings modal — future feature
- Logo/crest display — no logo system exists yet
- Season selector — only one save file at a time
- History tab content changes — Phase 3
