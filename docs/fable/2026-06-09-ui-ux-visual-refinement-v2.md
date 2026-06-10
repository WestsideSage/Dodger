# UI/UX Visual Refinement Pass v2 — 2026-06-09

Role: lead product designer / senior frontend engineer / UX researcher / a11y
reviewer / visual QA / cross-disciplinary synthesis lead. This is the
**report-informed** follow-up to the full-app elevation pass
(`2026-06-09-fable-ux-review.md`): every change below traces to a finding in
one of the five cross-disciplinary reports, or to a presentation-truth bug
found during the live browser audit. All work in the main repo working tree,
on top of the five (uncommitted) 2026-06-09 passes already there.

Tooling note: Pare MCP was largely bypassed — this pass needed the Claude
Preview MCP browser loop, raw pytest/playwright/vite output, and direct
file-tool reads, so normal shell/file tools were used (fallback disclosed per
`AGENTS.md`).

---

## 1. Outcome

**Eight targeted improvements implemented and browser-verified; the app is
experientially better in exactly the places the five reports said it was
weakest.** Every open *UI-owned* item from the five reports is now closed:
the week-1 scout contradiction, the Signing Day scouted-vs-verified ambiguity,
the Class Brief blob, the records-cadence noise, the rec rush-target dead
knob, and the unexplained official draw. The browser audit additionally found
and fixed two real presentation problems the reports had not reached: the
Dynasty History "All-Time Record" cell rendered a single-season snapshot under
an across-all-seasons label (false copy, now a true career total computed from
the same persisted rows), and playoff-length official matches (12–15 games)
ballooned the aftermath hero to ~450px by stacking set chips single-file in
the 4.5rem center column (now a horizontal full-width timeline band; hero is
184px).

Nothing in this pass changes match outcomes, engine math, seeded randomness,
signing math, or standings logic. The two backend changes are presentation
data threading (records previous-holder truth; history career totals), both
derived from already-persisted facts and pinned by new tests.

## 2. Reports synthesized (all five located)

All five inputs were found in `docs/fable/` (untracked, working tree):

| Report | File |
|---|---|
| Game Systems / Balance | `2026-06-09-systems-balance-audit.md` |
| Watchability / Broadcast | `2026-06-09-watchability-broadcast-pass.md` |
| Dynasty / Retention | `2026-06-09-dynasty-progression-retention-review.md` |
| Adversarial QA / Trust | `2026-06-09-adversarial-qa-trust-audit.md` |
| First-Hour Onboarding | `2026-06-09-first-hour-onboarding-review.md` |

Plus prior art: `2026-06-09-fable-ux-review.md` (the v1 elevation pass — used
to avoid re-doing shipped work). **No report was missing.** Key synthesis
fact: the five passes' code fixes are already in the working tree, so the
actionable surface for v2 was each report's *open items* section, filtered to
what is UI-owned.

## 3. Report findings addressed, by source report

**First-Hour Onboarding (§7 open items):**
- §7.2 *Scouted estimate vs signed truth unexplained* → one-line disclosure on
  Signing Day ("Ratings below are each prospect's verified overall. In-season
  scouting reads are estimates…"), `data-testid="signing-day-ovr-disclosure"`.
- §7.3 *"New intel revealed" badge beside "0/5 reads revealed"* → badge is now
  state-aware: emerald "New intel revealed" only when ≥1 tendency read exists;
  a quiet slate "Scouted · no tape yet" (with explanatory tooltip) when the
  scout action revealed only pre-tape facts. Verified live on a fresh week-1
  career.
- §7.6 *Class Brief run-on blob* → new `BriefProse` renderer keeps the
  backend's line structure: section labels ("Current roster sizes"), indented
  club rows, label·value fact rows. Verified live on a real Class Report.
- §7.5 *loss aftermath never browser-seen* → closed as a verification gap:
  two loss aftermaths reached live this pass (a 7–8 playoff loss and an 8–2
  road loss), honest Primary Factor / Manager Lesson copy confirmed rendering.

**Dynasty / Retention (§7.5):**
- *Records cadence is noise (same leaders re-break own counters ~2.5×/season)*
  → milestone-vs-bookkeeping presentation. `RatifiedRecord` now carries
  `is_new_holder` + `previous_holder_name` (compared against the persisted
  previous holder at ratify time). The ceremony renders holder *changes* and
  first-time records as the existing marquee cards (plus a "New Holder" chip
  and "takes the record from X" line on dethronings), while same-holder
  re-breaks compress into quiet "Extended their own records" ledger rows.
  Verified live across two ratifications: season 1 = 3 marquee first-time
  records, zero extensions; season 2 = 3 extension rows, zero marquee — the
  exact noise case the report measured. Backward compatible: cached payloads
  ratified before the fields existed default to marquee (pinned by test).

**Systems / Balance (§6, §7.5):**
- §7.5 *rush_target outcome-dead on rec but disclosed only on officials* →
  verified the deadness in source first (`rec_engine._opening_rush` ball
  targets flow only into throw-event context at `rec_engine.py:859`; the
  resolution path consumes only `sprinter_ids`, which Commit controls). The
  Policy Editor's Target row now carries a quiet advisory on rec careers
  ("Recorded as your announced assignment in the match log… Target does not
  change match outcomes yet."), `data-testid="rush-target-advisory-note"`.
  Verified live on both rulesets: official career shows the amber
  announced-only panel note (and not the rec note); rec career shows the rec
  note (and not the official note).
- §6 *even-strength official draws honest but unexplained in-product* → the
  aftermath hero now declares draws: a "◆ Draw" badge in the center column
  plus a full-width footer line — "Level on game points at full time. A drawn
  match awards one standings point to each club." (copy verified against
  `season.py:124`, wins×3 + draws×1; legacy variant says "Level at full
  time…"). Verified live on two real official draws (1-1 and 6-6).

**Adversarial QA / Trust:** no open UI-owned items (its fixes were already in
the tree; its remaining items — promises lane, department orders, WT-20 — are
deliberately NOT solved with UI, see §5). This pass's two found-bugs (history
record label, below) are the same presentation-truth family that report
hunts.

**Watchability / Broadcast:** no open UI-owned items; its §7 gaps are engine
or migration scoped. The set-story strip it added to the hero is the surface
this pass restructured for playoff-length matches (below) — outcome data
untouched.

## 4. Found-and-fixed during the live audit (not in any report)

1. **Dynasty History "All-Time Record" was the latest season's snapshot.**
   `MyProgramView` rendered `hero.current` (latest `season_standings` row)
   under the label "All-Time Record / Across completed seasons" — a week-2
   career showed "1-0-0" as its all-time record. The endpoint now also emits
   `hero.all_time` (wins/losses/draws/seasons summed over every season row,
   including the in-progress one) and the cell renders that with an honest
   "Across N seasons (incl. current)" trend; if a payload lacks the field the
   cell relabels itself "Latest Season Record" instead of lying. Pinned by
   `test_history_server.py::test_history_my_program_all_time_record_sums_every_season`.
   Verified live: 4-season career reads "11-1-4 · Across 4 seasons".
2. **Playoff-length matches ballooned the aftermath hero.** The set-story
   chips lived inside the 4.5rem-wide hero center column; a 15-game playoff
   match stacked them single-file and stretched the hero to ~450px of mostly
   empty panel. The strip is now a full-width horizontal timeline band under
   the scoreline (`grid-column: 1 / -1`), and the draw footer joins it as a
   second full-width row. Hero height for a 14-game match: 184px. Verified at
   1280/1440/1920 with zero horizontal overflow.

## 5. UI-owned vs deferred (the action matrix outcome)

**Fixed here (direct UI / honest-payload-threading):** the eight items in
§3–§4.

**Deliberately NOT solved with UI (systems/product scope — for the Product
Director pass):**
- WT-20 official live-rules enforcement (rush disclosure is the interim truth).
- The official catch-economy inversion (accuracy/dodge negative EV) — the UI
  must not encode current balance numbers in copy while the retune is pending.
- Contested Signing Day / AI recruiting access (the static-league decision) —
  the disclosure line added here states the *current* truth without
  pretending contestedness exists.
- Promises lane (no UI was built — surfacing a consumer-less system would be
  fake UI; revive-or-remove is STATUS Open Work #5).
- Department orders wire-or-drop (STATUS #6; honest flavor labels stand).
- True-OVR reveal at Signing Day (owner decision §7.2 of dynasty report;
  this pass added the disclosure, not the fog-of-war redesign).
- Official replay strip live-per-event sync (V16A intent-frames scope).

## 6. Files changed, grouped by purpose

**Report-driven frontend fixes**
- `frontend/src/components/ceremonies/RecruitmentChoice.tsx` — Signing Day
  scouted-vs-verified disclosure line.
- `frontend/src/components/match-week/command-center/PreSimDashboard.tsx` —
  state-aware scout badge ("Scouted · no tape yet" at 0 reads).
- `frontend/src/components/match-week/command-center/PolicyEditor.tsx` — rec
  rush_target advisory note (scoped to `!rushAnnouncedOnly`, target row only).
- `frontend/src/components/ceremonies/Ceremonies.tsx` — `BriefProse`
  structured renderer; Class Brief uses it.
- `frontend/src/components/ceremonies/StructuredOffseasonBeats.tsx` — records
  beat split into milestone cards (+ "New Holder" chip, dethroned-name line)
  and compact extension rows; every entry keeps
  `data-broadcast-proof-source` (v13 e2e contract preserved).
- `frontend/src/components/match-week/aftermath/MatchScoreHero.tsx` — "◆ Draw"
  badge + full-width draw footer; set-story strip moved to a full-width band.
- `frontend/src/components/dynasty/history/MyProgramView.tsx` — true
  all-time record cell with honest fallback label.
- `frontend/src/types.ts` — `RatifiedRecordEntry.is_new_holder` /
  `previous_holder_name`.
- `frontend/src/index.css` — `.command-score-sets` restyled as a full-width
  timeline band (comment documents why).

**Backend presentation-data threading (no outcome paths)**
- `src/dodgeball_sim/offseason_beats.py` — `RatifiedRecord.is_new_holder` /
  `previous_holder_name`, computed against persisted previous holders in
  `ratify_records`; serialization round-trip with marquee-defaulting
  back-compat.
- `src/dodgeball_sim/offseason_presentation.py` — `_parse_record_entries`
  passes the two fields through.
- `src/dodgeball_sim/server.py` — `/api/history/my-program` emits
  `hero.all_time` (summed from the same `season_standings` rows the endpoint
  already reads; endpoint has no response_model, so no field-strip risk).

**Tests**
- `tests/test_offseason_beats.py` — 4 new tests: first-time → new holder;
  same-holder re-break → not new holder (+ previous name); dethroning → new
  holder + previous name; cached pre-field payloads default to marquee.
- `tests/test_history_server.py` — 1 new test: all_time sums every season,
  current snapshot keeps its meaning.

## 7. Pages/panels verified in browser (live prod server, fresh build)

Title screen/save menu, New Game tab (ruleset card + path cards),
Build-from-Scratch Step 1, Season Preview, Command Center week 1 (pre-scout,
post-scout badge states, objective banner), Policy Editor (official AND rec
careers), full weekly loop ×9 weeks across seasons 1–4 (scout → confirm →
lock → simulate → aftermath → bank), aftermath in four result shapes (1-0 win,
1-1 draw, 6-6 twelve-game draw, 7-8 playoff loss, 8-2 road loss, 8-6
fourteen-game win), Records Ratified beat in both cadence states (season-1
first-time marquee; season-2 all-extensions) with My Club/League scope
toggle, Signing Day (disclosure, sign, lock-class-early confirm), Class
Report (structured Class Brief), Schedule Reveal, season rollover ×3, Roster
+ Manual Lineup Editor (incl. its honest no-bench empty state), Standings
(season 4, playoff race strip), Dynasty Office Recruit / History (My Program
glance + League view with live rivalry board) / Staff tabs.

Deep states were reached via real UI flows plus the existing
`POST /api/command-center/fast-forward`; all probe saves (`fable-v2-audit`,
`fable-v2-audit-rec`) were created via API, used, and **deleted**; the
previously-active save (`Fresh Player Run 2`) was restored as active. The
owner's "Twenty Season Truth Run" save was never touched.

**Honest gaps:** the bye-week aftermath was not reached (needs an odd-club
build-from-scratch career; unchanged by this pass — last verified in the §4
pass). The dethroning record card ("New Holder" chip + "takes the record
from X") did not occur naturally in the audited seasons; it is pinned by unit
test but was not browser-rendered. The match replay screen itself was not
deep-walked (nothing in it changed); its e2e specs ran green below.

## 8. Desktop viewport results

- **1440×900 (primary):** all fix surfaces composed and screenshot-reviewed;
  no horizontal overflow (`scrollWidth == clientWidth` checked).
- **1280×720 (minimum):** full weekly loop + loss aftermath + records beat
  walked; zero horizontal overflow; hero/strip geometry measured (184px/44px).
- **1920×1080:** aftermath verified (content cap holds at 1280px; no sparse
  drift); no overflow.
- **1366×768:** not separately re-walked this pass (no layout-primitives were
  changed; the v1 pass verified it and the only geometry change — the hero
  strip — was verified at the tighter 1280 floor). Stated honestly rather
  than claimed.

## 9. Tests/checks run — exact status

| Check | Result |
|---|---|
| `python -m pytest -q` (full suite, after all changes) | **PASS** — exit 0, 100%, all-dot (≈1,325 tests incl. 5 new) |
| Focused: `test_offseason_beats.py` + `test_records.py` + `test_offseason_ceremony.py` + `test_dispersed_helpers.py` | **PASS** (118) |
| Focused: `test_history_server.py` | **PASS** (2) |
| `npm run build` (frontend) | **PASS** (×4 during the pass; pre-existing >500 kB chunk warning only) |
| `npm run lint` | **PASS** (clean) |
| Playwright (chromium, live prod server): `command-center-aftermath`, `replay-score-parity`, `v13_broadcast_layer` (incl. offseason record-cards contract), `official-rules-replay`, `wt22-decision-proof`, `tier1_recognition`, `v15-recruit-board` | **17/17 PASS** |
| Playwright: `maximized-playthrough-qa` (full loop, multi-viewport) | **1/1 PASS** |
| Browser console (warn+error) across the entire audit | **zero** |

Not run (stated honestly): the full 3-browser e2e matrix (chromium only, per
the touched-contract selection above); a fresh 1366×768 sweep (see §8).

## 10. Unresolved issues / caveats

1. **Latent `season_id` string-sort in `/api/history/my-program`** —
   `ORDER BY season_id ASC` makes `season_10` sort before `season_2`, so
   `hero.current` (the "latest" season snapshot) picks the wrong row from
   season 10 onward. Pre-existing; the same trap family the dynasty pass
   fixed in rivalries (`game_loop.season_sort_key`). The new `all_time` sum
   is order-independent and unaffected. Recommend fixing alongside the other
   history queries in one pass.
2. The dev save list remains polluted with probe/e2e saves (known, accepted;
   onboarding report §7.7). This pass deleted its own two probe saves.
3. `replay-official-strip-before/after.png` (untracked screenshots from the
   onboarding pass) still sit in the repo root — not mine to delete, flagged
   for cleanup.

## 11. Owner-decision taste calls (separated from bugs)

- **Extension-row tone:** same-holder re-breaks are deliberately quiet (small
  ledger rows, no green delta chip). If the owner wants a middle tier (e.g.
  milestone thresholds like "100th career elimination"), that's a design
  addition, not a fix.
- **Draw footer copy** states the standings consequence ("one standings point
  each"). If draws should instead feel like narrative cliffhangers ("nothing
  separated them"), that's a voice call — the current line favors mechanics
  legibility per ADR 0002.
- **"Scouted · no tape yet"** keeps a badge at all (rather than suppressing
  entirely) so the scout action visibly *did something* in week 1.
- The All-Time Record cell counts the in-progress season and says so. If the
  owner prefers completed-seasons-only, drop the current row from the sum and
  the "(incl. current)" suffix together.

## 12. Recommendations for the Product Director pass

1. **The five reports' systems decisions are the real backlog:** AI offseason
   recruiting (static league + snowball), contested Signing Day (makes the
   entire scouting loop strategic), catch-economy retune (with golden-log
   strategy), WT-20 live rules, promises wire-or-remove, department orders
   wire-or-drop. Every one now has an honest UI placeholder, so none is
   urgent *as UI*, but all five reports independently converge on the first
   two as the highest-leverage product work.
2. **Presentation-truth audits keep paying.** Both found-bugs this pass were
   "true number under a false label" — same family as the dev-focus hijack
   and the replay scoreline bug. A periodic label-vs-source audit (especially
   on glance/summary cells) is cheap and high-trust-yield.
3. **Records cadence now has the data hooks** (`is_new_holder`,
   `previous_holder_name`) for richer dynasty storytelling — e.g. a League
   Wire item on dethronings, or a record-watch banner late in a chase season.
4. **The hero set-strip is now a timeline band** — it could become the
   click-to-jump entry into the replay (the replay already supports per-game
   jumps), unifying aftermath and replay navigation.
5. Fix the `season_id` ordering trap (§10.1) before any 10+ season dynasty
   playtest.
