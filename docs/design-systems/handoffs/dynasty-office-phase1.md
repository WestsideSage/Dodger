# Dynasty Office Phase 1: Replace the Recruiting List

**Design system reference:** `docs/design-systems/Dynasty-Office-Design-System.md`, sections 6–8

---

## Goal

Replace the vertical prospect list with a card-grid recruit board, add a filter panel and resource slots card so the recruiting page answers "who should I spend my limited actions on?" instead of "scroll forever."

---

## What exists today

The Dynasty Office screen lives in `frontend/src/components/DynastyOffice.tsx` (173 lines). The recruit tab renders:

- `CredibilityStrip` — shows tier grade, score, evidence bullets (in `dynasty/CredibilityStrip.tsx`)
- A 3-column grid layout: credibility strip | prospect list + budget display | staff room
- **Prospect list:** Renders each prospect as a `ProspectCard` in a vertical stack
- **Budget display:** Inline text showing scout/contact/visit as `used / max`
- `ProspectCard` (`dynasty/ProspectCard.tsx`) — full card with name, hometown, archetype, OVR band, fit score, interest evidence, and Scout/Contact/Visit action buttons with budget checking

**Key data from `DynastyOfficeResponse`:**
- `recruiting.credibility` — `{ score, grade, evidence[] }`
- `recruiting.budget` — `{ scout: [used, max], contact: [used, max], visit: [used, max] }`
- `recruiting.prospects[]` — `{ player_id, name, hometown, public_archetype, public_ovr_band, fit_score, promise_options, active_promise, interest_evidence }`
- `recruiting.rules` — recruiting rules text
- `staff_market.current_staff[]` — `{ department, name, rating_primary, rating_secondary, voice }`

**Current pain points:**
- Prospects render in a long vertical list — no grid, no pagination
- No filtering or sorting controls
- Budget display is inline text, not a visible resource card
- No "recruit board" feel — feels like a raw data dump

---

## What to build

### 1. `RecruitingSlotsCard`

**New file:** `frontend/src/components/dynasty/RecruitingSlotsCard.tsx`

A compact resource card showing remaining recruiting actions.

**Props:**
```ts
{
  scout: [number, number];    // [used, max]
  contact: [number, number];
  visit: [number, number];
}
```

**Layout:**
```
WEEKLY RECRUITING SLOTS

Scout      0 / 3     ━━━━━━━━━━━━
Contact    0 / 5     ━━━━━━━━━━━━
Visit      0 / 1     ━━━━━━━━━━━━
```

**Rules:**
- Show as three rows with label, count, and a mini progress bar
- Progress bar fills as slots are used (full = all used, empty = all available)
- When a slot type is exhausted, show it as muted/red text
- Card sits at the top of the recruit page alongside the credibility strip

### 2. `RecruitFilterPanel`

**New file:** `frontend/src/components/dynasty/RecruitFilterPanel.tsx`

A left-rail filter panel for the recruit board.

**Props:**
```ts
{
  filters: RecruitFilters;
  onChange: (filters: RecruitFilters) => void;
  onClear: () => void;
}
```

**Filter type:**
```ts
type RecruitFilters = {
  search: string;
  archetype: string | 'any';
  minFitScore: number;
};
```

**Layout:**
```
FILTERS                    [Clear]

Search
[ name, hometown... ]

Archetype
[ All ▼ ]

Min Fit Score
[ 0 ━━━━━━━━━━━━━━━ 100 ]
```

**Rules:**
- Search matches against `prospect.name` and `prospect.hometown`
- Archetype dropdown: All, Balanced, Power, Tactical
- Fit score: a simple number input or range slider with min value
- Clear button resets all filters
- Filter panel width ~240px on desktop, hidden on mobile with a toggle

### 3. `RecruitBoard`

**New file:** `frontend/src/components/dynasty/RecruitBoard.tsx`

The main grid container replacing the vertical prospect list.

**Props:**
```ts
{
  prospects: Prospect[];
  budget: { scout: [number, number]; contact: [number, number]; visit: [number, number] };
  onAction: (prospectId: string, action: 'scout' | 'contact' | 'visit') => void;
  sortBy: string;
  onSortChange: (sort: string) => void;
}
```

**Layout:**
```
RECRUIT BOARD     12 prospects            Sort: Fit Score ▼

┌──────────┐  ┌──────────┐  ┌──────────┐
│ Card     │  │ Card     │  │ Card     │
└──────────┘  └──────────┘  └──────────┘
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Card     │  │ Card     │  │ Card     │
└──────────┘  └──────────┘  └──────────┘
```

**Sort options:**
| Value | Label | Logic |
| ----- | ----- | ----- |
| `fit` | Fit Score | `fit_score` desc |
| `ovr` | Overall | `public_ovr_band[1]` desc (sort by max of range) |
| `name` | Name | `name` asc |

**Rules:**
- Grid layout: `grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))`
- Board header shows result count and sort dropdown
- Each card is the existing `ProspectCard` (reuse, don't rebuild)
- If no prospects match filters, show: "No prospects match your filters."

### 4. Refine `ProspectCard` for grid layout

**Edit:** `frontend/src/components/dynasty/ProspectCard.tsx`

The existing ProspectCard is designed for a vertical list. Adjust for grid:
- Set a consistent card height so the grid doesn't stagger
- Ensure action buttons sit at the bottom of the card
- Add a `RecruitFitBadge` — a colored label derived from `fit_score`:

```ts
function getFitLabel(score: number) {
  if (score >= 80) return { label: 'Strong Fit', className: 'dm-badge-cyan' };
  if (score >= 60) return { label: 'Good Fit', className: 'dm-badge-slate' };
  if (score >= 40) return { label: 'Neutral', className: 'dm-badge-slate' };
  return { label: 'Risk', className: 'dm-badge-orange' };
}
```

### 5. Update `DynastyOffice.tsx` recruit tab layout

**Edit:** `frontend/src/components/DynastyOffice.tsx`

Replace the current recruit tab content with the new layout:

```tsx
{/* Top summary row */}
<div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
  <CredibilityStrip ... />
  <RecruitingSlotsCard
    scout={recruiting.budget.scout}
    contact={recruiting.budget.contact}
    visit={recruiting.budget.visit}
  />
</div>

{/* Main workspace */}
<div style={{ display: 'grid', gridTemplateColumns: '240px 1fr 280px', gap: '1rem' }}>
  <RecruitFilterPanel filters={filters} onChange={setFilters} onClear={clearFilters} />
  <RecruitBoard
    prospects={filteredProspects}
    budget={recruiting.budget}
    onAction={handleRecruitAction}
    sortBy={sortBy}
    onSortChange={setSortBy}
  />
  {/* Staff room stays in right column */}
  <StaffRoomCard ... />
</div>
```

Add filter state and filtering logic to `DynastyOffice.tsx`:

```ts
const [filters, setFilters] = useState<RecruitFilters>({ search: '', archetype: 'any', minFitScore: 0 });
const [sortBy, setSortBy] = useState('fit');

const filteredProspects = useMemo(() => {
  let result = recruiting.prospects;
  if (filters.search) {
    const q = filters.search.toLowerCase();
    result = result.filter(p => p.name.toLowerCase().includes(q) || p.hometown.toLowerCase().includes(q));
  }
  if (filters.archetype !== 'any') {
    result = result.filter(p => p.public_archetype === filters.archetype);
  }
  if (filters.minFitScore > 0) {
    result = result.filter(p => p.fit_score >= filters.minFitScore);
  }
  // sort
  if (sortBy === 'fit') result.sort((a, b) => b.fit_score - a.fit_score);
  else if (sortBy === 'ovr') result.sort((a, b) => b.public_ovr_band[1] - a.public_ovr_band[1]);
  else if (sortBy === 'name') result.sort((a, b) => a.name.localeCompare(b.name));
  return result;
}, [recruiting.prospects, filters, sortBy]);
```

---

## Files to touch

| File | Action |
| ---- | ------ |
| `frontend/src/components/dynasty/RecruitingSlotsCard.tsx` | Create |
| `frontend/src/components/dynasty/RecruitFilterPanel.tsx` | Create |
| `frontend/src/components/dynasty/RecruitBoard.tsx` | Create |
| `frontend/src/components/dynasty/ProspectCard.tsx` | Edit — adjust for grid layout, add fit badge |
| `frontend/src/components/DynastyOffice.tsx` | Edit — new recruit tab layout, add filter/sort state |

---

## What NOT to build

- Recruit detail drawer (click card → side panel) — future feature
- Shortlist / star system — future feature
- Pagination — not needed unless prospect counts grow past ~50
- History tab changes — Phase 3
- DynastyOfficeHeader or DynastyTabs — Phase 2
