# First-Hour Onboarding / Retention Review — 2026-06-09

Role: first-hour game director / onboarding designer / player-empathy tester.
Question under test: **does the game teach itself through play, or does the
player need to already understand the codebase to enjoy it?**

Method note: orientation and verification used a real prod-server browser walk
(`python -m dodgeball_sim.web_cli`, port 8000, fresh PID after backend edits)
driven through the Playwright MCP, plus normal shell/git where Pare tooling was
not suitable — raw pytest/playwright output was needed for pass/fail evidence,
so shell fallback was used for test runs and is disclosed here per `AGENTS.md`.

---

## 1. First-hour verdict

**The game largely teaches itself — the weekly loop is genuinely
self-explanatory — but the recommended "Faster Start" path shipped with a
data-level lie that sabotaged the single most important retention loop
(player development), and the replay's official-state strip spoke raw engine
enums at the player.** Both are fixed in this pass.

What already works without any tutorial (verified by playing it cold):

- The **W## Directive banner** tells the player exactly what to do next at
  every stage ("2 actions left before lock → Scout / Confirm Lineup" →
  "Ready to lock" → "Plan locked. Simulate the week when ready").
- **Readiness gates** are visible, reasoned, and clear themselves through real
  actions; Lock Plan is disabled with an honest count of what is left.
- The **aftermath** leads with an honest Primary Factor backed by proof chips
  (e.g. "Catch disparity · Catches 7-3 · +4 catch swing"), echoes the
  player's locked tactics back in plain language, and ends with two clear
  next actions (View Full Replay / Bank the Result).
- The **fast-forward dialog** is a model disclosure: it says exactly which
  decisions get auto-made and offers three explained stop points.
- The **offseason ceremony** is an 8-beat sequence with one obvious Continue
  per beat, a real interactive decision (Signing Day with slot/roster-size
  counters and an irreversibility confirm), and a Schedule Reveal that hands
  the player their reason to keep playing.
- Zero console errors across the entire first-hour flow.

## 2. Fresh-player flow tested

Full loop, played cold from the save menu (career: `Fresh Player Run`,
Aurora Sentinels, official foam, 1440x900):

1. Save menu → New Game → ruleset explanation card → Take Over a Program.
2. Season Preview → Command Center (W1) → Scout → Confirm Lineup → Policy
   Editor inspection → Lock Plan → Simulate.
3. W1 aftermath (win) → full replay (33-event log, court view, key play) →
   postgame report (5 beats) → Bank the Result.
4. W2 loop repetition check → Roster Lab inspection → fast-forward (with
   dialog) to pre-playoffs.
5. Playoff semifinal and final played manually (won the championship).
6. All 8 offseason beats, including signing a rookie and locking the class
   early (confirm dialog verified).
7. Season 2 start; re-verified the loop resets cleanly.

A second fresh career (`Fresh Player Run 3`) was created after the fixes to
verify the repaired seeding, and the original save was re-loaded to verify
legacy-save display behavior.

## 3. Biggest comprehension failures found

Ranked; categories from the audit brief.

1. **"This looks broken" + "Did my choice matter?" — takeover rosters carried
   ceilings below current OVR and developed +0.** `build_curated_roster`
   seeded `traits.potential` as `gauss(50,15)` — a legacy scale — while the
   development engine (`headroom = potential - OVR`), the recruitment
   generator (55–96), the trajectory floors, and the Roster Lab "Ceiling"
   display all treat potential as an OVR-scale ceiling. Live-save proof: 5 of
   6 Aurora starters showed "Ceil 26–49" against OVRs of 62–67, the whole
   roster read tier Raw/Low, and after the first offseason **every player's
   development delta was exactly 0** (minutes were recorded — 63–310 each —
   so it was not a stats gap; no takeover player has a trajectory row to
   rescue them). The recommended first-hour path taught: development does not
   exist. This is the same family as the V14 "dev growth uniform" finding,
   surviving on the takeover path.
2. **"What does this term mean?" / "This looks broken" — the replay's
   Official-rules strip spoke raw engine enums.** `MODE: NO_BLOCKING`,
   `BURDEN: aurora · idle · 0s`, `BALL STATES: a0:held b0:held …`,
   `RULE CALLS: 11 · 11`, with both clocks reading "00:00 left" and nothing
   explaining that the strip is a full-time snapshot.
3. **"What does this term mean?" — Key Performers chips `3K 3C Imp 26` are
   never expanded anywhere.**
4. **Interaction bug — clicking a TermTip closed it.** Hover/focus set
   `open=true`, then the click handler toggled it back off, so the natural
   "click the term to ask what it means" gesture dismissed the answer.
5. **Broken template copy — scouting tape tooltips read "a strong, not their
   hidden plan" / "a leans, not their hidden plan."**
6. **"Not enough information" (minor) — club selection offers taglines only**,
   with no signal that the choice is identity rather than difficulty (rosters
   are generated at career start from the same templates, so no strength info
   exists to show — the gap was the unstated *absence* of a difficulty stake).

Non-blocking observations logged but intentionally not changed (see §7).

## 4. Implemented improvements, by flow stage

**Entry / career creation**
- `SaveMenu.tsx`: one honest line under the Club picker — every club starts
  with a comparable six; the choice is identity/rival style, not difficulty.

**First roster read + development loop (the root fix)**
- `career_setup.py`: new `_curated_potential_ceiling` maps the existing
  potential draw onto a true OVR-scale ceiling (age-scaled headroom, vets can
  be honestly plateaued, clamp 95). Implemented as a post-hoc
  `dataclasses.replace` so the RNG stream — names, ratings, ages, the other
  traits — is byte-identical to the previous seeding. New careers only;
  existing saves keep their persisted values.
- `web_status_service.py`: the roster payload now computes the displayed
  Ceiling exactly the way the development engine consumes it —
  `max(stored potential, trajectory floor, current OVR)` — so no save (new or
  legacy) can ever display "highest projected OVR" below the OVR the player
  already holds; `potential_tier` is derived from that same number so tier,
  ceiling, and headroom tell one coherent story.
- Verified live: fresh takeover roster now reads ceilings 68–76, headroom
  2–9, Low/Mid tier mix, all "growing"; the legacy save reads plateaued vets
  at `ceiling == OVR / headroom 0 / plateauing` and the high-ceiling rookie
  correctly Elite.

**First match replay**
- `MatchReplay.tsx` Official panel: added a "FULL TIME · Official state"
  framing cell (explains the 00:00 clocks), humanized MODE
  (`no_blocking` → "No Blocking", tooltip disclosing announced-only), burden
  now shows the club display name + "throw clock idle/…" instead of
  `aurora · idle · 0s`, ball states render `A0 held` style with an
  explanatory tooltip, and rule calls show an honest grouped count
  ("248 calls · Rule 11 ×24, Rule 13 ×64, Rule 20 ×48") instead of "11 · 11".
  `index.css`: panel grid 6 → 4 columns for two even rows.

**First aftermath**
- `KeyPlayersPanel.tsx`: one quiet legend line ("K eliminations · C catches ·
  D dodges · Imp impact") plus title tooltips on every chip, including an
  honest Imp definition (match-stat score, weighted up for winners).

**Whole-surface legibility plumbing**
- `TermTip.tsx`: click now keeps the tooltip open (hover-leave/blur close;
  Escape closes), fixing the click-dismisses-answer bug on every TermTip in
  the app.
- `PreSimDashboard.tsx`: tape-confidence tooltip now reads "a strong lean /
  a moderate lean / a mixed read".

**Tests**
- New `tests/test_first_hour_growth_truth.py` (7 tests): curated ceilings
  never below OVR across all six clubs; a fresh league contains real growth
  targets; curated seeding stays deterministic; a curated young player
  actually develops across a practice offseason (cause→effect regression for
  the +0 wall); payload clamps legacy below-OVR potential; payload honors the
  STAR trajectory floor; a fresh takeover roster is not all-Raw.
- `tests/e2e/maximized-playthrough-qa.spec.ts`: retconned one stale
  assertion — it waited for the raw `CLOTH` ruleset-key leak that WT-5
  (2026-06-01) removed, a dead locator that ate the whole 30s test budget on
  clean main too (pre-existing failure family already noted in STATUS); it
  now asserts the canonical "Cloth Division" display name on the official
  panel.

## 5. Screens/pages verified (live browser, prod server, fresh PID)

Save menu (list + New Game + takeover form), Season Preview, Command Center
pre-sim (directive, gates, Policy Editor, scouting report week-1 and
with-tape), Sim Lock states (pending → ready → locked), aftermath (win),
full Match Replay (official panel before/after screenshots:
`replay-official-strip-before.png` / `replay-official-strip-after.png`,
untracked in repo root), postgame report, week-2 reset, fast-forward dialog,
playoff semifinal + final debriefs, champions banner, all 8 offseason beats,
Signing Day + Class Report + Schedule Reveal, season-2 start, Roster Lab
(new + legacy saves), Standings, Dynasty Office. Viewports: 1440x900
throughout; 1280x720 sweep over command/replay/roster/standings/dynasty —
**zero horizontal overflow, zero console errors at both sizes.**

## 6. Tests/checks run — exact status

- `python -m pytest tests -q` (full suite, e2e excluded): **PASS** (exit 0,
  two runs — once mid-pass, once after all changes; 1,278 tests collected,
  incl. the 7 new ones; see also targeted runs below).
- Targeted: `test_first_hour_growth_truth.py`, `test_growth_legibility.py`,
  `test_roster_payload.py`, `test_recruitment.py`, `test_development.py`,
  `test_development_growth_band.py` → **52 passed**; plus
  `test_canonical_fielded_six.py`, `test_lineup_default_rollover.py`,
  `test_use_cases.py`, `test_week_briefing.py`, `test_auto_pilot.py`,
  `test_offseason_ceremony.py` → **73 passed**.
- `npm run build` → **PASS** (pre-existing >500 kB chunk warning only);
  `npm run lint` → **PASS** (clean).
- Playwright e2e: `official-rules-replay` + `replay-score-parity` →
  **6/6 passed** (chromium, firefox, webkit);
  `maximized-playthrough-qa` (chromium) → **failed once on the stale CLOTH
  locator, 1/1 passed after the retcon**; all six `v15-*` legibility specs
  (TermTip consumers, chromium) → **36/36 passed**.

## 7. Remaining onboarding risks / owner-decision calls

1. **AI development symmetry (decide if the new balance needs a probe run).**
   The seed fix applies to all curated clubs, so AI rosters also gain real
   headroom and will develop over multi-season careers (symmetric with the
   player; recruits were already on the proper scale). Existing balance gates
   and the champion-parity probe tests pass, but a dedicated multi-season
   Monte Carlo (V12-style) has not been re-run this pass.
2. **Scouted estimate vs signed truth is unexplained at the moment of
   signing.** A prospect listed "65 scouted" signed at "OVR 62". Honest
   fog-of-war, but Signing Day never says "scouted = estimate." A one-line
   disclosure on the Recruitment Desk would close it.
3. **Week-1 scout reveals 0/5 tendency reads** (no tape exists yet) while a
   "New intel revealed" badge shows. The explanation paragraph below is
   honest, but the badge-next-to-0/5 still reads contradictory for a few
   seconds. Consider suppressing the badge when only pre-tape facts changed.
4. **The official replay strip is still a full-time snapshot**, not synced to
   the scrubbed event. It is now labeled as such ("FULL TIME"); making it
   live-per-event is real work (replay-state-per-tick) and an owner call.
5. **Win-only playthrough.** This pass never saw a loss aftermath, so Manager
   Lesson / honest-loss copy rests on its existing unit coverage
   (`test_manager_lesson.py`), not on a fresh browser walk.
6. **Class Brief prose is a run-on blob** ("Current roster sizes: …" all on
   one line) — cosmetic, low priority.
7. **Dev-machine save list is polluted** with probe/e2e saves that don't match
   the debug-prefix filter (`s4-bye`, `probe-save-2`, `ggrg`, …). Irrelevant
   to a real fresh install (zero saves → clean "Start New Game" empty state,
   which works), but worth a prefix-list sweep someday.

---

*Working-tree pass; no commits made. Builds on (and does not disturb) the
uncommitted 2026-06-09 trust-audit changes already in the tree.*
