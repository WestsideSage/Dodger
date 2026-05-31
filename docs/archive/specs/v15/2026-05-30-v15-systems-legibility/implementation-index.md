# V15 — Systems Legibility: Implementation Index

This is the **program index** for V15. It is not a task list — it is the dependency map, the
parallelization lanes, the plan-file manifest, and (critically) the **locked toolkit API contract**
that every screen plan references so parallel work cannot drift.

Read the [planning report](planning-report.md) first for thesis, scope, and the full observation
inventory. Hard invariant for the whole milestone: **zero engine/sim/RNG changes** — the
`tier_engine_health_probe` must read identically before/after every phase.

---

## Plan-file manifest

| Plan | File | Depends on | Parallelizable with |
|---|---|---|---|
| Phase 0 — Traceability bugs | `phase-0-implementation-plan.md` | — | everything |
| Phase 1 — Legibility toolkit (keystone) | `phase-1-toolkit-implementation-plan.md` | — | Phase 0 |
| Phase 2a — Recruit Board | `phase-2a-recruit-board-plan.md` | Phase 1 | 2b/2c/2d, all of Tier 2/3 |
| Phase 2b — Roster & Player Card | `phase-2b-roster-player-card-plan.md` | Phase 1 | other 2x, 3x, 4x |
| Phase 2c — Lineup Editor | `phase-2c-lineup-editor-plan.md` | Phase 1 | other 2x, 3x, 4x |
| Phase 2d — Standings & Matchup copy | `phase-2d-standings-matchup-plan.md` | Phase 1 | other 2x, 3x, 4x |
| Phase 3a — Dynasty Office / Credibility | `phase-3a-dynasty-office-plan.md` | Phase 1 | any other 2x/3x/4x |
| Phase 3b — Staff impact | `phase-3b-staff-impact-plan.md` | Phase 1 | any other 2x/3x/4x |
| Phase 3c — Season Preview density | `phase-3c-season-preview-plan.md` | Phase 1 (Phase 0 Task 4 first) | any other 2x/3x/4x |
| Phase 4a — History & Identity | `phase-4a-history-identity-plan.md` | Phase 1 | any other 2x/3x/4x |
| Phase 4b — App shell (nav, settings, hamburger) | `phase-4b-app-shell-plan.md` | Phase 1 | any other 2x/3x/4x |
| Phase 5 — Verification hardening | `phase-5-verification-plan.md` | all above | — |

**Status:** ✅ All 11 plans written (Phase 0, Phase 1, Phases 2a–2d, 3a–3c, 4a–4b, 5). Phases 2–5 were drafted in parallel against the locked contract, then reconciled — see [Cross-plan normalization](#cross-plan-normalization-post-parallel-pass) below for the binding decisions that supersede any conflicting per-plan step.

---

## Dependency graph & parallel lanes

```
Phase 0 ──────────────────────────────────────────────┐  (independent, ship first for trust)
                                                       │
Phase 1 (toolkit) ──┬──> Phase 2a Recruit Board ───────┤
   KEYSTONE         ├──> Phase 2b Roster/Player Card ───┤
   blocks 2–4       ├──> Phase 2c Lineup Editor ────────┤
                    ├──> Phase 2d Standings/Matchup ─────┤
                    ├──> Phase 3a Dynasty Office ────────┼──> Phase 5
                    ├──> Phase 3b Staff impact ──────────┤   (verification
                    ├──> Phase 3c Season Preview ────────┤    hardening,
                    ├──> Phase 4a History/Identity ──────┤    last)
                    └──> Phase 4b App shell ─────────────┘
```

**Parallelization rules for agents:**
1. **Lane 1 (now):** Phase 0 and Phase 1 can run **simultaneously** (different files: Phase 0 is backend + a few existing components; Phase 1 is a new `frontend/src/legibility/` directory). No collision.
2. **Gate:** Phases 2–4 must not start until **Phase 1 is merged**, because they `import` the locked contract below. Starting earlier means inventing the API and guaranteeing a rebase.
3. **Lane 2 (after Phase 1 merges):** every Phase 2/3/4 plan is **mutually parallel** — each owns a distinct screen/component, and all only *consume* the toolkit (read-only on `frontend/src/legibility/`). The only shared file risk is `frontend/src/legibility/terms.ts` (each phase **adds** its screen's term entries). Mitigation: term additions are append-only to `TERMS`; resolve trivially, or pre-seed all term ids in Phase 1 (see Phase 1 Task 2 note).
4. **Lane 3 (last):** Phase 5 after all merge.

---

## LOCKED toolkit API contract (Phase 1 delivers exactly this)

Every Phase 2/3/4 plan imports from `frontend/src/legibility/`. These signatures are **frozen** by
Phase 1; later phases reference them verbatim. No new npm dependencies — components use the repo's
existing inline-style + `dm-*` className convention (the codebase does not use Tailwind utility
classes in components).

### `frontend/src/legibility/terms.ts`
```ts
export type TermKind = 'mechanical' | 'flavor';
export interface TermDef {
  label: string;   // canonical display label, e.g. "Ball Hawk / Dodger"
  plain: string;   // one-line plain meaning
  why: string;     // why it matters to a decision
  kind: TermKind;  // mechanical = affects match outcomes; flavor = cosmetic identity
}
// TERMS is the single source of truth. `as const satisfies` makes TermId a closed union,
// so any <TermTip term="..."> referencing a missing id is a COMPILE error (the no-orphan gate).
export const TERMS = { /* ...entries... */ } as const satisfies Record<string, TermDef>;
export type TermId = keyof typeof TERMS;
export function getTerm(id: TermId): TermDef;
```

### `frontend/src/legibility/TermTip.tsx`
```tsx
// Accessible explainer: wraps children, shows label/plain/why + a mechanical|flavor pill on
// hover/focus/tap. Uses aria-describedby + a keyboard-focusable trigger.
export function TermTip(props: { term: TermId; children: React.ReactNode }): React.ReactElement;
```

### `frontend/src/legibility/KnownValue.tsx`
```tsx
export type Knowledge = 'known' | 'estimated' | 'hidden';
// Fog-of-war convention: known = solid, estimated = dashed + "±"/range, hidden = locked glyph.
export function KnownValue(props: {
  state: Knowledge;
  label: string;             // what this value is, e.g. "OVR"
  value?: React.ReactNode;   // shown for known/estimated
  hint?: string;             // e.g. "Scout to narrow" for estimated/hidden
}): React.ReactElement;
```

### `frontend/src/legibility/ProofChip.tsx`
```tsx
// Generalizes Aftermath evidence_chips. `source` MUST be a payload-derived string; never a
// hardcoded claim. Renders label + a small "proof" affordance exposing source.
export function ProofChip(props: { label: string; source: string }): React.ReactElement;
```

### `frontend/src/legibility/EmptyState.tsx`
```tsx
// Honest empty-state: title + body, no fabricated data. For banners/alumni/wire/records.
export function EmptyState(props: { title: string; body: string; icon?: React.ReactNode }): React.ReactElement;
```

### `frontend/src/legibility/PipelineEmblem.tsx`
```tsx
export type PipelineTier = 1 | 2 | 3 | 4 | 5;
// Tier 5 pink, 4 cyan, 3 gold, 2 silver, 1 bronze. aria-label "Pipeline Tier N".
export function PipelineEmblem(props: { tier: PipelineTier; size?: 'sm' | 'md' }): React.ReactElement;
```

### `frontend/src/legibility/archetypeMap.ts`
```ts
// Canonical display/enum -> TermId maps; screens import these, never reverse-map from strings.
export const PLAYER_ARCHETYPE_TERM: Record<string, TermId>;  // PlayerArchetype enum value -> TermId
export const CLUB_ARCHETYPE_TERM: Record<string, TermId>;    // classify_club_archetype() string -> TermId
```

### `frontend/src/legibility/index.ts`
Barrel re-exporting all of the above + types + the archetype maps.

---

## Cross-plan normalization (post-parallel pass)

These decisions were made after the Tier 2–5 plans were drafted in parallel. **They are binding and
supersede any conflicting step inside an individual plan.**

1. **Terms are pre-seeded canonically in Phase 1.** Phase 1 `terms.ts` now seeds the **8 real
   `PlayerArchetype` enum keys** (`archetype.thrower/catcher/ball_hawk/dodger_anchor/thrower_catcher/
   thrower_dodger/catcher_hawk/hawk_dodger`, labels = recruitment display names) and the **6 club
   archetypes** (`program.archetype.*`). Any step in Phase 2a/2b/2d/3c that says "append/add the
   archetype term keys" is **superseded** — those keys already exist; treat such steps as "verify /
   edit copy only." (The first parallel pass guessed wrong keys; this is the fix.)
2. **Shared archetype map.** Phase 1 ships `frontend/src/legibility/archetypeMap.ts`
   (`PLAYER_ARCHETYPE_TERM`, `CLUB_ARCHETYPE_TERM`). Screens MUST import these instead of defining
   their own display→TermId reverse maps (2a/2b/2d/3c each independently proposed one — use the
   shared map).
3. **Emit-enum-key payload pattern.** Where a backend payload currently sends only a *display name*
   for an archetype (e.g. Season Preview), the owning screen plan adds the raw **enum key**
   (`archetype_key`) alongside it so the frontend can resolve a `TermId`. Do not reverse-map from
   display strings. (3c already specifies this; 2a/2b confirmed their payloads already carry the key.)
4. **Single-owner term namespaces are fine as append-only** (no collision): `program.archetype.*`
   (seeded in Phase 1), `dept.*` (3a), `staff.*` (3b), `lineup.slot_order` (2c). Each is touched by
   exactly one plan. If two ever need the same key, add it to Phase 1's seed instead.
5. **DynastyOffice.tsx is shared by 3a + 3b.** 3a owns `CredibilityStrip`/`RecruitingContext`/
   `SettingsModal`; 3b owns `StaffBrief`/`StaffTab`/`StaffMarketModal`. **Merge order: 3a before 3b**;
   3b rebases to consolidate the single shared `import … from '../legibility'` line.
6. **ProgramModal split (2d ↔ 4a).** **4a owns the modal's content + a11y** (`role="dialog"`, focus
   trap, tabs, banner/alumni). **2d owns only the standings row-click wiring** (state + passing club
   ids). They do not edit the same code; 4a should land the dialog a11y fix.
7. **Credibility tier ticks (3a).** The CredibilityStrip tier ticks must align to the real `_grade()`
   thresholds **F/D/C/B/A at 0/40/55/70/85%** (not 0/33/66/100) — 3a's plan already corrects this;
   it is the concrete fix for the "Tier C vs score 0 reads contradictory" complaint.
8. **No dev-only e2e routes.** The e2e suite serves a **pre-built bundle via the Python backend**
   (`playwright.config.ts` `webServer` = uvicorn; specs hit `http://127.0.0.1:8000`), so
   `import.meta.env.DEV` is false and any `?debug`-style route is unreachable. All Playwright
   assertions target legibility surfaces **on the real shipping screens** (Phase 5), never a harness.
9. **Staff honesty (3b).** Per `staff_market.py`'s own rule, only the **training** department has a
   real mechanical hook (`training_modifier_pct`, derived from the live offseason-dev formula). Other
   departments are advisory — ProofChips/copy must say so, never imply a fake stat bonus.

## Shared constraints (every plan)
- Mobile 390×844, no horizontal overflow; AI-friendly semantic markup (`role`, `aria-*`).
- No new npm/python dependencies; no routing/auth change; no engine/RNG/scoring edits.
- "Explain, don't decide" — the event log is canon; UI surfaces it, never replaces it.
- Honesty: a `ProofChip.source` and any `KnownValue` must be backed by a real payload field; if data
  doesn't exist, use `EmptyState`, not invented content.
- Verification per plan: `python -m pytest -q` (when backend touched) · `npm run build` (tsc gate
  catches orphan terms) · `npm run lint` · `npm run e2e` for behavioral surfaces · engine-health
  probe unchanged.

## Out of scope for ALL V15 plans (deferred to their own specs)
Program Archive milestone-tree · Dynasty Office department-hub / Program-Settings subpages ·
recruiting-visits-as-major-action · sim-balance (foam draw density, catch-lever dominance).
