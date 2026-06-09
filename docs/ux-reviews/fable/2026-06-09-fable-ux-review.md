# 2026-06-09 Fable UX Review — Full-App Visual Elevation Pass

> **Addendum (same day): Command Center deep redesign.** A second, focused pass on the
> pre-sim Command Center followed the app-wide sweep — see §8 at the end of this document.

Author: Claude (Fable 5), acting as lead product designer / senior frontend engineer / a11y reviewer.
Scope: app-wide desktop visual/UX refinement on top of the shipped Section 4 work. No engine math, no
routing/auth/build architecture, no new dependencies, no payload fields invented.

Tooling note: **Pare MCP was not available in this session** — orientation and verification used the
normal file/search/git tools and Playwright MCP, per the AGENTS.md fallback rule.

## 1. Outcome

The app is visually better, and the change is screenshot-verified end to end. The pass had three layers:

1. **A global "elevation layer"** appended at the end of `frontend/src/index.css` (clearly fenced with a
   header comment): court-floor atmosphere on the app shell, themed scrollbars/selection, a broadcast
   title slash on the page header, a real button interaction system (`.dm-action*` hover/active/focus),
   panel hairlines, table zebra striping, and panel-internal layout fixes.
2. **Surface redesigns** where drama or clarity was missing: the landing/save menu is now a title screen
   (court geometry, brand mark, club monograms per save row); the offseason reads as ONE ceremony
   (every beat now carries the `Offseason Beat n/N` header + progress pips); the champion beat got a
   gold broadcast stage; Hall of Fame inductees got enshrined plaques; retirements got farewell banner
   cards; the player detail modal became a two-column scouting card (no tab-flipping between bio and
   ratings).
3. **Visual bug fixes found by screenshot audit** (see §2 "fixes" group) — the biggest being the
   readiness-gate chips whose WT-4 detail copy overflowed 55px-wide cells into unreadable overlap.

One backend presentation-truth fix shipped with it: the retirements beat payload carried a float OVR
(`"ovr_final": 55.7`) which rendered player-facing; it now int-rounds exactly like the development beat
ten lines below it (same idiom, same file). This is the same float-leak family as the §4.1/retirements
prose fixes already on main.

## 2. Files changed, grouped by purpose

**Global design foundation**
- `frontend/src/index.css` — all additions fenced in the `ELEVATION LAYER — 2026-06-09` section at the
  end of the file (≈600 lines): shell atmosphere, scrollbars/selection, `.dm-action` button system,
  panel/table polish, gate-checklist redesign, landing styles, ceremony stage + champion/HoF/farewell
  treatments, credibility-meter lane fix, archive-timeline dot fix, standings numeric column width,
  app-boot state.
- `frontend/src/components/ui.tsx` — `ActionButton` now renders `.dm-action .dm-action-<variant>`
  classes instead of inline styles, so every button app-wide gains hover/active/disabled feedback.
  API unchanged (`style` still passes through).

**Fixes (visual bugs found in the before-state audit)**
- `frontend/src/index.css` (elevation layer) — readiness gates: 6 gates were squeezed into a 5-column
  grid of ~55px cells with full-sentence WT-4 details overflowing on top of each other; now a 2-up
  checklist where pending gates span the full row with readable detail copy. Also: the legacy
  `.command-readiness-chips span` boxing rule is neutralized inside the gate list.
- `frontend/src/index.css` — `.cc-panel-body` switched from a stretch-grid (which distributed leftover
  column height as voids *between* content rows — the big empty block in the Operational Plan panel)
  to a flex column with footers pinned to the bottom.
- `frontend/src/index.css` — Dynasty credibility meter: tier tick letters floated at -22px into the
  bracket-label line ("TIER A · MAX REACH" read as clipped); ticks now have their own lane.
- `frontend/src/index.css` — program-archive timeline: the node dot was absolutely positioned on top of
  the tick label (read as glitched glyphs); now stacked.
- `frontend/src/components/MatchReplay.tsx` — court player name labels were 9px gray-on-dark and faded
  to 0.22 opacity during throws (illegible); brighter team-tinted labels, 0.45 inactive opacity.
- `src/dodgeball_sim/offseason_presentation.py` — retirements `ovr_final` int-rounded (float leak,
  pinned by no test before or after; the existing dev-beat rounding idiom was reused).

**Landing / save menu**
- `frontend/src/components/SaveMenu.tsx` — `landing-shell`/`landing-brand`/`landing-card` classes,
  deterministic club monograms on save rows (presentation-only, derived from club name), hover rows,
  `dm-action` Load/Delete/Continue buttons. Save-row testids (`save-item`, `load-save-btn`,
  `delete-save-btn`, `continue-career-hero`) preserved.

**Weekly loop**
- `frontend/src/components/match-week/command-center/SeasonPreview.tsx` — week pills are now visible
  (cyan fills) instead of near-black bars; "None scheduled" bye note is calm slate instead of warning
  amber (amber only when a bye exists); CTA uses the primary button system; the section is capped at
  64rem and centered (at 1920 it was a wall-to-wall banner with a ~1700px button).

**Ceremonies**
- `frontend/src/components/ceremonies/CeremonyShell.tsx` — optional `beatIndex`/`totalBeats` props
  render the same `Offseason Beat n/N` eyebrow + progress pips as the structured beats; new
  `dm-ceremony-stage` backdrop.
- `frontend/src/components/ceremonies/Ceremonies.tsx` — all CeremonyShell call sites pass beat
  position; retirements use the new farewell cards (int OVR display); MVP name in display font;
  reveal columns widened (520→640px).
- `frontend/src/components/ceremonies/ChampionReveal.tsx` — gold `champion-stage` hero + unified header.
- `frontend/src/components/ceremonies/StructuredOffseasonBeats.tsx` — HoF inductees render as
  `hof-plaque` cards (gold gradient name, ENSHRINED badge, career chips). Legacy score copy is now
  "Legacy X · clears the Y induction bar" — both numbers are payload-backed and deliberately fractional.
- `frontend/src/components/ceremonies/DevelopmentResults.tsx`, `RecapStandings.tsx`,
  `RookieClassPreview.tsx` — custom headers replaced with the unified PageHeader + beat pips.

**Dynasty / roster / modal**
- `frontend/src/components/DynastyOffice.tsx` + `dynasty/ProspectCard.tsx` — the fit-tier color legend
  and the "Scout to narrow…" explainer were repeated on EVERY prospect card; they now appear once at
  board level. The per-card `KnownValue` "Scout to narrow" hint stays.
- `frontend/src/components/PlayerDetailModal.tsx` — two-column scouting card (bio/potential/growth left,
  full rating sheet right), 46rem wide; tabs and the placeholder "More" tab removed; the
  TermTip-wrapped rating rows (which collapsed to content width, rendering "THROW SELECTION IQ79")
  now use RatingBar's native accessible `explanation` tooltip.
- `frontend/src/components/Roster.tsx` — removed the duplicated "Roster Lab" kicker (the broadcast
  header 40px above already says it).
- `frontend/src/components/App.tsx` — branded app-boot loading state (role="status", reduced-motion
  safe) instead of bare "Loading...".

**Tests**
- `tests/e2e/v15-recruit-board.spec.ts` — two assertions updated to match the legend/explainer moving
  from per-card to board level (the legibility information is still asserted visible, once).

## 3. Pages/panels verified in browser (live, vite dev + prod-server smoke)

Landing/save list, New Game tab, pre-sim dashboard (fresh week, scouted state, locked state, playoff
semifinal week), Season Preview, readiness gates (pending + ready), policy editor, lineup editor,
scout reveal, simulate → match aftermath (win + loss variants across the session), match replay
(court, possession timeline, event log), Roster (detailed view), player detail modal, Dynasty Office
Recruit (credibility strip, action slots, recruit board), History (glance + archive timeline), Staff
tab, Standings (regular season + live playoff bracket + race concluded state), and the full offseason
ceremony sequence twice (recap, champion, awards, records ratified, development, retirements, rookie
class preview, signing day incl. lock-class confirm, class report, schedule reveal). Deep states were
reached via real flows plus the existing `POST /api/command-center/fast-forward`
(`pre_playoffs` / `offseason`) endpoint on the scratch save `Caveman Dynasty` (seasons 11–12 were
played/fast-forwarded during this pass).

Not browser-reached this pass (honest): bye-week aftermath (no bye in this save's schedules), the
HoF beat with the NEW plaque styling (season 11 had no inductees — the plaque is build-verified and
CSS-only over the same DOM contract), the in-season RecruitmentChoice panel variant of Signing Day
(`can_recruit` path was exercised; the card-grid `My/Rival/Surprise` class-report tab mode was not,
same caveat as the prior verification pass), and the Build-from-Scratch 3-step flow (its buttons share
`ActionButton`, build/lint verified only).

## 4. Desktop viewport results

- **1440×900 (primary)** — primary composed experience; all core screens captured and reviewed.
- **1280×720 (minimum)** — `document.scrollWidth == clientWidth` (no horizontal overflow) checked on
  command center (preview + pre-sim), roster, dynasty, standings; screenshots reviewed.
- **1920×1080** — pre-sim composes via the 1440 max-content cap; the one sparse/stretched offender
  found (Season Preview) was capped at 64rem and re-verified.
- **1366×768** — verified directly at the end of the pass: no horizontal overflow
  (`scrollWidth == clientWidth`) and the pre-sim three-column layout holds; screenshot reviewed.

## 5. Tests/checks run — exact status

- `npm run build` (frontend): **pass** (run after every batch; final run green).
- `npm run lint` (frontend): **pass** (no output).
- `python -m pytest -q` (full suite): **pass — exit 0, twice** (once during, once after the backend
  change). The summary count line was swallowed by output capture; both runs show all-dot progress and
  exit code 0. Targeted `-k "offseason or retirement or ceremony"` also green (87 tests).
- Playwright/browser verification: live walks as listed in §3, on the vite dev server (port 5173,
  launch token fetched at runtime) plus a prod-server smoke (port 8000, built dist with injected
  token) confirming the shipped bundle renders the new UI. Browser console: **0 errors** at final
  check. The root `npm run e2e` suite was **not** run this pass (it requires its own server
  orchestration); the one spec I edited (`v15-recruit-board.spec.ts`) was updated to match the
  deduplicated legend and should be exercised on the next e2e run.

## 6. Unresolved issues / caveats

- **Transient dev-only incident:** an HMR update mid-edit (import landed one save after its usage)
  crashed the vite dev process once; restarted, no residue. The committed code builds clean.
- `tests/e2e/v15-recruit-board.spec.ts` changes are reasoned but not executed (see §5).
- The possession-timeline grid in the replay is information-dense but was left as-is — it doubles as
  the scrubber and is functional; a redesign would be a behavior change.
- The HoF plaque and bye-aftermath render paths are code/build-verified but were not visible in this
  save's beats (see §3).

## 7. Owner-decision taste calls (not bugs)

- **Save-row club monograms** use a deterministic palette hash of the club name, not real club colors
  (the save-list payload has no colors field). If club colors land in `SaveInfo`, swap the hash for
  the real identity.
- **Champion stage gold-gradient name** is intentionally the loudest element in the app; if it should
  also scale by "your club won vs. someone else won", that's a copy/emphasis decision for the owner.
- **HoF legacy line** keeps the deliberately fractional score ("Legacy 120.8 · clears the 120.0
  induction bar"); rounding it would hide the mechanical readout.
- The duplicated **broadcast-header/page-header kicker** pattern was removed on Roster only; Dynasty
  Office and Standings have lighter duplication that read acceptably — unify further if desired.
- `prefers-reduced-motion` is respected by the new boot pulse and the existing ceremony skip logic;
  no new animation plays on data-bearing surfaces.

---

## 8. Addendum — Command Center deep redesign (second pass, same day)

The pre-sim Command Center got a teardown on top of the sweep. The page's job is
"read the matchup, set the plan, lock it" — the redesign makes every fact appear exactly once and
stages the page in three acts. All work in `PreSimDashboard.tsx` + the elevation-layer CSS
(section 15); no payload, routing, or behavior changes; every e2e contract was audited first
(`presim-command-strip` Record/Form text, `matchup-band` + `data-standing`, `plan-readout`,
`staff-impact`/`staff-impact-row` + `data-department`, gate chip `title`, `.command-threat-row`
count, `lock-weekly-plan`/`simulate-command-week`, fast-forward testids — all preserved).

**Deduplication ledger** (the core of the change — each fact's single home):

| Fact | Was shown | Now shown |
| --- | --- | --- |
| Opp record / last meeting | Hero stats AND Opponent File grid | Hero stats only |
| Matchup band | 4th hero stat cell | Badge beside the headline, toned by standing |
| Staff recommendation reason | Plan callout, Opponent File head, Risk Notes, bottom scouting-note callout | Counter Read only |
| Threat-vs-your-best OVR compare | Opponent File head AND scouting-note callout | Opponent File head only |
| Intent | Identity strip, plan h2, intent select, "Decision" readout row | Plan h2 + intent select |
| Lock status | Identity strip "Status" AND rail header | Rail header only |
| Readiness count | Rail header, gate list, "Readiness" row, hint sentence | Header + readout row + dock meta (each a different altitude) |

**Structural moves:** Match-Day Staff relocated from the Opponent File to the Plan desk (it's the
player's own operation) as a compact `cc-staff-strip`; the "Risk Notes" cell and the bottom
scouting-note callout were deleted outright; the lock readout slimmed from five rows to three
(Risk / Readiness / Next Issue); the identity strip slimmed from six cells to four and now
declares `· Bye Week` / playoff round in the Week cell (which also makes the naive-playtest
runner's strip-text bye check actually work).

**The launch dock:** the lock/simulate action now sits in a framed stage (`.cc-launch`) with
broadcast corner ticks and an orange glow that arms when all gates go green and goes live once
locked — the champion-stage level of emphasis, pointed at the page's one true action.

**Copy retcon:** action hints cut to a line ("All gates green. Lock it in." / "Plan locked. Run the
match when ready." / "N items left before lock."); the court-card caption "Schematic — live
positions" was corrected to "Projected sixes" (the diagram is a projection, not live data); the
false "⌘ ⏎ to confirm" footer hint was removed (no such handler exists anywhere in the app —
verified by grep); the dock meta now states something true instead: "N of M gates green ·
Auto-saved".

**Verification:** build + lint green; browser-verified at 1440×900 and 1280×720 (no horizontal
overflow, console clean) across blocked → armed → locked states. The armed/locked states were
exercised on a throwaway `e2e-cc-redesign-check` save created and deleted via the API, because the
owner's active career ("Twenty Season Truth Run") changed hands mid-session and was deliberately
left untouched; it was restored as the active save afterwards. Honest caveats: the bye-week hero
variant of the redesigned layout and the playoff-strip variant were not browser-rendered this pass
(code paths reviewed; the bye hides the band/stats row by construction), and the root e2e suite
was again not executed — the contracts above were verified by reading every spec that touches
this surface.

### 8.1 Owner-feedback round (five priorities, same day)

The owner reviewed the redesign and set five priorities; all five are implemented:

1. **Dead vertical space killed.** `.cc-body` is now `align-items: start` — the plan and intel
   desks are content-height instead of stretching (with internal voids) to match the tall
   decision rail.
2. **Current objective banner.** A new `cc-objective` strip (testid `current-objective`,
   `role="status"`) sits under the identity strip: amber **"N actions left before lock"** with
   the pending gates as direct action buttons (testids `objective-scout` /
   `objective-confirm_lineup` — distinct from the canonical gate-button testids to keep
   Playwright strict-mode single matches); it flips to emerald **"Ready to lock"** when gates
   clear and orange **"Plan locked — simulate the week when ready"** after lock. Verified live:
   clicking the banner's Scout cleared the gate and the banner transitioned through all three
   states.
3. **Sim Lock rebalanced.** Each pending gate row now carries its own resolving action button
   (`Scout now ▸` / `Confirm six ▸` — these carry the canonical `scout-opponent` /
   `confirm-lineup` testids, the old standalone button row is gone), and the **disabled Lock
   button renders as a quiet slate outline** — the orange slab (and its sweep animation) is
   reserved for the moment it can actually be pressed. Blockers now visually dominate the
   unavailable action.
4. **Opponent duplication finished.** The Opponent File's h2 no longer repeats the opponent name
   the hero just announced in 3rem type — the desk is titled **"Scouting Report"** (kicker stays
   "Opponent File").
5. **Fog-of-war made intentional.** "Unscouted" cells render as a dashed, diagonal-striped cyan
   `cc-fog` chip with a "Locked intel — scout the opponent to reveal observed tendencies" tooltip
   instead of italic gray that read as missing data; the cold-start block got the same locked-layer
   framing and its label was retconned from "Opponent File (no tape yet)" to
   **"Pre-tape intel — what the league already knows."**

Verification for this round: build + lint green; browser-verified at 1440×900 and 1280×720 (no
overflow, console clean); the pending → ready → locked banner/dock cycle exercised on a throwaway
`e2e-cc-feedback-check` save (deleted afterwards; the owner's save restored as active). The
Python `test_scout_reveal` / `test_tactical_diff` suites pin the cold-start payload, not the
frontend label, so the copy retcon is test-safe; the root e2e suite remains unexecuted this pass.

### 8.2 Owner fix-list round 2 (five items, same day)

1. **Lower dead space collapsed (must-fix).** The League Wire moved inside the `.cc-body` grid:
   it fills the second row under the plan/intel desks while the decision rail spans both rows
   (`.cc-body > .cc-lock { grid-row: span 2 }`, wire `grid-column: 1 / 3`; both reset below
   1180px). Measured live: the page bottom now tracks the tallest *content* column, not the
   sidebar — with a fully-scouted intel desk the wire sat 17px under it and the page ended 24px
   later.
2. **"Ready to Decide" → "Ready to Lock?"** in the Sim Lock panel header.
3. **Directive subtitle.** The banner now carries a second line composed from the actual pending
   gates — e.g. "Scout their projected six and confirm the six you will field before you sim." —
   via a `gatePhrase` map with the gate's own `short_label` as the fallback for any future gate.
4. **Tactical Diff payoff made explicit.** A new intel meter chip in the diff header
   (`tactical-diff-intel-meter`) shows the locked layer's fill state — dashed/striped cyan at
   "0/5 reads revealed", solid cyan when partial, emerald at full reveal — with a tooltip
   explaining that scouting reveals tendencies row by row.
5. **Banner reads as a command directive.** A mono `W0N · Directive` tag chip, broadcast corner
   ticks, and a scanline wash replace the generic alert-bar look; state colors (amber order /
   emerald ready / orange locked) carry through the tag and ticks.

Verification: build + lint green; browser console clean; banner + layout verified live at
1440×900 on the owner's active save **read-only** (the owner had scouted/confirmed it themselves
mid-session, which conveniently exercised the partial/revealed intel-meter states); geometry
asserted via `getBoundingClientRect` rather than mutating the save. Root e2e suite still not
executed; no testid contracts changed in this round (one testid added: `tactical-diff-intel-meter`).

### 8.3 Owner fix-list round 3 (same day)

1. **Uniform desk heights.** The Opponent File was the long column; its depth intel (the pre-tape
   cold-start block and the Observed/Prior intel notes) folded into a **Full Scouting File**
   dialog (trigger `open-scouting-file`, shared Dialog primitive, same overlay pattern as the
   Policy Editor), and the per-row tape provenance ("Tape · strong 90% · n=59" block lines)
   compressed to an inline "90% · n59" suffix with the full sentence in the tooltip. Measured:
   the intel desk dropped from 1035px to 779px tall — now within ~90–170px of its neighbors
   instead of ~350px longer. Constraint honored: the Broadcast Frame stays in-card because
   `v13_broadcast_layer.spec.ts` requires it visible on pre-sim. The cold-start/intel testids
   moved into the dialog (no e2e spec references them; Python suites pin the payload).
2. **League Wire → broadcast ticker.** The wire is now a CNN-style ticker: an orange "live" bug
   with a pulsing pip, items scrolling on a 38s loop (`W3 — Won 2–1 vs Lunar Syndicate ◆ League
   leader: …`), edge-fade mask, pause on hover, static under `prefers-reduced-motion` — and it
   only runs **when there is actual news**; a quiet league gets one honest static line ("Quiet
   week on the wire — no league results logged yet"), keeping the `secondary-intel-rail`
   visibility contract.
3. **Color language disambiguated.** Emerald was leaking onto things that were merely *set*, so a
   high-risk plan still glowed green. Now: **emerald = verified good** (gates cleared, profile
   aligned, intel fully revealed), **cyan = informational/set** (the four policy cells' "ready"
   state changed from emerald to cyan), **amber = needs attention**, **rose = risk/threat**,
   **orange = the primary action**. An Aggressive plan now shows cyan cells + rose "High" risk —
   verified live on the owner's own Aggressive plan.
4. **Redundant "Edit Game Plan" button removed.** The tactics cells themselves are now real
   `<button>`s (keyboard-accessible, with aria-labels; the static Training/Development cells lost
   their misleading ▸ affordance). The `open-policy-editor` testid moved to the Tactical Approach
   cell so the wt21/wt22/tier1 specs keep their entry point; the panel foot now reads
   "Click a tactics cell to edit".

Verification: build + lint green, console clean, verified read-only on the owner's live save at
1440×900 (uniform heights asserted by bounding-rect: plan 1298 / lock 1380 / intel 1468 page-px
bottoms; page height 1557 vs 1813 before). The Full Scouting File dialog opened/closed via
Escape. Honest caveats: the scrolling ticker state was not visually exercised (the owner's
season has no logged results yet — the static no-news line rendered; the marquee is CSS-only),
and the root e2e suite remains unexecuted across all rounds.

### 8.4 Owner fix-list round 4 (same day)

1. **League Wire moved to the top of the page** — it now opens the Command Center like a network
   rundown bar (slimmer chrome padding), above the identity strip. The round-2 in-grid placement
   and its `grid-row: span 2` machinery were removed.
2. **Quiet-week clip fixed** — the ticker's edge-fade mask was eating the first characters of the
   static line; the mask now applies only while news is actually scrolling (`.has-news`).
3. **Crisp uniform bottoms** — with the desks rebalanced, `.cc-body` returned to stretch
   alignment and every desk pins its foot (plan foot / new `.cc-intel-foot` Full File trigger /
   launch dock). The Tactical Diff rows also tightened (0.3rem→0.24rem padding). Asserted by
   bounding-rect: **all three desks bottom at exactly 1564px**, page ends 24px later.
4. **Broadcast Frame interrogated and relocated.** Answer to "what is it for": it is the V13
   proof-backed narrative layer — stakes/rivalry/archetype tags plus the historical hook, each
   carrying a `data-broadcast-proof-source` and a View-evidence toggle. That is *matchup framing*,
   not scouting intel — so it moved onto the hero's left column under the This Week/Watch lines,
   where the billboard lives. This also keeps the `v13_broadcast_layer.spec.ts` contract
   ("Broadcast Frame" text + proof toggle visible on pre-sim) with zero spec edits.

Remaining same-scrutiny candidates left as owner taste calls: the Court Read schematic (kept —
it orients the key-threat flag spatially), the deterministic season title ("The Hungry Year" —
flavor, one line), and the hero Watch line (your own player's storyline; kept as the one flavor
line on the billboard).


### 8.5 Pre-merge verification round (commit gate)

Run before folding into main, at the owner's request:

- **Full `python -m pytest -q`: green** (twice during the session, plus once after the server fix).
- **`npm run build` / `npm run lint`: green.**
- **Targeted Playwright e2e: 45/45 passed** - 13 specs covering every touched contract
  (command-center hero/strip/panels/gates/lock flow, WT-21 dialogs, WT-22 decision proof,
  V13 broadcast layer, V14 tactical diff + staff impact, V15 recruit board/legibility/no-overflow,
  playoff record label, aftermath flow, tier-1 recognition, official-rules replay, replay score
  parity) on chromium against a fresh prod server.
- **Closed in the process - the documented "tokenless e2e sweep" open item:** the first run failed
  37/45 because every older spec's `request.post` setup ran tokenless against the real WT-12
  guard. All 23 affected specs now attach the token via `_token.ts`.
- **Found and fixed a real presentation-truth bug the re-enabled suite exposed:**
  `server.MatchReplayResponse` didn't declare `scoring_model` / game-point fields, so FastAPI
  stripped them from the response and every official replay rendered as a legacy survivor
  scoreline (it could directly contradict the aftermath hero - verified live: aftermath "1-0
  game points" vs replay "+2 SURVIVORS"). Both remaining e2e failures were first confirmed to
  reproduce identically on a clean-main baseline (stash -> rebuild -> run -> restore) before
  being treated as pre-existing. Fix in `server.py`; serialization-layer regression test added;
  two stale specs retconned to current truthful behavior (WT-2 game-point heroes, the
  "Bank the Result"/"Next Week" action labels) and the parity spec de-flaked (it raced the
  hero's 1.5s count-up animation).