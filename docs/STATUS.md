# Repository Status

Canonical snapshot of what is actually built and what is still open. When code
state changes materially, update this file in the same pass. If this file and
the source disagree, the source wins - then fix this file.

Last updated: 2026-06-10. `main` / `origin/main`: V16 shipped at `0c9bf28`
(child of `5668471`, which followed the `2969271` Task 0 sweep that landed
the six 2026-06-09 audit passes — the "Task 0 sweep" entries below).
Master-roadmap Phases 0-7 are on main. Section 4 (the Phase 8 desktop-first
visual implementation, briefs 4.1-4.8) is **implemented on main** and was
**browser-verified 2026-06-09** - see the "Shipped And Verified" entries.
**V16 Contested Offseason is SHIPPED (2026-06-10)** — all seven plan tasks
(`docs/specs/2026-06-09-v16-contested-offseason-sprint-plan.md`; retro:
`docs/retrospectives/2026-06-10-v16-contested-offseason-retrospective.md`).
**V17 Official Engine Truth is IN PROGRESS** — the greenlit post-V16 backlog
was sequenced into milestones V17–V21 on 2026-06-10
(`docs/specs/2026-06-10-post-v16-greenlit-backlog-sequencing-plan.md`,
commit `e235326`); V17 Task 1 (catch-economy retune) is shipped (entry
below), WT-20 enforcement is next.

## Current Phase

Post-V11. The game is playable end to end: career creation, weekly command
loop, official-rules match replay, playoffs, offseason ceremonies, and
multi-season dynasty history all work in the browser. The post-V11 redesign
is progressing: Plan A (hybrid driver architecture + Tier 1 engine) and
Plan B (player attribute v2) shipped on 2026-05-20. Plans C and D have
successfully landed and their briefs are archived.

Section 4 (the desktop-first visual implementation, briefs 4.1-4.8) is
**done**: all eight briefs were implemented on main across 2026-05-30 in four
`feat(design)` commits (`1de41e2` 4.1; `719f036` 4.2/4.5/4.8; `17e0f6e`
4.3/4.4; `542e6fe` 4.6/4.7) and were browser-verified on 2026-06-09. V15
(Systems Legibility) has shipped, establishing the legibility toolkit and term
registry. The current focus remains refinement and gameplay optimization, not
unrelated new systems. The Section 4 briefs are now historical design
references (validated against current source during the verification pass),
not pending work.

The master-roadmap trust pass is landed on main through Phase 7:
`3e04af6` (Phase 1), `e880405` (WT-6), `e9084ed` (P2), `6a7f7dd` (P3),
`bdf1b70` (P3b), `c9ab733` (P4), `f27a904` (P5), `3b6448c` (P6), and
`b1de840` (P7). The only roadmap engine work still deferred is the WT-20
"Official Live Rules" milestone (No Blocking / throw-clock / opening-rush),
which needs an owner decision on the unresolved reduced-blocking parameters
before implementation.

## Shipped And Verified

- **V17 Task 2 — WT-20 Official Live Rules enforcement + draw texture**
  (2026-06-10) - the three announced-only live rules now mechanically resolve
  (owner-ungated; the reduced-blocking params left OPEN by Workflow-0 shipped
  as proposed-with-measurement sim-design, disclosed, never claimed as USAD
  fidelity). *Ball lifecycle (the real draw fix):* out players forfeit held
  balls (Section 24-core, `queue_player_holds_ball_forfeit` finally invoked
  by the live loop) and a retrieval pass re-enters loose balls each tick —
  pre-WT-20, balls stranded on out players leaked out of play until neither
  side could throw and games dead-aired to the tick cap (measured: 552 of
  1,572 uniform-even games stalled with both sides alive, eating ~20 of 24
  match minutes; after: **0 stalls in 5,321 games**, matches play 12-14 real
  games). Uniform-even match draws 33.5% → **10.5%**, spread-even ~11%, and
  every remaining draw is an honest equal game-point split (6-6/7-7) — the
  0-0 stall draw is extinct (gated by
  `test_wt20_live_rules.py::test_even_strength_draws_are_bounded_and_honest`).
  *No Blocking (Section 27) enforced:* regulation play now models held-ball
  blocking (`official_resolution`: a ball-holding catch-decliner blocks at
  p≈0.65 even-ratings, keyed on the blocker's CATCH vs thrower power); while
  No Blocking is active the branch is disabled — the held ball genuinely
  stops protecting. Activation carries the SOURCED "balls do not reset"
  (the old `three_per_side` contradicted the primary source) and the SOURCED
  match-end source (clock expiry mid-game → match-end No Blocking game,
  play continues). Conformance ledger section 27 flipped ANNOUNCED → ENFORCED
  with the honesty note; 24-core marked SPLIT. *Throw clock:* honestly
  dispositioned, not theater — the autonomous loop throws every ≤6s tick
  whenever a side controls a ball, so the sourced 10s/5s failure windows are
  unreachable by construction; the penalty primitives stay unit-tested and
  the ledger note says exactly that. *Opening rush wired (disclosed
  sim-design):* `rush_target` orders which players secure the designated
  balls (NEAREST = slot order, STRONGEST_SIDE = power, CENTER = overall —
  holders are the early throwers and blockers, so `lineup.slot_order` is
  mechanical again with qualified copy); `rush_commit` shades the
  opening-exchange catch economy both ways (all-in throws harder to catch
  early / all-in rushers catch worse on the counter); first offense is a
  seeded coin flip, retiring a hardcoded team-A first-throw asymmetry. A
  rank-based initiative model was tried first and REJECTED by measurement
  (hold_back +17pp dominant). Policy Editor official note flipped from
  announced-only to the enforced-sim-design note; rec rush_target advisory
  unchanged (V19). *Blocked throws are honest replay events:* new "blocked"
  outcome through sequence payload → translator → replay labels ("BLOCK: X
  walls away Y's throw"), play-by-play voice, narration — never narrated as
  a miss. *Balance verification (400-trial probes, final constants):* every
  tactic axis is now a real tradeoff with no trap or dominant option
  (postures 40.8-49.5, rush_commit 44.0-46.2, targeting 45.8-47.2 vs
  baseline 49.0 — all within CI overlap; three measured re-tunes during the
  pass killed a go_for trap at −15pp and a play_safe spike); attribute matrix
  vs 47.5 baseline: accuracy 78.2 / power 70.5 / dodge 61.8 / catch 85.8,
  dead stats flat (V19 wires them). OVR curve steepened honestly (+24 net →
  82.5%, +72 → 98.8%, slope +56.5pp): a 24-minute match now aggregates ~13
  real games, so the better roster expresses reliably; draws across rungs
  4.7%. Champion parity (matched-OVR shapes): the long-standing Defensive
  skew (65-73.8%) FLIPPED to Power Throwers 63.8% (gate passes: 3 distinct,
  max ≤ 0.85; blocks were re-keyed from power to catch specifically to stop
  Power double-dipping) — recorded as a V19 design item, since the
  roles/stamina/tactical_iq wiring will reshape this economy anyway. WT-7 +
  watchability pins re-captured (70v63 favorite now 22/24 — best-of-13
  aggregation; seed-4242: 8-4 over 12 games). Verification: 103 tests across
  the 11 affected files green (incl. 11 new WT-20 gates), full suite at
  commit time, `npm run build` + `npm run lint` clean.
- **V17 Task 1 — Official catch-economy retune** (2026-06-10) - the official
  engine's throw resolution now shades catchability by throw quality
  (`official_resolution._CATCH_THROW_QUALITY_SLOPE = 2.0`, new) and rebalances
  `_CATCH_BIAS` 0.9 → 0.7, dropping even-strength p(catch|attempt) from ~0.527
  — far above the 1/3 EV-neutral line (a catch is a −2 swing vs +1 for a hit),
  which made an on-target throw net-NEGATIVE EV and turned two of the five
  displayed core skills into measured liabilities — to just under EV-neutral.
  Measured BEFORE → AFTER (`tools/decision_impact_probe.py`, 400 trials/attr,
  even strength, baseline 38.2 → 35.5): **+12 accuracy 31.2% → 54.2%**,
  **+12 dodge 30.5% → 39.2%**, +12 catch 71.5% → 62.7% (still clearly the
  premium skill; dominance reduced), +12 power 52.8% → 48.2%. OVR curve
  (`tier_engine_health_probe`, 400/rung): slope +36.0pp → **+44.8pp**, +72
  floor 72.0% → **79.8%**, draws across rungs 23.1% → 22.2%, median match
  length 241 → 183 events. Champion parity (40 seeds × 2 seasons,
  official_foam): Defensive Specialist 65.0% → **37.5%** / Power Throwers
  2.5% → **32.5%** / Balanced Rebuild 32.5% → 30.0% — near-parity, closing
  the audit's defense-skew finding. `_PLAY_SAFE_EVASION_BONUS` 0.25 → 0.10
  in the same change: the old value was compensation priced for the old
  economy and made play_safe the NEW dominant posture post-retune (50.7% vs
  go_for 40.2%); at 0.10 the posture spread is a real tradeoff (36.2–43.2
  across options vs 41.2 baseline, 400 trials). All frozen official-outcome
  pins re-captured as a documented intentional outcome change (AGENTS.md
  golden-log rule): WT-7 winners/kind-totals in
  `tests/test_official_engine_balance.py` (the uncapped dramatic baseline is
  now measured cap-independently from CATCH_QUEUE `return_on_catch` events:
  8.04/match), and the watchability seed-4242 pin (8-0 over 9 games → 11-0
  over 12). New permanent gates:
  `test_v17_no_displayed_core_skill_is_a_liability` (accuracy/dodge must
  never sit materially below the even baseline again) and
  `test_v17_catch_remains_the_premium_skill` (the retune must not delete the
  catch economy). Verification: full `python -m pytest -q` green (1,352
  tests, incl. the re-captured pins and the dynasty health gate against the
  retuned engine); no rec-engine changes.
- **V16 — Contested Offseason** (2026-06-10) - the offseason class is a
  market: prospect picks resolve through the contested V2-B round
  (`recruitment.conduct_recruitment_round`, first production caller), where
  interest built by in-season courtship strengthens the user offer (config
  `CONTESTED_USER_OFFER_BASE 90.0 + interest × 0.18`, tuned against
  `tools/contested_offer_probe.py`: uncourted star picks sniped 54%,
  contact+visit 22%, full courtship 7%); snipes are honest outcomes with
  offer-number explanations, never errors. The picker exposes the SCOUTED
  public band instead of `true_overall()` (field, fit_score, sort order, and
  the auto-pick path all moved to public estimates), generated bands are now
  center-jittered so the midpoint no longer encodes the hidden truth, and
  signing reveals "Scouted L–H → verified OVR N". AI clubs sign real
  prospects (1/club/offseason cap, roster ceiling 10): league churn went
  from zero to 5.0 AI signings per offseason, user title share 41.7% → 12.5%
  on the probe sweep, AI rosters off the 6-player floor to 10, six distinct
  champions across 24 probed seasons — **the static-league and
  solved-recruiting findings from the 2026-06-09 dynasty/balance reports are
  closed.** Interest/pipeline/credibility flipped to mechanical in the term
  registry (fit stays honest flavor); the `season_id` string-sort family was
  fixed across all history queries; `TestDynastyHealthGate` pins title share
  ≤ 0.35, AI roster floor, distinct champions, per-offseason AI churn, and a
  ≥1-snipe contested-ness tripwire. No match-engine changes (invariance pins
  and golden logs untouched). Retro:
  `docs/retrospectives/2026-06-10-v16-contested-offseason-retrospective.md`.
- **UI/UX visual refinement pass v2 — report-informed** (2026-06-09, landed
  in the 2026-06-10 Task 0 sweep) - closes every open *UI-owned* item from the five 2026-06-09
  cross-disciplinary reports; handoff with the full action matrix in
  `docs/fable/2026-06-09-ui-ux-visual-refinement-v2.md`. *Report-driven:*
  Signing Day now discloses scouted-estimate vs verified OVR; the week-1
  "New intel revealed" badge is state-aware ("Scouted · no tape yet" at 0
  tendency reads); the Class Brief renders structured rows via `BriefProse`
  (was a run-on blob); the Records Ratified beat separates milestones (new
  holder / first-time — marquee cards, "New Holder" chip, "takes the record
  from X") from same-holder re-breaks (quiet "Extended their own records"
  ledger rows) on new `RatifiedRecord.is_new_holder`/`previous_holder_name`
  fields compared against the persisted previous holder (back-compat: old
  cached payloads default to marquee, pinned); the Policy Editor's rush
  Target row discloses outcome-deadness on REC careers too (consumer truth
  re-verified in `rec_engine.py` before writing copy); official draws are
  declared on the aftermath hero ("◆ Draw" badge + "one standings point to
  each club" footer, verified against `season.py` scoring). *Found in the
  live audit and fixed:* the Dynasty History "All-Time Record" cell rendered
  the latest single-season snapshot under an across-all-seasons label — the
  endpoint now emits a true `hero.all_time` career total (summed from the
  same `season_standings` rows) with an honest fallback label; playoff-length
  official matches (12-15 games) ballooned the aftermath hero to ~450px by
  stacking set chips in the 4.5rem center column — the set story is now a
  full-width horizontal timeline band (hero 184px). *Known latent issue
  flagged (not fixed):* `/api/history/my-program` string-sorts season ids
  (`season_10 < season_2`), so `hero.current` picks a wrong "latest" row from
  season 10 on. Verification: full `python -m pytest -q` green (exit 0, incl.
  5 new tests); `npm run build` + `npm run lint` clean; targeted Playwright
  18/18 (chromium, live prod server — aftermath, replay parity, v13 record
  cards, official replay, wt22, tier1, recruit board, maximized playthrough);
  live browser walks at 1280/1440/1920 over seasons 1-4 of a throwaway career
  (deleted after; prior active save restored) with zero console errors and
  zero horizontal overflow; both record-cadence states, two real draws, and
  two real loss aftermaths rendered live.
- **Dynasty progression / retention pass** (2026-06-09, landed in the 2026-06-10 Task 0 sweep) - full
  multi-season audit with sweep evidence; handoff with all numbers in
  `docs/fable/2026-06-09-dynasty-progression-retention-review.md`. *Dead
  league-memory feeds fixed:* rivalry_records and team records (most_titles /
  longest_unbeaten_run) were only ever written by the retired sandbox CLI —
  the Dynasty Office rivalry board, `/api/history/league`, broadcast rivalry
  tags, and the club side of the record book read tables the web game never
  fed. Rivalries now rebuild from match_records at the post-match chokepoint
  (`game_loop.rebuild_rivalry_records`, idempotent, retroactive for legacy
  saves; numeric season ordering fixes a `season_10 < season_2` sort hazard)
  and team records ratify in `offseason_beats.ratify_records` from club
  trophies + match records. *Development reps unit bug fixed:* the
  `minutes/1000` reps gate never matched either engine's measured scale
  (official starter season = 64-206 event-tick "minutes", rec = 10-27), so all
  post-practice development ran at 1-20% rate and stalled 15-22 OVR below the
  advertised ceiling; `apply_season_development` now takes appearance counts
  (starter fielding every match = full rate; legacy path byte-identical when
  params absent) and the offseason passes them. *Aftermath truth:* the
  survivor-derived winner in `_build_aftermath` (which could only ever
  contradict the resolved result — measured 17 degraded aftermath panels per
  80 auto-piloted seasons, all on official game-points draws) is removed.
  *Roster-floor trap closed:* the user club is exempt from every AI roster
  repair, so skipping recruitment annually bled a measured roster of 4 by
  season 10; the offseason "skip" now 409s below a fieldable six while
  signable players exist, and `Offseason.tsx` finally renders action errors
  inline. *Copy truth:* Signing Day's rating badge claimed "scouted" but is
  the prospect's actual overall regardless of scouting — relabeled "OVR".
  *Instrumentation:* `tools/dynasty_health_probe.py` (seeded N-season sweep of
  the shipping loop) + `tests/test_dynasty_progression_health.py` (16 guards
  incl. dynasty determinism). *Measured, NOT changed (owner decisions, see
  handoff §7):* AI clubs cannot recruit (league has zero roster churn for 7
  seasons; engaged user wins 60% of titles at +8-9 fielded OVR), Signing Day
  reveals true OVR (scouting strategically void), development still closes
  only ~half of remaining headroom by peak-end (pool dilution, not the unit
  bug), first league retirement waits until season 8. Verification: full
  `python -m pytest -q` green (1,320 tests); `npm run build` + `npm run lint`
  clean; Playwright v13-broadcast + maximized-playthrough 3/3 (chromium);
  live prod-server walk on a throwaway save (15 rivalry pairs in history,
  team-record ceremony cards with My Club scope, "OVR" label, zero console
  errors; probe save deleted).
- **Systems design / balance audit pass** (2026-06-09, landed in the 2026-06-10 Task 0 sweep) - full
  decision-systems audit with new measurement; handoff with all numbers in
  `docs/fable/2026-06-09-systems-balance-audit.md`. *Balance bug fixed:* the
  official engine's PLAY_SAFE catch posture computed a 0.75 catch-attempt
  threshold — above virtually every roster's catch band — so a play-safe team
  **never attempted a catch** and measured **0 wins in 400** even-strength
  matches (catches are the official scoring economy); "Preserve Health"
  (whose preset selects play_safe) was a hidden self-destruct on official
  careers, and the AI "Aging Veterans" archetype fell into the same pit. Fixed
  via threshold 0.65 + a play-safe evasion bonus on declined catches
  (`official_tactics._catch_thresholds`,
  `official_resolution._PLAY_SAFE_EVASION_BONUS`); measured 0.0% -> 36.8% W
  on a realistic catch/dodge-spread fixture (default mirror 44.0%), all
  non-play_safe matches byte-identical (WT-7 frozen winners re-verified),
  pinned by two new gates in `tests/test_official_engine_balance.py`.
  *Truth fixes:* the slot-role "liability" model has NO consumer in any
  shipping engine (only the retired legacy MatchEngine applied penalties), so
  the replay's "suffered a liability penalty" / "Liability exploited ... was
  punished" copy was fiction — reworded to advisory fit notes + saved facts;
  the "liability_involvement" Primary Factor was REMOVED (it directed players
  at a non-existent lever); `lineup.slot_order` term downgraded to flavor with
  honest copy; the all-in-rush "extreme fatigue risk" warning (no engine
  applies rush fatigue) replaced with the true early-catch-exposure tradeoff.
  Recruiting courtship truth: interest/fit/pipeline/credibility have no
  consumer in the shipping signing path (the offseason picker signs directly;
  `conduct_recruitment_round` is dormant and `/api/recruiting/sign` is a dead
  stub guarding on a nonexistent state) — terms downgraded to flavor with
  honest copy until a contested Signing Day ships, and the dormant round's
  hardcoded credibility=50 now uses the real score. *Instrumentation added:*
  `tools/decision_impact_probe.py` (tactic-axis + per-attribute win-rate
  impact, both drivers) and `tests/test_attribute_consumers.py` (same-seed
  invariance pins for the per-driver dead-attribute matrix; terms.ts identity
  -trait claims now qualified per ruleset). *Measured, reported, NOT tuned
  (owner decision):* at even strength on officials, +12 catch = +31pp win
  rate while +12 accuracy/dodge = MINUS 8-10pp (throwing on-target into an
  attempting catcher is negative EV), go_for_catches is the dominant posture
  in both engines, and the defensive shape wins 73.8% of matched-OVR titles —
  the catch-economy retune needs its own golden-log-aware pass (plan in the
  handoff §7).
- **Match watchability / broadcast pass** (2026-06-09, landed in the 2026-06-10 Task 0 sweep) - the
  watched replay now tells the truth and tells a story; full handoff with
  evidence in `docs/fable/2026-06-09-watchability-broadcast-pass.md`.
  *Truth bugs fixed:* (a) catch re-entries never reached the persisted
  event stream (both engines) and official per-game resets weren't
  represented, so **99% of official replay events displayed a wrong live
  score** (court saturated to 12 eliminated players) — returns now ride as
  `state_diff.player_return` (officials joined on (game_id, sequence_id);
  sequence ids restart per game), throws carry `context.official`
  game/tick metadata, and the proof score-state resets per game (now 0
  drift vs engine ground truth); (b) **legacy rec recorded outcomes could
  be false** — `rec_adapter._derive_box_score` ignored returns, undercounting
  recorded survivors on 40/40 probed seeds, and `franchise.simulate_match`
  derives the recorded winner from those survivors (live repro: an event-log
  2-0 elimination win recorded as a 0-0 Draw); the box now computes final
  on-court status from the full diff stream, so records agree with the
  event log (forward-only; officials byte-identical, pinned by a frozen-seed
  test + before/after season probes); (c) the "TURNING POINT" was literally
  the first hit of the match — now the biggest in-game swing (lead-flip
  weighted, never scored across a game reset) with `turning_point_index` so
  the jump lands on the headline event. *Watchability added:* official
  replays show a SETS strip (per-game chips + running game points, jump
  targets from per-event game metadata; persisted `official_score_json` is
  finally surfaced), possession-bar game dividers + amber moment pips,
  GAME-n labels in the readout/current-event card, "fresh court" delta at
  game boundaries, in-playback moment banners (moments now carry
  `game_number` + server-resolved `anchor_index`), the V13 highlight reel is
  finally rendered (dead `MatchHighlights.tsx` wired into the replay sidebar
  with working jumps; game-aware moment anchoring fixed in `highlights.py`),
  re-entry narration + USAD rule refs in event labels/details, variable
  autoplay pacing + the previously-dead `ReplaySpeedControl` (1x/2x/4x/skip),
  and an aftermath set-story strip on the score hero
  (`match_card.games`). Verification: full `python -m pytest -q` green
  (1,294 tests; 16 new in `tests/test_replay_watchability.py`); `npm run
  build` + `npm run lint` clean; Playwright 8/8 (official-rules-replay
  extended with set-strip/swing pins, replay-score-parity, wt22, aftermath,
  v13 ×2, tier1); live browser walk (1440×900 + 1280×720, zero console
  errors, zero overflow). *Open:* legacy saves keep old-replay limitations
  (no retroactive inference); official engine still persists no intent
  context (V16A research spec); `test_server_save_boundary` has a
  pre-existing order-dependent flake (failed once in one full run, passed
  in two subsequent full runs + isolation).
- **First-hour onboarding / growth-truth pass** (2026-06-09, landed in the 2026-06-10 Task 0 sweep) -
  fresh-player first-hour audit (career creation → weekly loop → replay →
  aftermath → playoffs → full offseason → season 2) with focused fixes;
  handoff: `docs/fable/2026-06-09-first-hour-onboarding-review.md`. *Root
  bug fixed:* curated/takeover rosters seeded `traits.potential` as
  `gauss(50,15)` — a legacy scale below current OVR for ~half the roster —
  while the development engine, recruitment seeds, trajectory floors, and the
  Roster "Ceiling" display all treat potential as an OVR-scale ceiling; live
  save proof showed every takeover starter developing **+0** in the first
  offseason and the Roster Lab rendering "Ceil 26" on a 66-OVR starter.
  `career_setup._curated_potential_ceiling` now maps the same draw (RNG
  stream byte-identical) onto a true age-scaled ceiling at/above OVR (new
  careers only), and `web_status_service.build_roster_payload` computes the
  displayed ceiling exactly as the engine consumes it
  (`max(stored, trajectory floor, OVR)`) so legacy saves stop displaying
  impossible ceilings; tier derives from the same number. Pinned by
  `tests/test_first_hour_growth_truth.py` (7 tests incl. a cause→effect
  "young curated player actually develops" regression). *Legibility fixes:*
  replay Official panel humanized (FULL TIME framing, "No Blocking" not
  `NO_BLOCKING`, club name not raw id in burden, `A0 held` ball chips,
  grouped rule-call counts not "11 · 11"); TermTip click no longer closes the
  tooltip it just opened; Key Performers K/C/D/Imp legend + honest Imp
  tooltip; scout-tape tooltip grammar ("a strong lean"); takeover club picker
  states the choice is identity, not difficulty. *Stale spec retconned:*
  `maximized-playthrough-qa.spec.ts` waited on the pre-WT-5 raw `CLOTH` key
  (dead locator since 2026-06-01, pre-existing failure); now asserts "Cloth
  Division". Verification: full `python -m pytest -q` green (1,278 tests);
  `npm run build` + `npm run lint` clean; Playwright
  official-rules-replay + replay-score-parity 6/6 (3 browsers),
  maximized-playthrough-qa 1/1 (post-retcon), v15 legibility 36/36; live
  prod-server browser walks at 1440x900 + 1280x720 with zero horizontal
  overflow and zero console errors. *Open (owner calls):* AI-symmetric
  development balance probe not re-run; Signing Day doesn't disclose
  scouted-estimate vs signed-truth; official replay strip remains an honestly
  labeled full-time snapshot (not per-event).
- **Adversarial QA / trust audit fixes** (2026-06-09, landed in the 2026-06-10 Task 0 sweep) - full
  red-team pass over decision traceability, outcome truth, official-rules
  honesty, and copy claims; handoff with ranked findings + evidence in
  `docs/fable/2026-06-09-adversarial-qa-trust-audit.md`. *Real bug fixed:* the
  offseason dev-focus read had no club filter, so an AI club's persisted plan
  (dev_focus `YOUTH`/`VETERAN`, silently treated as BALANCED) could replace
  the player's chosen focus — now `offseason_ceremony._load_player_dev_focus`
  filters by player club (2 new regression tests). *Copy truth:* the six no-op
  department orders no longer claim "AFFECTS PLAY"/engine effects (terms.ts →
  flavor; Dynasty Office settings modal rewritten + boundary banner); the
  Policy Editor's Opening Rush panel now discloses announced-only on official
  careers (new `ruleset_selection` on `CommandCenterResponse`, pinned by a
  serialization-guard test); "+1 training unit", bye "Squad Rested/recovered",
  "medical incidents", "critically fatigued", and "Preserve Health protects
  them" all replaced with mechanically true statements. *Test integrity:* a
  false-confidence staff-development test (wrong department key + trivial
  `>=`) repaired to actually guard the hook. Verification: full
  `python -m pytest -q` green (1,271 tests); `npm run build` + `npm run lint`
  clean; live prod-server browser checks (official career: rush note renders,
  FLAVOR tooltips, settings banner, zero console errors). Playwright e2e not
  run (changed strings grepped against all specs — no pins affected).
- **Full-app UX elevation + Command Center redesign** (landed 2026-06-09) - an
  app-wide visual refinement pass plus four owner-feedback iterations on the
  pre-sim Command Center, documented in full in
  `docs/fable/2026-06-09-fable-ux-review.md` (moved from
  `docs/ux-reviews/fable/`; read that for the per-surface ledger; this entry
  is the index). *App-wide:* an append-only
  "ELEVATION LAYER" CSS section (court-floor atmosphere, `.dm-action` button
  system with real hover/focus states, themed scrollbars, table zebra),
  title-screen save menu with club monograms, unified offseason ceremony
  headers with beat pips on every beat, gold champion stage, HoF plaques,
  retirement farewell cards, two-column player scouting modal, and a set of
  visual bug fixes (readiness-gate overlap, credibility-meter clip, archive
  timeline dot, replay court label legibility, prospect-card legend dedup).
  *Command Center:* every fact appears exactly once (dedup ledger in handoff
  §8), League Wire news ticker opens the page, weekly directive banner with
  gate-action buttons, launch-dock lock CTA (standby/armed/live), uniform
  desk bottoms (bounding-rect equal), fog-of-war intel chips + meter, color
  language fixed (emerald = verified good only; cyan = set/informational).
  *Backend (one fix):* retirements beat `ovr_final` int-rounded in
  `offseason_presentation.py` (float-leak family). *Test changes:*
  `tests/e2e/v15-recruit-board.spec.ts` updated for the board-level legend.
  *Also closed in the same push:* (a) the open "tokenless e2e sweep" item —
  all 23 e2e specs with raw mutating `request.post` calls now attach the real
  launch token via `tests/e2e/_token.ts` (they had silently depended on an
  unguarded server and failed against the real WT-12 guard); (b) a
  presentation-truth bug the re-enabled suite immediately exposed:
  `server.MatchReplayResponse` did not declare `scoring_model`/game-point
  fields, so FastAPI stripped them and **every official replay rendered as a
  legacy survivor scoreline**, able to contradict the aftermath hero (WT-2/3
  family). Fixed in `server.py`, pinned at the serialization layer by
  `test_official_replay_scoreboard.py::test_replay_response_model_serializes_official_scoring`,
  and browser-pinned by the updated `replay-score-parity.spec.ts` (which also
  now waits out the hero count-up animation instead of racing it). Two stale
  specs were retconned to current truthful behavior (game-point heroes; the
  "Bank the Result / Next Week" action labels).
  Verification: full `python -m pytest -q` green; `npm run build` +
  `npm run lint` clean; targeted Playwright e2e **45/45 passed** (13 specs
  covering every touched command-center/legibility/broadcast contract,
  chromium, fresh prod server — and the two prior failures were confirmed to
  reproduce identically on clean main, i.e. pre-existing); live browser
  sweeps at 1280/1366/1440/1920 with zero horizontal overflow and zero
  console errors.
- **Section 4 desktop-first visual implementation - implemented + browser-verified** (implemented on main 2026-05-30 across four `feat(design)` commits; verified 2026-06-09) - all eight §4 briefs are shipped on main: `1de41e2` (4.1 Class Report), `719f036` (4.2 Season Preview / 4.5 Rookie Class Preview / 4.8 Records Ratified), `17e0f6e` (4.3 Bye Aftermath / 4.4 Match Aftermath), `542e6fe` (4.6 War Room / 4.7 Policy Editor). **Doc-lag correction:** `STATUS.md` had only ever recorded the Phase 8 *briefs* (documentation, `ce50c14`) and still listed Section 4 as "next / re-validate before implementation" - the `feat(design)` implementation that followed was never logged here. A re-validation fan-out (8 briefs vs current source + design-system survey) plus a live **prod-server** browser sweep (`python -m dodgeball_sim`, port 8000, fresh PID; vite/`DODGEBALL_DEV` avoided so the SPA carries the launch token) at **1280x720** (the no-horizontal-overflow floor) confirmed all eight screens meet their brief success criteria with **zero horizontal overflow** (with one honest 4.1 caveat noted below). Deep states were reached via `POST /api/command-center/fast-forward` (`pre_playoffs`/`offseason` - active and completed playoff bracket, offseason ceremony beats) and a build-from-scratch 7-club career (`next_bye`/`max_weeks` - a real bye week). Drift confirmed-resolved against the frozen briefs: 4.1 `signed_count` is the single authoritative count (no card-derived count) and the read-only **legacy fallback** path renders a structured GlancePanel not a text blob (HONEST CAVEAT: only that legacy path was browser-rendered - the **card-grid tab mode** `My/Rival/Surprise` -> "Your Picks/Rival Picks/Surprises" is code-verified via the `FILTER_LABELS` constant but populates from `load_recruitment_signings`, i.e. *in-season* Recruitment Day signings the fast-forwarded careers skipped, so it was not browser-rendered this pass); 4.2 carries the post-brief `archetype_key` for TermTip + a week-timeline bar; 4.4 hero is **game points** (not survivors) with grouped YOU/THEM/RESULT body + the new `manager_lesson` card; 4.6 bracket leads with **game-point** scorelines, a distinct gold "LEAGUE CHAMPIONS" champion card, `YOU ADVANCED` outcome badges, and playoff-aware race copy replacing the stale regular-season copy; 4.8 has a prominent My Club/League scope toggle with `aria-pressed`. **One fix landed:** the §4.1 recruitment/draft ceremony body prose leaked a float OVR ("64.0 OVR") - `overall_skill()` returns an `int` but the prose formatted it `:.1f`; corrected to integer in `offseason_ceremony.py` (3 sites) and pinned by `tests/test_dispersed_helpers.py::test_recruitment_beat_body_renders_integer_ovr_not_float`. Verification: full `python -m pytest -q` green (exit 0); live browser screenshots of all eight screens. **Open (owner-decision enhancements, NOT bugs):** (a) 4.4 surfaces no moment-beat above the collapsed ReplayTimeline when one exists (criterion #5 is "Consider..."; a 5-moment match was confirmed to keep all moments inside the collapsed "POSTGAME REPORT" timeline); (b) the 4.6 champion card is gold + trophy + "LEAGUE CHAMPIONS" but equal-*size* to the semifinal columns - elevating it further is a taste call; (c) `narrative_note` (overtime/seed-tiebreaker copy) renders only on contested playoff results and was not exercised this run. **Adjacent float-leak triage (investigated, mostly NOT leaks):** the one other *web-facing* int-OVR `:.1f` leak - the **retirements** ceremony body (rendered verbatim by the `Graduation` component) - was also fixed and guarded (`test_retirements_beat_body_renders_integer_ovr_not_float`). The rest are deliberately NOT touched: the **development** ceremony body's deltas are *intentionally fractional* (pinned by `test_dispersed_helpers.py` asserting `"+1.2"`) as is `records.py` `overall_gap` (pinned by `test_records.py` asserting `"11.5 OVR underdog"`); `dynasty_office.py` `build_player_profile_details` and `replay_service.py` `team_snapshot` are **test-only legacy** text formatters not wired to the web UI (the web uses structured payloads), so their `:.1f` is harmless dead-path formatting. Non-bug: `offseason_ceremony.py:1061` would `AttributeError` on a `Prospect` in the `draft_pool`, but production passes `load_free_agents(conn) -> list[Player]`, so the `Iterable[Player]` contract holds and the crash is unreachable.
- **Post-playtest hardening** (landed 2026-06-02, `0673d40`) - closes a follow-up pass after the roadmap trust work: scoring/decision truth repairs, signing-day consistency, scout + aftermath legibility refinements, 403 hardening, missed-playoffs recap coverage, official replay scoreboard tests, and launch-token-aware WT21/WT22 E2E helpers (`tests/e2e/_token.ts`). Verification recorded in the commit includes new Python coverage across manager lesson, scout reveal, signing day, standings intent labels, playoff resolution, and official replay scoreboard paths.
- **Post-roadmap cleanup** (landed 2026-06-01, `d89f502`) - removes dead `server.py` build-from-scratch code and deduplicates Manager Lesson / Next-Best-Improvement aftermath overlap in `use_cases.py`, pinned by `tests/test_aftermath_dedup.py`. These were previously listed here as open follow-ups; they are now closed.
- **Master-roadmap Phases 2-7 - trust-pass continuation** (landed on main 2026-06-01, `e9084ed` through `b1de840`) - executes the remaining work items of `docs/specs/2026-05-31-master-implementation-roadmap-audit-synthesis.md` (amended by the grill-resolutions log) under ADR 0002, phase-by-phase with a per-phase mechanical-verify + adversarial-faithfulness gate. **P2** (`e9084ed`): capped official `DRAMATIC_CATCH` moment spam to clutch catches (WT-7; outcomes byte-identical), dropped the inert rush `proximity_modifier` proof (WT-8 interim), re-measured even-rung draws (WT-31 = 30.2%; accept honest draws, real reduction deferred to WT-20). **P3** (`6a7f7dd`): editor-saved lineups reach the sim and recap (WT-9), inline `/simulate` overrides validate through `apply_manual_lineup` (WT-10), and AI tactics reach secondary/playoff sim paths (WT-11). **P3b** (`bdf1b70`): Scout reveals derived opponent intel (WT-30), fast-forward confirmation discloses skipped decisions (WT-29), and Manager Lesson surfaces on inconclusive losses with an honest no-lever fallback (WT-32). **P4** (`c9ab733`): launch-token CSRF defense, SPA path containment, atomic founding-roster validation, non-mutating save listing, fail-loud corrupt cursor, and backend ruleset default -> `official_foam` (WT-12..WT-17). **P5** (`f27a904`): ruleset copy corrected and conformance matrix converted to enforced / announced-only / absent (WT-18/WT-19). **P6** (`3b6448c`): shared accessible primitives and migrated broken surfaces, plus timer cleanup (WT-21/WT-28). **P7** (`b1de840`): pipeline tier semantics flipped so tier 5 = Elite = strongest, standings label equals mechanical `program_archetype`, AI champion-parity probe added, and decision-proof Playwright spec added (WT-25/WT-24/WT-23/WT-22). Verification on that branch tip was `python -m pytest -q` green (1228 tests), frontend build/lint clean, targeted Playwright green, and balance/parity probes within gates. **Still OPEN:** WT-20 "Official Live Rules" engine enforcement remains deferred pending the owner decision on reduced-blocking parameters; do not silently wire No Blocking / throw-clock / opening-rush outcomes as a routine bugfix.
- **Master-roadmap trust pass — Phase 0 + Phase 1 + WT-6, with the engine milestone gated OPEN** (landed 2026-06-01) — executes the verified slice of `docs/specs/2026-06-01-master-roadmap-grill-resolutions.md` under ADR 0002 (faithfulness over scope). **Workflow 0 (primary-source gate):** re-verified the No Blocking rule against usadodgeball.com/rules (`docs/specs/2026-06-01-workflow0-primary-source-rule-verification.md`) — the *trigger* and the terminal "match-end No Blocking game" are SOURCED, but **what "reduced blocking" changes in resolution is OPEN** (the page doesn't specify it), so per the HARD RULE **WT-20/WT-31 enforcement does NOT ship**; the announce-not-enforce interim + disclosed playoff tiebreak stay. The "PRIMARY-SOURCE CONFIRMED" overclaim was corrected in `CONTEXT.md` + the resolutions log (a narrow ADR-0002 amendment is *proposed*, not applied). **Phase 1 (presentation truth):** WT-1 replay never renders `-`/empty-space for target-less throws (rec headshot + official clock-violation read as fouls; official miss = a dodge that "doesn't connect"); WT-2 official aftermath headline uses game points not survivors (0-0 draw no longer reads 0-3); WT-3 broadcast last-meeting scoreline uses game points for official matches; WT-4 readiness-gate blocking reason is visible + accessible with **state-aware** detail copy (no satisfied-state assertion shown on a red gate); WT-5 a single canonical ruleset display-name module (`frontend/src/legibility/rulesetNames.ts`) removes `USAD FOAM`/`FOAM-OPEN` key leaks in the scoreboard and official-rules panel. **WT-6 (engine, balance-gated):** the official catch-posture inversion is fixed (the defender's own catch policy now drives the defender's catch decision); BEFORE/AFTER `tier_engine_health_probe --driver both --trials 400` are byte-identical (official slope +36.0pp, floor 72%, draws 23.1%) → **0.0pp attributable balance delta** with symmetric AI policies, and an asymmetric proof test pins that the defender's posture now governs (it inverts/fails on the pre-fix code); foam+cloth `official_match_probe` gates hold. Verification: `python -m pytest -q` green (1133 tests, incl. 4 new test files; +2 guards from the post-review cleanup); `npm run build` + `npm run lint` clean; a 7-agent adversarial review caught three residual lies (official dodge mis-narrated as "empty space"; the OfficialRulesPanel ruleset-key leak; pending gates captioned with satisfied-state text) which were fixed and re-verified. **Not done this pass (honest):** Phases 3/3b/4/5/6/7 and the WT-20 engine milestone (held OPEN); no live browser walk was run (verification rests on the suite + build/lint + probes + behavioral checks). **Status: committed to main 2026-06-01** — Phase 1 presentation truth (`3e04af6`), WT-6 engine fix (`e880405`), and this docs/roadmap commit. The independent review (`docs/specs/2026-06-01-ultracode-test-drive-review.md`) and its cleanup pass closed the actionable findings (misattribution lie, WT-4 detail coverage, proximity-doc wording, duplicate imports).
- **V15 - Systems Legibility** (landed 2026-05-31) - Established the foundational legibility toolkit API (`frontend/src/legibility/`) including the term registry, accessible `TermTip`, `KnownValue` fog-of-war states, and `ProofChip` primitives. The toolkit was then integrated into the Recruit Board, Roster, Lineup Editor, Standings, and Dynasty Office surfaces to provide proof-backed, semantic feedback without touching engine simulation math.
- **Playtest-fixes Phase 8 - §4 design-handoff briefs** (landed 2026-05-29) - D8, documentation only. Eight Claude Design handoff briefs in `docs/specs/2026-05-29-section4-design-briefs/` (4.1 Class Report, 4.2 Season Preview, 4.3 Bye Week Aftermath, 4.4 Match Aftermath, 4.5 Rookie Class Preview, 4.6 War Room, 4.7 Policy Editor, 4.8 Records Ratified) plus a README index. Each brief delivers the plan's required sections from `docs/archive/plans/2026-05-29-playtest-fixes-multi-phase-plan.md` - teardown, primary/secondary/cut information hierarchy, a data inventory of the REAL payload fields available, the shared constraints ([Superseded: 390×844 mobile] now desktop-first/desktop-only matrix, semantic/AI-friendly markup, no new deps, no routing/auth change, "explain don't decide"), and success criteria - and reflects the then-settled Phases 1-7 behavior (set scoring, honest PRIMARY FACTOR, moments, readiness gates, records scope filter/empty-state, Policy Editor de-dup, growth deltas). These were briefs, NOT finished UI - they were the *handoff*; the UI implementation followed on 2026-05-30 in four `feat(design)` commits and is now shipped + browser-verified (see the top "Section 4 desktop-first visual implementation" entry).
- **Playtest-fixes Phase 4b - foam-official default + scoreboard + PRIMARY FACTOR** (landed 2026-05-29) - flips new careers onto the now-OVR-rewarding official engine (gated on Phase 4a). *Default flip:* the new-career ruleset selector defaults to `official_foam` (Generic stays selectable; existing legacy saves untouched), so new "Build from Scratch" careers play real set-based scoring. *Moment coupling (the trap):* `OfficialEngineAdapter.run_generic` previously discarded the engine's moments; it now carries `moment_events` onto the `match_end` event context in the exact shape `aftermath_context.moment_events_from_payload` expects, so the Tier-1 moment beats / tier1 voice / V13 highlights survive the default flip (pinned by `test_official_routing` - moments reach the aftermath payload). *PRIMARY FACTOR (4.4 logic):* `derive_match_explanation` now takes a `point_margin` (the official game-point gap); a decisive 0-4 / 6-0 set result is treated as decisive even when survivor counts are close, so it never falls into the "stayed close / variance / inconclusive" copy - a real factor is surfaced, or a decisive-result message ("the result wasn't close") replaces the coin-flip shrug. Generic matches pass `point_margin=0` and are unchanged. Verification: `python -m pytest -q` green (1085 tests) with new tests (official moment-coupling guard, decisive-set PRIMARY FACTOR cases); frontend `npm run build` + `npm run lint` clean; live fresh-server proof (a new `official_foam` career's match reported `home/away_game_points` set scoring, 12 `moment_events` on the replay's match_end, and a "Catch disparity" PRIMARY FACTOR instead of "inconclusive").
- **Playtest-fixes Phase 4a - official engine balance + moments + probe gate** (landed 2026-05-29) - resolves the measured D4 blocker: the shipping official match engine (`run_autonomous_match`) did not reward OVR (favorite at +72 net edge won only ~44% with ~22% draws), because a catch (outs the thrower + resurrects a defender) was the default outcome of an on-target throw, so throwing was net-negative EV and games stalled to clock-expiry 0-0 draws. *Balance retune:* `official_resolution.compute_throw_probabilities` now biases the catch-given-attempt probability down and sharpens its rating sensitivity (`_CATCH_SLOPE=4.0`, `_CATCH_BIAS=0.9`) - the catch-outs-thrower-and-resurrects rule itself is unchanged (faithful to USA Dodgeball). Measured on the real engine (400 trials/rung): favorite win rate +0->36% / +24->50% / +48->63% / +72->72%, slope **+36pp** (gate +10), top floor **72%** (gate 60%), monotonic; draws now decline with edge (28%->18%) instead of swamping OVR, and games are decisive (P50 match length 386->241 events, 77% of even-team games reach a winner). *Moments:* `run_autonomous_game`/`run_autonomous_match` now emit recognition moments DRAMATIC_CATCH, LATE_GAME_ESCAPE, ONE_V_ONE_FINALE, COMEBACK (GASSED_COLLAPSE / FLOOD_THROW deferred - no fatigue/batch-throw model), surfaced through a new `OfficialMatchEngineDriver` (the shipping multi-set engine as an `EngineDriver`). *Probe fixes:* `tier_engine_health_probe.py --driver official` was importing the wrong module (the single-game `official_driver.OfficialDriver` stub) and could not run; it now drives `OfficialMatchEngineDriver`, and `tools/official_match_probe.py` reuses the same source driver. *Graduated gate:* new `tests/test_official_engine_balance.py` asserts the OVR slope/floor + a coupled top-rung draw cap, and that the official driver emits all four feasible moment kinds - this gates the Phase 4b default-flip. Verification: `python -m pytest -q` green (1080 tests); full official conformance/V11 suite unaffected (no golden-log breakage).
- **Playtest-fixes Phase 7 - records empty-state + scope filter** (landed 2026-05-29) - D5/5.1, no synthetic history. *Scope filter:* `RatifiedRecord` now carries `holder_club_id` (threaded from the career-stats club_id in `ratify_records`), and the records_ratified beat payload tags each entry with `holder_club_id` + server-computed `is_my_club`; `StructuredOffseasonBeats` renders a My Club / League toggle (defaults to My Club when the player's club holds a record, else League). *Empty-states:* the payload now carries `records_book_empty` (`len(load_league_records) == 0`), distinguishing two honest states - "the record book is empty" (no records exist league-wide yet) vs the existing "no new records were set this season" (book exists, no incumbent beaten). HONEST DEVIATION FROM D5 COPY: the spec's "history begins when your first legends retire" wording was rejected as inaccurate - `ratify_records` seeds the book from ALL active players at the first offseason, not from retirees, so the book is effectively never empty by the time the offseason beat shows; the book-empty state is the truthful message for the degenerate case. The genuinely fresh-player empty book lives on the in-season Dynasty Office records panel (left for a follow-up; out of this phase's scope). *Record trim (5.1):* dropped `career_dodges` (high-variance survival stat, undramatic) and `most_seasons_at_one_club` (loyalty trivia); kept career_eliminations, career_catches, most_championships, and all team records. Verification: `python -m pytest -q` green (1078 tests) with new tests in `test_offseason_beats`/`test_dispersed_helpers`/`test_offseason_ceremony`/`test_records` (holder_club_id + scope filter, both empty-states, trim); frontend `npm run build` + `npm run lint` clean.
- **Playtest-fixes Phase 6 - correctness cleanups + straddler logic** (landed 2026-05-29) - four contained fixes (logic only; visual redesigns stay deferred to Phase 8 per D6). *2.6 float leak:* `next_best_improvement.weakest_position_group`/`strongest_position_group` now return `avg_overall` as an int, so no raw `62.0 OVR` float leaks into the post-loss panel or season-preview copy. *2.7 new-save name collision:* the build-from-scratch flow validates save-name uniqueness on Step 1 (`IdentityStep` takes `takenNames`, blocks Next, and shows a `role="alert"` banner), and the commit error banners (new-save + build) are now visible `role="alert"` callouts instead of tiny red text (the backend already returned 409, now pinned by a `test_server_save_boundary` test). *2.4 Operational Plan green-while-misaligned:* the alignment pill no longer reflects only the staff intent verdict - it now also reads pending operational orders, and the foot "N pending" count is the operational-order count, not the unrelated readiness-gate count (which the Phase 3 gates had inflated); so the pill can no longer show green "Aligned" while orders are pending. *4.7 Policy Editor de-dup:* each category showed the selected option three times (pill + right-of-box label echo + description); the redundant right-of-box label echo is removed (the pill conveys selection, the preview describes it). Verification: `python -m pytest -q` green (1070 tests) with new tests (`test_next_best_improvement` no-float-leak, `test_server_save_boundary` 409 collision); frontend `npm run build` + `npm run lint` clean.
- **Playtest-fixes Phase 5 - growth legibility** (landed 2026-05-29) - D9, presentation only (no development-engine math changed). Makes the genuine, already-happening development visible. *Player Card:* the roster payload now carries `potential_ceiling` (numeric), `headroom` (`max(0, ceiling - OVR)`), and `projected_growth` (`growing`/`plateauing`/`declining`, derived from age vs the player's peak window and headroom); the Player detail modal shows a Growth card and `Ceiling NNN · +N room`. *Offseason Development beat:* each player row now carries `attr_deltas` (per-attribute integer deltas across all nine ratings) and `potential_ceiling`, rendered as inline ACC/POW/DOD/... chips under the composite OVR move. *Roster Lab:* season-over-season OVR trend renders a real sparkline when data exists, with an honest "appears after first offseason" empty-state otherwise. HONESTY NOTE: no per-season ratings history is stored (the DB keeps only match stats), so the trend is the latest offseason's `[before, after]` from `offseason_development_json` (overwritten yearly) rather than a fabricated multi-season series. Verification: `python -m pytest -q` green (1068 tests) with `tests/test_growth_legibility.py` (ceiling/headroom/growth present and Elite>Low, dev-beat attr_deltas correct + ints + round-trip); frontend `npm run build` clean.
- **Playtest-fixes Phase 3 - matchup legibility: favorite band + readiness** (landed 2026-05-29) - D2/D3 of the May 2026 plan, built on the Phase 1 canonical fielded-6. *D2 (favorite band):* the matchup edge headline is now the BAND - Favorite / Even Matchup / Underdog - derived from the fielded-6 net starter OVR; the signed `+NNN net starter OVR` is demoted to a small, explicitly advisory "roster strength" detail that never implies a mechanical edge (`week_briefing._build_edge` returns `headline` + `advisory_detail`; the pre-sim dashboard renders the band as the "Matchup" value with the net OVR as sub-text). *D3 (readiness):* two deliberate-action gates - `scout` and a new `confirm_lineup` - now start UNMET on a fresh weekly plan and clear only on a real action (`POST /api/command-center/scout`, `POST /api/command-center/confirm-lineup`, backed by persisted `opponent_scouted` / `lineup_confirmed` plan flags); gameplan/training/health stay default-satisfied (preserving the Balanced-default convenience), a bye week auto-clears both, saving an edited lineup auto-confirms it, and the flags survive in-week tactics saves (reset only at the start of a new week). Pre-sim dashboard surfaces Scout Opponent / Confirm Lineup buttons while the gates are pending. Verification: `python -m pytest -q` green (1055 tests) with new/updated `tests/test_week_briefing.py` (band headline + advisory, scout/confirm start-unmet-and-clear, bye auto-clear, missing-flags-default-unmet) and `tests/test_readiness_gates.py` (the actions through the real persistence path, flag survival, lineup-edit auto-confirm); frontend `npm run build` clean; live fresh-server API proof (gates start `scout:false, confirm_lineup:false`, ready-to-lock false; after the two actions both true and ready-to-lock true; headline renders as the band). The `maximized-playthrough-qa` e2e spec now scouts + confirms before locking.
- **Playtest-fixes Phase 2 - multi-week auto-pilot** (landed 2026-05-29) - fast-forward over the command-center weekly loop. `use_cases.auto_pilot_weeks` repeatedly runs the canonical `simulate_week` with `update=None`, so each skipped week reuses the persisted weekly plan and the Phase 1 canonical fielded-6 (rebuilding the default from the last intent only when no plan is saved); bye weeks advance transparently and readiness gates auto-satisfy by construction (they never block simulation). The loop runs to season-complete or an optional `max_weeks` cap, with a hard safety cap. Determinism is inherited from the seeded per-match RNG: two careers from the same `root_seed` produce identical week-by-week results and standings. New additive endpoint `POST /api/command-center/fast-forward` and a "Fast-forward Season" control on the pre-sim dashboard. Verification: `python -m pytest -q` green (1044 tests) with `tests/test_auto_pilot.py` (run-to-offseason, `max_weeks`, zero-is-noop, same-seed determinism, auto-vs-manual week-by-week parity, endpoint smoke, already-complete no-op); frontend `npm run build` clean; live fresh-server proof (loaded a compatible save, began the season, fast-forwarded 3 weeks then the remainder to `season_complete_offseason_beat` with honest per-week W/L vs named opponents).
- **Playtest-fixes Phase 0 + Phase 1** (landed 2026-05-29) - first two phases of the May 2026 playtest-fixes plan (`docs/archive/plans/2026-05-29-playtest-fixes-multi-phase-plan.md`).
  - *Phase 0 - verification hardening.* `scripts/dev-restart.ps1` makes the stale-server guard one command: it kills any process listening on the dev port, restarts the backend, waits for it to bind, and exits non-zero if the new PID matches the old. Wired into `docs/workflows/dev-server-verification.md`. The dev server can silently serve stale code, which had produced false "regressions" in playtest synthesis; every later phase's browser verification now runs against a confirmed-fresh PID.
  - *Phase 1 - canonical fielded-6 (D1).* Root cause: club creation saved the user club's `lineup_default` as raw roster order, so `_lineup_recommendation` summed the *whole* roster (uncapped) for the matchup edge while the sim fielded only the first six - a fresh club showed a FAVORITE headline over a six that got shut out. Fixes: the user club's default is now `optimize_ai_lineup` (best-by-role/OVR) at creation (`career_setup._persist_initial_lineup_default`; AI clubs keep roster order so AI-vs-AI baselines are unchanged); `command_center._lineup_recommendation` resolves the *same* `LineupResolver` path the sim uses, capped to six, with the optimized six as the no-default fallback; the manual lineup now persists across the season rollover (`offseason_ceremony._reconcile_user_lineup_default`, previously overwritten with roster order) and across rookie/free-agent signings (`_lineup_default_after_signing` keeps the manual top five and seats the recruit at slot 6 in both signing paths). Verification: `python -m pytest -q` green (1037 tests) with new regression tests (`test_canonical_fielded_six.py` - briefing<->sim parity plus a cause->effect proof that the optimized six materially out-survives and out-wins the weak six on the rec path; `test_lineup_default_rollover.py` - rollover and signing persistence); three tests that encoded the now-fixed "default == roster order" assumption were updated. Browser-verified on a fresh build-a-club career: exactly six fielded players and an honest "-84 NET OVR (UNDERDOG)" edge, no console errors. Known residual (deferred, owner's call): `_lineup_recommendation`'s "Develop Youth" intent swaps a prospect into the *briefing's* six that the sim won't field - pre-existing and conservative (understates the edge).
- **First-season decision-traceability fixes** (landed 2026-05-28) - a fresh-player playthrough exposed that several core weekly/dynasty decisions did not actually change outcomes, which silently undercuts the V14 legibility thesis (a legible recap is worthless if the decision it explains had no effect). Fixed at the root and pushed to main as six focused commits:
  - *Tactics now drive the sim and the recap.* `save_command_center_plan_payload` rebuilt the plan from the intent default on every save, so the intent-only plan-lock discarded Policy Editor edits; it now preserves the saved tactics/lineup and only re-derives from the preset when the intent actually changes. `use_cases.simulate_week` loaded `clubs` before applying the command plan, so the engine built each team from the base `coach_policy` and the locked tactics never reached the match or the post-match recap (the recap recorded the base policy, making tactical choices look meaningless); it now reloads `clubs` after the plan applications. The `Balanced` intent maps to a genuinely balanced preset instead of the conservative club default.
  - *Recruiting can sign for full rosters.* Club creation allows up to 10 players but the offseason recruiting gate required `len(roster) < 9`, so a club built at/near the creation cap was permanently locked out (`can_recruit` false -> read-only Signing Day instead of the prospect picker). A shared `offseason_presentation.MAX_USER_ROSTER = 12` now gates `can_recruit` and the recruit endpoint.
  - *Development is headroom-proportional.* Offseason growth had collapsed to a near-uniform +1 OVR (the reps signal is tiny, so the pool fell to a flat baseline that swamped potential). Base growth is now `headroom (potential - current OVR) x dev-trait rate`: high-ceiling players develop most even from a low current OVR, growth tapers to zero at the ceiling (never overshoots), and no-headroom players grow ~0 by construction - restoring the meaning of Potential Tiers and the development-focus order. Also fixed a latent `DeterministicRNG.randint` crash in the potential-upgrade branch (drawn via `choice()` now). The bye-week scout readiness gate is marked ready when there is no opponent to scout.
  - *Recruiting interest actually transfers.* `recruiting_office._class_year_from_season` returned `season + 1`, so the in-season board built interest on next year's class while the offseason signed `class_year = season_number` from a different pool - the board and the signing pool were disjoint and a season of Scout/Contact/Visit work could never sign a courted prospect. Dropped the +1 so both reference the same class.
  - *Archetype display names in player-facing copy.* The Season Preview strength/"Watch Area" and the post-loss "Shore up your <group> depth" nudge rendered raw enum keys (`hawk_dodger`, `thrower`). A new `models.archetype_display_name()` (known values -> display names, anything else passed through) is applied at those payload boundaries so players see "Ball Hawk / Dodger" / "Thrower".
  - Verification: `python -m pytest -q` green (~1000 tests) with new regression tests (`test_command_plan_lock_preserves_tactics.py`, `test_locked_plan_drives_sim_and_recap.py`, `test_recruiting_roster_cap.py`, `test_development_growth_band.py`, `test_recruiting_interest_transfer.py`, plus archetype-display assertions in `test_season_preview.py` / `test_next_best_improvement.py`); the tactics fix was additionally browser-verified end to end (locked "Patient" now renders as Patient in the debrief).
- **Rookie Run playtest polish Tasks 6-11** (landed 2026-05-27) - continued the fresh-player playtest fix plan after the P0 trust fixes. Build-from-scratch recruiting now shows a non-blocking suggested roster foundation with live Throwing/Catching/Survival coverage. Standings rows expand in place into a club-history lane instead of navigating to nowhere. Playoff command strips label the regular-season `Record` rather than recent `Form`. Weekly aftermath now surfaces honest training-impact progress and bye-week fatigue-exposure avoidance instead of defaulting to "No growth logged this week." Full replay pins a Current Event card next to the log and scrolls the active event into view. Staff pipeline rows expose an Interview action using the existing staff-hire endpoint, and no-plan command weeks now default to `Balanced` rather than silently starting `Win Now`.
- **Post-V13 final bug-blitz hardening** (landed 2026-05-24) - tightened the browser regression surface around the live polish fixes without redesigning unrelated systems. The build-from-scratch flow now uses real form associations (`htmlFor` / input ids and semantic fieldsets) so the onboarding labels are machine-readable and clickable. Playwright coverage now pins replay/result score parity from aftermath into replay, verifies the build-from-scratch identity labels are not orphaned, and checks the roster remains inside a `390x844` viewport without horizontal overflow. The V13 offseason browser smoke was corrected to accept both valid `records_ratified` paths: proof-backed record cards when records exist, and the explicit empty-state message when no new league records were set that season.
- **V13 - Broadcast and Presentation Layer** (shipped 2026-05-24) - see `docs/archive/specs/v13/2026-05-24-v13-broadcast-presentation/design.md`, `docs/archive/retrospectives/v13/2026-05-24-v13-broadcast-presentation-handoff.md`, and `docs/archive/learnings/v13/2026-05-24-v13-broadcast-presentation-learnings.md`. Added `broadcast.py` and `highlights.py` as deterministic presentation facades over existing league-memory and replay data. Matchup preview and replay header now surface structured broadcast frames, playoff matches render a distinct overlay, finished matches expose a highlight package plus proof-linked commentary inserts, and offseason `records_ratified` / `hof_induction` cards now render richer proof-backed presentation. Verification: `python -m pytest -q`, `npm run build`, `npm run lint`, and Playwright browser walks in `tests/e2e/v13_broadcast_layer.spec.ts` plus `tests/e2e/command-center-aftermath.spec.ts`. The event log remains canonical and no new engine math shipped as part of V13.
- **V12 - AI Program Managers and Rival Adaptation Loop** (shipped 2026-05-24) — see `docs/archive/specs/v12/2026-05-24-v12-ai-program-managers/design.md`. Fully integrates program archetypes, weekly plans, multi-season trajectory persistence, bounded adaptation when player's win rate >= 70%, and archetype-aware recruitment selection. Standings page renders beautiful program chips and trajectory labels; matchup preview exposes adaptation plans. Tested with a 50-season Monte Carlo sweep confirming excellent archetype championship parity.
- **O1 - Rec Driver Rebalancing** (shipped 2026-05-24) — see `docs/archive/specs/superpowers/2026-05-24-o1-rec-driver-rebalancing-design.md`. Implemented randomized tick-level team evaluation order in `_tick` and `_select_throwers` in `rec_engine.py` to eliminate 0-edge asymmetry (symmetric OVR win rate balanced perfectly at 50.9%). Replaced the flat 5% noise headshot rate with a `throw_selection_iq` modulated formula: `0.08 - 0.05 * (thrower_iq / 100.0)`. Implemented composed logistic connect contest `base ** 0.7` where `base = accuracy / (accuracy + (1.0 - dodge))`. The `test_ovr_curve_rec_driver_smoke` test has been graduated from xfail to a hard gate with a tightened floor `>= 66%` under order randomization, and a new moment-explanation test (`test_fav_losses_explained_by_moments` requiring `>= 75%` moment explanation) has been integrated.
- **Post-V11 redesign - Plan D: Simulation-health probe** (landed 2026-05-22) — see `docs/archive/specs/superpowers/2026-05-22-plan-d-simulation-health-probe-design.md`. New `tools/probe_lib.py` shares match-input construction, Wilson CIs, OVR-curve runner, and four summarizers (moments / match-length / outcomes / OVR). New `tools/tier_engine_health_probe.py` CLI prints four diagnostic sections per driver; supports `--driver {rec,official,both}` and `--trials N`. New `tests/test_engine_health.py::test_ovr_curve_rec_driver_smoke` is `xfail(strict=True)` on the O1 baseline — when the rebalancing pass lands and the assertions hold, pytest will fail the suite to force graduating the test to a hard gate. `tools/o1_variance_probe.py` deleted (subsumed). `tools/tier_1_sanity_probe.py` refactored to consume `probe_lib.make_match_input`; behavior unchanged. The Tier 1 Match Loop milestone (Plans A/B/C/D) is now complete.
- **Post-V11 redesign - Plan C: Tier 1 player-facing surface** (landed 2026-05-22) — see `docs/archive/specs/post-v11/2026-05-20-post-v11-redesign-brief/plan-c-tier1-surface.md`. `CoachPolicy` is now a five-enum v2 model (Approach / TargetFocus / CatchPosture / OpeningRushCommit / OpeningRushTarget); legacy 8-float payloads raise on load. `RecTier1Driver` consumes all four pre-match knobs (`_opening_rush`, throw-eagerness multiplier, target-focus scoring, catch-posture renormalization). `OfficialDriver` accepts v2 policy through a branch-equivalent semantic-intent mapping; V11 / USAD conformance still green. Voice modules (`voice_verdict`, `voice_aftermath`, `voice_pregame`) read `AftermathContext` + moment events and route every player-facing string through `voice_register.tier1` (Tier 1 rec-league register). Command Center renders `PolicyEditor` with full radiogroup aria + arrow-key navigation; `POST /api/tactics` accepts v2 strings and rejects legacy floats with HTTP 400; `GET /api/voice-register/{tier}` exposes the register to the frontend. `ReplayTimeline` was rewritten to render moment-aware inline beats with `LateGameBanner`, `OneVOneBanner`, and `ComebackCard`; moment events carry server-rendered `display_text` so the frontend renders fully formatted strings. `ReplaySpeedControl` replaces the old cycle button with 1x/2x/4x/instant. Playwright walk: `tests/e2e/tier1_recognition.spec.ts`. Audit-7.6 (deferred at the 2026-05-22 pre-Plan-C knockout) is implicitly resolved by the new v2 policy editor surface — the legacy float pill display is gone. Plan D is the next strict step in the post-V11 brief.
- **Pre-Plan-C knockout** (shipped 2026-05-22) — closed 11 of 12 audit-7.x bugs from the 2026-05-21 QA pass (7.6 deferred to Plan C by design) plus the rec-driver comeback heuristic (Plan A follow-up). See `docs/archive/specs/superpowers/2026-05-22-pre-plan-c-knockout-design.md` and the resolution table at the top of `docs/archive/qa/2026-05-21-browser-playthrough-audit.md`.
- **V11 - Official USA Dodgeball Rules Integration** (shipped 2026-05-19) - see `docs/specs/MILESTONES.md` and `docs/archive/specs/v11/2026-05-20-v11-official-usad-rules/design.md`. Fully integrates warning records, blue cards, and discipline states (Section 34 & 35) with a complete conformance matrix verification.
  - Career creation only: the official ruleset cannot be opted into mid-career. Existing V1-V10 saves remain on the generic ruleset.
  - Rulesets: Foam, No-Sting, and Cloth ruleset profiles are fully supported.
  - Deferred: yellow/red card tournament persistence, designated retriever realism, pinching, flight kills, injuries, interference, player collision, bracket expansion, and full administrative rules.
  - Conformance matrix reference: verified completeness of all must-have official rules in `tests/test_official_conformance_matrix.py`.
- **Post-V11 redesign - Plan A: Hybrid driver architecture + Tier 1 engine** (landed 2026-05-20, closed-out 2026-05-20 after review) - see `docs/archive/specs/post-v11/2026-05-20-post-v11-redesign-brief/plan-a-hybrid-driver.md`. New `EngineDriver` protocol with `RecTier1Driver` (Local Rec League, brief section 3.5) and `OfficialDriver` (wraps V11). New primitives: `fatigue`, `flood_throws`, `stall_timer`, and `moment_events` (six-moment contract). V11 / USAD tests still pass. Tier 1 sanity probe lives at `tools/tier_1_sanity_probe.py`. Review caught a `match_id="rt"` placeholder bug in `_mark_out` (corrupted `GassedCollapse.match_id` and catch-queue events); fixed by threading `match_id` through the runtime and pinned by a regression test in `tests/test_tier_1_integration.py::test_rec_driver_moments_carry_match_id`. Known follow-ups for Plans B/C: the rec-driver comeback heuristic is loose (about 22/25 matches; closed 2026-05-22 Task 12 of pre-Plan-C knockout) and `OfficialDriver.moment_events` is intentionally empty. Plans C/D remain queued in `tier-1-roadmap.md`.
- **Post-V11 redesign - Plan B: Player attribute v2** (landed 2026-05-20) - see `docs/archive/specs/post-v11/2026-05-20-post-v11-redesign-brief/plan-b-design.md` and `docs/archive/specs/post-v11/2026-05-20-post-v11-redesign-brief/plan-b-player-attribute-v2.md`. `PlayerRatings` now includes `catch_courage`, `throw_selection_iq`, and `conditioning_curve`. `PlayerArchetype` was rewritten to four rec-league bases plus four named hybrids, `overall_skill()` is now the five-skill mean, and behavioral identity traits surface separately through `identity_profile()`. `derive_archetype` is the single canonical assignment helper, recruitment / scouting / identity / lineup / development now consume the Plan B semantics, the rec driver reads the new attributes at three decision points, legacy V1-V11 player payloads fail loudly at load, the Tier 1 sanity probe still emits all six moment kinds, and the V11 / USAD conformance checks still pass.
- **V1-V10** - see `docs/specs/MILESTONES.md` for the per-milestone index.
- **UX Polish initiative** (three waves, 15 subplans; plan archived at `docs/archive/plans/2026-05-08-ux-polish/`). The frontend reflects it: the three-mode `MatchWeek` shell, sequenced aftermath blocks, the Roster theater view, Dynasty Office `Recruit`/`History` sub-tabs, the `voice_*` writer modules, offseason ceremony takeovers, the Build-From-Scratch new-game flow, and the rebuilt Match Replay.
- **Playoff bracket** on the Standings screen (`/api/playoffs/bracket` + `PlayoffBracket` component).
- **Browser playthrough bug fixes B1-B14** from the 2026-05-18/19 Playwright playthrough - see `docs/archive/playthrough-bug-log.md`.
- **Product-coherence-audit follow-ups - all remaining gaps closed** (2026-05-22) - the 2026-05-15 audit (`docs/archive/product-coherence-audit.md`) was reconciled, then its open items were implemented in four phases.
  - *Phase 1 - mechanical frontend:* Fix 4 restored the "Last Match" strip in the reworked `PreSimDashboard`; Fix 7 added the compact-card Elimination-Differential tooltip; E5 warmed the opponent-history fallback copy (`matchup_details.build_matchup_details`); E6 made the aftermath Advance button result-based (Bank the Result / Move On / Shake It Off).
  - *Phase 2 - Command Center depth:* Fix 2 made Dev Focus editable from the CC order pills and removed the buried Roster `DevFocusChip`; E1 rewrote `voice_aftermath.render_headline` into a margin-aware generator that references the scoreline; E2 added a deterministic season title shown in the CC header; E3 ("player to watch"), E7 ("this week's stakes"), and E9 (post-match bulletin) are frontend generators in `presimNarrative.ts`; E8 surfaced honest per-staff effect-lane summaries (`staff_market.staff_effect_summary`).
  - *Phase 3 - Fix 6:* the standings response now carries `total_weeks` / `current_week` / `playoff_spots` (`playoffs.PLAYOFF_FIELD_SIZE`), and `LeagueContext` renders a week-of-Z / playoff-cutoff callout with a games-remaining chip and a cutoff-row divider.
  - *Phase 4 - offseason:* E10 made `records_ratified` / `hof_induction` structured beat cards (`StructuredOffseasonBeats.tsx`); this also fixed a latent state-key bug where those beats and `compute_active_beats` read `offseason_records_json` / `offseason_hof_json` - keys never written - so the beats had never actually appeared. The offseason recruitment auto-pick was replaced with a full prospect-list choice panel (`RecruitmentChoice.tsx`, backed by `sign_chosen_rookie` and `available_recruitment_choices`; `sign_best_rookie` kept as the empty-pool fallback).
  - Verified: full pytest green (~795 tests), frontend `npm run build` and `npm run lint` clean. Browser smoke test (loaded a progressed save) confirmed the Command Center and Standings render cleanly with no console errors - this caught and fixed a layout regression where the two new Command Center strips became extra children of the `.command-dashboard` CSS grid (which has three fixed row tracks); the strips are now wrapped in a single flow container so the grid keeps its three children. The aftermath, offseason-beat, and recruitment-choice flows were not browser-reached (each needs a full match/season playthrough) and rest on the test-suite + build verification.

## Open Work And Known Gaps

0. **Section 4 is DONE (implemented + browser-verified 2026-06-09).** Not open
   work. Remaining are non-blocking owner-decision enhancements, not bugs:
   (a) optionally surface one moment-beat above the collapsed ReplayTimeline on
   the 4.4 Match Aftermath when a moment exists; (b) optionally elevate the 4.6
   champion card beyond its current gold + trophy framing; (c) `narrative_note`
   (overtime / seed-tiebreaker copy) renders only on contested playoff results
   and has not been browser-exercised. Out-of-scope follow-up: the same int-OVR
   `:.1f` float-leak pattern fixed in §4.1 also exists in `dynasty_office.py`,
   `replay_service.py`, and the retirements/development ceremony prose.
1. **WT-20 Official Live Rules — SHIPPED 2026-06-10 (V17 Task 2).** No
   Blocking resolution, ball lifecycle (Section 24-core forfeiture +
   retrieval), and opening rush (disclosed sim-design) are enforced by the
   official engine; the throw-clock penalty paths are honestly dispositioned
   as structurally unreachable in autonomous play (ledger note). The
   reduced-blocking resolution params that Workflow-0 left OPEN shipped as
   proposed-with-measurement sim-design, never claimed as USAD fidelity. The
   even-rung draw-texture gate landed in the same change (stall draws
   extinct; even-strength draws ~10-11%, all honest splits). See the V17
   Task 2 entry above. Remaining genuinely-open slice: entering-player
   micro-fouls (24-core SPLIT note) and rec-career rush_target wiring (V19).
2. **E2E launch-token coverage sweep — CLOSED 2026-06-09.** Every e2e spec's
   raw mutating `request.post` call now attaches the real token via
   `tests/e2e/_token.ts` (23 specs swept in the UX-pass commit). The older
   specs had silently depended on an unguarded server and failed against the
   real WT-12 guard; they now run against it.
3. **`origin/playtest-fixes-2026-05-27` branch decision.** The remote branch has
   commits not on main; make an explicit keep/delete/port decision before
   treating it as historical noise.
4. **Frontend UI/UX targets.** Product direction is desktop-first/desktop-only.
   Future frontend/design audits should treat desktop as the product target and
   mobile as optional/non-goal (see `AGENTS.md` for viewport matrix).
5. **Recruiting promises have NO UI surface (owner decision).** The V8 promise
   lane is backend-complete (`POST /api/dynasty-office/promises`, a 3-active
   cap, offseason evaluation with evidence strings in
   `dynasty_office.evaluate_season_promises`), but no frontend component
   creates or displays promises — the V8 claim "exposed through the Dynasty
   Office" is stale for the current UI. Promise results also feed nothing
   mechanical. **DECIDED 2026-06-10: revive the surface, with renamed/clear
   player-facing language** ("Promise Lane" itself failed owner comprehension)
   and a real consumer for promise results. (Found by the 2026-06-09
   adversarial QA pass — see
   `docs/fable/2026-06-09-adversarial-qa-trust-audit.md`; decision in
   `docs/fable/2026-06-10-owner-decision-log.md`.)
6. **Department orders (other than Dev Focus) are flavor-only (owner
   decision).** Six weekly orders (tactics/training/conditioning/medical/
   scouting/culture) have no mechanical consumer; the 2026-06-09 QA pass
   corrected the UI copy that claimed engine effects (injury chance, morale,
   fatigue trade-offs) and marked the term-registry entries `flavor`.
   **DECIDED 2026-06-10: wire real effects** — staff must stop being
   meaningless (`docs/fable/2026-06-10-owner-decision-log.md` §1.3).
7. **V16 Contested Offseason SHIPPED 2026-06-10** (all seven plan tasks —
   see the top Shipped entry and
   `docs/retrospectives/2026-06-10-v16-contested-offseason-retrospective.md`).
   The owner-greenlit post-V16 backlog awaits its next product-director
   sequencing pass: WT-20 (item 1 above), catch-economy retune, promises
   revival (#5), department-order effects (#6), development-ceiling
   overhaul, role/stat hookups, replay intent frames, and the
   language/dedup/no-floats passes — full dispositions in
   `docs/fable/2026-06-10-owner-decision-log.md`. One V16 tuning note for
   real playtests: a passive auto-pilot career now finishes BELOW the AI
   curve (by design — engaged play buys the edge); soften via
   `AI_OFFSEASON_SIGNINGS_PER_CLUB` / `AI_OFFSEASON_MAX_ROSTER` if needed.

## Sources Of Truth

1. `AGENTS.md` - repo rules, workflow, architecture snapshot, current facts.
2. `docs/README.md` - documentation map and reading order.
3. `docs/STATUS.md` - this file: current build state and open work.
4. `docs/specs/MILESTONES.md` - the milestone history index.
5. Source code and tests - final authority when docs and code disagree.
