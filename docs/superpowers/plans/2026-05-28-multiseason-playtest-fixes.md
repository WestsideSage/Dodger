# Multi-Season Playtest Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the trust-breaking bugs Codex surfaced across a 5-season Rain City Rockets playtest so the *next* Codex run (S6→S20) can actually evaluate dynasty depth instead of re-reporting the same surface issues. Specifically: make playoff resolution legible, give the player real lineup agency, kill score/story contradictions, surface recruiting cause→effect, and stop save-state identity from silently resetting between seasons.

**Architecture:** The findings cluster into five themes, each of which crosses the Python sim (`src/dodgeball_sim/`, authoritative truth) and the React frontend (`frontend/src/`, presentation). The dominant root cause across themes is **derived copy/UI that doesn't read from canonical state** — postgame narration runs in parallel with the resolved `MatchResult`, the bye-week header doesn't read the same week pointer as its body, the staff recommendation echoes the user's selection rather than a stored coach plan, and Season 2's intent reset suggests `coach_policy` isn't carrying forward across `advance_season()`. The plan's spine is therefore: (1) make canonical state the only source the UI is allowed to render, then (2) restore agency where it's missing (lineup editor, recruiting deltas).

**Tech Stack:** Python 3 + FastAPI web service, pytest, React + TypeScript + Vite frontend, Playwright for browser end-to-end.

**Priority tiers:**
- **P0 (Trust-breaking — block next playtest):** Tasks 1–4. Playoff resolution, lineup agency, score-vs-story consistency, season-rollover identity.
- **P1 (Recurring trust leaks):** Tasks 5–8. Bye-week header mismatch, staff-recommendation echo, recruiting opacity, signing-day table.
- **P2 (Framing & polish, raises ceiling of next playtest):** Tasks 9–12. Playoff-loss framing, championship continue, "next best improvement" panel, Season Preview, copy de-duplication.

Each task is independently committable. Do P0 in order; P1 and P2 may parallelise.

**Predecessor plans (do NOT duplicate work):**
- [2026-05-27-rookie-run-playtest-fixes.md](2026-05-27-rookie-run-playtest-fixes.md) — Season 1 findings. Several of its tasks (postgame truth, draft→roster) overlap with Task 3 below. Before starting Task 3, check which steps of that plan have shipped; this plan extends rather than replaces it.
- [2026-05-27-new-player-ux-polish.md](2026-05-27-new-player-ux-polish.md) — Shipped polish on action-bar labels, wizard badges, key-players standout. Out of scope here.

---

## Pre-work: Reproduce the multi-season scenario

The earlier rookie-run plan only needed a single-match repro. This run needs a multi-season save so Tasks 4, 7, and 9 have something to verify against.

- [ ] **Step 0.1: Capture or replay the Rain City save**

  If Codex's S5 save is accessible (check `playtest_artifacts/` and `~/.dodgeball_sim/saves/`), copy it to `playtest_artifacts/multiseason-baseline/rain-city-s5.json`.

  If not, generate a deterministic equivalent. Add a CLI flag if and only if one doesn't exist (do not invent a seed system; check `src/dodgeball_sim/career_setup.py` and `rng.py` first):

  ```bash
  python -m dodgeball_sim --autoplay-seasons 5 --club "Rain City Rockets" --seed 4242 \
    --export-save playtest_artifacts/multiseason-baseline/rain-city-s5.json
  ```

  If no autoplay hook exists, file that as a sub-issue and capture the save manually by playing through with the dev console; **do not** add an autoplay mode just for this plan (YAGNI).

- [ ] **Step 0.2: Stash baseline artifacts**

  Under `playtest_artifacts/multiseason-baseline/`:
  - `rain-city-s5.json` — save file
  - `season-2-playoff-bracket.json` — exported bracket showing the S1 0-0 semifinal
  - `season-4-final-week-screenshot.png` — the 1-week-left vs 2-to-play contradiction
  - `season-2-debrief-screenshot.png` — Defensive selected, tactic cards Aggressive

  Commit:
  ```bash
  git add playtest_artifacts/multiseason-baseline
  git commit -m "test: capture multi-season playtest baseline artifacts"
  ```

---

## P0 — Trust-breaking

### Task 1 (P0): Explicit playoff resolution — overtime, then visible tiebreaker

**Problem (Codex S1 critical #1 & #2):** Semifinal ended 0-0, game silently advanced *by seed* (confirmed at `src/dodgeball_sim/playoffs.py:100-115`), then jumped to offseason without telling the player whether Rain City was eliminated or advanced. This is the single most-cited trust break in the report.

**Files:**
- Modify: `src/dodgeball_sim/playoffs.py:87-125` (`create_final_match` — currently the silent seed fallback)
- Modify: `src/dodgeball_sim/match_lifecycle.py` (find where playoff matches resolve; add overtime hook before the seed fallback)
- Create: `src/dodgeball_sim/playoff_resolution.py` (typed `PlayoffOutcome` with `winner_id`, `loser_id`, `decided_by: Literal["regulation", "overtime", "seed_tiebreaker"]`, `narrative_note: str`)
- Modify: `frontend/src/components/standings/PlayoffBracket.tsx` (show decided-by tag)
- Create: `frontend/src/components/match-week/aftermath/PlayoffResolutionBanner.tsx`
- Test: `tests/test_playoff_resolution.py`

- [ ] **Step 1.1: Read the current resolution path**

  Open `src/dodgeball_sim/playoffs.py` and `match_lifecycle.py`. Confirm exactly where a tied playoff match resolves to a winner. The current `create_final_match` resolves the *bracket* by seed when a semifinal winner is missing, but the upstream match-result code may still be returning `winner_team_id=None`. Write findings into a working note before editing.

- [ ] **Step 1.2: Write the failing test**

  Create `tests/test_playoff_resolution.py`:

  ```python
  from dodgeball_sim.playoff_resolution import resolve_playoff_match, PlayoffOutcome
  from dodgeball_sim.sample_data import scripted_tied_semifinal

  def test_tied_semifinal_goes_to_overtime_then_seed():
      match = scripted_tied_semifinal(home_seed=4, away_seed=1, regulation_score=(0, 0))
      outcome = resolve_playoff_match(match)
      assert isinstance(outcome, PlayoffOutcome)
      # Overtime must be attempted first.
      assert outcome.decided_by in {"overtime", "seed_tiebreaker"}
      assert outcome.winner_id is not None
      assert outcome.loser_id is not None
      # If overtime also tied, the better seed (away, #1) advances and the
      # outcome explicitly says so.
      if outcome.decided_by == "seed_tiebreaker":
          assert outcome.winner_id == match.away_club_id
          assert "seed" in outcome.narrative_note.lower()
  ```

- [ ] **Step 1.3: Run test, confirm failure**

  Run: `python -m pytest tests/test_playoff_resolution.py -v`
  Expected: `ImportError` (module doesn't exist yet).

- [ ] **Step 1.4: Implement `playoff_resolution.py`**

  Create the typed outcome and a `resolve_playoff_match(match)` function. Order: regulation → one overtime period (call into existing `match_lifecycle.simulate_period` or equivalent; do **not** reimplement match sim) → if still tied, seed tiebreaker with explicit `narrative_note`.

  Keep this function pure: takes a resolved-regulation match, returns `PlayoffOutcome`. Do not couple it to the bracket; the bracket caller will translate `outcome.winner_id` into the existing `winners_by_match_id` mapping.

- [ ] **Step 1.5: Wire `create_final_match` to consume `PlayoffOutcome`**

  Replace the silent seed fallback at `playoffs.py:100-115` with a call site that already received a `PlayoffOutcome` from upstream. The bracket code should never have to invent a winner — if it gets `None` here, raise loudly. Leave the loud raise in place; it's correct behavior once Task 1 is wired end-to-end.

- [ ] **Step 1.6: Surface resolution to the frontend payload**

  Find the playoff match payload assembler (grep `playoff` in `src/dodgeball_sim/web_*.py` or `payload*.py`). Add `decided_by` and `narrative_note` to the match result DTO. Don't add new endpoints — extend the existing aftermath payload.

- [ ] **Step 1.7: Render the banner**

  Create `frontend/src/components/match-week/aftermath/PlayoffResolutionBanner.tsx`. Renders one of:
  - "Advanced to Finals — won in regulation"
  - "Advanced to Finals — won in overtime"
  - "Advanced to Finals — tiebreaker (higher seed)"
  - "Eliminated — lost in regulation/overtime/tiebreaker"

  Mount it at the top of the aftermath flow when `match.kind === "playoff"`. The component must read `decided_by` directly — no derivation from score.

- [ ] **Step 1.8: Update `PlayoffBracket.tsx`**

  Tag each completed bracket node with the decided-by mode (small chip: "OT", "Seed"). Keep it terse.

- [ ] **Step 1.9: Verify and commit**

  Run: `python -m pytest -q && cd frontend && npm run build`
  Manual check: load the multi-season baseline, replay the S1 semifinal, confirm the banner appears and the offseason transition is gated until the player clicks Continue on the banner.
  Commit: `feat(playoffs): explicit overtime + seed-tiebreaker resolution with player-facing banner`

---

### Task 2 (P0): Re-enable Lineup Editor (or show *why* it's locked)

**Problem (Codex S2, S3, S5):** Ezra Prism started S2 at 74 OVR (#7), grew to 76 OVR by S5, and was *still* benched with the Lineup Editor disabled. Confirmed at `frontend/src/components/Roster.tsx:261` — the button is hard-disabled with no tooltip. This is the strongest agency complaint across the run.

**Files:**
- Modify: `frontend/src/components/Roster.tsx:255-270`
- Audit: `src/dodgeball_sim/lineup.py`, `src/dodgeball_sim/ai_lineup.py`
- Create or modify: `frontend/src/components/lineup/LineupEditor.tsx` (check if a stub exists before creating)
- Modify: API payload for roster — extend with a writable `starter_slot` per player
- Test: `tests/test_manual_lineup.py`, `frontend/src/__tests__/LineupEditor.test.tsx`

- [ ] **Step 2.1: Decide scope (5 minutes, write the decision into the PR description)**

  Two paths. Pick one *before* writing tests:
  - **A. Ship a real editor.** Drag-or-click slot swapping for starters 1–6, validates positional constraints from `lineup.py`.
  - **B. Ship a "locked" affordance.** Keep the button disabled but show a tooltip ("Auto-lineup is on. Turn off in Settings → Coach Plan to override.") and add the toggle.

  Codex's complaint is about agency. Path A is the correct fix; Path B is acceptable only if `lineup.py` has constraints we don't yet expose. Default to A unless investigation reveals a hard blocker.

- [ ] **Step 2.2: Audit `lineup.py` for swap constraints**

  Open `src/dodgeball_sim/lineup.py` and `ai_lineup.py`. List the rules currently used to build a starting six (positional, fatigue, condition, morale). These become the editor's validation rules.

- [ ] **Step 2.3: Write the failing backend test**

  `tests/test_manual_lineup.py`:

  ```python
  from dodgeball_sim.lineup import apply_manual_lineup, LineupViolation
  from dodgeball_sim.sample_data import club_with_bench_star

  def test_manual_swap_promotes_bench_star():
      club = club_with_bench_star(bench_player_id="ezra_prism", bench_ovr=76)
      new_lineup = apply_manual_lineup(
          club,
          starters=["ezra_prism", "p2", "p3", "p4", "p5", "p6"],
      )
      assert "ezra_prism" in [p.player_id for p in new_lineup.starters]

  def test_manual_swap_with_injured_player_raises():
      club = club_with_bench_star(bench_player_id="ezra_prism", bench_ovr=76, injured=True)
      try:
          apply_manual_lineup(club, starters=["ezra_prism", "p2", "p3", "p4", "p5", "p6"])
      except LineupViolation as exc:
          assert "injured" in str(exc).lower()
      else:
          raise AssertionError("expected LineupViolation")
  ```

- [ ] **Step 2.4: Implement `apply_manual_lineup`**

  Add to `src/dodgeball_sim/lineup.py`. Reuse existing constraint checks. Returns a new `Lineup` or raises `LineupViolation` with a structured reason (`"injured"`, `"suspended"`, `"position_count"`, etc.).

- [ ] **Step 2.5: Persist manual override across weeks**

  Find where weekly lineups are recomputed (likely `match_lifecycle.py` or a weekly scheduler). If a `coach_policy.manual_lineup` slot doesn't exist, add it; AI auto-fill should fall back to it unless invalidated by injury/suspension. Surface invalidation in the next week's notice panel rather than silently reverting.

- [ ] **Step 2.6: Wire the API**

  Extend the existing roster/coach-policy payload with `manual_lineup: list[str] | null` and an endpoint or POST body to set it. Reuse the existing coach-policy mutation endpoint if one exists; do not create a parallel `/lineup` route.

- [ ] **Step 2.7: Build the React editor**

  Create `frontend/src/components/lineup/LineupEditor.tsx`. Click-to-swap UI: tap a starter slot, then tap a bench player; backend validates. Show inline error messages for `LineupViolation` reasons.

- [ ] **Step 2.8: Replace the disabled button**

  Edit `frontend/src/components/Roster.tsx:261`:

  ```tsx
  <button
    className="dm-btn"
    type="button"
    onClick={() => setLineupEditorOpen(true)}
  >
    Lineup Editor ▸
  </button>
  ```

  Remove `disabled`. Mount the editor as a modal.

- [ ] **Step 2.9: Verify and commit**

  Run: `python -m pytest -q && cd frontend && npm run build && npm run test`
  Manual: open the S5 baseline, promote Ezra Prism into the starting six, confirm he appears in the next match's match-up card and his minutes show up in the post-match.
  Commit: `feat(lineup): manual lineup editor with constraint-aware validation`

---

### Task 3 (P0): Postgame truth pass (extends rookie-run Task 1)

**Problem (Codex S2, S3, S4):** Multiple shutouts narrated as comebacks. "Down 2 and clawed it back with 0 catches" appeared on a 3-0 win. "Defensive selected" on the verdict line, "Aggressive" on the tactic cards. The rookie-run plan opened this work; this task closes it across **all** generated copy paths and **all** debrief panels, not just headlines.

**Files (extend the rookie-run plan's investigation list):**
- `src/dodgeball_sim/voice_aftermath.py`
- `src/dodgeball_sim/voice_verdict.py`
- `src/dodgeball_sim/aftermath_context.py`
- `src/dodgeball_sim/copy_quality.py`
- `src/dodgeball_sim/replay_proof.py`
- `frontend/src/components/match-week/aftermath/MatchCard.tsx`
- `frontend/src/components/match-week/aftermath/ComebackCard.tsx` (likely dead-codeable on shutouts)
- `frontend/src/components/match-week/aftermath/ReplayTimeline.tsx`

- [ ] **Step 3.1: Inventory every copy site**

  Grep `headline`, `verdict`, `comeback`, `tactic`, `plan_label`, `narrative` across both source trees. Build a table: `(source_file, what_state_it_reads, what_it_should_read)`. The "should read" column must always be a field on the final `MatchResult` or its `ReplayProof`.

- [ ] **Step 3.2: Add proof-of-truth assertions to existing tests**

  In `tests/test_postgame_truth.py` (created by the rookie-run plan; create if missing), add:

  ```python
  def test_no_comeback_copy_on_shutout():
      result = scripted_shutout_win(home_score=3, away_score=0)
      copy = build_aftermath_copy(result)
      for blob in (copy.headline, copy.body, copy.tactic_summary):
          lowered = blob.lower()
          assert "comeback" not in lowered
          assert "clawed" not in lowered
          assert "down" not in lowered or "settled down" in lowered

  def test_tactic_summary_matches_selected_plan():
      result = scripted_match(selected_plan="Defensive", final_score=(3, 0))
      copy = build_aftermath_copy(result)
      assert "defensive" in copy.tactic_summary.lower()
      assert "aggressive" not in copy.tactic_summary.lower()
  ```

- [ ] **Step 3.3: Make `ReplayProof` the only source for narrative beats**

  In `replay_proof.py`, expose a typed `NarrativeBeats` containing: `was_shutout`, `largest_deficit`, `lead_changes`, `selected_plan_label`, `actual_plan_executed`. Every copy function must take a `NarrativeBeats` instead of free-form match state. Refactor each generator in the table from Step 3.1.

- [ ] **Step 3.4: Delete or gate comeback copy**

  `ComebackCard.tsx` must early-return `null` if `largest_deficit === 0`. Same for any "clawed back"/"so close" generator branch.

- [ ] **Step 3.5: Fix "Target —" rendering**

  Grep `Target -` and `Target —` across frontend. The rookie-run plan covered this for replay events; verify it's also fixed in the tactical read panel. If still present, write `"no legal target"` or suppress the event entirely.

- [ ] **Step 3.6: Verify and commit**

  Run: `python -m pytest tests/test_postgame_truth.py -v`
  Manual: replay the S3 W5 match (Defensive selected, Aggressive cards) on the baseline save, confirm tactic summary now matches selection.
  Commit: `fix(aftermath): derive all narrative copy from ReplayProof beats; no contradictions on shutouts`

---

### Task 4 (P0): Season rollover preserves coach identity

**Problem (Codex S2):** Last year's Aggressive identity — which drove the S1 playoff run — silently reset to Balanced at S2 W1. This is the same bug-class as the staff recommendation echo (Task 6): UI/state isn't reading the persisted coach policy.

**Files:**
- `src/dodgeball_sim/coach_policy.py` (or wherever the 8-field `CoachPolicy` lives — `AGENTS.md` confirms it exists)
- `src/dodgeball_sim/offseason.py` / `season_lifecycle.py` — wherever `advance_season()` lives
- `src/dodgeball_sim/save_service.py`
- `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`
- Test: `tests/test_season_rollover.py`

- [ ] **Step 4.1: Find `advance_season` and read what it preserves**

  Grep `advance_season` and `next_season`. List, in a note, every field that's reset vs preserved. The 8-field `CoachPolicy` should be in the "preserved" column.

- [ ] **Step 4.2: Write the failing test**

  ```python
  def test_coach_policy_persists_across_season_rollover():
      career = career_with_aggressive_identity()
      assert career.coach_policy.tactic == "aggressive"
      career = advance_season(career)
      assert career.coach_policy.tactic == "aggressive", "Coach identity must carry over"
  ```

- [ ] **Step 4.3: Fix the rollover**

  Remove the default reset. If the reset was intentional (e.g., for a "fresh start" feature), gate it behind an explicit user action in the offseason ceremony — not a silent default.

- [ ] **Step 4.4: Verify and commit**

  Run: `python -m pytest tests/test_season_rollover.py -v`
  Manual: load S5 baseline, advance one season, confirm coach plan UI shows the prior identity (not Balanced).
  Commit: `fix(season): preserve CoachPolicy across season rollover`

---

## P1 — Recurring trust leaks

### Task 5 (P1): Single source for current-week header and body

**Problem (Codex S1, S2, S4):** Bye-week banner says Week 03 while the bye card says W02. Season 4 standings said "1 week left, 1-2-1" while Command Center said "2 to play, 1-3". Every occurrence is a header reading a different week pointer than the body.

**Files:**
- Audit: `frontend/src/state/` (Redux/Zustand store — find the week selector)
- Modify: `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`
- Modify: `frontend/src/components/standings/*.tsx`
- Modify: `frontend/src/components/ceremonies/Ceremonies.tsx` (grep already shows `bye.{0,10}week` here)

- [ ] **Step 5.1: Find every `currentWeek` / `week` source**

  Grep all reads. Expect to find at least two: a store selector and a payload-embedded copy. Pick the store selector as canonical.

- [ ] **Step 5.2: Replace local week reads with the canonical selector**

  In each component above, replace direct `props.week` reads with `useCurrentWeek()` (create the hook if needed; reuse if it exists).

- [ ] **Step 5.3: Add a snapshot/regression test**

  In `frontend/src/__tests__/`, add a test that mounts the command center, standings widget, and bye-week ceremony with the same store and asserts they all render the same week label.

- [ ] **Step 5.4: Rename "POSTGAME REPORT" → "BYE WEEK REPORT" on bye weeks**

  Find the header in `Ceremonies.tsx`. Condition on `weekKind === "bye"`.

- [ ] **Step 5.5: Verify and commit**

  Run: `cd frontend && npm run build && npm run test`
  Commit: `fix(week): all surfaces read week from a single store selector; bye-week header renamed`

---

### Task 6 (P1): Staff recommendation reads coach-stored plan, not user selection

**Problem (Codex S3):** "Keep current plan" follows whatever the user just selected, which is meaningless feedback. The recommendation should reflect a *staff-computed* recommendation that exists independently of the selection.

**Files:**
- `src/dodgeball_sim/coach_policy.py` or `ai_coach.py`
- API payload assembler for the pre-sim dashboard
- `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`

- [ ] **Step 6.1: Find the recommendation source**

  Grep `recommend`, `keep current plan`. Confirm whether the recommendation is generated server-side or in the frontend from `selectedPlan`.

- [ ] **Step 6.2: Add a server-side `staff_recommendation` field**

  Compute it from recent results + opponent (this likely already exists in some form). Always return it. The frontend must render that field, never derive from `selectedPlan`.

- [ ] **Step 6.3: Add a test**

  ```python
  def test_staff_recommendation_independent_of_selection():
      ctx = pre_sim_context(recent_results=["L", "L"], selected_plan="defensive")
      rec = compute_staff_recommendation(ctx)
      # After two losses on Defensive, staff should suggest a change, not "Keep".
      assert rec.action != "keep"
      ctx2 = pre_sim_context(recent_results=["L", "L"], selected_plan="aggressive")
      rec2 = compute_staff_recommendation(ctx2)
      # Recommendation must depend on context, not on selection.
      assert rec2 == rec
  ```

- [ ] **Step 6.4: Verify and commit**

  Commit: `fix(coach): staff recommendation is context-derived, not a mirror of the user's selection`

---

### Task 7 (P1): Recruiting action → effect deltas

**Problem (Codex every season):** Actions change labels but show no payoff. Codex couldn't tell whether Scout, Contact, Visit did anything. By S5 this had eroded all trust in the recruiting subsystem.

**Files:**
- `src/dodgeball_sim/recruitment.py`, `recruiting_office.py`, `recruitment_domain.py`
- Audit: where prospect interest / range / odds are stored
- Frontend: find the recruiting office screen (grep `recruiting` under `frontend/src/components/`)

- [ ] **Step 7.1: Confirm what each action mutates**

  Open the three recruitment files and tabulate: `(action, what_it_changes, by_how_much)`. If Scout doesn't visibly narrow the OVR range, either (a) it isn't actually narrowing it, or (b) the narrowing isn't surfaced to the payload. Determine which.

- [ ] **Step 7.2: Expose pre/post deltas in the API**

  After each action, return a `RecruitingActionResult` with `before` and `after` snapshots (interest %, OVR range, signing odds, next-step suggestion).

- [ ] **Step 7.3: Render deltas inline**

  In the recruiting office UI, replace "Scouted" / "Contacted" labels with toast-style deltas: `"Scout → OVR range 68–82 → 71–77"`, `"Visit → Interest 35% → 52%"`.

- [ ] **Step 7.4: Test**

  Backend test that each action produces a non-trivial delta in at least one tracked field on the average case. If any action produces no delta, that's the *real* bug — fix the sim, not the UI.

- [ ] **Step 7.5: Verify and commit**

  Commit: `feat(recruiting): surface action → effect deltas (interest, range, odds)`

---

### Task 8 (P1): Signing Day result table

**Problem (Codex S2, S3):** Signing Day is a dense paragraph that never links Rain City's actions to outcomes.

**Files:**
- `src/dodgeball_sim/signing_day_payload.py` (already exists)
- Frontend: signing day ceremony component (grep `signing` under `frontend/src/components/ceremonies/`)

- [ ] **Step 8.1: Extend the payload**

  For each prospect Rain City touched, return: `target_name`, `actions_taken: list[str]`, `result: "signed" | "lost" | "withdrew"`, `signed_by: club_id`, `reason: str`. Reason should be a short structured string ("higher interest", "better facilities fit", "you outbid them").

- [ ] **Step 8.2: Render as a table**

  Replace the prose block with a five-column table. Sort signed → lost → withdrew. Highlight the row(s) that went to Rain City.

- [ ] **Step 8.3: Verify and commit**

  Commit: `feat(signing-day): structured recruit-result table replaces prose block`

---

## P2 — Framing & polish

### Task 9 (P2): Playoff-loss framing screen

**Problem (Codex S3):** Elimination jumps straight to the regular-season recap. Big emotional moment, wasted. Pair-fix with Task 1 — Task 1 makes the *resolution* legible; this makes the *defeat* feel like a defeat.

- [ ] **Step 9.1: Add an `EliminationCeremony` component**

  Mount between the final playoff match's aftermath and the regular-season recap. One screen: opponent, final score, "What ended your run" (the `decided_by` from Task 1), top three contributing players, one-line look-ahead ("Returns next season: …, …, …"). Player must click Continue.

- [ ] **Step 9.2: Commit**

  Commit: `feat(playoffs): elimination ceremony before season recap`

---

### Task 10 (P2): Championship payoff timing

**Problem (Codex S2):** Title win required an extra Continue before the celebration; the immediate final-game debrief undersold it.

- [ ] **Step 10.1: Audit the final-game ceremony order**

  Find the championship ceremony component. Confirm whether the celebration screen renders *before* or *after* the standard debrief. Reorder so the celebration is the first screen the player sees on a title-clinching win.

- [ ] **Step 10.2: Commit**

  Commit: `fix(championship): celebration ceremony precedes standard debrief on title-clinching win`

---

### Task 11 (P2): "Next best improvement" panel after losses

**Problem (Codex S1):** After a tough loss, no clear next step. This is a low-cost win: the data already exists.

- [ ] **Step 11.1: Compute the panel**

  After each loss, surface the top three actionable suggestions: weakest position group, lowest-condition starter, lowest-interest critical recruit. Pull from existing systems; don't invent new scoring.

- [ ] **Step 11.2: Render on the aftermath screen for losses only**

  Commit: `feat(aftermath): next-best-improvement panel on loss screens`

---

### Task 12 (P2): Season Preview screen on W1

**Problem (Codex S1):** Season length, playoff cut, top goal not taught up front. The dynasty matters; the structure was opaque to a new player for 3-4 weeks.

- [ ] **Step 12.1: Build a one-screen preview**

  W1 only. Render: schedule length, bye-week placement, playoff cut line (top N), this-season top goal (from `coach_policy` or career arc), one strength + one weakness from the roster.

- [ ] **Step 12.2: Add a "Skip preview" preference**

  Returning players don't need it every season. Persist in coach policy or settings.

- [ ] **Step 12.3: Commit**

  Commit: `feat(season): W1 Season Preview screen explaining structure and goal`

---

## Cross-cutting polish (do alongside P2 or fold into the relevant task)

- [ ] **De-duplicate canned phrases.** Grep `leaves no room for excuses` and similar. Tag each generator branch with a `mood: "win" | "loss"` and split the pool. This is one PR.
- [ ] **Drop "1 to play" reuse in playoffs.** Grep `1 to play`. Playoff weeks must say "Semifinal" / "Final", not regular-season cadence copy.

---

## Final verification (before declaring this plan done)

- [ ] Run full Python suite: `python -m pytest -q`
- [ ] Run frontend build + tests: `cd frontend && npm run build && npm run test`
- [ ] Manual replay against `playtest_artifacts/multiseason-baseline/rain-city-s5.json`:
  - S1 semifinal now ends with an explicit overtime/tiebreaker banner
  - Ezra Prism can be promoted into the starting six
  - S3 W5 debrief shows "Defensive" everywhere (no Aggressive contradiction)
  - S2 W1 shows Aggressive identity, not Balanced
  - Bye-week header and body agree on the week number
  - Recruiting actions show deltas, Signing Day shows a table
- [ ] Hand the updated build back to Codex with the multi-season save and instructions to resume at S6. The next playtest report should *not* surface any of the bugs above.

---

## Scope notes — what this plan deliberately does NOT cover

- **Lunar Syndicate as rival.** Codex flagged this as the strongest positive emergent behavior in S5. Do not touch it. Any "rivalry system" work belongs in a separate plan after S6-S20 data confirms it generalizes.
- **Fatigue/condition legibility.** Codex called it "promised, not legible" — real signal, but designing the legibility pass needs more data than a 5-season run. Defer.
- **Awards/development screens.** Codex called them "promising." Don't refactor what's working.
- **20-season completion itself.** The goal of *this* plan is to let the next Codex run *reach* S20 by removing trust breaks. The plan is done when the next playtest report doesn't repeat any P0/P1 finding from the first.
