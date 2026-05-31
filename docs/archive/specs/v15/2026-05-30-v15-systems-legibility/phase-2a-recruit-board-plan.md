# V15 Phase 2a — Recruit Board Legibility: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the recruit board self-explanatory. Every number, color, and label on a prospect card must convey meaning on its own, using the Phase 1 toolkit. No engine change, no new deps, no schema migration.

**Architecture:** Two files own the board:
- `frontend/src/components/dynasty/ProspectCard.tsx` — the per-card component (all card-level changes live here)
- `frontend/src/components/DynastyOffice.tsx` → `RecruitBoard` function (board-level: sort controls, filter empty-state)

Phase 1 toolkit is imported from `frontend/src/legibility/`. Backend payload already includes `pipeline_tier` (confirmed in `recruiting_office.py:167` and `types.ts:1107`) and `scouted` boolean (`recruiting_office.py:168`) — **no backend task required**. Terms `recruit.fit`, `recruit.interest`, `recruit.ovr_range`, `recruit.pipeline`, and most `archetype.*` ids are pre-seeded in Phase 1's `terms.ts`. Task 1 of this phase **appends three new term keys** to `terms.ts` for the archetype labels the pre-seed missed (all confirmed against `recruitment.py:93–102`); all other edits to `terms.ts` are copy-only.

**Tech Stack:** React 19 + TypeScript ~6 + Vite 8. Verification: `npm run build` (tsc gate + no-orphan-term gate) + `npm run lint` from `frontend/`; `npm run e2e` from repo root for behavioral smoke. No backend changes in this phase; `python -m pytest -q` must stay green but no new Python tests are added.

> **Pre-flight:**
> - Phase 0 must be merged. After Phase 0, `ProspectCard.tsx:101` reads `'Fair Fit'` for the middle tier; `DynastyOffice.tsx RecruitBoard` has filter state `'all' | 'strong' | 'fair' | 'risk'` with three mutually-exclusive chips and the `'visit'` key is gone.
> - Phase 1 must be merged (`frontend/src/legibility/` exists with the locked contract).
> - Branch off `main`: `git checkout -b feat/v15-phase2a-recruit-board`.
> - Verify green baseline: from `frontend/`, `npm run build && npm run lint` must pass.
> - Do **not** touch any `frontend/src/legibility/` file except `terms.ts` (append-only new keys per instructions below; never change existing keys' id strings).
> - The Visit button **mechanic** (budget.visit slot spending) is a deferred spec. This phase only sharpens its `title` copy — the button and its action stay unchanged.

---

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `frontend/src/legibility/terms.ts` | Append 3 missing archetype term keys (`archetype.ball_hawk`, `archetype.iron_anchor`, `archetype.two_way_threat`) | 1 |
| `frontend/src/components/dynasty/ProspectCard.tsx` | Card legibility: imports, archetype TermTip mapping, hometown label, priority annotation, FIT/Interest/OVR disambiguation, fit-tier legend, KnownValue fog-of-war for OVR, scouting caption, PipelineEmblem, visit label | 1, 2, 3, 4 |
| `frontend/src/components/DynastyOffice.tsx` (RecruitBoard function only) | Sort controls (Fit/Interest/Pipeline), `EmptyState` swap for no-match empty state | 5 |
| `tests/e2e/v15-recruit-board.spec.ts` | Playwright smoke: archetype TermTip, KnownValue scouting state, PipelineEmblem, sort toggle, filter empty-state | 6 |

---

## Task 1: Append missing archetype terms + archetype TermTip on the card

**Context:**
The eight archetype labels that can appear in `prospect.public_archetype` (confirmed from `recruitment.py:93–102 _RECRUITMENT_DISPLAY_NAMES`) are: **Sharpshooter, Net Specialist, Ball Hawk, Iron Anchor, Two-Way Threat, Skirmisher, Possession Specialist, Hit-and-Run**. Phase 1 pre-seeded `archetype.thrower`, `archetype.hawk_dodger`, `archetype.net_specialist`, `archetype.skirmisher`. Three labels have no honest term match yet: "Ball Hawk" (`archetype.ball_hawk`), "Iron Anchor" (`archetype.iron_anchor`), "Two-Way Threat" (`archetype.two_way_threat`). Append them now so every label resolves at compile time.

The existing `archetypeBadge` helper in `ProspectCard.tsx` maps only "sharpshooter", "net specialist", "possession specialist", and "hit-and-run" to tones — "Ball Hawk", "Iron Anchor", and "Two-Way Threat" fall through to `dm-badge-cyan` (the Thrower tone), which is wrong. Fix the tone mapping at the same time. Then wrap the badge in `TermTip`.

**Files:**
- Modify (append-only): `frontend/src/legibility/terms.ts`
- Modify: `frontend/src/components/dynasty/ProspectCard.tsx`

- [ ] **Step 1: Append three archetype term keys to `terms.ts`**

Open `frontend/src/legibility/terms.ts`. Locate the closing `} as const satisfies Record<string, TermDef>;` line. Immediately **before** that closing brace, append:

```ts
  // --- Additional player archetypes (missing from Phase 1 pre-seed) ---
  'archetype.ball_hawk': {
    label: 'Ball Hawk',
    plain: 'Evasive player who hunts loose balls and intercepts throws.',
    why: 'High catch-attempt rate plus evasion — keeps themselves alive and converts turnovers.',
    kind: 'mechanical',
  },
  'archetype.iron_anchor': {
    label: 'Iron Anchor',
    plain: 'Durable survivor who holds their ground and absorbs pressure.',
    why: 'Hard to eliminate; a reliable back-line presence when your attack is spent.',
    kind: 'mechanical',
  },
  'archetype.two_way_threat': {
    label: 'Two-Way Threat',
    plain: 'Balanced player effective at both throwing and catching.',
    why: 'Harder to contain because opponents can\'t assign a single counter tactic.',
    kind: 'mechanical',
  },
```

- [ ] **Step 2: Confirm tsc still sees `TermId` as a closed union**

Run (from `frontend/`): `npm run build`
Expected: PASS. The three new keys are now in `TERMS`; `TermId` includes them.

- [ ] **Step 3: Add legibility imports to `ProspectCard.tsx`**

At the top of `frontend/src/components/dynasty/ProspectCard.tsx`, after the existing imports, add:

```tsx
import { TermTip, PipelineEmblem, KnownValue } from '../../legibility';
import type { PipelineTier, TermId } from '../../legibility';
```

- [ ] **Step 4: Replace `archetypeBadge` with a fully-mapped, TermTip-wrapped version**

The complete eight-label mapping, with correct tones and honest term ids, replaces lines 26–37 of `ProspectCard.tsx`:

```tsx
// Maps the eight recruitment display names (recruitment.py _RECRUITMENT_DISPLAY_NAMES)
// to their badge tone and TermId. Tone groups: orange = aggressive throwers / hybrids;
// violet = catch/possession specialists; cyan = evasion/hawk; slate = anchor.
const ARCHETYPE_MAP: Array<{
  match: string[];
  tone: string;
  termId: TermId;
}> = [
  { match: ['sharpshooter'],         tone: 'dm-badge-orange',  termId: 'archetype.thrower' },
  { match: ['skirmisher'],           tone: 'dm-badge-orange',  termId: 'archetype.skirmisher' },
  { match: ['two-way threat'],       tone: 'dm-badge-orange',  termId: 'archetype.two_way_threat' },
  { match: ['net specialist'],       tone: 'dm-badge-violet',  termId: 'archetype.net_specialist' },
  { match: ['possession specialist'],tone: 'dm-badge-violet',  termId: 'archetype.net_specialist' },
  { match: ['ball hawk'],            tone: 'dm-badge-cyan',    termId: 'archetype.ball_hawk' },
  { match: ['hit-and-run'],          tone: 'dm-badge-cyan',    termId: 'archetype.hawk_dodger' },
  { match: ['iron anchor'],          tone: 'dm-badge-slate',   termId: 'archetype.iron_anchor' },
];

const archetypeBadge = (label: string) => {
  const n = label.toLowerCase();
  const entry = ARCHETYPE_MAP.find((m) => m.match.some((s) => n.includes(s)));
  const tone = entry?.tone ?? 'dm-badge-cyan';
  const termId: TermId = entry?.termId ?? 'archetype.thrower';
  return (
    <TermTip term={termId}>
      <span className={`dm-badge ${tone}`}>{label.toUpperCase()}</span>
    </TermTip>
  );
};
```

> Note: `dm-badge-slate` may or may not exist in `index.css`. Run `git grep -n "dm-badge-slate" -- frontend/src` before committing. If absent, use `dm-badge-cyan` for Iron Anchor as a fallback, or add `.dm-badge-slate { background: #334155; color: #cbd5e1; }` to `frontend/src/index.css` alongside the other `dm-badge-*` rules. Check the existing badge definitions first.

- [ ] **Step 5: Relabel the sub-row — hometown with a "From" prefix, priority rank as an annotated superscript**

In the `do-recruit-sub` div (currently renders `#{priority} · {hometown} · badge · status`), replace the inner spans with:

```tsx
          <span
            aria-label={`Board rank ${priority}`}
            title="Your board rank for this prospect — sorted by fit by default"
            style={{ fontSize: '0.6rem', color: '#64748b', letterSpacing: '0.04em' }}
          >
            #{String(priority).padStart(2, '0')}
          </span>
          <span className="dot">·</span>
          <span aria-label={`Hometown: ${prospect.hometown}`}>
            <span
              style={{
                fontSize: '0.55rem',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                color: '#64748b',
                marginRight: '0.2rem',
              }}
            >
              From
            </span>
            <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>{prospect.hometown}</span>
          </span>
          <span className="dot">·</span>
          {archetypeBadge(prospect.public_archetype || 'Balanced')}
          <span className="dot">·</span>
          <RecruitingBadge status={displayStatus} pending={pending} />
```

- [ ] **Step 6: Build + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS. `TermId` now covers all eight archetype labels. The `dm-badge-slate` fallback from Step 4 must be resolved before this passes if the class was missing.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/legibility/terms.ts frontend/src/components/dynasty/ProspectCard.tsx
git commit -m "feat(v15-p2a): append missing archetype terms, full badge mapping, hometown label

Adds archetype.ball_hawk / iron_anchor / two_way_threat to terms.ts
(3 recruitment display names not in the Phase 1 pre-seed); fixes the
archetypeBadge tone mapping so all 8 labels resolve correctly; wraps each
badge in TermTip for on-hover explanation; hometown gets a 'From' prefix so
it can't be misread as a surname; priority rank carries aria + title copy.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: FIT / Interest / OVR disambiguation + fit-tier legend row

**Context:**
- The `do-recruit-fit` block renders `FIT` as a large mono number with the same visual weight as an OVR — players read `FIT 74` as if it were OVR.
- The meter label row shows `{fitLabel}`, `INT {interest}%`, and `OVR {low}-{high}` with no term explanations. Each label gets a `TermTip`.
- "INT" abbreviates `interest` — it is ambiguous. Replace "INT" with "Interest" wrapped in `TermTip(recruit.interest)`.
- The grey (risk) vs amber (neutral/strong) card tone from `fit-${fitTier}` is unexplained — a small inline legend row below the meter explains it once per card.
- The `interest_evidence[0]` string is `"Public range {low}-{high}…"` (see `recruiting_office.py:162`). Combined with the meter's `OVR {low}-{high}`, the same band appeared on two surfaces. This task removes the "Public range" evidence line from the displayed evidence, keeping only the non-redundant lines (pipeline tier, interest %, credibility grade). The raw `interest_evidence` array in the payload is **unchanged** — only the display filter changes.

**Files:**
- Modify: `frontend/src/components/dynasty/ProspectCard.tsx`

- [ ] **Step 1: Derive the display-evidence slice (remove "Public range" redundancy)**

After the existing `const evidence = prospect.interest_evidence.filter(Boolean).slice(0, 2);` line (line ~102), replace it with a version that filters out the "Public range" string, which is redundant with the OVR meter display:

```tsx
  // Filter the "Public range …" line — it repeats the OVR band already shown
  // in the meter. Display at most 2 of the remaining evidence strings.
  const evidence = prospect.interest_evidence
    .filter(Boolean)
    .filter((s) => !s.toLowerCase().startsWith('public range'))
    .slice(0, 2);
```

- [ ] **Step 2: Rewrite the `do-recruit-fit` block to distinguish FIT from a roster OVR**

Replace the existing `<div className="do-recruit-fit">` block with:

```tsx
        <div className="do-recruit-fit" aria-label={`Fit score: ${prospect.fit_score} out of 100`}>
          <TermTip term="recruit.fit">
            <span className="lbl">FIT</span>
          </TermTip>
          <span
            className="val mono"
            style={{
              fontSize: '1.1rem',
              color:
                prospect.fit_score >= 80
                  ? '#34d399'
                  : prospect.fit_score >= 65
                    ? '#f59e0b'
                    : '#f87171',
            }}
          >
            {prospect.fit_score}
            <span
              style={{ fontSize: '0.55rem', color: '#64748b', fontWeight: 400, marginLeft: '0.15rem' }}
            >
              /100
            </span>
          </span>
        </div>
```

The `/100` denominator and tier-colored value make FIT visually distinct from an OVR (which has no denominator and uses different scaling).

- [ ] **Step 3: Rewrite the meter label row with TermTip on each label**

Replace the `<div className="do-recruit-meter-labels">` block with:

```tsx
          <div className="do-recruit-meter-labels">
            <span>
              <TermTip term="recruit.fit">
                <span>{fitLabel.toUpperCase()}</span>
              </TermTip>
            </span>
            {typeof prospect.interest === 'number' && (
              <span className="mono">
                <TermTip term="recruit.interest">
                  <span>Interest</span>
                </TermTip>
                {' '}{prospect.interest}%
              </span>
            )}
          </div>
```

The OVR band is moved to `KnownValue` in Task 3 below. Do not place it here; Task 3's `KnownValue` component renders in the meter-labels row next to these two items.

- [ ] **Step 4: Add a fit-tier legend row below the meter**

Immediately after the closing `</div>` of `do-recruit-meter-labels`, still inside `do-recruit-meter`, add:

```tsx
          <div
            aria-label="Card color key: green = Strong Fit, amber = Fair Fit, red = At Risk"
            style={{
              display: 'flex',
              gap: '0.75rem',
              marginTop: '0.3rem',
              fontSize: '0.55rem',
              color: '#64748b',
              letterSpacing: '0.04em',
              flexWrap: 'wrap',
            }}
          >
            <span style={{ color: '#34d399' }}>● Strong Fit ≥80</span>
            <span style={{ color: '#f59e0b' }}>● Fair Fit 65–79</span>
            <span style={{ color: '#f87171' }}>● At Risk &lt;65</span>
          </div>
```

- [ ] **Step 5: Build + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/dynasty/ProspectCard.tsx
git commit -m "feat(v15-p2a): disambiguate FIT vs OVR, label Interest, add fit-tier legend

FIT shows /100 denominator and tier color (green/amber/red) so it cannot
read as a roster OVR; meter row uses TermTip on Fit and Interest labels;
'INT' abbreviation replaced by full 'Interest' label; 'Public range' line
removed from displayed evidence (redundant with OVR meter — payload intact);
fit-tier legend row explains card background color inline.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: KnownValue fog-of-war for OVR range + scouting explainer

**Context:**
- `prospect.scouted` (boolean, `recruiting_office.py:168`) is already in the payload. When `false`, `narrow_band()` returns the full wide band (estimated); when `true`, the band is tighter. The card currently shows the band identically in both states.
- `KnownValue` with `state="estimated"` (dashed amber border + hint) for unscouted and `state="known"` (solid border) for scouted makes the epistemic state visible.
- This component renders in the meter-labels row, as the third item after the Fit label and Interest (from Task 2). The OVR band is not wrapped in a `TermTip` because `KnownValue` already carries the `label` text "OVR" and the `hint` "Scout to narrow" — adding another popover trigger on a small row would overcrowd the mobile layout. The label text "OVR" is sufficient at this context; the `recruit.ovr_range` term is accessible via the `TermTip` placed on the board's sort button ("OVR" sort) in Task 5 if desired.
- A short scouting caption below the evidence row explains what scouting changes — backed by the `narrow_band` mechanic in `recruiting_office.py`.

**Files:**
- Modify: `frontend/src/components/dynasty/ProspectCard.tsx`

- [ ] **Step 1: Add the `KnownValue` OVR to the meter-labels row**

Inside `<div className="do-recruit-meter-labels">` (from Task 2 Step 3), add the `KnownValue` as the third item, after the Interest span:

```tsx
            <KnownValue
              state={prospect.scouted ? 'known' : 'estimated'}
              label="OVR"
              value={`${low}–${high}`}
              hint={prospect.scouted ? undefined : 'Scout to narrow'}
            />
```

The complete `do-recruit-meter-labels` div now contains three items: `TermTip(fitLabel)`, `TermTip(Interest) + %`, and `KnownValue(OVR)`.

- [ ] **Step 2: Add a scouting-reveals caption below the evidence row**

After the closing `</div>` of the `do-recruit-evidence` block (or after the evidence conditional if evidence is empty), add the caption only when the prospect is not yet scouted:

```tsx
      {!prospect.scouted && (
        <p
          style={{
            margin: '0.25rem 0 0',
            fontSize: '0.6rem',
            color: '#64748b',
            lineHeight: 1.4,
          }}
        >
          Scout to narrow the OVR range and sharpen fit precision. Contact and visits build interest.
        </p>
      )}
```

- [ ] **Step 3: Build + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS. `KnownValue` state values `'known'` and `'estimated'` are valid members of the `Knowledge` union.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/dynasty/ProspectCard.tsx
git commit -m "feat(v15-p2a): KnownValue fog-of-war for OVR range + scouting explainer

Unscouted OVR shows dashed amber KnownValue with 'Scout to narrow' hint;
scouted OVR shows solid border. No new payload fields: scouted boolean was
already in the row payload (recruiting_office.py:168). A scouting caption
below the evidence row explains what changes — backed by narrow_band.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: PipelineEmblem on the prospect card

**Context:**
- `prospect.pipeline_tier` is in the payload (`recruiting_office.py:167`, `types.ts:1107`), a 1–5 integer.
- The evidence row already contains `"Pipeline Tier N base interest."` as text. The `PipelineEmblem` makes this visual — the tier number becomes a colored badge readable at a glance.
- Place the emblem in the `do-recruit-sub` header row, after the `RecruitingBadge`, so it is visible without reading the evidence strings.
- `PipelineTier` is `1 | 2 | 3 | 4 | 5`; clamp with `Math.round` before casting.

**Files:**
- Modify: `frontend/src/components/dynasty/ProspectCard.tsx`

- [ ] **Step 1: Derive a safe `PipelineTier` cast**

After the existing `const evidence = ...` line, add:

```tsx
  const safePipelineTier = (
    Math.min(5, Math.max(1, Math.round(prospect.pipeline_tier ?? 1)))
  ) as PipelineTier;
```

- [ ] **Step 2: Append `PipelineEmblem` to the sub-row**

At the end of the `do-recruit-sub` div (after the `RecruitingBadge` span and its separator), append:

```tsx
          <span className="dot">·</span>
          <span
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
          >
            <TermTip term="recruit.pipeline">
              <span
                style={{
                  fontSize: '0.55rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: '#64748b',
                }}
              >
                Pipeline
              </span>
            </TermTip>
            <PipelineEmblem tier={safePipelineTier} size="sm" />
          </span>
```

- [ ] **Step 3: Mobile overflow guard**

Run: `git grep -n "do-recruit-sub" -- frontend/src/index.css frontend/src/components`
If the `do-recruit-sub` flex container does not already have `flex-wrap: wrap`, add it as an inline style on the `<div className="do-recruit-sub">`:

```tsx
      <div className="do-recruit-sub" style={{ flexWrap: 'wrap' }}>
```

This prevents horizontal overflow on 390px when the sub-row accumulates rank · From location · badge · status · pipeline.

- [ ] **Step 4: Build + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dynasty/ProspectCard.tsx
git commit -m "feat(v15-p2a): PipelineEmblem on prospect card header

pipeline_tier was already in the row payload; render it as the shared
PipelineEmblem (T5 pink → T1 bronze) for glanceable tier reading.
TermTip on the 'Pipeline' label routes to recruit.pipeline for one-hop
explanation. Sub-row gets flex-wrap to stay overflow-safe at 390px.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Board-level — sort controls, `EmptyState`, visit label clarification

**Context:**
- Phase 0 (already merged) gave `RecruitBoard` three mutually-exclusive filter chips (Strong Fit / Fair Fit / At Risk) and filter state `'all' | 'strong' | 'fair' | 'risk'`. This task does **not** rewrite the filter chips — it adds sort controls and the EmptyState alongside the existing chips.
- The static `<span className="do-board-meta">Sorted by Fit - Desc</span>` label has no interactive controls. Add Fit / Interest / Pipeline sort buttons with a direction toggle. Sort is client-side over the already-filtered prospect list.
- The no-match empty-state is a raw `<div style={{...}}>` — replace it with `EmptyState`.
- The Visit button `title` (line ~194 in `ProspectCard.tsx`) reads `'Spend a visit slot'` — sharpen it to mention its role without implying mechanic changes.

**Files:**
- Modify: `frontend/src/components/DynastyOffice.tsx` (RecruitBoard function only)
- Modify: `frontend/src/components/dynasty/ProspectCard.tsx` (Visit button title only)

- [ ] **Step 1: Add `EmptyState` import and `useMemo` guard in `DynastyOffice.tsx`**

At the top of `DynastyOffice.tsx`, add `EmptyState` to the legibility import (or add the full import if not already present from earlier tasks):

```tsx
import { EmptyState } from '../legibility';
```

Confirm `useMemo` is already imported on line 1 of `DynastyOffice.tsx` (it is — `import { useEffect, useMemo, useState } from 'react'`). Do not add a duplicate import.

- [ ] **Step 2: Add sort state inside `RecruitBoard`**

Inside the `RecruitBoard` function, directly after the existing `filter` state declaration, add:

```tsx
  const [sort, setSort] = useState<'fit' | 'interest' | 'pipeline'>('fit');
  const [sortDir, setSortDir] = useState<'desc' | 'asc'>('desc');
```

Replace the existing `const filtered = prospects.filter(...)` with a `useMemo` that both filters and sorts:

```tsx
  const filtered = useMemo(() => {
    const base = prospects.filter((prospect) => {
      if (filter === 'strong') return prospect.fit_score >= 80;
      if (filter === 'fair') return prospect.fit_score >= 65 && prospect.fit_score < 80;
      if (filter === 'risk') return prospect.fit_score < 65;
      return true;
    });
    return [...base].sort((a, b) => {
      let av: number;
      let bv: number;
      if (sort === 'interest') {
        av = a.interest ?? 0;
        bv = b.interest ?? 0;
      } else if (sort === 'pipeline') {
        av = a.pipeline_tier ?? 1;
        bv = b.pipeline_tier ?? 1;
      } else {
        av = a.fit_score;
        bv = b.fit_score;
      }
      return sortDir === 'desc' ? bv - av : av - bv;
    });
  }, [prospects, filter, sort, sortDir]);
```

- [ ] **Step 3: Add sort controls to the board header**

Locate the `<span className="do-board-meta">Sorted by Fit - Desc</span>` span (after the `do-board-sep` in the filters div). Replace only that span with the sort control group:

```tsx
          <div
            role="group"
            aria-label="Sort prospects"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.3rem',
              flexWrap: 'wrap',
            }}
          >
            <span
              style={{
                fontSize: '0.6rem',
                color: '#64748b',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              Sort
            </span>
            {(['fit', 'interest', 'pipeline'] as const).map((key) => (
              <button
                key={key}
                className={`do-board-filter ${sort === key ? 'is-active' : ''}`}
                onClick={() => {
                  if (sort === key) {
                    setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
                  } else {
                    setSort(key);
                    setSortDir('desc');
                  }
                }}
                type="button"
                aria-pressed={sort === key}
                title={
                  key === 'fit'
                    ? 'Sort by Fit score (how well this prospect matches your program)'
                    : key === 'interest'
                      ? 'Sort by Interest % (how interested the prospect is in your program)'
                      : 'Sort by Pipeline Tier (1–5; higher tiers close more easily)'
                }
              >
                {key === 'fit' ? 'Fit' : key === 'interest' ? 'Interest' : 'Pipeline'}
                {sort === key && (
                  <span aria-hidden="true" style={{ marginLeft: '0.2rem' }}>
                    {sortDir === 'desc' ? '↓' : '↑'}
                  </span>
                )}
              </button>
            ))}
          </div>
```

- [ ] **Step 4: Replace the raw empty-state div with `EmptyState`**

Locate the no-match fallback in the `do-board-grid` div (the `filtered.length === 0` block that currently renders a raw `<div style={{...}}>No prospects match the current filter.</div>`). Replace it with:

```tsx
        {filtered.length === 0 && (
          <EmptyState
            title="No prospects match this filter"
            body="Try 'All' to see the full board, or adjust your filter. Prospects are generated each season."
          />
        )}
```

- [ ] **Step 5: Clarify the Visit button title in `ProspectCard.tsx`**

In `frontend/src/components/dynasty/ProspectCard.tsx`, find the Visit `<button>` (the `primary` variant). Its `title` currently reads `'Spend a visit slot'`. Replace the full title prop:

```tsx
          title={
            canVisit
              ? 'Spend a visit slot — your highest-commitment weekly signal to this prospect'
              : 'No Visit slots remain this week'
          }
```

- [ ] **Step 6: Build + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS. Confirm `filter` state type in `RecruitBoard` has no remaining reference to `'visit'` (Phase 0 removed it; this step must not re-introduce it).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/DynastyOffice.tsx frontend/src/components/dynasty/ProspectCard.tsx
git commit -m "feat(v15-p2a): sort controls + EmptyState on recruit board, visit label

Fit/Interest/Pipeline sort buttons with direction toggle replace the static
'Sorted by Fit - Desc' label; client-side sort is a useMemo over the
existing filtered list; no-match empty-state uses toolkit EmptyState;
Visit button title clarified — mechanic unchanged (deferred spec).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Playwright smoke for recruit-board legibility

**Context:** The e2e suite lives in `tests/e2e/`. The navigation pattern is established in `tests/e2e/v14-legibility.spec.ts`: create a save via `POST /api/saves/new`, navigate to `http://127.0.0.1:8000/`, then click to reach the target screen. The base URL is `http://127.0.0.1:8000` (hardcoded in existing specs — **not** via `baseURL` config; use the same pattern). The Dynasty Office is reached via the main nav; the recruit tab is the default subtab.

**Files:**
- Create: `tests/e2e/v15-recruit-board.spec.ts`

- [ ] **Step 1: Create the spec**

```ts
import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

// V15 Phase 2a legibility smoke for the recruit board.
// Does NOT re-test scout/contact/visit action mechanics (covered elsewhere).
test.describe('recruit board legibility (V15 Phase 2a)', () => {
  let saveName: string;

  test.beforeEach(async ({ page, request }) => {
    saveName = `e2e-v15-recruit-${Date.now()}`;
    const create = await request.post(`${baseUrl}/api/saves/new`, {
      data: { name: saveName, club_id: 'aurora' },
    });
    expect(create.ok()).toBeTruthy();

    // Navigate to Dynasty Office → Recruit tab (default subtab).
    await page.goto(`${baseUrl}/?tab=dynasty`);
    // Wait for either the recruit board or an initial loading state to resolve.
    await expect(page.locator('.do-board')).toBeVisible({ timeout: 10_000 });
  });

  test('hometown reads with a "From" prefix, not as a surname', async ({ page }) => {
    const card = page.locator('.do-recruit').first();
    await expect(card).toBeVisible();
    // The "From" prefix must appear in the sub-row.
    await expect(card.locator('text=From')).toBeVisible();
    // The sub-row must NOT render prospect.hometown immediately after a "·" with no prefix.
    // (Verified structurally by the "From" label being present.)
  });

  test('archetype badge opens a TermTip tooltip on focus', async ({ page }) => {
    const card = page.locator('.do-recruit').first();
    // The TermTip renders as a button with aria-label "What is <ArchetypeName>?".
    // Use `.first()` in case multiple TermTips are on the same card.
    const archetypeTip = card
      .getByRole('button', { name: /What is (Sharpshooter|Net Specialist|Ball Hawk|Iron Anchor|Two-Way Threat|Skirmisher|Possession Specialist|Hit-and-Run)\?/i })
      .first();
    await archetypeTip.focus();
    await expect(page.getByRole('tooltip').first()).toBeVisible();
    // The tooltip must classify the term as mechanical (affects play).
    await expect(page.getByRole('tooltip').first()).toContainText(/affects play/i);
  });

  test('OVR range shows KnownValue estimated state for unscouted prospect', async ({ page }) => {
    // Fresh career: all prospects are unscouted — the KnownValue must show estimated state.
    // The KnownValue group's aria-label contains "estimated" for unscouted.
    const card = page.locator('.do-recruit').first();
    const ovrGroup = card.getByRole('group', { name: /OVR.*estimated/i });
    await expect(ovrGroup).toBeVisible();
    // The "Scout to narrow" hint must be present on the card.
    await expect(card).toContainText(/Scout to narrow/i);
    // The scouting caption below the evidence row must also appear.
    await expect(card).toContainText(/Scout to narrow the OVR range/i);
  });

  test('FIT value shows /100 denominator to distinguish it from a roster OVR', async ({ page }) => {
    const card = page.locator('.do-recruit').first();
    // The /100 suffix must be visible on the card's FIT number.
    await expect(card).toContainText(/\/100/);
  });

  test('fit-tier legend row explains card color', async ({ page }) => {
    const card = page.locator('.do-recruit').first();
    await expect(card).toContainText(/Strong Fit ≥80/i);
    await expect(card).toContainText(/Fair Fit 65/i);
    await expect(card).toContainText(/At Risk/i);
  });

  test('PipelineEmblem carries an accessible tier label', async ({ page }) => {
    const card = page.locator('.do-recruit').first();
    // PipelineEmblem renders as role="img" with aria-label "Pipeline Tier N (TierName)".
    const emblem = card.getByRole('img', { name: /Pipeline Tier [1-5]/i });
    await expect(emblem).toBeVisible();
  });

  test('sort by Interest changes or preserves order without crashing', async ({ page }) => {
    // Click the Interest sort button.
    await page.getByRole('button', { name: /^Interest$/i }).click();
    // Board must still render cards.
    await expect(page.locator('.do-recruit').first()).toBeVisible();
    // Clicking again toggles direction (↓ becomes ↑ in button text).
    await page.getByRole('button', { name: /Interest/i }).click();
    await expect(page.locator('.do-recruit').first()).toBeVisible();
  });

  test('sort by Pipeline changes or preserves order without crashing', async ({ page }) => {
    await page.getByRole('button', { name: /^Pipeline$/i }).click();
    await expect(page.locator('.do-recruit').first()).toBeVisible();
  });

  test('At Risk filter empty-state renders without fabricated data', async ({ page }) => {
    await page.getByRole('button', { name: /At Risk/i }).click();
    const cardCount = await page.locator('.do-recruit').count();
    if (cardCount === 0) {
      // EmptyState must be present (role="status") and must say "No prospects match".
      await expect(page.getByRole('status')).toContainText(/No prospects match/i);
      // Must NOT fabricate a prospect name or stat.
      await expect(page.getByRole('status')).not.toContainText(/OVR|Fit \d+|Interest \d+/i);
    }
    // If cardCount > 0, filter is working correctly — no empty-state assertion needed.
  });
});
```

- [ ] **Step 2: Run the spec**

Run (from repo root): `npm run e2e -- v15-recruit-board`
Expected: all tests PASS.

If `page.goto('/?tab=dynasty')` does not land on the recruit tab directly (e.g. the tab param name differs), check how the existing `v14-legibility.spec.ts` navigates to the dynasty subtab and replicate that pattern. Run `git grep -n "tab=dynasty\|subtab=recruit\|dynastyOffice\|do-board" -- tests/e2e` to find the correct query param.

- [ ] **Step 3: Run the full e2e suite**

Run (from repo root): `npm run e2e`
Expected: zero regressions. If any pre-existing spec asserts `'Visit-Ready'` or `'INT '` text, update it to the new labels (Phase 0 already removed "Visit-Ready"; "INT " → "Interest").

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/v15-recruit-board.spec.ts
git commit -m "test(v15-p2a): Playwright legibility smoke for recruit board

Covers: 'From' prefix on hometown; archetype TermTip opens on focus with
AFFECTS PLAY classification; OVR KnownValue shows estimated state + hint
for a fresh-career unscouted prospect; FIT /100 denominator present;
fit-tier legend text present; PipelineEmblem accessible tier label;
sort toggles without crash; At Risk empty-state renders honestly.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 2a Exit Gates

Run all before declaring Phase 2a done:

- [ ] From `frontend/`: `npm run build` — clean (proves the no-orphan-term gate: every `TermTip term="..."` resolves).
- [ ] From `frontend/`: `npm run lint` — clean.
- [ ] From repo root: `npm run e2e -- v15-recruit-board` — all tests green.
- [ ] From repo root: `npm run e2e` — full suite zero regressions.
- [ ] `python -m pytest -q` — green (no backend files changed, but required as the baseline invariant check).
- [ ] `python tools/tier_engine_health_probe.py --driver official --trials 50` — summary **unchanged** vs Phase 0 baseline (zero engine touch this phase; required per V15 hard invariant).
- [ ] Manual check at 390×844 on a fresh "Build from Scratch" career:
  - No horizontal overflow on any prospect card.
  - The `do-recruit-sub` sub-row wraps cleanly (rank · From location · badge · status · pipeline).
  - FIT number shows `/100`; OVR shows dashed KnownValue with "Scout to narrow".
  - Fit-tier legend (● Strong Fit ≥80, ● Fair Fit 65–79, ● At Risk <65) is visible on each card.
  - Sort buttons (Fit / Interest / Pipeline) appear in the board header with a direction arrow on the active sort.
  - "Visit-Ready" does not appear anywhere on the page.
  - Archetype badge hover/tap shows a tooltip with "AFFECTS PLAY" classification.
- [ ] Confirm `frontend/src/legibility/terms.ts` has exactly 3 new key additions (`archetype.ball_hawk`, `archetype.iron_anchor`, `archetype.two_way_threat`) and no existing key ids were changed.
- [ ] Confirm `frontend/src/legibility/` has no new files (only `terms.ts` was edited).

---

## Cross-screen overlap notes for future phases

- **`archetypeTermId` / `ARCHETYPE_MAP`:** Phase 2b (Roster/Player Card) needs the same archetype-label → `TermId` mapping. Extract `ARCHETYPE_MAP` and the `archetypeBadge` function to a shared utility at `frontend/src/legibility/archetypeMap.ts` when writing Phase 2b to avoid duplicating the logic.
- **FIT tier colors** (`#34d399` / `#f59e0b` / `#f87171`): verify these do not conflict with the Roster's player OVR tier color scheme before Phase 2b ships. If Roster uses different hex values for the same tiers, normalize them in a shared `tierColor.ts` utility.
- **`KnownValue` "estimated" dashed style:** Roster (Phase 2b) also has hidden/estimated attributes (growth ceiling, potential). Use the same `KnownValue` pattern — do not re-derive a bespoke dashed border.
- **Sort controls:** The `do-board-filter` button class is reused for sort toggles. If Phase 2c (Lineup Editor) needs sort affordances, normalize to a shared pattern rather than copy-pasting.
- **`pipeline_tier` in the payload:** Confirmed present in `_prospect_rows` (line 167) and in `types.ts:1107`. No backend task needed this phase. Phase 3b (Staff pipeline candidates) should confirm whether its candidate payload also includes `pipeline_tier` before reusing `PipelineEmblem` there.
- **`dm-badge-slate`:** If added to `index.css` for the Iron Anchor badge, document it alongside the other `dm-badge-*` rules so Phase 2b/3x don't duplicate it.
