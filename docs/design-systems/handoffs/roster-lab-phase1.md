# Roster Lab Phase 1: Clarify Existing Screen

**Design system reference:** `docs/design-systems/Roster-Lab-Design-System.md`

---

## Goal

Improve the visual hierarchy of the existing roster table so potential tier, archetype, and OVR are clearly separated signals. This phase doesn't add new features — it refines what's already there.

---

## What exists today

The roster screen lives in `frontend/src/components/Roster.tsx` (157 lines). It renders:

- `PageHeader` with eyebrow "Roster Lab", stats showing Avg Age, Avg OVR, Trend, DevFocusChip, and a compact/theater toggle
- A `<table>` with two view modes:
  - **Theater view:** `PlayerTheaterRow` — shows player identity, 4 rating bars (accuracy, power, dodge, catch), PotentialBadge, OVR+Sparkline, and role badge
  - **Compact view:** `PlayerCompactRow` — shows name, ACC, POW, DOD, CAT, OVR, Status

**Existing sub-components** in `frontend/src/components/roster/`:
- `PlayerTheaterRow.tsx` — the full row with rating bars and potential badge
- `PlayerCompactRow.tsx` — minimal row
- `PotentialBadge.tsx` — shows "Potential: {tier}" with stars for scouting confidence
- `Sparkline.tsx` — mini OVR trend line from `weekly_ovr_history`

**Key data:** `Player` type has `ratings` (accuracy, power, dodge, catch, stamina, tactical_iq), `potential_tier`, `scouting_confidence`, `archetype` ("Balanced"/"Power"/"Tactical"), `overall`, `role`, `age`, `newcomer`.

**Current gaps:**
- Only 4 of 6 ratings shown (missing stamina, tactical_iq)
- PotentialBadge has no visual rarity falloff — all tiers look the same
- Archetype has no color distinction
- No potential tier legend

---

## What to build

### 1. Refine `PotentialBadge` visual treatment

**Edit:** `frontend/src/components/roster/PotentialBadge.tsx`

Currently all tiers use the same cyan color. Add rarity-based visual falloff:

| Tier    | Text Color | Border | Glow |
| ------- | ---------- | ------ | ---- |
| Elite   | Gold (#facc15) | Gold border | Subtle gold glow |
| High    | Cyan (#22d3ee) | Cyan border | Subtle cyan glow |
| Solid   | Lime (#84cc16) | Muted border | None |
| Limited | Slate (#94a3b8) | Muted border | None |

**Rules:**
- Only Elite gets gold + glow. High is bright but not legendary.
- Solid and Limited use progressively muted treatment.
- Keep the star rating for scouting confidence.

### 2. Add `ArchetypeBadge` component

**New file:** `frontend/src/components/roster/ArchetypeBadge.tsx`

A small colored badge showing the player's archetype.

**Props:**
```ts
{ archetype: string }  // "Balanced" | "Power" | "Tactical"
```

**Color mapping:**
| Archetype | Badge Class | Color |
| --------- | ----------- | ----- |
| Balanced  | `dm-badge-cyan` | Cyan |
| Power     | `dm-badge-orange` | Orange |
| Tactical  | `dm-badge-purple` | Purple |

Fall back to `dm-badge-slate` for unknown values.

### 3. Add `PotentialTierLegend` component

**New file:** `frontend/src/components/roster/PotentialTierLegend.tsx`

A compact legend bar pinned below the roster table.

**Layout:**
```
POTENTIAL TIERS
[Gold] Elite 90+    [Cyan] High 80–89    [Green] Solid 65–79    [Gray] Limited <65
```

**Rules:**
- Use the same tier colors as PotentialBadge
- Reduced size — explanatory, not decorative
- Sits at the bottom of the roster panel

### 4. Update `PlayerTheaterRow` to show all 6 ratings

**Edit:** `frontend/src/components/roster/PlayerTheaterRow.tsx`

Currently shows accuracy, power, dodge, catch in a 2x2 grid. Change to a 3x2 grid adding stamina and tactical_iq:

```
Accuracy  76    Power      63
Dodge     60    Catch      91
Stamina   72    Tactical IQ 71
```

Also add the `ArchetypeBadge` next to the player name.

### 5. Update `Roster.tsx` to include legend

Add `<PotentialTierLegend />` after the closing `</table>` tag.

---

## Files to touch

| File | Action |
| ---- | ------ |
| `frontend/src/components/roster/PotentialBadge.tsx` | Edit — add tier-based color/glow |
| `frontend/src/components/roster/ArchetypeBadge.tsx` | Create |
| `frontend/src/components/roster/PotentialTierLegend.tsx` | Create |
| `frontend/src/components/roster/PlayerTheaterRow.tsx` | Edit — add all 6 ratings + ArchetypeBadge |
| `frontend/src/components/Roster.tsx` | Edit — add PotentialTierLegend |

---

## What NOT to build

- Sorting/filtering toolbar — Phase 2
- Player detail drawer — Phase 3
- Compact view changes — Phase 2
