# Roster Lab Phase 2: Improve Scanning

**Depends on:** Phase 1 complete (PotentialBadge refined, ArchetypeBadge and PotentialTierLegend exist)

**Design system reference:** `docs/design-systems/Roster-Lab-Design-System.md`, sections 5, 17, 18

---

## Goal

Make the roster feel like a management tool — sortable, scannable, and responsive to how the player wants to evaluate their team.

---

## What exists after Phase 1

The roster screen (`frontend/src/components/Roster.tsx`, 157 lines) renders:

- `PageHeader` with eyebrow "Roster Lab", stats (Avg Age, Avg OVR, Trend, DevFocusChip), compact/theater toggle button
- A `<table>` with two view modes controlled by `isCompact` state
- **Theater view:** `PlayerTheaterRow` — player identity, 6 rating bars, refined PotentialBadge, ArchetypeBadge, OVR+Sparkline, role badge
- **Compact view:** `PlayerCompactRow` — name, 4 compact RatingBars (ACC, POW, DOD, CAT), OVR, role badge
- `PotentialTierLegend` below the table

**Current sorting:** Hardcoded in a `useMemo` — starters first, then by OVR descending, then age ascending. No user-controllable sort.

**Current compact view gaps:** Only shows 4 of 6 ratings, no potential tier, no archetype, no age.

---

## What to build

### 1. `RosterToolbar`

**New file:** `frontend/src/components/roster/RosterToolbar.tsx`

A control bar between the PageHeader and the table.

**Props:**
```ts
{
  sortBy: string;
  onSortChange: (sort: string) => void;
  isCompact: boolean;
  onToggleCompact: () => void;
}
```

**Layout:**
```
[Sort: Overall ▼]                              [Compact] [Theater]
```

**Sort options:**
| Value | Label | Sort logic |
| ----- | ----- | ---------- |
| `overall` | Overall | `player.overall` desc |
| `potential` | Potential | tier order (Elite > High > Solid > Limited), then OVR |
| `age` | Age | `player.age` asc |
| `name` | Name | `player.name` asc |

**Rules:**
- Sort dropdown uses `dm-panel` styling with `dm-kicker` labels
- View toggle replaces the inline button currently in the PageHeader stats area
- Keep it compact — one row, not a full filter panel

### 2. Add sorting logic to `Roster.tsx`

**Edit:** `frontend/src/components/Roster.tsx`

Replace the hardcoded `useMemo` sort with a `sortBy` state variable. Starters-first grouping should still apply within each sort. The sort function needs a tier-order map for potential sorting:

```ts
const TIER_ORDER: Record<string, number> = { Elite: 0, High: 1, Solid: 2, Limited: 3 };
```

Move the compact toggle out of the `PageHeader` stats area and into the `RosterToolbar`.

### 3. Improve `PlayerCompactRow`

**Edit:** `frontend/src/components/roster/PlayerCompactRow.tsx`

The compact view currently shows only name, 4 ratings, OVR, and role. Update to show a more scannable summary:

**New column layout:**
```
Name          Archetype   Age   ACC  POW  DOD  CAT  STA  TIQ  OVR  Potential  Role
Mika Thorn    Balanced    31    76   63   60   91   72   71   66   Elite      Starter
```

**Changes:**
- Add archetype as a colored text label (not full badge — too wide for compact)
- Add age column
- Add stamina (STA) and tactical_iq (TIQ) columns
- Add potential tier as a colored text label
- Keep role badge

### 4. Add column header tooltips

**Edit:** `frontend/src/components/Roster.tsx`

Add `title` attributes to the `<th>` elements in both views:

| Column Header | Tooltip |
| ------------- | ------- |
| ACC | Accuracy — throwing precision |
| POW | Power — throw speed and force |
| DOD | Dodge — evasion ability |
| CAT | Catch — ball-catching skill |
| STA | Stamina — endurance over time |
| TIQ | Tactical IQ — reads and positioning |
| OVR | Overall — composite player rating |
| Potential | Future ceiling based on growth curve |

### 5. Update compact view `<thead>`

**Edit:** `frontend/src/components/Roster.tsx`

Update the compact view column headers to match the new columns:

```
Name | Type | Age | ACC | POW | DOD | CAT | STA | TIQ | OVR | Pot | Role
```

---

## Files to touch

| File | Action |
| ---- | ------ |
| `frontend/src/components/roster/RosterToolbar.tsx` | Create |
| `frontend/src/components/roster/PlayerCompactRow.tsx` | Edit — add archetype, age, STA, TIQ, potential |
| `frontend/src/components/Roster.tsx` | Edit — add sortBy state, RosterToolbar, move compact toggle, update thead |

---

## What NOT to build

- Filter panel (archetype, role, potential filters) — keep it simple for now
- Clickable rows / player detail drawer — Phase 3
- Drag-to-reorder lineup — out of scope
