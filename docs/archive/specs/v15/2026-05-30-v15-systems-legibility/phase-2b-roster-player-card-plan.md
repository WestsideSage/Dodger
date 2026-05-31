# V15 Phase 2b — Roster & Player Card Legibility: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the Phase 1 legibility toolkit to the Roster screen and PlayerDetailModal, eliminating the four legibility gaps called out in Appendix A of the planning report: archetype redundancy, unreadable growth language, undifferentiated growth status for mid-tier players, v2 attribute tooltips, sort-direction opacity, and flat bio. No engine changes; presentation-layer and payload-plumbing only.

**Architecture:** Six tasks, each independently committable. Tasks 1–5 are pure frontend edits consuming the Phase 1 toolkit. Task 6 is a small backend payload addition (bio fields) with a corresponding frontend update and a pytest gate. The Phase 1 barrel (`frontend/src/legibility/`) must be merged before any task here begins.

**Tech Stack:** React 19 + TypeScript ~6 + Vite 8. Inline `style={{}}` + `dm-*` classNames (no Tailwind utilities). Verification: `npm run build && npm run lint` from `frontend/`; `npm run e2e` from repo root; `python -m pytest -q` for Task 6.

> **Pre-flight for the executor:**
> - Branch off `main` (after Phase 1 merges): `git checkout -b feat/v15-phase2b-roster-card`
> - Confirm green baseline: from `frontend/`, `npm run build && npm run lint` PASS; `python -m pytest -q` PASS.
> - Confirm Phase 1 is present: `ls frontend/src/legibility/` should show `terms.ts`, `TermTip.tsx`, `KnownValue.tsx`, `ProofChip.tsx`, `EmptyState.tsx`, `PipelineEmblem.tsx`, `index.ts`.
> - Do **not** touch any engine or RNG file. The `python tools/tier_engine_health_probe.py` probe must be unchanged before and after this entire phase.

---

## Archetype vocabulary reference (read before any TermTip task)

The `player.role` field (set by `archetype_for_player()` in `recruitment.py`) maps to exactly 8 display strings via `_RECRUITMENT_DISPLAY_NAMES`. These are the only strings that ever appear in the Roster or Player Card:

| `player.role` string | Underlying `PlayerArchetype` enum |
|---|---|
| `"Sharpshooter"` | `THROWER` |
| `"Net Specialist"` | `CATCHER` |
| `"Ball Hawk"` | `BALL_HAWK` |
| `"Iron Anchor"` | `DODGER_ANCHOR` |
| `"Two-Way Threat"` | `THROWER_CATCHER` |
| `"Skirmisher"` | `THROWER_DODGER` |
| `"Possession Specialist"` | `CATCHER_HAWK` |
| `"Hit-and-Run"` | `HAWK_DODGER` |

The seeded `TERMS` in Phase 1 contains only 4 archetype keys (`archetype.thrower`, `archetype.hawk_dodger`, `archetype.net_specialist`, `archetype.skirmisher`). Task 1 must **append** the remaining 4 keys (append-only, no rebase risk) and correct the mismatch between the existing seeded label copy and the real display strings.

---

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `frontend/src/legibility/terms.ts` | Append 4 missing archetype term keys; correct existing archetype copy to match real role strings | 1 |
| `frontend/src/components/Roster.tsx` | Remove redundant archetype badge; wrap TermTip on surviving badge; directional sort affordances | 1, 5 |
| `frontend/src/components/PlayerDetailModal.tsx` | Growth relabelling (TermTip); high-upside ProofChip; v2 attr TermTip; bio personality section | 2, 3, 4, 6 |
| `frontend/src/components/ceremonies/DevelopmentResults.tsx` | v2 attr TermTip on attribute delta labels | 4 |
| `frontend/src/types.ts` | Add `bio_strongest_attr` / `bio_secondary_attr` fields to `Player` interface | 6 |
| `src/dodgeball_sim/web_status_service.py` | Emit `bio_strongest_attr` / `bio_secondary_attr` in roster payload | 6 |
| `tests/test_web_status_service.py` (or nearest roster payload test) | Assert bio fields are present and are non-empty strings | 6 |

---

## Task 1: Archetype de-duplication + TermTip (Roster)

**Context:** In `Roster.tsx`, `archetypeBadge(player.role)` is called **twice** per row: once in the player meta line (line ~327, inside the `rl-player-meta` div) and again as a standalone `<td>` at line ~394. The Role column (`<th>Role</th>`) is the informative one; the meta-line copy is decorative redundancy. Remove the meta-line copy, keep the Role `<td>`, and wrap its badge in a `TermTip` so the archetype meaning is always one interaction away.

**Event-propagation note:** Every `<tr>` has `onClick={() => setSelectedPlayer(player)}` (line ~318). `TermTip` renders a `<button>`. Without `stopPropagation`, tapping the TermTip toggle also opens the PlayerDetailModal. The TermTip button already calls `onClick={() => setOpen(v => !v)}` — add `e.stopPropagation()` in the wrapper `onClick` on the `<td>` that hosts the TermTip, not inside the toolkit component itself (the toolkit is not to be modified).

**Phase 1 hand-off:** 4 of the 8 archetype TermIds were pre-seeded with incorrect labels. Append the missing 4 and correct the copy as part of this task's first commit (terms-only, so it can land as a standalone append before the Roster edit).

**Files:**
- Edit: `frontend/src/legibility/terms.ts`
- Edit: `frontend/src/components/Roster.tsx`

- [ ] **Step 1: Append missing archetype keys + correct existing seeded copy in `terms.ts`**

The four seeded keys used generic mechanic descriptions that don't match the real role strings. Edit their labels to match the display names exactly, then append the 4 missing keys. The complete correct archetype block (replace the 4 existing seeded archetype entries and append below them):

```ts
// --- Player archetypes (mechanical: drive match behavior) ---
// Labels MUST match the display strings from recruitment.archetype_for_player().
'archetype.sharpshooter': {
  label: 'Sharpshooter',
  plain: 'Aggressive attacker who prioritizes high-accuracy throws to eliminate opponents.',
  why: 'Higher throw volume and accuracy — your primary source of eliminations.',
  kind: 'mechanical',
},
'archetype.net_specialist': {
  label: 'Net Specialist',
  plain: 'Catch-focused defender who turns incoming throws into resurrections.',
  why: 'Catches out the thrower AND brings a teammate back — high swing on each attempt.',
  kind: 'mechanical',
},
'archetype.ball_hawk': {
  label: 'Ball Hawk',
  plain: 'Court-control player who hunts loose balls and accumulates possession.',
  why: 'Keeps your team armed and limits opponent ammo — compounds over a long match.',
  kind: 'mechanical',
},
'archetype.iron_anchor': {
  label: 'Iron Anchor',
  plain: 'Evasive survivor who is hard to eliminate and stays alive deep into rallies.',
  why: 'Late-rally staying power; buys time for teammates to catch or reset.',
  kind: 'mechanical',
},
'archetype.two_way_threat': {
  label: 'Two-Way Threat',
  plain: 'Hybrid who throws with authority and attempts catches on incoming balls.',
  why: 'No single defensive answer — opponents cannot key on one vulnerability.',
  kind: 'mechanical',
},
'archetype.skirmisher': {
  label: 'Skirmisher',
  plain: 'Mobile attacker who throws quickly and retreats to avoid return fire.',
  why: 'Generates elimination attempts without committing to a long throw exchange.',
  kind: 'mechanical',
},
'archetype.possession_specialist': {
  label: 'Possession Specialist',
  plain: 'Catch-and-control player who prioritizes holding the ball over throwing.',
  why: 'Starves the opponent of ammo; forces them to take lower-percentage risks.',
  kind: 'mechanical',
},
'archetype.hit_and_run': {
  label: 'Hit-and-Run',
  plain: 'Fast attacker who strikes and repositions before opponents can respond.',
  why: 'Disrupts defensive positioning without exposing themselves to counterattacks.',
  kind: 'mechanical',
},
```

> **Important:** Remove the 4 old seeded keys (`archetype.thrower`, `archetype.hawk_dodger`, `archetype.net_specialist` [old], `archetype.skirmisher` [old]) from their original positions in the file and replace them with the 8 new entries above. Keep the rest of `TERMS` unchanged. Since `TermId` is a closed union, the tsc gate will catch any stale reference at compile time — the self-check in Step 2 confirms this.

- [ ] **Step 2: Compile gate (terms-only)**

Run (from `frontend/`): `npm run build`
Expected: PASS. If any existing code referenced the 4 old keys, tsc will flag them here — fix those references now, before touching Roster.tsx.

- [ ] **Step 3: Commit terms append**

```bash
git add frontend/src/legibility/terms.ts
git commit -m "feat(v15-p2b): append full 8-archetype term set, correct labels to match role strings

Four pre-seeded keys had generic labels that didn't match the display
strings emitted by archetype_for_player(). Replace with 8 keys that
match the real _RECRUITMENT_DISPLAY_NAMES labels exactly.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 4: Remove the redundant meta-line archetype badge in `Roster.tsx`**

In the `<td>` that renders `rl-player-meta` (around line 324), find and delete `{archetypeBadge(player.role)}` and its separator dot. Keep `<span>Age {player.age}</span>` and the starter pin. The meta line should become:

```tsx
<div className="rl-player-meta">
  <span>Age {player.age}</span>
  {starter && <span className="rl-pin">●</span>}
</div>
```

- [ ] **Step 5: Add the `ROLE_TERM_ID` lookup map and wrap the Role `<td>` in a TermTip**

Add this lookup constant near the top of `Roster.tsx` (after the existing imports), after all other import statements:

```tsx
import { TermTip } from '../legibility';
import type { TermId } from '../legibility';

// Maps player.role strings to their TermId. Exhaustive over all 8 archetypes
// that archetype_for_player() can emit (see recruitment._RECRUITMENT_DISPLAY_NAMES).
const ROLE_TERM_ID: Record<string, TermId> = {
  'Sharpshooter':         'archetype.sharpshooter',
  'Net Specialist':       'archetype.net_specialist',
  'Ball Hawk':            'archetype.ball_hawk',
  'Iron Anchor':          'archetype.iron_anchor',
  'Two-Way Threat':       'archetype.two_way_threat',
  'Skirmisher':           'archetype.skirmisher',
  'Possession Specialist':'archetype.possession_specialist',
  'Hit-and-Run':          'archetype.hit_and_run',
};
```

Then in the table body, replace the Role `<td>` (currently `<td>{archetypeBadge(player.role)}</td>`) with:

```tsx
<td
  onClick={(e) => e.stopPropagation()}
  style={{ cursor: 'default' }}
>
  {ROLE_TERM_ID[player.role]
    ? (
      <TermTip term={ROLE_TERM_ID[player.role] as TermId}>
        {archetypeBadge(player.role)}
      </TermTip>
    )
    : archetypeBadge(player.role)
  }
</td>
```

The `stopPropagation` on the `<td>` prevents the row's `onClick → setSelectedPlayer` from firing when the player taps the TermTip toggle. The fallback (bare badge) covers any unexpected role string that is not yet in the map.

- [ ] **Step 6: Confirm compact view Role column also gets TermTip**

In compact view the table has a `<th>Role</th>` header and each row also renders `<td>{archetypeBadge(player.role)}</td>` (the final `<td>` in the compact row). Apply the same `stopPropagation` + TermTip wrapper there. The `ROLE_TERM_ID` map and the cell pattern are identical.

- [ ] **Step 7: Build + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS. Confirm there are no TypeScript errors about invalid `TermId` keys.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/Roster.tsx
git commit -m "feat(v15-p2b): de-dup archetype badge; Role column gets TermTip

Remove the redundant archetypeBadge from the player meta line (the Role
column already shows it). Wrap the surviving Role badge in a TermTip so
players can tap any archetype for its plain meaning and AFFECTS PLAY flag.
stopPropagation on the td prevents the row-click modal from firing.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Growth legibility — relabel Ceiling/Headroom with TermTip (PlayerDetailModal)

**Context:** `PlayerDetailModal.tsx` shows two growth sub-cards on the Overview tab. The Potential card (lines ~95–104) shows "Ceiling {player.potential_ceiling} · +{player.headroom} room" — the word "ceiling" is jargon and "+22 room" is opaque. The Growth card (lines ~105–125) shows "▲ Growing / ▼ Declining / — Plateauing" which is also correct but unexplained. All three fields (`potential_ceiling`, `headroom`, `projected_growth`) already exist in the payload.

**Files:**
- Edit: `frontend/src/components/PlayerDetailModal.tsx`

- [ ] **Step 1: Add TermTip import to PlayerDetailModal**

Add at top of file:

```tsx
import { TermTip } from '../legibility';
```

- [ ] **Step 2: Relabel the Potential card**

Replace the existing Potential sub-card content (the `<div style={{ marginTop: '0.35rem', ... }}>` block that shows `"Ceiling {player.potential_ceiling}"` and `"+{player.headroom} room"`) with clearly-labelled fields using TermTip:

```tsx
<div style={{ background: '#0f172a', padding: '1rem', borderRadius: '4px', border: '1px solid #1e293b' }}>
  <div className="dm-kicker">Potential</div>
  <div style={{ fontSize: '1.125rem', color: '#fff', fontWeight: 600 }}>{player.potential_tier}</div>
  <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontSize: '0.8rem' }}>
      <TermTip term="growth.ceiling">
        <span style={{ color: '#94a3b8' }}>Ceiling</span>
      </TermTip>
      <span style={{ color: '#e2e8f0', fontVariantNumeric: 'tabular-nums', fontWeight: 600 }}>
        OVR {player.potential_ceiling}
      </span>
    </div>
    {player.headroom > 0 && (
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontSize: '0.8rem' }}>
        <TermTip term="growth.headroom">
          <span style={{ color: '#94a3b8' }}>Headroom</span>
        </TermTip>
        <span style={{ color: '#22d3ee', fontVariantNumeric: 'tabular-nums', fontWeight: 600 }}>
          +{player.headroom}
        </span>
      </div>
    )}
    {player.headroom === 0 && (
      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>At ceiling — no headroom remaining.</span>
    )}
  </div>
</div>
```

- [ ] **Step 3: Relabel the Growth card's sub-label from bare "OVR N" to something meaningful**

The Growth card's bottom line currently shows `OVR {player.overall}` (line ~121). Replace it with a clearer "Current OVR" label:

```tsx
<div style={{ marginTop: '0.35rem', fontSize: '0.75rem', color: '#64748b' }}>
  Current OVR {player.overall}
</div>
```

(No TermTip needed on `projected_growth` itself — "▲ Growing / ▼ Declining / — Plateauing" is self-explanatory with the ceiling/headroom cards alongside it.)

- [ ] **Step 4: Build + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/PlayerDetailModal.tsx
git commit -m "feat(v15-p2b): growth legibility — ceiling/headroom TermTip in Player Card

Replace 'Ceiling NNN · +22 room' with clearly labelled TermTip-wrapped
fields ('Ceiling OVR 84' / 'Headroom +22'). Terms seeded in Phase 1.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: High-upside marker (PlayerDetailModal)

**Context:** Every player with `projected_growth === 'growing'` shows "▲ Growing" — even a 30-year-old with headroom of 2. This makes all growing players look like develop targets. The engine already differentiates by headroom (do NOT change dev math). Add a **presentation-only** ProofChip that appears only when a player is genuinely high-upside: `projected_growth === 'growing' && headroom >= 12 && player.age <= 23`. The chip's `source` text is constructed from real payload fields — it is never invented.

The threshold values (headroom ≥ 12, age ≤ 23) are presentation heuristics only. They require no backend change. If thresholds need tuning after playtesting, they live only in this component.

**Files:**
- Edit: `frontend/src/components/PlayerDetailModal.tsx`

- [ ] **Step 1: Add ProofChip import**

Extend the existing legibility import to:

```tsx
import { TermTip, ProofChip } from '../legibility';
```

- [ ] **Step 2: Add the high-upside marker inside the Growth card**

Below the existing "▲ Growing / ▼ Declining / — Plateauing" display value and above the "Current OVR" sub-label, insert:

```tsx
{player.projected_growth === 'growing'
  && player.headroom >= 12
  && player.age <= 23
  && (
  <ProofChip
    label="High Upside"
    source={`${player.headroom} OVR of headroom remaining at age ${player.age} — this player has genuine develop-target upside.`}
  />
)}
```

- [ ] **Step 3: Build + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/PlayerDetailModal.tsx
git commit -m "feat(v15-p2b): high-upside ProofChip — only fires for headroom>=12 && age<=23

Every growing player previously showed the same 'Growing' status. The
ProofChip appears only for genuine develop targets; its source text is
constructed from real payload fields. Engine math untouched.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: v2 attribute TermTip (PlayerDetailModal + DevelopmentResults)

**Context:** `throw_selection_iq` and `catch_courage` are shown in two places: the Ratings tab of `PlayerDetailModal` and the `DevelopmentResults` ceremony screen. Both places currently show the attribute without any mechanical explanation. The terms `attr.throw_selection_iq` and `attr.catch_courage` are already seeded in Phase 1's `terms.ts`. This task wires the TermTip to both surfaces, completing V14 Task 3.

**Files:**
- Edit: `frontend/src/components/PlayerDetailModal.tsx`
- Edit: `frontend/src/components/ceremonies/DevelopmentResults.tsx`

### PlayerDetailModal — Ratings tab

- [ ] **Step 1: Wrap v2 attribute RatingBars in TermTip**

In the Ratings tab (lines ~129–150), the v2 attrs are rendered via:

```tsx
{typeof player.ratings.throw_selection_iq === 'number' && (
  <RatingBar label="Throw Selection IQ" rating={player.ratings.throw_selection_iq} explanation="..." />
)}
{typeof player.ratings.catch_courage === 'number' && (
  <RatingBar label="Catch Courage" rating={player.ratings.catch_courage} explanation="..." />
)}
```

Replace with (the existing `explanation` prop text on `RatingBar` is overridden by TermTip — keep the prop if `RatingBar` still accepts it, but the TermTip takes precedence for discoverability):

```tsx
{typeof player.ratings.throw_selection_iq === 'number' && (
  <div>
    <TermTip term="attr.throw_selection_iq">
      <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Throw Selection IQ</span>
    </TermTip>
    <RatingBar label="Throw Selection IQ" rating={player.ratings.throw_selection_iq} />
  </div>
)}
{typeof player.ratings.catch_courage === 'number' && (
  <div>
    <TermTip term="attr.catch_courage">
      <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Catch Courage</span>
    </TermTip>
    <RatingBar label="Catch Courage" rating={player.ratings.catch_courage} />
  </div>
)}
```

> **Confirm first:** check if `RatingBar` already renders a label internally (it does — `label="Throw Selection IQ"`). To avoid showing the label twice, check the `RatingBar` component props signature in `frontend/src/components/ui.tsx` (or wherever `RatingBar` is defined). If `RatingBar` renders a label, pass `hideLabel` or omit the label prop if supported — otherwise remove the `<span>` above and rely solely on the TermTip wrapper on the `RatingBar`'s label area. Match whatever pattern is cleanest for the component.

- [ ] **Step 2: Build + lint (mid-task gate)**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS.

### DevelopmentResults — attribute delta labels

- [ ] **Step 3: Add TermTip import and wrap CC / TIQ delta labels**

In `DevelopmentResults.tsx`, the `movedAttrs` section renders each changed attribute as a short label from `_ATTR_LABEL` (e.g. `CC`, `TIQ`). These abbreviations are especially opaque for the two v2 attributes. Add TermTip wrappers for those two labels specifically:

At top of file, add:

```tsx
import { TermTip } from '../../legibility';
```

In the `movedAttrs.map(([attr, val]) => ...)` render, replace the `{label}` span for the two v2 attrs:

```tsx
{movedAttrs.map(([attr, val]) => {
  const attrColor = val > 0 ? '#10b981' : '#ef4444';
  const label = _ATTR_LABEL[attr] ?? attr;
  const termId =
    attr === 'throw_selection_iq' ? 'attr.throw_selection_iq' as const
    : attr === 'catch_courage' ? 'attr.catch_courage' as const
    : null;
  return (
    <span
      key={attr}
      style={{
        fontSize: '0.7rem',
        color: '#94a3b8',
        fontVariantNumeric: 'tabular-nums',
      }}
    >
      {termId ? (
        <TermTip term={termId}>{label}</TermTip>
      ) : (
        label
      )}{' '}
      <span style={{ color: attrColor, fontWeight: 600 }}>
        {val > 0 ? `+${val}` : `${val}`}
      </span>
    </span>
  );
})}
```

- [ ] **Step 4: Build + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/PlayerDetailModal.tsx frontend/src/components/ceremonies/DevelopmentResults.tsx
git commit -m "feat(v15-p2b): v2 attr TermTip on PlayerDetailModal + DevelopmentResults (V14 Task 3)

throw_selection_iq and catch_courage now show a TermTip on the Ratings
tab and on the offseason development attribute-delta labels. Terms were
seeded in Phase 1. Completes V14 Task 3.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Roster sort — directional affordances + Age sort clarity

**Context:** The Roster table uses a `<select>` for sorting (line ~258). The current options are: `"Sort · Lineup → OVR"`, `"Sort · Potential"`, `"Sort · OVR"`, `"Sort · Age"`. Problems:
1. Age sort direction is ambiguous (ascending by `left.player.age - right.player.age` = youngest first, but "Sort · Age" implies nothing about direction).
2. There is no visual confirmation of which sort is active beyond the selected `<option>` text.
3. Players don't know which direction any sort goes.

**Decision:** Keep the `<select>` (avoid a header-click refactor that risks table overflow on mobile). Make direction explicit in every option label, and add a visible sort indicator badge beside the select that echoes the active sort and direction. No new data, no payload change.

**Files:**
- Edit: `frontend/src/components/Roster.tsx`

- [ ] **Step 1: Update select option labels to be direction-explicit**

Replace the four `<option>` texts in the `<select>`:

```tsx
<select className="rl-sort" value={sortKey} onChange={(event) => setSortKey(event.target.value as typeof sortKey)}>
  <option value="lineup">Lineup order (starters first, then OVR ↓)</option>
  <option value="potential">Potential tier (Elite → Low)</option>
  <option value="overall">OVR highest first ↓</option>
  <option value="age">Age youngest first ↑</option>
</select>
```

- [ ] **Step 2: Add a sort-indicator badge adjacent to the select**

Below (or right-after) the `<select>`, render a compact inline badge summarising the active sort. Define a lookup above the component (near `ROLE_TERM_ID`):

```tsx
const SORT_INDICATOR: Record<typeof sortKey extends infer K ? K & string : never, { label: string; arrow: string }> = {} as never;
// Correct version — place the lookup inside the component or as a module-level const:
```

Instead, use a simple inline object inside the JSX (cleaner than a typed module-level const for this small case):

```tsx
{(() => {
  const indicators: Record<string, { label: string; dir: string }> = {
    lineup:   { label: 'Lineup',    dir: '→ OVR ↓' },
    potential:{ label: 'Potential', dir: 'Elite first' },
    overall:  { label: 'OVR',      dir: '↓ highest' },
    age:      { label: 'Age',      dir: '↑ youngest' },
  };
  const ind = indicators[sortKey];
  return (
    <span
      aria-label={`Sorted by ${ind.label}, ${ind.dir}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.25rem',
        fontSize: '0.65rem',
        fontWeight: 700,
        letterSpacing: '0.04em',
        color: '#22d3ee',
        background: 'rgba(34,211,238,0.08)',
        border: '1px solid rgba(34,211,238,0.25)',
        borderRadius: '3px',
        padding: '0.15rem 0.4rem',
        whiteSpace: 'nowrap',
      }}
    >
      {ind.label} {ind.dir}
    </span>
  );
})()}
```

Place this span inside the existing `rl-head-actions` div, immediately after the `<select>` element and before the "Lineup Editor ▸" button. This keeps the layout in the header row and does not affect the table or overflow.

- [ ] **Step 3: Build + lint — confirm no overflow at 390px**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS.

Visually confirm: at 390×844 viewport, the sort badge wraps gracefully within `rl-head-actions`. If it causes overflow, add `flexWrap: 'wrap'` to `.rl-head-actions` in the existing CSS (check `frontend/src/App.css` or the component's inline styles for `.rl-head-actions`).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Roster.tsx
git commit -m "feat(v15-p2b): roster sort direction badge + explicit age-sort label

Sort options now state their direction ('youngest first ↑', 'OVR ↓',
etc.) and a live indicator badge echoes the active sort beside the
select so direction is always visible without opening the dropdown.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Player bio — surface existing identity data (backend payload + PlayerDetailModal)

**Context:** The Overview tab's Bio section (lines ~88–93 of `PlayerDetailModal.tsx`) currently renders: `"{player.name} is a {player.age}-year-old {player.role.toLowerCase()} with {player.potential_tier.toLowerCase()} potential."` — mechanical and flat. The planning report and owner decisions (#4) confirm V15 only re-surfaces **existing** identity data; no new generative bio system.

**Available existing data (deterministic, no RNG, already computed from player ratings):**
- `player.role` — archetype display label (already in payload)
- `player.age` — already in payload
- `player.potential_tier` — already in payload
- `strongest_attribute` / `secondary_attribute` — computed by `identity._top_attributes()` from ratings; deterministic; NOT currently in the roster payload

**Decision:** Add `bio_strongest_attr` and `bio_secondary_attr` to the roster builder in `web_status_service.py` using `identity._top_attributes()`. These are fully deterministic (no RNG). The nickname requires `DeterministicRNG` and is out of scope for this task. `hometown` exists only on prospects, not active players — do not surface it.

**Files:**
- Edit: `src/dodgeball_sim/web_status_service.py`
- Edit: `frontend/src/types.ts`
- Edit: `frontend/src/components/PlayerDetailModal.tsx`
- Test: add to `tests/test_web_status_service.py` (find with `ls tests/ | grep web_status`)

- [ ] **Step 1: Confirm the test file path**

Run: `ls tests/ | grep -i "web_status\|roster"`
If no match: run `ls tests/` and identify the test file that imports `build_roster_payload` or covers the roster endpoint. Use that file in Step 4.

- [ ] **Step 2: Write the failing test**

In the identified test file, add:

```python
def test_roster_payload_has_bio_fields(tmp_path):
    """bio_strongest_attr and bio_secondary_attr must be non-empty strings."""
    import sqlite3
    from dodgeball_sim import persistence
    from dodgeball_sim.web_status_service import build_roster_payload

    db = tmp_path / "bio.db"
    conn = persistence.connect(str(db))
    # build_roster_payload requires an active career; use a minimal seeded career
    # if the helper is available, or skip via pytest.importorskip if the fixture
    # pattern in adjacent tests is different.
    # Adapt to whatever minimal-career fixture pattern the existing roster tests use.
    # The assertion to satisfy:
    result = build_roster_payload(conn, player_club_id="club_user")
    for player in result["roster"]:
        assert isinstance(player["bio_strongest_attr"], str) and player["bio_strongest_attr"], player
        assert isinstance(player["bio_secondary_attr"], str) and player["bio_secondary_attr"], player
```

> Before writing the full test, read the nearest existing roster test for the correct fixture pattern (how they seed a minimal career, what `player_club_id` to use). Match that pattern exactly.

- [ ] **Step 3: Run the failing test**

Run: `python -m pytest tests/<test_file>.py::test_roster_payload_has_bio_fields -v`
Expected: FAIL — `KeyError: 'bio_strongest_attr'` (field does not exist yet).

- [ ] **Step 4: Add `bio_strongest_attr` / `bio_secondary_attr` to `web_status_service.py`**

In `web_status_service.py`, add import at top of file (near other identity imports, or add if not already imported):

```python
from .identity import _top_attributes
```

In the roster enrichment loop (after the `projected_growth` block, around line 141), add:

```python
        # Bio identity — deterministic from ratings, no RNG needed.
        strongest_attr, secondary_attr = _top_attributes(player)
        player_dict["bio_strongest_attr"] = strongest_attr
        player_dict["bio_secondary_attr"] = secondary_attr
```

> `_top_attributes` is a module-level function in `identity.py` that returns `(strongest: str, secondary: str)` from the five base ratings. It is deterministic and requires no RNG. It is a private helper (underscore prefix) but is used directly here rather than through the full `build_identity_profile()` to avoid requiring a `DeterministicRNG`.

- [ ] **Step 5: Run the test; verify it passes**

Run: `python -m pytest tests/<test_file>.py::test_roster_payload_has_bio_fields -v`
Expected: PASS.

- [ ] **Step 6: Full suite**

Run: `python -m pytest -q`
Expected: green.

- [ ] **Step 7: Update `types.ts` — add the new fields to `Player`**

In `frontend/src/types.ts`, in the `Player` interface (after the existing `ovr_season_trend` field), add:

```ts
/** Strongest base attribute (e.g. "Accuracy"), derived from ratings. */
bio_strongest_attr: string;
/** Second-strongest base attribute (e.g. "Power"), derived from ratings. */
bio_secondary_attr: string;
```

- [ ] **Step 8: Update the Bio section in `PlayerDetailModal.tsx`**

Replace the flat one-liner bio with a structured identity card that surfaces existing data with personality:

```tsx
<div>
  <h3 style={{ margin: '0 0 0.5rem', fontSize: '0.875rem', color: '#e2e8f0' }}>Bio</h3>
  <div style={{
    background: '#0f172a',
    border: '1px solid #1e293b',
    borderRadius: '6px',
    padding: '0.75rem 1rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.4rem',
  }}>
    <p style={{ margin: 0, fontSize: '0.875rem', color: '#cbd5e1', lineHeight: 1.5 }}>
      {player.name} is a{' '}
      <TermTip term={PLAYER_TERM_ID[player.role] ?? 'archetype.sharpshooter'}>
        <span style={{ color: '#22d3ee', fontWeight: 600 }}>{player.role}</span>
      </TermTip>
      {' '}at age {player.age}, with a game built on{' '}
      <strong style={{ color: '#e2e8f0' }}>{player.bio_strongest_attr.toLowerCase()}</strong>
      {' '}and{' '}
      <strong style={{ color: '#e2e8f0' }}>{player.bio_secondary_attr.toLowerCase()}</strong>.
    </p>
    <p style={{ margin: 0, fontSize: '0.8rem', color: '#64748b', lineHeight: 1.4 }}>
      {player.potential_tier === 'Elite' || player.potential_tier === 'High'
        ? `${player.headroom > 0 ? `${player.headroom} OVR of headroom ahead — a genuine develop target.` : 'At ceiling. Maximise playing time over long-term growth.'}`
        : player.projected_growth === 'declining'
        ? 'Past peak. Deploy as a stabilising veteran while managing workload.'
        : player.headroom > 0
        ? 'Solid rotation contributor with room to improve.'
        : 'Development ceiling reached. Best used as a reliable depth piece.'}
    </p>
  </div>
</div>
```

Add the following lookup constant at the top of `PlayerDetailModal.tsx` (below the imports):

```tsx
import { TermTip, ProofChip } from '../legibility';
import type { TermId } from '../legibility';

// Mirrors ROLE_TERM_ID in Roster.tsx — kept in sync with recruitment._RECRUITMENT_DISPLAY_NAMES.
const PLAYER_TERM_ID: Record<string, TermId> = {
  'Sharpshooter':          'archetype.sharpshooter',
  'Net Specialist':        'archetype.net_specialist',
  'Ball Hawk':             'archetype.ball_hawk',
  'Iron Anchor':           'archetype.iron_anchor',
  'Two-Way Threat':        'archetype.two_way_threat',
  'Skirmisher':            'archetype.skirmisher',
  'Possession Specialist': 'archetype.possession_specialist',
  'Hit-and-Run':           'archetype.hit_and_run',
};
```

> **Cross-screen note:** `PLAYER_TERM_ID` and `ROLE_TERM_ID` in `Roster.tsx` are identical. Consider extracting to `frontend/src/legibility/archetypeTermId.ts` as a shared helper if both files are edited in the same PR (see "Cross-screen overlap" note in the Exit Gates). For now, a simple duplication is acceptable; the extraction is a cleanup task.

- [ ] **Step 9: Build + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add src/dodgeball_sim/web_status_service.py tests/<test_file>.py frontend/src/types.ts frontend/src/components/PlayerDetailModal.tsx
git commit -m "feat(v15-p2b): player bio with identity data — strongest/secondary attr from payload

Add bio_strongest_attr + bio_secondary_attr to roster payload (deterministic
from ratings via identity._top_attributes, no RNG). Bio section now shows
archetype with TermTip, top two attributes, and a role-appropriate status
line. Flat one-liner bio replaced. Pytest gate added.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 2b Exit Gates

Run all before declaring Phase 2b done:

- [ ] From `frontend/`: `npm run build` — clean (the tsc no-orphan-term gate proves every `TermTip term="..."` resolves).
- [ ] From `frontend/`: `npm run lint` — clean.
- [ ] From repo root: `npm run e2e` — zero failures.
- [ ] `python -m pytest -q` — green (covers the bio-fields payload test from Task 6).
- [ ] `python tools/tier_engine_health_probe.py --driver official --trials 50` — summary **identical** to Phase 0 baseline (this phase is purely presentation; probe must not drift).
- [ ] Manual smoke at 390×844 on a fresh career: Role column shows TermTip popover on tap; Growth card shows "Ceiling OVR N" and "Headroom +N"; High Upside chip appears for a young high-headroom player; CC/TIQ labels in DevelopmentResults show TermTip; sort badge echoes active sort direction; bio is not the flat one-liner.
- [ ] No `playtest_output/*.png` or `*.db` files committed.

---

## Cross-screen overlap to normalize (flag for Phase 5 or a cleanup PR)

1. **`ROLE_TERM_ID` / `PLAYER_TERM_ID` duplication.** Both `Roster.tsx` and `PlayerDetailModal.tsx` maintain the same 8-entry archetype→TermId map. Extract to `frontend/src/legibility/archetypeTermId.ts` as a shared export. Low urgency — they don't drift independently as long as `recruitment._RECRUITMENT_DISPLAY_NAMES` is unchanged.

2. **Coach archetype TermTip is not handled here.** The planning report mentions coach archetypes should get TermTip where shown. Coach archetype display (program_archetype strings: Contender, Development Factory, Defensive Specialist, Power Throwers, Aging Veterans, Balanced Rebuild) is rendered in Dynasty Office and Standings — not Roster or Player Card. Those surfaces are owned by Phase 3a and Phase 2d respectively. The `coach.*` term keys in `terms.ts` should be expanded there (only `coach.balanced` is currently seeded; the full set of 6 program archetypes needs keys).

3. **`potential_ceiling` in `DevelopmentResults.tsx`.** Line ~74 shows `"Ceiling {player.potential_ceiling}"` without TermTip — the same jargon fixed in Task 2 for the Player Card. Phase 2b is the right phase to fix it. Add `import { TermTip } from '../../legibility'` (already done in Task 4) and wrap `"Ceiling"` there:

   ```tsx
   {player.potential_ceiling != null && (
     <span style={{ color: '#64748b', fontSize: '0.7rem' }}>
       <TermTip term="growth.ceiling">Ceiling</TermTip>{' '}{player.potential_ceiling}
     </span>
   )}
   ```

   This is a minor addition to the Task 4 commit scope — include it there or as a follow-up in the same PR.
