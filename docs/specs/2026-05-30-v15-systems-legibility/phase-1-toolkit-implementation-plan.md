# V15 Phase 1 — Legibility Toolkit (Keystone): Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the reusable legibility toolkit in a new `frontend/src/legibility/` directory, delivering the frozen API contract in `implementation-index.md` so every Phase 2–4 screen plan can consume it without drift.

**Architecture:** Six small, single-responsibility React/TS modules + a barrel. The terms registry uses `as const satisfies` so `TermId` is a closed union — referencing a missing term is a **compile error** (`tsc -b`), which is the "no-orphan-term" gate without any new test dependency. No screen consumes the toolkit in this phase; Phase 1 only ships the infrastructure and a Playwright smoke that mounts each primitive on a throwaway dev-only route.

**Tech Stack:** React 19 + TypeScript ~6 + Vite 8 (`tsc -b && vite build`), ESLint, root Playwright (`npm run e2e`). **No frontend unit-test runner exists and none may be added** (no new deps) — verification is the compile gate + lint + a Playwright smoke.

> **Pre-flight:**
> - Branch off `main`: `git checkout -b feat/v15-phase1-toolkit`. Phase 1 only **creates** files under `frontend/src/legibility/` (+ one dev-only smoke route), so it can run fully parallel to Phase 0.
> - Components in this repo use **inline `style={{}}` + `dm-*` classNames**, not Tailwind utilities. Match that. Colors follow the existing palette (slate/cyan/amber seen across `dm-*` components).
> - Verify green baseline: from `frontend/`, `npm run build && npm run lint` must pass before starting.

---

## File Structure

| File | Responsibility |
|---|---|
| `frontend/src/legibility/terms.ts` | The terms registry + `TermId` closed union + `getTerm` |
| `frontend/src/legibility/TermTip.tsx` | Accessible term explainer (hover/focus/tap) |
| `frontend/src/legibility/KnownValue.tsx` | Fog-of-war known/estimated/hidden convention |
| `frontend/src/legibility/ProofChip.tsx` | Reusable payload-backed evidence chip |
| `frontend/src/legibility/EmptyState.tsx` | Honest empty-state |
| `frontend/src/legibility/PipelineEmblem.tsx` | Tiered pipeline emblem (T5 pink → T1 bronze) |
| `frontend/src/legibility/index.ts` | Barrel export |
| `frontend/src/legibility/archetypeMap.ts` | Shared player/club archetype → `TermId` maps (consumed by 2a/2b/2d/3c) |

---

## Task 1: Pipeline emblem (no dependencies — warm-up)

**Files:**
- Create: `frontend/src/legibility/PipelineEmblem.tsx`

- [ ] **Step 1: Create the component**

```tsx
// Tiered recruiting-pipeline emblem. College-football-style tier colors so a
// glance communicates pipeline strength: T5 pink (elite) down to T1 bronze.
export type PipelineTier = 1 | 2 | 3 | 4 | 5;

const TIER_STYLE: Record<PipelineTier, { color: string; ring: string; name: string }> = {
  5: { color: '#ec4899', ring: 'rgba(236,72,153,0.35)', name: 'Elite' },
  4: { color: '#22d3ee', ring: 'rgba(34,211,238,0.35)', name: 'Premier' },
  3: { color: '#f59e0b', ring: 'rgba(245,158,11,0.35)', name: 'Gold' },
  2: { color: '#cbd5e1', ring: 'rgba(203,213,225,0.30)', name: 'Silver' },
  1: { color: '#b45309', ring: 'rgba(180,83,9,0.30)', name: 'Bronze' },
};

export function PipelineEmblem({ tier, size = 'md' }: { tier: PipelineTier; size?: 'sm' | 'md' }) {
  const t = TIER_STYLE[tier];
  const dim = size === 'sm' ? '1.1rem' : '1.5rem';
  return (
    <span
      role="img"
      aria-label={`Pipeline Tier ${tier} (${t.name})`}
      title={`Pipeline Tier ${tier} — ${t.name}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: dim,
        height: dim,
        borderRadius: '50%',
        color: '#0b1220',
        fontWeight: 800,
        fontSize: size === 'sm' ? '0.6rem' : '0.75rem',
        background: t.color,
        boxShadow: `0 0 0 3px ${t.ring}`,
        fontVariantNumeric: 'tabular-nums',
      }}
    >
      {tier}
    </span>
  );
}
```

- [ ] **Step 2: Compile gate**

Run (from `frontend/`): `npm run build`
Expected: PASS (component is self-contained and exported).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/legibility/PipelineEmblem.tsx
git commit -m "feat(v15-p1): pipeline emblem primitive (tiered T5-T1)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Terms registry + the compile-time no-orphan gate

**Context:** `TERMS` is the single source of truth for every explainable term. `as const satisfies Record<string, TermDef>` keeps full literal types **and** validates the shape, so `TermId = keyof typeof TERMS` is a closed union. Any later `<TermTip term="missing.id">` fails `tsc`. **Seed all known term ids now** (even with first-draft copy) so Phase 2–4 plans only *edit* copy, never *add keys* — eliminating the one shared-file merge risk in the parallel lanes.

**Files:**
- Create: `frontend/src/legibility/terms.ts`

- [ ] **Step 1: Create the registry, pre-seeded with the V15 term set**

```ts
export type TermKind = 'mechanical' | 'flavor';

export interface TermDef {
  label: string;
  plain: string;
  why: string;
  kind: TermKind;
}

// Single source of truth. Keys are stable ids ("<group>.<name>"). Phase 2-4 plans
// EDIT copy here but should not need to ADD keys (all known terms are pre-seeded).
export const TERMS = {
  // --- Player archetypes (mechanical: drive match behavior) ---
  // KEYED BY THE CANONICAL PlayerArchetype ENUM VALUE (models.py:12). Labels are the
  // recruitment display names (recruitment.py:93 _RECRUITMENT_DISPLAY_NAMES). All eight
  // are pre-seeded so screen phases (2a/2b/3c) only edit copy, never add keys.
  'archetype.thrower': {
    label: 'Sharpshooter',
    plain: 'Aggressive attacker who looks to eliminate opponents with throws.',
    why: 'Higher throw volume and accuracy — a primary source of eliminations.',
    kind: 'mechanical',
  },
  'archetype.catcher': {
    label: 'Net Specialist',
    plain: 'Catch-focused defender who turns incoming throws into resurrections.',
    why: 'A catch outs the thrower AND brings a teammate back — high swing.',
    kind: 'mechanical',
  },
  'archetype.ball_hawk': {
    label: 'Ball Hawk',
    plain: 'Aggressive catcher who hunts risky catches off live throws.',
    why: 'Generates catches (resurrections) but can over-commit and get out.',
    kind: 'mechanical',
  },
  'archetype.dodger_anchor': {
    label: 'Iron Anchor',
    plain: 'Evasive survivor who anchors the floor and avoids elimination.',
    why: 'Stays alive late, when survivor counts decide foam games.',
    kind: 'mechanical',
  },
  'archetype.thrower_catcher': {
    label: 'Two-Way Threat',
    plain: 'Balanced hybrid who both throws to eliminate and catches to resurrect.',
    why: 'Flexible lineup glue with no glaring liability to target.',
    kind: 'mechanical',
  },
  'archetype.thrower_dodger': {
    label: 'Skirmisher',
    plain: 'Mobile attacker who throws and evades rather than catching.',
    why: 'Pressures opponents while staying hard to eliminate.',
    kind: 'mechanical',
  },
  'archetype.catcher_hawk': {
    label: 'Possession Specialist',
    plain: 'Catch-first player who controls tempo and wins the catch battle.',
    why: 'Tilts the catch swing — often the deciding factor at large OVR gaps.',
    kind: 'mechanical',
  },
  'archetype.hawk_dodger': {
    label: 'Hit-and-Run',
    plain: 'Evasive opportunist who picks catches and slips elimination.',
    why: 'Survives and steals swing catches without holding ground.',
    kind: 'mechanical',
  },
  // --- Coach / program archetypes (mechanical: bias the AI club's tactics) ---
  // The six values classify_club_archetype() returns (persistence.py:900). Keyed by slug.
  'coach.balanced': {
    label: 'Balanced',
    plain: 'No strong tactical lean; adapts to the matchup.',
    why: 'Safe default — fewer exploitable tendencies, fewer sharp edges.',
    kind: 'mechanical',
  },
  'program.archetype.balanced_rebuild': {
    label: 'Balanced Rebuild',
    plain: 'A well-rounded club without a dominant strength yet.',
    why: 'No obvious matchup edge to exploit or fear — read it as average.',
    kind: 'flavor',
  },
  'program.archetype.contender': {
    label: 'Contender',
    plain: 'A high-overall roster built to win now.',
    why: 'Expect a strong starting six — a genuinely tough matchup.',
    kind: 'flavor',
  },
  'program.archetype.development_factory': {
    label: 'Development Factory',
    plain: 'A young, high-potential roster that may rest starters in soft weeks.',
    why: 'Beatable now, dangerous later; they sometimes field developing players.',
    kind: 'flavor',
  },
  'program.archetype.defensive_specialist': {
    label: 'Defensive Specialist',
    plain: 'A club skewed toward dodging and catching over throwing.',
    why: 'Hard to eliminate and catch-heavy — the catch swing favors them.',
    kind: 'flavor',
  },
  'program.archetype.power_throwers': {
    label: 'Power Throwers',
    plain: 'A club skewed toward accuracy and power over defense.',
    why: 'Throw-heavy pressure; thinner on catches and survival.',
    kind: 'flavor',
  },
  'program.archetype.aging_veterans': {
    label: 'Aging Veterans',
    plain: 'An older roster past its physical peak.',
    why: 'Experienced but declining — upside is limited going forward.',
    kind: 'flavor',
  },
  // --- V2 attributes (mechanical; finishes V14 Task 3) ---
  'attr.throw_selection_iq': {
    label: 'Throw Selection IQ',
    plain: 'How well a player picks good throws vs. low-percentage ones.',
    why: 'Higher IQ means fewer wasted/headshot throws and fewer flood-throw mistakes.',
    kind: 'mechanical',
  },
  'attr.catch_courage': {
    label: 'Catch Courage',
    plain: 'Willingness to attempt catches on hard incoming throws.',
    why: 'More catch attempts = more resurrections, but missed attempts cost eliminations.',
    kind: 'mechanical',
  },
  // --- Growth / potential (mechanical framing of dev) ---
  'growth.ceiling': {
    label: 'Ceiling',
    plain: 'The highest OVR this player is projected to reach.',
    why: 'Headroom above current OVR is how much they can still grow.',
    kind: 'mechanical',
  },
  'growth.headroom': {
    label: 'Headroom',
    plain: 'Ceiling minus current OVR — remaining growth room.',
    why: 'High headroom + young age = a genuine high-upside develop target.',
    kind: 'mechanical',
  },
  // --- Recruiting signals (mechanical) ---
  'recruit.fit': {
    label: 'Fit',
    plain: 'How well this prospect matches your program right now (0-100).',
    why: 'Higher fit closes more easily; it is NOT the same as their OVR.',
    kind: 'mechanical',
  },
  'recruit.interest': {
    label: 'Interest',
    plain: 'How interested the prospect is in your program (%).',
    why: 'Rises with contact/visits and credibility; courted prospects are easier to sign.',
    kind: 'mechanical',
  },
  'recruit.ovr_range': {
    label: 'OVR Range',
    plain: 'The estimated band for this prospect’s true overall.',
    why: 'Scouting narrows the band — you learn how good they really are.',
    kind: 'mechanical',
  },
  'recruit.pipeline': {
    label: 'Pipeline',
    plain: 'A recruiting region/tier your program has a relationship with.',
    why: 'Stronger pipeline tier means warmer prospects and easier closes.',
    kind: 'mechanical',
  },
  // --- Program credibility vs club prestige (the naming collision) ---
  'program.credibility': {
    label: 'Program Credibility',
    plain: 'The recruiting-facing reputation that sets which prospects are interested.',
    why: 'Rises with wins and dev; gates the tier of recruits you can attract.',
    kind: 'mechanical',
  },
  'program.prestige': {
    label: 'Club Prestige',
    plain: 'A separate long-term score earned from titles and facilities.',
    why: 'Feeds into credibility over time; 0 on a brand-new club is normal.',
    kind: 'mechanical',
  },
  // --- Standings (mostly flavor/among-derived) ---
  'standings.diff': {
    label: 'Differential',
    plain: 'Eliminations for minus against across the season.',
    why: 'A tiebreaker and a rough strength signal beyond W-L-D.',
    kind: 'mechanical',
  },
  'standings.playoff_line': {
    label: 'Playoff Line',
    plain: 'The cutoff seed that makes the postseason (top N).',
    why: 'Clubs above the line are in; below are out — your weekly target.',
    kind: 'mechanical',
  },
  // --- Identity (flavor) ---
  'identity.intent': {
    label: 'Program Identity',
    plain: 'Your program’s historical strategic lean (e.g. Balanced).',
    why: 'A flavor summary of how you’ve managed — not a hidden stat bonus.',
    kind: 'flavor',
  },
} as const satisfies Record<string, TermDef>;

export type TermId = keyof typeof TERMS;

export function getTerm(id: TermId): TermDef {
  return TERMS[id];
}
```

- [ ] **Step 2: Compile gate**

Run (from `frontend/`): `npm run build`
Expected: PASS. (If `as const satisfies` errors, confirm `typescript ~6` in `package.json` — `satisfies` requires TS ≥ 4.9; this repo is on 6.)

- [ ] **Step 3: Prove the gate works (negative check — do NOT commit this)**

Temporarily add to any `.tsx`: `import { getTerm } from './legibility/terms'; getTerm('does.not.exist');`
Run: `npm run build`
Expected: FAIL — `Argument of type '"does.not.exist"' is not assignable to parameter of type 'TermId'`. Revert the temporary line. This confirms the no-orphan-term gate is live.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/legibility/terms.ts
git commit -m "feat(v15-p1): terms registry with compile-time no-orphan gate

TermId is a closed union via 'as const satisfies'; a missing term is a tsc
error, so the no-orphan-term gate needs no test runner. Pre-seeded with the
V15 term set so screen phases edit copy, not keys.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: TermTip explainer

**Files:**
- Create: `frontend/src/legibility/TermTip.tsx`

- [ ] **Step 1: Create the component (accessible, keyboard + tap + hover)**

```tsx
import { useId, useState } from 'react';
import { getTerm, type TermId } from './terms';

// Wraps a term in an accessible explainer. The trigger is a focusable button so
// keyboard and touch users get the same popover as hover; aria-describedby ties
// the trigger to the description for screen readers.
export function TermTip({ term, children }: { term: TermId; children: React.ReactNode }) {
  const def = getTerm(term);
  const [open, setOpen] = useState(false);
  const descId = useId();

  return (
    <span style={{ position: 'relative', display: 'inline-flex' }}>
      <button
        type="button"
        aria-describedby={open ? descId : undefined}
        aria-label={`What is ${def.label}?`}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen((v) => !v)}
        style={{
          background: 'none',
          border: 'none',
          padding: 0,
          margin: 0,
          font: 'inherit',
          color: 'inherit',
          cursor: 'help',
          borderBottom: '1px dotted #64748b',
        }}
      >
        {children}
      </button>
      {open && (
        <span
          id={descId}
          role="tooltip"
          style={{
            position: 'absolute',
            bottom: 'calc(100% + 6px)',
            left: 0,
            zIndex: 50,
            width: 'min(16rem, 70vw)',
            background: '#0b1220',
            border: '1px solid #1e293b',
            borderRadius: '6px',
            padding: '0.5rem 0.6rem',
            boxShadow: '0 10px 30px -10px rgba(0,0,0,0.6)',
            textAlign: 'left',
            whiteSpace: 'normal',
          }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.2rem' }}>
            <b style={{ color: '#fff', fontSize: '0.72rem' }}>{def.label}</b>
            <span
              style={{
                fontSize: '0.5rem',
                fontWeight: 800,
                letterSpacing: '0.05em',
                padding: '0.05rem 0.3rem',
                borderRadius: '2px',
                color: '#0b1220',
                background: def.kind === 'mechanical' ? '#22d3ee' : '#a78bfa',
              }}
            >
              {def.kind === 'mechanical' ? 'AFFECTS PLAY' : 'FLAVOR'}
            </span>
          </span>
          <span style={{ display: 'block', color: '#cbd5e1', fontSize: '0.66rem', lineHeight: 1.4 }}>
            {def.plain}
          </span>
          <span style={{ display: 'block', color: '#94a3b8', fontSize: '0.62rem', lineHeight: 1.4, marginTop: '0.25rem' }}>
            {def.why}
          </span>
        </span>
      )}
    </span>
  );
}
```

- [ ] **Step 2: Compile + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS. (If lint flags the `React.ReactNode` global, add `import type { ReactNode } from 'react'` and use `ReactNode` — match whatever the repo's other components do; check with `git grep -n "ReactNode" -- frontend/src`.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/legibility/TermTip.tsx
git commit -m "feat(v15-p1): TermTip accessible term explainer

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: KnownValue, ProofChip, EmptyState

**Files:**
- Create: `frontend/src/legibility/KnownValue.tsx`, `ProofChip.tsx`, `EmptyState.tsx`

- [ ] **Step 1: KnownValue (fog-of-war)**

```tsx
// Fog-of-war convention. known = solid value; estimated = dashed + range/±, with a
// "scout to narrow" hint; hidden = locked glyph. Lets recruit/scouting surfaces show
// honestly what the player knows vs. doesn't.
export type Knowledge = 'known' | 'estimated' | 'hidden';

export function KnownValue({
  state,
  label,
  value,
  hint,
}: {
  state: Knowledge;
  label: string;
  value?: React.ReactNode;
  hint?: string;
}) {
  const border = state === 'known' ? '1px solid #334155' : state === 'estimated' ? '1px dashed #f59e0b' : '1px dashed #475569';
  return (
    <span
      role="group"
      aria-label={`${label}: ${state === 'hidden' ? 'unknown, scout to reveal' : state}`}
      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', border, borderRadius: '4px', padding: '0.1rem 0.4rem' }}
    >
      <span style={{ fontSize: '0.55rem', letterSpacing: '0.05em', color: '#94a3b8', textTransform: 'uppercase' }}>{label}</span>
      <span style={{ fontVariantNumeric: 'tabular-nums', color: state === 'hidden' ? '#64748b' : '#e2e8f0', fontWeight: 700 }}>
        {state === 'hidden' ? '🔒' : value ?? '—'}
      </span>
      {hint && state !== 'known' && (
        <span style={{ fontSize: '0.55rem', color: '#f59e0b' }}>{hint}</span>
      )}
    </span>
  );
}
```

- [ ] **Step 2: ProofChip**

```tsx
import { useId, useState } from 'react';

// A claim with its receipt. `source` must be a payload-derived string (e.g. an
// evidence sentence the backend computed); never a hardcoded assertion. Click/focus
// reveals the source so any claim is auditable — the decision-traceability north star.
export function ProofChip({ label, source }: { label: string; source: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <span style={{ position: 'relative', display: 'inline-flex' }}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.25rem',
          background: 'rgba(34,211,238,0.10)',
          border: '1px solid rgba(34,211,238,0.4)',
          color: '#67e8f9',
          borderRadius: '3px',
          padding: '0.1rem 0.4rem',
          fontSize: '0.62rem',
          fontWeight: 700,
          cursor: 'pointer',
        }}
      >
        {label} <span aria-hidden="true">ⓘ</span>
      </button>
      {open && (
        <span
          id={id}
          role="note"
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            zIndex: 50,
            width: 'min(15rem, 70vw)',
            background: '#0b1220',
            border: '1px solid #1e293b',
            borderRadius: '6px',
            padding: '0.4rem 0.55rem',
            fontSize: '0.62rem',
            color: '#cbd5e1',
            lineHeight: 1.4,
          }}
        >
          {source}
        </span>
      )}
    </span>
  );
}
```

- [ ] **Step 3: EmptyState**

```tsx
// Honest empty-state. No fabricated data — when there is nothing yet, say so plainly
// and tell the player what will fill it.
export function EmptyState({ title, body, icon }: { title: string; body: string; icon?: React.ReactNode }) {
  return (
    <div
      role="status"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '0.35rem',
        textAlign: 'center',
        padding: '1.25rem 1rem',
        color: '#94a3b8',
        border: '1px dashed #1e293b',
        borderRadius: '8px',
        background: 'rgba(15,23,42,0.4)',
      }}
    >
      {icon && <span aria-hidden="true" style={{ fontSize: '1.4rem', opacity: 0.7 }}>{icon}</span>}
      <strong style={{ color: '#cbd5e1', fontSize: '0.8rem' }}>{title}</strong>
      <span style={{ fontSize: '0.68rem', lineHeight: 1.4, maxWidth: '22rem' }}>{body}</span>
    </div>
  );
}
```

- [ ] **Step 4: Compile + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/legibility/KnownValue.tsx frontend/src/legibility/ProofChip.tsx frontend/src/legibility/EmptyState.tsx
git commit -m "feat(v15-p1): KnownValue, ProofChip, EmptyState primitives

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Barrel + shared archetype map

**Context:** No frontend unit-test runner exists. The e2e suite (`tests/e2e`) runs against the **Python backend serving a pre-built static bundle** (`playwright.config.ts` `webServer` launches uvicorn; specs hard-code `http://127.0.0.1:8000`), so `import.meta.env.DEV` is **false** at e2e time — a dev-only smoke route would be unreachable. Therefore Phase 1 verifies the primitives via the **compile gate + lint** only; their *behavior* is covered in Phase 5 on the real screens that ship them (Recruit Board, Roster, Standings). This task ships the barrel plus the shared archetype map that every archetype-displaying screen (2a/2b/2d/3c) consumes so they don't each build their own reverse map.

**Files:**
- Create: `frontend/src/legibility/index.ts`, `frontend/src/legibility/archetypeMap.ts`

- [ ] **Step 1: Barrel**

```ts
export { TERMS, getTerm } from './terms';
export type { TermId, TermDef, TermKind } from './terms';
export { TermTip } from './TermTip';
export { KnownValue } from './KnownValue';
export type { Knowledge } from './KnownValue';
export { ProofChip } from './ProofChip';
export { EmptyState } from './EmptyState';
export { PipelineEmblem } from './PipelineEmblem';
export type { PipelineTier } from './PipelineEmblem';
export { PLAYER_ARCHETYPE_TERM, CLUB_ARCHETYPE_TERM } from './archetypeMap';
```

- [ ] **Step 2: Shared archetype map (single source for screen phases)**

Backend payloads should carry the canonical **enum key / classifier string** (not only a pre-translated display name) so the frontend can resolve a `TermId`. Where a payload currently sends only a display name, the consuming screen plan adds the raw key (see Phase 2a/2b/3c). These maps are the one place display/key → `TermId` lives.

```ts
import type { TermId } from './terms';

// PlayerArchetype enum value (models.py) -> TermId. Keys match the backend enum exactly.
export const PLAYER_ARCHETYPE_TERM: Record<string, TermId> = {
  thrower: 'archetype.thrower',
  catcher: 'archetype.catcher',
  ball_hawk: 'archetype.ball_hawk',
  dodger_anchor: 'archetype.dodger_anchor',
  thrower_catcher: 'archetype.thrower_catcher',
  thrower_dodger: 'archetype.thrower_dodger',
  catcher_hawk: 'archetype.catcher_hawk',
  hawk_dodger: 'archetype.hawk_dodger',
};

// classify_club_archetype() string (persistence.py) -> TermId.
export const CLUB_ARCHETYPE_TERM: Record<string, TermId> = {
  'Balanced Rebuild': 'program.archetype.balanced_rebuild',
  'Contender': 'program.archetype.contender',
  'Development Factory': 'program.archetype.development_factory',
  'Defensive Specialist': 'program.archetype.defensive_specialist',
  'Power Throwers': 'program.archetype.power_throwers',
  'Aging Veterans': 'program.archetype.aging_veterans',
};
```

- [ ] **Step 3: Compile + lint gate**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS. The `Record<string, TermId>` values are checked against the closed `TermId` union, so a typo in any archetype TermId is a compile error here.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/legibility/index.ts frontend/src/legibility/archetypeMap.ts
git commit -m "feat(v15-p1): toolkit barrel + shared archetype->term maps

Behavioral coverage of the primitives lands in Phase 5 on the real screens
(the e2e suite serves a pre-built bundle, so a dev-only smoke route is
unreachable). The compile gate + lint verify Phase 1.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 1 Exit Gates
- [ ] From `frontend/`: `npm run build` (the tsc gate — also proves the no-orphan-term union compiles and the archetype maps resolve) && `npm run lint` — clean.
- [ ] Run the negative check in Task 2 Step 3 once to confirm the no-orphan-term gate fails the build on an undefined `TermId`, then revert.
- [ ] `frontend/src/legibility/` exports exactly the [locked contract](implementation-index.md#locked-toolkit-api-contract-phase-1-delivers-exactly-this) plus the archetype maps; no screen imports it yet (grep: `git grep -n "from '.*/legibility'" -- frontend/src` shows only the barrel's internal files).
- [ ] No backend/engine files touched. Behavioral verification of the primitives is deferred to Phase 5 (on the real screens), because the e2e suite serves a pre-built bundle and cannot reach a dev-only route.

## Hand-off note to Phase 2–4 authors
Import from `frontend/src/legibility`. If a screen needs a term not in `TERMS`, ADD the key in the
same PR (append-only) — but prefer editing the pre-seeded copy. Every `ProofChip.source` and
`KnownValue` you place must be wired to a real payload field; if the field doesn't exist, that's a
backend task in your phase, or an `EmptyState` — never invented text.
