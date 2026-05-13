# Roster Lab Phase 3: Add Player Depth

**Depends on:** Phase 2 complete (RosterToolbar, sorting, improved compact view exist)

**Design system reference:** `docs/design-systems/Roster-Lab-Design-System.md`, sections 6, 14, 18

---

## Goal

Turn the roster from a read-only table into a true lab — clicking a player opens a detail drawer with full ratings, traits, development notes, and match readiness.

---

## What exists after Phase 2

- Sortable roster table with toolbar
- Theater and improved compact views
- All 6 ratings visible in both views
- Archetype badge, potential badge with rarity falloff, potential tier legend

**Current gaps:**
- Rows are not clickable — no way to inspect a single player
- Traits (`growth_curve`, `consistency`, `pressure`) are on the `Player` type but never shown
- No development notes or training recommendation surface
- No newcomer badge shown

---

## What to build

### 1. Make rows clickable

**Edit:** `frontend/src/components/Roster.tsx`

Add a `selectedPlayerId` state. Clicking a `PlayerTheaterRow` or `PlayerCompactRow` sets it. The selected row gets a visual highlight:

```css
border-left: 3px solid rgba(34, 211, 238, 0.45);
background: rgba(34, 211, 238, 0.045);
```

Pass `selected` and `onClick` props down to both row components.

### 2. `PlayerDetailDrawer`

**New file:** `frontend/src/components/roster/PlayerDetailDrawer.tsx`

A right-side panel that slides in when a player is selected. Does not overlay the table — appears in the layout alongside it.

**Props:**
```ts
{
  player: Player;
  starter: boolean;
  onClose: () => void;
}
```

**Layout:**
```
┌─────────────────────────────────┐
│ ✕ Close                         │
│                                 │
│ MIKA THORN                      │
│ Balanced · Age 31 · Starter     │
│                                 │
│ OVERALL                         │
│ 66                    ↑ trend   │
│ Sparkline graph                 │
│                                 │
│ POTENTIAL                       │
│ Elite ★★★★                      │
│ Rare talent. Franchise-         │
│ changing upside.                │
│                                 │
│ RATINGS                         │
│ Accuracy     76  ━━━━━━━━━━     │
│ Power        63  ━━━━━━━        │
│ Dodge        60  ━━━━━━         │
│ Catch        91  ━━━━━━━━━━━━   │
│ Stamina      72  ━━━━━━━━━      │
│ Tactical IQ  71  ━━━━━━━━━      │
│                                 │
│ TRAITS                          │
│ Growth Curve: steady            │
│ Consistency:  0.72              │
│ Pressure:     0.61              │
│                                 │
│ STATUS                          │
│ Newcomer: No                    │
│ Role: Starter                   │
└─────────────────────────────────┘
```

**Data sources (all from `Player` type):**
- `player.name`, `player.archetype`, `player.age`, `player.role`
- `player.overall`, `player.weekly_ovr_history` (for sparkline)
- `player.potential_tier`, `player.scouting_confidence`
- `player.ratings` (all 6)
- `player.traits` (growth_curve, consistency, pressure)
- `player.newcomer`

**Sections:**
| Section | Content |
| ------- | ------- |
| Identity | Name, archetype badge, age, role |
| Overall | OVR number + Sparkline from `weekly_ovr_history` |
| Potential | PotentialBadge (reuse Phase 1 component) with tier description |
| Ratings | All 6 RatingBars (reuse `RatingBar` from `ui.tsx`) |
| Traits | `growth_curve`, `consistency`, `pressure` from `player.traits` |
| Status | Newcomer flag, role badge |

**Rules:**
- Drawer width ~320px, does not overlap the table
- Close button at top right
- Uses `dm-panel` background with `dm-kicker` section labels
- Reuse existing sub-components (`PotentialBadge`, `RatingBar`, `Sparkline`, `ArchetypeBadge`)
- Trait values use descriptive labels where possible (e.g. growth_curve is already a string like "steady")

### 3. Update layout when drawer is open

**Edit:** `frontend/src/components/Roster.tsx`

When `selectedPlayerId` is set, shift to a two-column layout:

```tsx
<div style={{ display: 'grid', gridTemplateColumns: selectedPlayerId ? '1fr 320px' : '1fr', gap: '1rem' }}>
  <div>{/* table */}</div>
  {selectedPlayer && <PlayerDetailDrawer player={selectedPlayer} starter={...} onClose={...} />}
</div>
```

### 4. Newcomer badge

**Edit:** `frontend/src/components/roster/PlayerTheaterRow.tsx`

If `player.newcomer === true`, show a small "NEW" badge next to the player name using `dm-badge-cyan`.

---

## Files to touch

| File | Action |
| ---- | ------ |
| `frontend/src/components/roster/PlayerDetailDrawer.tsx` | Create |
| `frontend/src/components/Roster.tsx` | Edit — add selectedPlayerId state, two-column layout |
| `frontend/src/components/roster/PlayerTheaterRow.tsx` | Edit — add onClick, selected styling, newcomer badge |
| `frontend/src/components/roster/PlayerCompactRow.tsx` | Edit — add onClick, selected styling |

---

## What NOT to build

- Training focus / development recommendation system — requires backend support
- Match readiness indicators — requires match scheduling data
- Player comparison view — future feature
- Editable lineup from the roster screen — out of scope
