# PreSim Dashboard Polish

**Date:** 2026-05-14  
**Scope:** `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`

Three focused improvements to the pre-match Command Center screen: Key Threat card content, pre-lock smart flag, and a full redesign of the Starter Readiness section into a head-to-head Match Card.

---

## 1. Key Threat Card — Insight Rows

**Problem:** The card shows name, role, and OVR, then has empty space below.

**Solution:** Three full-width insight rows, each spanning the card width with a severity chip pinned right.

### Layout per row
```
[icon]  [descriptive text — flex 1]      [SEVERITY CHIP]
```

### Three rows (all derived from existing data — no new backend fields)

| Row | Icon | Text | Chip | Color |
|-----|------|------|------|-------|
| OVR gap | ⚡ | "Outrates your top starter ([name]) by +N OVR" | DANGER | red |
| Approach conflict | 🎯 | "[Approach] approach exploits [Role] threats — expect direct pressure" | EXPOSED | orange |
| Counter hint | 🛡️ | "Counter: switch to [approach] to neutralize [Role] threats" | COUNTER | green |

### Derivation logic (frontend only)
- **OVR gap:** `gap = parseInt(threat.ovr) - Math.max(...activePlayers.map(p => p.overall))`
  - If `gap > 0`: chip reads "Outrates your top starter ([name]) by +N OVR" → **DANGER** (red)
  - If `gap <= 0`: chip reads "Your top starter ([name]) covers this threat by +N OVR" → **COVERED** (green)
- **Approach conflict:** compare `selectedIntent` vs `threat.role` using a role→counter map:
  - `Win Now` (Aggressive) vs `Tactical` → conflict
  - `Win Now` (Aggressive) vs `Pressure` → conflict
  - All other combinations → no conflict (chip reads "Approach is compatible with this role" → **ALIGNED**, green)
- **Counter hint:** same role→counter map for the suggestion text:
  - `Tactical` → Control, `Pressure` → Defensive, `Balanced` → Balanced, others → Control

---

## 2. Pre-Lock Smart Flag — Replaces Stats Strip

**Problem:** The bottom strip (Elim Diff / Last result / Plans count) provides no decision-making value at plan-lock time.

**Solution:** Remove the three-stat strip entirely. Replace with a single contextual flag row above the Lock button.

### Two states

**Warning (orange background):**
```
⚠️  Plan conflict: Aggressive approach vs. Tactical threat — consider Control.
```

**OK (green background):**
```
✓  Plan looks solid. Control approach aligns with the Tactical threat. Stamina is healthy.
```

### Flag logic (frontend, no backend changes)
1. Check `selectedIntent` vs `threat.role` using the same role→counter map as the insight rows.
2. Check avg stamina: `activePlayers.filter(p => p.stamina !== undefined && p.stamina < 60).length > 1` → flag fatigue.
3. If any conflict detected → warning state. Otherwise → OK state.

The flag is purely informational. It does not block the Lock button.

---

## 3. Match Card — Starter Readiness Redesign

**Problem:** Listing your own starters duplicates the Roster tab. No matchup context. OVR numbers unlabeled. Section header "3 pts" meaningless without a label.

**Solution:** Replace the starter list with a head-to-head matchup leverage chart comparing your starters to the opponent's starters slot by slot.

### Backend changes required

**File:** `src/dodgeball_sim/command_center.py`

1. Add `opponent_lineup` to `CommandCenterPlan` — an object with a `players` array using the same shape as the existing lineup players: `{id, name, overall, stamina}`.
2. Fetch the opponent's starting 6 from their roster using the same selection logic as `_build_lineup()`.
3. Extend `_player_summary()` to be reusable for opponent players (it already is — just call it for each).

**Frontend type change:** Add `opponent_lineup?: { players: LineupPlayer[] }` to `CommandCenterPlan` in `types.ts`.

**Fallback:** If `opponent_lineup` is absent or empty (e.g. week 1 before opponent data exists), render the Match Card in a degraded state — show your starters only with a "Opponent lineup unavailable" placeholder in the right column. Do not crash or hide the section entirely.

**Opponent lineup fetch logic:** Use the opponent team's current active roster sorted by `overall()` descending, top 6. Do not simulate or predict — use their actual current player ratings.

### Component layout

```
[NORTHWOOD IRONCLADS]  VS  [LUNAR SYNDICATE]          [OVR | STA]
┌─────────────────────────────────────────────────────────────────┐
│  IRONCLADS   74          OVERALL EDGE           68   SYNDICATE  │
│  Team OVR            +32 Ironclads               Team OVR       │
└─────────────────────────────────────────────────────────────────┘
◀ IRONCLADS ADVANTAGE    Longer bar = larger OVR mismatch    SYNDICATE ADVANTAGE ▶
──────────────────────────────────────────────────────────────────
 Avery Voss  85       ◀ IRON +17   [████████░░░░░░░░░]    68  Jin Park
 Cass Frost  83       ◀ IRON +13   [██████░░░░░░░░░░░]    70  Lex Dorn
 Dex Vale    58         SYN +13 ▶  [░░░░░░░░░██████░░]    71  Rho Vance
 Ezra Okafor 75       ◀ IRON +12   [█████░░░░░░░░░░░░]    63  Ori Vale
 Avery Helix 83       ◀ IRON +9    [████░░░░░░░░░░░░░]    74  Cas Wren
 Nex Crane   59         SYN +6 ▶   [░░░░░░░░░███░░░░░]    65  Mika Keene
──────────────────────────────────────────────────────────────────
4 slot advantages                           2 slot disadvantages
```

### Bar math
- Bar extends **from the center outward** toward the winning side.
- `maxGap = Math.max(...slots.map(s => Math.abs(s.gap)))`
- `barWidth = (Math.abs(gap) / maxGap) * 50` (percent of track)
- Cyan bar: `right: 50%; width: barWidth%` (grows left)
- Red bar: `left: 50%; width: barWidth%` (grows right)
- Center divider: 2px line at `left: 50%`

### Gap labels
- Your team wins slot: `◀ ABBR +N` (cyan)
- Opponent wins slot: `ABBR +N ▶` (red)
- Team abbreviation: last word of team name, first 4 chars uppercase — e.g. "Northwood Ironclads" → "IRON", "Lunar Syndicate" → "SYND"

### OVR/STA toggle
- Toggles all stat values, bar widths, gap labels, and summary stats simultaneously
- Rows **re-sort by gap magnitude** on toggle — biggest mismatch always at top
- OVR mode: default sort; STA mode: sort by stamina gap magnitude descending
- Summary strip updates: "OVERALL EDGE" ↔ "STAMINA EDGE", avg values swap to stamina

### Section header
- Remove the `{userStanding?.points} pts` label from the section heading — no longer needed since the old strip and this unlabeled number are both removed.
- Section label changes from "STARTER READINESS" to the team VS header shown in the card itself.

### Stat coloring
- Winning side stat: cyan (`#22d3ee`)
- Losing side stat: red (`#f43f5e`)
- No name dimming — both names always full white

### Tally row
- `flex; justify-content: space-between`
- Left: `[N] slot advantages` (cyan N)
- Right: `[N] slot disadvantages` (red N)
- Top border separates from the last row

---

## Implementation order

1. Backend: extend `_player_summary()` and add `opponent_lineup` to plan response
2. Frontend types: add `opponent_lineup` to `CommandCenterPlan`
3. Key Threat card insight rows
4. Match Card layout (OVR mode only first, then add STA toggle)
5. Smart pre-lock flag (remove old strip, add flag component)
