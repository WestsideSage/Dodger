# Owner Decision Log — 2026-06-10

Maurice answered every open owner-decision item from the seven 2026-06-09
reports in `docs/fable/`. This log maps each answer to its source item and
records the binding disposition. Where an answer was "not sure what this
means", the item is restated below with the interpretation taken (flagged
`INTERPRETED`).

**The standing directive that frames all of these:** *treat every unhooked
system as hookup-able now; nothing stays mocked unless strictly necessary;
analyze remaining open systems across the whole game and wire them for real.*

## 1. Adversarial QA / Trust Audit (§8)

| # | Item | Decision |
|---|------|----------|
| 1 | WT-20 Official Live Rules (No-Blocking enforcement, throw-clock, opening rush) | **GREENLIT — implement.** Owner: prior simulation/rules-revamp work means this should slot in. The reduced-blocking parameters left OPEN by Workflow-0 are now to be proposed-with-measurement during implementation, not owner-pre-gated. |
| 2 | Promise lane: revive UI or remove backend | **REVIVE + RENAME.** Owner could not parse "Promise Lane" at first glance — the term itself is the bug. Build the player-facing surface with clear, meaningful wording (what a promise is, what it does), and give promise results a real consumer. |
| 3 | Department orders: wire real effects or drop modal | **WIRE.** Owner: "staff is basically meaningless right now" — staff systems get real mechanical effects. |
| 4 | Signing-day credibility fallback (=50) for zero-action prospects | Owner answer: "not sure what this means." **INTERPRETED:** prospects the player never courted get a hardcoded neutral credibility of 50 at Signing Day instead of a computed value — minor display/mechanics drift. Disposition per the report's own recommendation: **fix opportunistically inside V16** (which rebuilds exactly this code path). No owner call actually needed. |
| 5 | `dynasty_office.py` promise evidence strings have no render surface | **Covered by item 2** (owner: "refer to item 2"). The revived promise surface renders the evaluation evidence. |

## 2. Dynasty Progression / Retention (§7)

| # | Item | Decision |
|---|------|----------|
| 1 | AI recruiting access (static-league fix) | **GREENLIT — major hookup.** Plus the standing directive: audit all remaining open/mocked systems game-wide and wire them. This is V16 Task 2. |
| 2 | True-OVR reveal at Signing Day: (a) scouted band vs (b) keep reveal | **(a), "for sure."** Confirms V16 plan D1: scouted band + `KnownValue` fog, truth revealed only after signing. |
| 3 | Development ceiling shortfall (~half of headroom reachable) | **GREENLIT — overhaul.** Players must actually grow toward their ceiling; redo the math (`_HEADROOM_CLOSE_RATE`, OVR-stat weighting) if needed, with the dev-arc probe as the before/after instrument. Owner calls this a pivotal feature. |
| 4 | Seed 31–33-year-old veterans in curated rosters | **APPROVED.** Deliberate design change accepted (owner cites Teamfight Manager 2's vet/rising-star/prodigy mix). |
| 5 | Records cadence: milestones vs marquee | **APPROVED.** Records must feel like real records (marquee only for genuine holder-breaks — the "Mondo Duplantis" bar); routine counter re-breaks present as milestones. Data hooks (`is_new_holder`) already exist. |
| 6 | Promises: "decide revive-or-remove before season-5" | Owner answer: "not sure what revive-or-remove means." **INTERPRETED:** the choice was build a UI for the promise backend (revive) vs delete the dormant lane (remove). Resolved by Adversarial QA #2 above: **revive, with clear language.** |

## 3. UX Review 1 — Fable UX / Visual Elevation (§7)

| # | Item | Decision |
|---|------|----------|
| 1 | Save-row club monograms (palette hash, not real colors) | **KEEP — owner loves them.** Swap to real club colors if/when `SaveInfo` carries them. |
| 2 | Champion stage gold-gradient name | **KEEP as-is.** |
| 3 | HoF legacy line fractional score ("Legacy 120.8") | **CHANGE — zero floats anywhere.** No fractional numbers on any player-facing surface; integerize the legacy line and sweep remaining float displays (the §4.1 float-leak family in `dynasty_office.py`, `replay_service.py`, ceremony prose is already flagged in STATUS #0). |
| 4 | Kicker duplication on Dynasty Office / Standings | **UNIFY + run a dedicated app-wide information-deduplication pass.** |
| 5 | `prefers-reduced-motion` handling | **FINE — no action.** |

## 4. First-Hour Onboarding (§7)

| # | Item | Decision |
|---|------|----------|
| 1 | AI development symmetry — Monte Carlo not re-run | **RUN IT.** Updated multi-season Monte Carlo (V12-style) is wanted; tuning verification is a standing expectation. |
| 2 | Scouted-estimate vs signed-truth disclosure | **DO IT — and broader:** a full pass purging vague/ambiguous language across every surface, with disclosures where fog is honest. |
| 3 | Week-1 scout reveals 0/5 tendency reads + "New intel" badge | **HOOK UP SCOUTING for real** so a scout action yields actual information; where it can't, never display ambiguity (suppress the contradictory badge). |
| 4 | Official replay strip is a full-time snapshot | **HOOK UP — live per-event** (replay-state-per-tick), even though it's real work. |
| 5 | Loss aftermath never browser-tested | **TEST ALL SCENARIOS** including loss screens, explicitly. |
| 6 | Class Brief run-on blob | **REDESIGN — owner has long been annoyed.** The card must be formatted as if the information matters: structured, scannable, useful. Not cosmetic-low-priority anymore. |
| 7 | Dev save list polluted | **PURGED 2026-06-10** — all 2,443 files in `saves/` deleted (owner: no real playthrough saves exist). |

## 5. Systems Balance Audit (§7)

| # | Item | Decision |
|---|------|----------|
| 1 | Official catch-economy retune | **GREENLIT.** Catching is core to real dodgeball; make accuracy/dodge non-negative EV at evens, probe matrix before/after, update WT-7 frozen winners + frozen-seed pins in the same change. |
| 2 | Contested Signing Day (dormant V2-B round) | **GREENLIT** (V16 core). Mindset: every dormant system is hookup-able now. |
| 3 | Slot-role model: wire or drop | **WIRE.** Roles get real, disclosed engine effects; design recruiting around role fit being mechanically meaningful. |
| 4 | Attribute sheet rationalization (stamina, tactical_iq consumers) | **WIRE.** Every displayed stat must have a real impact; give stamina and tactical_iq actual consumers rather than dropping them from display. |
| 5 | Rec rush/posture disclosure parity | **WIRE** rec rush targeting (not the disclose-only option). |
| 6 | Even-rung draw texture → fold into WT-20 | **APPROVED** — and WT-20 itself is now greenlit (QA #1), so the draw-ceiling gate folds into that milestone. |

## 6. UX Review 2 — UI/UX Visual Refinement v2 (§10 + §11)

| # | Item | Decision |
|---|------|----------|
| 1 | Latent `season_id` string-sort in `/api/history/my-program` | **FIX** alongside the other history queries in one pass (recommendation accepted). |
| 2 | Dev save list pollution | **PURGED 2026-06-10** (see Onboarding #7). |
| 3 | Stray root screenshots | **PURGED 2026-06-10** — the two untracked `replay-official-strip-*.png` deleted; additionally all ignored playtest screenshot folders deleted and 191 tracked May-era playtest artifacts (`playtest_output/`, `playtest_artifacts/`, root-level pngs, `.codex-artifacts/recruitment-flow.png`) staged for deletion in the Task 0 commit. |
| 4 | Extension-row tone (same-holder re-breaks quiet) | **ADD the middle milestone tier** (e.g. "100th career elimination") — milestones should feel like real milestones. |
| 5 | Draw footer copy (mechanics vs narrative voice) | **IMPROVE THE VOICE** — part of the app-wide voice/language pass (Onboarding #2). Keep mechanics legibility, lose the flatness. |
| 6 | "Scouted · no tape yet" badge retention | **KEEP** (recommendation accepted), in tandem with making week-1 scouting actually yield intel (Onboarding #3). |
| 7 | All-Time Record cell includes in-progress season | **COMPLETED SEASONS ONLY.** Drop the current row from the sum and the "(incl. current)" suffix together. |

## 7. Watchability / Broadcast Pass (§7)

| # | Item | Decision |
|---|------|----------|
| 1 | Old saves keep old replay limitations | **MOOT — stale saves purged 2026-06-10.** No legacy re-derivation needed. |
| 2 | Rec recorded-outcome correction forward-only | Owner wants complete hookup. **With the save purge, forward-only IS complete** — no pre-correction records remain; every future save gets the corrected recording. No migration needed. |
| 3 | Official survivors column stores meaningless metric | **CLEAN UP** (recommendation accepted — remove the ambiguous data). |
| 4 | Official decision context / intent frames (V16A research slice) | **IN SCOPE.** Big-ticket engine work is the current phase; bring intent persistence into the plan. |
| 5 | `test_server_save_boundary` order-dependent flake | **INVESTIGATE** (`server._active_save_path` shared state) as part of the save-state analysis accompanying the cleanup effort. |
| 6 | States not browser-exercised (cloth ties, OT copy, byes) | **MAIN DIVISION RULESET FIRST**, then a pass over the others. |
| 7 | `stats.extract_player_stats` ignores returns; `revivals_caused` hardcoded 0 | **HOOK UP** — stats-truth fix. |
| 8 | Playwright/E2E uvicorn launch config | **FINE — keep.** |

## Execution notes

- Decisions that change STATUS Open Work items (#1 WT-20, #5 promises,
  #6 department orders, #7 V16/D1) are reflected in `docs/STATUS.md` as of
  this date.
- V16 plan D1 is owner-confirmed (band). D2 (snipe model) and D3 (AI volume)
  remain recommended-defaults to confirm at Task 3.
- The newly greenlit non-V16 work (WT-20 + draw texture, catch retune, dev
  ceiling overhaul, promises UI, department orders/staff effects, role
  effects, stat consumers, scouting intel, replay-per-tick + intent frames,
  language/voice + dedup + no-floats passes, Class Brief redesign, records
  milestone tier, history sort fixes, stats truth, Monte Carlo re-run,
  loss-scenario coverage) is post-V16 backlog to be sequenced by the next
  product-director pass — V16 Task 0 (land the working tree) remains the
  first action, unchanged.
