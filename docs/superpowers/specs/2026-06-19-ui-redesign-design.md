# Floodlight — Full Frontend Redesign & Rebuild

**Status:** Design direction **approved** (2026-06-19). Implementation plan **not yet approved** — to be produced via writing-plans and reviewed before execution. Execution begins with **Phase 0 only**; no screen rewrites until the audit ledger + primitive/test foundation are in place.
**Companion audit (checked into repo — the executable contract):** [2026-06-19-ui-redesign-audit.md](2026-06-19-ui-redesign-audit.md) — 73-screen inventory, 97-behavior non-regression ledger, 10 layout-bug patterns.
**Brainstorm mockups (local, gitignored — illustrative only, NOT a gating dependency):** `.superpowers/brainstorm/929-1781901505/content/`.

---

## 1. Goal

Replace the entire Dodger frontend with a single, coherent, production-grade design system — **Floodlight** — that fixes the *structural* causes of the "never looked polished" feel (text overflow, inconsistent spacing, off-screen content) and gives the game its own identity instead of a generic dark sports-dashboard look. Every one of the 73 screens is touched.

Repo-verified diagnosis: the frontend is built around a giant global `frontend/src/index.css` (8,744 lines / 260 KB) carrying **two competing token systems** (`--color-*` warm + `--dm-*` dark), 615 hardcoded hex colors bypassing tokens, pervasive inline styles, and no shared layout primitives. Tailwind is wired via `vite.config.ts` and imported in `index.css`. The new-game wizard makes raw `fetch()` calls outside `api/client.ts`. The "full design-system rebuild through primitives" approach is the correct fix.

---

## 2. Locked decisions (this brainstorm's ledger)

| Decision | Choice |
|---|---|
| **Scope** | Full ground-up rewrite of the **frontend** (not an incremental polish pass). |
| **Boundary** | Frontend is fair game; the **server boundary is preserve-first** — see §2.1. |
| **Guardrail (non-negotiable)** | The **simulation engine and faithfulness stay sacred.** The player must never be shown anything *less true* than today. No resurrected falsifying scores, no lost receipts. Current behavior + the Python suite are the safety net. We change how truth is *served and shown*, never *what is true*. |
| **Aesthetic** | **Floodlight** — evolved from moodboard A (live-sports), stripped of generic-AI-sports-UI clichés. Warm graphite canvas, single Volt accent, throw-arc motif, lit/extinguished states, traceability woven in (from C), legacy warmth quarantined to history (from B). |
| **Render approach** | Premium web-game *feel* via DOM/CSS for management screens; a lightweight animated **live match canvas** (SVG, see §11) for the match viewer. No heavy 3D engine. |
| **Viewport budget** | **Desktop-first** — see §9 matrix. Mobile: avoid catastrophic breakage only; not optimized unless reopened. |

### 2.1 Boundary contract (web layer) — REVISED
"Full rewrite" does **not** mean free rein on the server boundary. This is a UI/UX rebuild, not permission to churn the API.

- **Fair game:** frontend architecture, components, styles, layout primitives, presentation formatters.
- **Preserve-first:** API route paths and response shapes.
- **Additive-only:** backend payload changes must be additive unless a change is explicitly justified in the implementation plan.
- **Gated:** any schema/payload change requires, in the same change — Python guards updated, TypeScript types updated, and affected-consumer tests updated/added.

---

## 3. The Floodlight design language

### 3.1 Concept
Dodger is a **live court under stadium light**: a calm, warm-dark instrument stitched together by the **trajectory of a throw**. Everything *alive* is lit; everything *resolved* settles and dims. Any surfaced number can quietly reveal *why* (a receipt), without the UI becoming a data console.

### 3.2 Color tokens + the 5-color role contract
Single token source (`tokens.css`, CSS custom properties).

**Canvas & surfaces (warm graphite, not cool slate):**
- `--court: #121110` — base, rendered with a radial stadium-light gradient (`#211d16` top → `#0d0c0a` edges)
- `--raise: #1b1915` (surface 1) · `--raise2: #211e18` (surface 2)
- `--line: rgba(241,236,226,.08)` · `--line2: rgba(241,236,226,.15)`
- `--lit: rgba(255,251,242,.16)` — the "lit top edge" (light-from-above)

**Text:** `--text: #F1ECE1` · `--text2: #C3BBAD` · `--muted: #9A9285`

**The 5-color role contract (enforced system-wide; may not drift per-component):**
| Role | Token | Used ONLY for |
|---|---|---|
| **Coral / Volt** | `--volt #FF4A2B` / `--volt2 #FF6A48` | live, active, primary, currently selected. The only loud color. |
| **Mint** | `--ok #54B98E` | verified, positive, trust/up. Never selection, never live. |
| **Gold** | `--gold #F2B23C` / `--gold2 #FFD27A` | elite talent / ceiling, **intensity scales with grade** (§3.5). |
| **Dim / Extinguished** | `--out #8E8678` | resolved, out, injured, eliminated. De-emphasized **but readable**. |
| **Record Room** | dark surfaces (`--raise`/`--raise2`) + `--gold` honors + `--serif` headings | history/archive screens ONLY (§3.8). Recolored off the retired `--legacy-*` cream/ink paper 2026-06-21. |

Losses get **darkness, not red** — coral is reserved for live/primary.

### 3.3 Typography
Self-hosted (no FOUT/offline/no external dep). No Inter/Roboto/Oswald/Anton.
- `--disp: 'Archivo Expanded'` — hero numerals & scorelines
- `--head: 'Archivo'` — titles & section headers
- `--ui: 'Geist'` — body, UI, and **labels** (the everyday voice)
- `--mono: 'Geist Mono'` (tabular-nums) — **data/instrumentation only**
- `--serif: 'Fraunces'` — Record Room / history headings only

**Voice rule:** all-caps letterspaced = instrumentation only (labels titling a number, live readouts). Everyday labels = Geist sentence case. **Legibility floor ~0.7rem** for any meaning-bearing label (retire all 0.5–0.68rem load-bearing labels, audit Pattern 7).

### 3.4 Scales
Define and use only these tokens (no magic values): **spacing** step scale (2/4/6/8/12/16/20/24/32/40), **radius** sm/md/lg/xl, **elevation** surface-0→1→2 (each lighter + soft shadow + `--lit` top border), **type scale** display/h1/h2/body/label/data.

### 3.5 Signature motif + states
- **Throw-arc motif:** a thin Volt arc is the connective element — dividers ("throw line"), active indicators, transitions, and literally the trajectory in the match canvas.
- **Lit vs. extinguished:** live elements carry a lit edge that intensifies on hover/focus; resolved/eliminated data extinguishes — **color-dimmed (not opacity-crushed), holds ≥ ~0.85 readability, strike on names only, numbers stay legible.** Atmosphere never beats legibility.
- **Talent glow (gold, scaled by grade):** ceiling badge + host card glow proportional to grade — **A+ brightest** → A strong → A− lit outline → B+ faint → B/B− neutral → C dims. A **ceiling ladder** legend is the reference key.

### 3.6 Motion (subtle, tactile, restrained)
Panels lift on hover/press; exactly one ambient "breathing" pulse on **truly-live** elements only; tab/content transitions *settle* (staggered); match canvas animates throws. **`prefers-reduced-motion` honored.** CSS for micro-interactions (no dep); Motion library only if a staged-reveal need justifies it (§11, default: CSS-only).

### 3.7 Traceability woven in
Re-skin the existing legibility system (ProofChip/KnownValue/TermTip/receipts) into Floodlight: a quiet trace affordance reveals the backend's **verbatim** receipt in a portal popover with edge-flip. A hover, not a war-room grid. Mechanical-vs-flavor badges + receipt-verbatim rendering preserved exactly (audit §2.C).

### 3.8 Record Room mode (history / archive)
History/records/trophies/franchise/HoF get a **Record Room** framing on the standard dark Floodlight surfaces — Fraunces serif headings + **gold** honors accents (titles / banners / tiers), with volt reserved for active controls — a distinct archival feel that stays on the dark canvas. **Quarantined** to `history/*.module.css`. (Recolored off the original cream + ink + paper treatment on 2026-06-21 — owner call that the light "record book" read too out of place; the `--legacy-paper/ink/brick` tokens were retired.)

### 3.9 Content & formatting rules
- **"Week 9", not "Week 09"** — remove the `padStart(2,'0')` in `App.tsx`; **scheduled into Phase 1** (app shell), not a late sweep. No zero-padding on week/season counters.
- **Integer player-facing numbers** (carry V21 zero-floats); training-credit `.toFixed(1)` is the one deliberate receipt exception.
- Ruleset display names humanized; never leak impl keys.

---

## 4. Component & layout primitives (the anti-bug system)

A primitives library is the core deliverable — it makes the audit's bug classes structurally impossible. No screen re-implements these.

| Primitive | Kills | Behavior |
|---|---|---|
| `<Truncate>` / `.truncate` | P2 | `min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap`. |
| `<Grid>` (responsive) | P3, P10 | auto-collapse breakpoints; replaces every hard `repeat(N,…)`/fixed-px column. |
| `<ScrollRegion>` | P4 | owns height vs viewport; never nests fixed-height scrolls; no guessed `calc(100vh-…)`. |
| `<Card>`/`<Panel>`/`<Surface>` | P1 | token-driven elevation + lit edge. |
| `<Table>` + density | P1, P2 | tabular-nums; **Comfortable** (visual cards/stat-bars) + **Compact** (dense numbers); atomic non-wrapping records. |
| `<StatBar>` | — | glanceable rating; brightness = strength. |
| `<CeilingBadge>` | — | gold glow scaled by grade. |
| `<Tag>`/`<RecordCell>` | P2 | status pills; atomic tabular records (`7–2` never wraps; trend its own column). |
| `<Modal>` | P4, P8 | one Dialog: focus-trap, max-height + internal scroll, safe-area, `min(vw,rem)` width. |
| `<Popover>` | P5 | **portal-rendered, edge-flip/clamp** — fixes TermTip/ProofChip clipping/off-edge. |
| `<ActionBar>` | P5 | one sticky bar, safe-area aware, buttons stack. |
| SVG primitives (`<Court>`,`<MiniCourt>`,`<Sparkline>`) | P6 | fluid viewBox + player-count param; measured-fit text; honest NO-DATA fallback. |

**Migrate, don't duplicate (REVISED):** the repo already has shared helpers in `frontend/src/components/ui.tsx`. Phase 0 **audits `ui.tsx`**, decides what survives as Floodlight primitives, and **renames/replaces in place** rather than standing a new library beside it. **Old `dm-*` primitives and new Floodlight primitives must not coexist indefinitely** — each phase migrates its consumers off the old ones.

**Match viewer:** a dedicated lightweight live-court renderer (SVG, §11) driven by the replay payload — players as lit/extinguished tokens, throws as animated arcs. Enhancement over existing replay data; no 3D engine.

---

## 5. Architecture & stack

- **Keep** React 19 + Vite + TypeScript.
- **Styling = one token source + scoped component styles + primitives.** `tokens.css` is the only color/space/type authority; component styles in **CSS Modules** (retires the global monolith).
- **Token discipline rule (REVISED from "zero literal hex/px"):**
  - No visual **color** or **spacing** literals inside application components.
  - Colors, spacing, radii, typography, elevation, and semantic states come from tokens/primitives.
  - **Allowed exceptions:** SVG geometry, canvas coordinates, `0`, `1px` hairlines (only if tokenized or explicitly named), percentage/flex math, `viewBox` values, test fixtures.
  - **Gate:** a search/lint audit runs after Phase 0 (and thereafter) to catch new un-tokenized component styles.
- **Data layer:** every network call routes through `api/client.ts`; **fold the wizard's raw `fetch()`** (`starting-staff`, `starting-prospects`) into it so the launch-token guard (audit §2.J #91) covers them.
- **Centralized faithfulness formatting (cannot drift):** `formatScoreline()`/`survivorDetail()`/`rulesetNames.ts`/`formatters.ts`/`playerDisplay.ts` remain the **only** sources. No surface reads `home_survivors`/`home_game_points`/`season_id` directly. Reconcile the tier vocabularies into **one enum + one rank map**, preserving the deliberate de-collision (audit §2.G #57, §3 P9).
- **Truth hooks are a tested contract (REVISED — anti-strip guards):**
  - No rewrite removes a proof/test attribute (`data-testid`, `data-broadcast-proof-source`, `data-player-outcome`) unless the replacement test lands **in the same phase**.
  - New primitives **forward arbitrary `data-*`, `aria-*`, `role`, `id`** props.
  - `<Modal>`/`<Popover>`/`<Table>`/`<Card>` have tests proving those attributes survive.

---

## 6. Non-regression contract & verification harness

The audit's **§2 ledger (97 behaviors)** is the binding non-regression contract; every item stays green. It is **checked into the repo** ([audit doc](2026-06-19-ui-redesign-audit.md)) — not invisible companion material.

**The implementation plan must make it executable:**
- Each phase **lists which behaviors it covers** (by audit §2 number).
- Each behavior has a **test strategy:** existing Python guard · new Vitest+RTL · Playwright/e2e · or explicit manual-browser proof. No behavior is "covered by vibes."

**Test harness is a Phase 0 dependency change (REVISED — explicit):**
- Add **Vitest + React Testing Library** (Playwright + axe already present).
- Scripts: `npm run test`, `npm run build`, `npm run lint`; targeted Playwright/e2e where browser behavior matters; **Python suite stays green** where frontend payload contracts are touched.
- **Per-phase gate:** `test` + `build` + `lint` + relevant e2e + `python -m pytest` (where applicable) all green before advancing.

---

## 7. Scope & dead-code

**All 73 screens** (audit §1) rebuilt; none left on old CSS. Retire dead Vite boilerplate (`App.css`).

**Validate before deleting (REVISED):** the ~11 "likely-dead" components (audit §1 list) are **not deleted by vibes**:
- Run an import-graph/search for each candidate first.
- Delete in **small batches**, running `build` after each.
- If a component is reachable only via an obscure offseason/deep-state path, **preserve it until that path is rebuilt and browser-checked.**

---

## 8. Sequencing (REVISED — granular plan produced in writing-plans)

Incremental and **always-runnable**; each phase gated by §6.

- **Phase 0A — Contract capture:** confirm the audit is committed; build the per-phase preservation checklist (behaviors → phase → test strategy); identify exact files/components per phase.
- **Phase 0B — Foundations:** `tokens.css` + scales; primitives library (§4); **`components/ui.tsx` migration plan + execution**; `api/client` consolidation (wizard `fetch()` folded in); faithfulness-formatter + tier-vocab consolidation; **Vitest+RTL harness**; **Tailwind decision executed** (§11); token-discipline lint/search gate; dead-code validation pass.
- **Phase 1 — App shell + SaveMenu:** boot/loading, left nav, broadcast header, menu/new-game frame, **Week-number formatting fix**. No gameplay surfaces yet.
- **Phase 2 — Command loop + aftermath + replay (highest risk/value):** PreSimDashboard, MatchWeek, aftermath, MatchReplay + live match canvas. Preserve scoreline truth, replay proof hooks, match-receipt behavior.
- **Phase 3 — Roster + lineup + player detail** (Comfortable/Compact + gold glow).
- **Phase 4 — Standings + league context + bracket + pyramid.**
- **Phase 5 — Dynasty office + recruiting + history** (incl. Record Room legacy mode).
- **Phase 6 — Ceremonies / offseason beats.**
- **Phase 7 — New-game wizard** (4 steps).
- **Phase 8 — Sweep:** legibility primitives reskin, responsive QA at the viewport matrix, axe pass, reduced-motion, final dead-code removal, polish.

---

## 9. Acceptance criteria (definition of done)

- All 73 screens rebuilt in Floodlight; **zero screens on old CSS**; `index.css` monolith + dual token systems retired in favor of one token source.
- **Token discipline** (§5) holds; the lint/search gate is clean.
- All 97 preserve-behaviors green under the harness; Python suite green where payload contracts touched.
- **No horizontal overflow / off-screen content / clipped popovers** across the viewport matrix; long names truncate; numeric tables tabular.
- 5-color role contract enforced; "Week 9" formatting; integer player-facing numbers.
- `test` + `build` + `lint` clean; axe accessibility pass; `prefers-reduced-motion` honored.
- Dead components validated and removed.

**Acceptance viewport matrix (desktop-first):**
- **1440×900** — primary
- **1366×768** — stress
- **1280×720** — minimum desktop
- **1920×1080** — polish
- Mobile — no catastrophic breakage; not optimized unless Maurice reopens scope.

---

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Regressing the 97 trust behaviors | Harness-first per area; audit ledger is the checklist; Python suite green; anti-strip hook guards. |
| Server-boundary churn | §2.1 boundary contract: preserve-first routes/shapes, additive-only payloads, gated by tests. |
| Scope (73 screens) | Phased, always-runnable; primitives do the structural work so screens are thin. |
| Parallel primitive systems | Phase 0B migrates `ui.tsx` in place; no indefinite `dm-*`/Floodlight coexistence. |
| Deleting reachable code | §7 validate-before-delete (import graph + small batches + build + deep-path preservation). |
| Font perf | Self-host + subset; `font-display: swap`. |
| Match canvas complexity | Lightweight SVG over existing replay data; no 3D engine. |

---

## 11. Decisions resolved at lock (defaults chosen)

1. **Styling mechanism:** CSS Modules + `tokens.css` + primitives. *(Resolved.)*
2. **Tailwind v4:** **Remove** — in one controlled Phase 0B/1 pass: drop the `index.css` import, the `tailwindcss()` plugin in `vite.config.ts`, the package deps, and any class usage. *(If, mid-pass, removal proves larger than a phase, fall back to: freeze utility usage and require all new work to use Floodlight primitives/tokens — explicitly noted in the plan.)*
3. **Live match canvas:** SVG (scales with viewBox; consistent with the existing DarkCourt). Revisit Canvas 2D only if entity/animation volume demands it.
4. **Motion library:** CSS-only by default; add Motion only if a staged-reveal need justifies it (separate dependency decision in the plan).

---

## 12. References
- Audit & non-regression contract: [2026-06-19-ui-redesign-audit.md](2026-06-19-ui-redesign-audit.md)
- Brainstorm visual mockups (illustrative, gitignored): `.superpowers/brainstorm/929-1781901505/content/`
- Faithfulness-first principle: ADR 0002 (decision-traceability north star)
