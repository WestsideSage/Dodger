# Floodlight Redesign — Parallelization & Sequencing Strategy

**Status:** Produced 2026-06-19 by a multi-agent analysis (8 coupling readers → strategist → 3 adversarial verifiers → finalizer), **grounded in-repo** (every claim verified against actual files, not the per-phase reports). This is the binding orchestration contract for executing Phases 1–8. Companion: [design](../specs/2026-06-19-ui-redesign-design.md), [audit/97-behavior contract](../specs/2026-06-19-ui-redesign-audit.md), [preservation checklist](floodlight-preservation-checklist.md), [Phase 0 plan](2026-06-19-floodlight-phase-0-foundations.md).

## Headline
Phases **can** be parallelized, but as a **diamond**, not a naive 8-way fan-out. Realistic **~1.7–2.1× speedup** vs pure-sequential (compresses toward ~1.5× if Phase 2's net-new SVG match canvas overruns — P2 sets the critical path). The win is concurrent **authoring** (components + CSS Modules + vitests) in git worktrees; the **deletion** of legacy `index.css` rules **must serialize** through one integrator — that single decision is what protects the 97-behavior trust contract.

## The load-bearing verdict: `index.css` is a SINGLE-WRITER resource
`frontend/src/index.css` is 8,743 lines with **interleaved `@media` brace-blocks**. The intuitive "each phase deletes its own disjoint selector range → clean 3-way merge" is **false-safe**: e.g. `.app-shell` is defined **4×** (lines 108, 360, 7571, **8631**), and the 8631 def lives inside an `@media (max-width:720px)` block that mixes P1 `.app-shell/.left-nav/.nav-item` + P6 `.fallout-grid` + P2 `.cc-*/.mr-*` in one brace-block. Two worktrees each deleting their own line from that shared hunk → conflict or a **silent dangling brace** that cascades and can break an unrelated truth-bearing layout (a scoreline number overlapping its label = the ADR-0002 "shown something less true" failure).
→ **Phases CREATE `*.module.css` + rewire components concurrently in worktrees; ALL `index.css` legacy deletion is deferred to a single serial integrator lane (STEP 3), one phase at a time, re-gated after each.** Begin STEP 3 with a programmatic brace-depth scan to re-derive the true `@media` interleave map (do not trust hand counts).

## Dependency DAG
- 0 → (done) · 1 → [0] · 2,3,4,5,7 → [0,1] · **6 → [0,1,4]** (ChampionReveal.tsx:4 statically imports PlayoffBracket from standings/) · 8 → [0,1,2,3,4,5,6,7]
- **Merge-strict edges** (depend on the *merged* commit, not branch-from): **7→1** (the wizard physically lives in SaveMenu.tsx, P1's file) and **6→4**.

## Cross-file contracts (the freezes that make the window safe)
| File | Rule |
|---|---|
| `index.css` | Single-writer. Phases create module CSS only; integrator does all deletions in STEP 3. P1 (solo) also deletes the **unowned dead** `.dm-app-shell/.dm-left-nav/.dm-nav-item/.dm-content` family. |
| `components/ui.tsx` | **NO in-place edits.** But **false-safe**: `ActionButton, PageHeader, StatusMessage, RatingBar, RadioGroup` exist ONLY here (no `src/ui` drop-in). STEP-1A creates **signature-identical token-driven `src/ui` shims** (+ `role='alert'`/handler contract vitests); phases re-point imports only. **No `ActionButton→ActionBar` remap** during the window (deferred to P8). |
| `MatchWeek.tsx:334` | `closest('.dm-left-nav')` is a **stale no-op today** (nav is `.left-nav`) AND a P1↔P2 global-class DOM contract gating reveal-skip (#1–8/#11–18). P1 adds `data-nav-rail` + vitest; P2 rewrites to `closest('[data-nav-rail]')` + a "nav-click does NOT advance revealStage" vitest. Only `closest()` in the codebase. |
| `match-week/matchResult.ts` | **Frozen** cross-phase contract (4 importers P2+P4). Public API `formatScoreline/survivorDetail/ScorelineFields/MatchScoreline` unchanged; no relocation (re-introduces the PT6 0-0 trust-break). |
| `dynasty/history/ProgramModal.tsx` | P5-owned, P4-consumed. P5 lands a **prop-stable skeleton on trunk in STEP 1** (before P4 integrates). |
| `standings/PlayoffBracket.tsx` | P4-owned, P6-consumed (real source edge). P4 lands a **prop-stable skeleton on trunk in STEP 1**. |
| `index.css` `command-action-bar` / `command-policy-overlay` | **SHARED, not P2-owned** — consumed by 10 P6 ceremony files + P2, and P5 ProgramModal + P2 respectively. Deletable **only in P8** behind a grep-zero gate (protects #17 worlds_user receipt, #67, #71, league-history overlay). |
| `scripts/check-tokens.mjs` (SCAN_DIRS) | **Integrator owns all appends** (8-way same-line append would conflict). Phases never touch it. |
| `legibility/*` | **Read-only for P2–P7; sole-writer P8.** Accept mixed Floodlight+legacy look until P8. Preserve `data-*` provenance through the new Popover; no focus-trap on TermTip. |
| `App.tsx` | **P1 sole-writer.** Publishes a compile-time interface for the MatchWeek mount props + `commandReplay` shape that P2 asserts against. `padStart` Week fix at line 249 here. |

## Execution sequence
**STEP 0 (DONE):** Phase 0 merged (19/19). Trunk green.

**STEP 1 — GROUP [1] SOLO, merge first.**
- *1A (integrator pre-step):* create signature-identical `src/ui` shims for the 5 orphan primitives + contract vitests; append to `src/ui/index.ts`.
- *1B (Phase 1):* 11 behavior vitests RED (#9,#10,#82–89,#91) + `data-nav-rail` + 720px-breakpoint vitests; reskin App.tsx + SaveMenu to CSS Modules; add `data-nav-rail`; `padStart` fix; delete all 4 `.app-shell` defs + dead dm-shell family; publish the MatchWeek-prop/`commandReplay`/`data-nav-rail` contracts; **land P4 PlayoffBracket + P5 ProgramModal prop-stable skeletons on trunk.**
- Gate (build+lint+lint:tokens+vitest+e2e+pytest) → merge.

**STEP 2 — PHASES 2,3,4,5,6,7 CONCURRENT** in 6 worktrees off post-STEP-1 trunk. Whole-window freezes: no `index.css` edits (module CSS only), no `ui.tsx` edits (re-point to shims, no API remap), `matchResult.ts`/`ProgramModal`/`PlayoffBracket` frozen, `command-action-bar`/`command-policy-overlay` shared, `legibility/*` untouched, `check-tokens.mjs` untouched. Each phase writes behavior + **enumerated `data-*` anti-strip vitests as HARD RED preconditions** before rebuilding. Within P2, sequence sub-areas (PreSimDashboard → aftermath → MatchReplay+canvas) — MatchWeek is the serial orchestrator, do not parallelize inside P2.

**STEP 3 — SERIAL `index.css` integration on trunk.** Brace-depth scan first. Merge one phase at a time, tight blocks first: P3 → P4 → P5 → P6 → P7(no css deletes) → **P2 last** (cc-/mr- + the shared `@media` tail). After EACH merge: remove that phase's legacy selectors (never the shared globals), append its dir to SCAN_DIRS, re-run **full `tsc --noEmit` + full vitest** (import graph crosses phases) + the V20 #1–8 single-payload vitest + e2e smoke.

**STEP 4 — PHASE 8 SOLO** on merged trunk. Destructive deletes behind grep-zero gates (`.dm-empty-state`, and the now-orphan `command-action-bar`/`command-policy-overlay` — migrate stragglers first). Reskin the 6 legibility primitives to tokens+Popover. Deferred `ActionButton→ActionBar` consolidation + delete legacy `ui.tsx` exports after grep-zero. Cross-cutting responsive + axe + reduced-motion QA. Final full gate.

## Residual risks (accepted)
- **P2 is the intrinsic bottleneck** (MatchWeek orchestrator + net-new untested SVG canvas + largest phase) — budget it as the longest; it defines the window length.
- Runtime club-color inline styles (P3/P7) may trip the token gate → decide per-phase at token-clean time (extend ALLOW_LINE or move to CSS custom props); integrator appends SCAN_DIRS only when the dir is actually clean.
- Exact mixed-`@media` block set is unverified at strategy time → STEP 3 must derive it programmatically.

## New scope this analysis surfaced (not in the Phase 0 plan)
1. `src/ui` shims for 5 orphan legacy primitives (STEP 1A). 2. `data-nav-rail` DOM contract + MatchWeek:334 rewrite. 3. Reclassifying `command-action-bar`/`command-policy-overlay` as shared (P8 deletion). 4. Per-phase `data-*` anti-strip vitests (the harness has zero screen tests today). 5. P4/P5 prop-stable skeletons + compile-time contracts landed pre-window.
