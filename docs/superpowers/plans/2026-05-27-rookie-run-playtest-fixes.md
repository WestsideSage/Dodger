# Rookie Run Playtest Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address the 10 bugs / UX problems from the Codex "Rookie Run" playtest so a fresh player can complete Season 1 without the simulation contradicting itself, and so the systems the player invests in (recruiting, draft, weekly development) feel responsive.

**Architecture:** Fixes split across (1) the Python sim/web service (`src/dodgeball_sim/`) that generates the authoritative truth (scores, replay facts, recruiting state, roster identity) and (2) the React frontend (`frontend/src/`) that renders that truth. The single biggest theme — *postgame copy contradicting the actual game* — gets a dedicated "truth pass" task that gates everything else: copy must be derived from the verified match result + replay log, not generated independently. Other tasks restore state continuity (draft → roster, recruiting actions → state, weekly dev → eventual growth) and tighten clearly broken interactions (clickable standings rows, replay highlighting).

**Tech Stack:** Python 3 + FastAPI/Flask-style web service, pytest, React + TypeScript + Vite frontend, Playwright for end-to-end.

**Priority tiers:**
- **P0 (Trust-breaking, Major):** Tasks 1–4. Ship before next playtest.
- **P1 (Continuity, Minor):** Tasks 5–8.
- **P2 (Polish):** Tasks 9–11.

Each task is independently committable. Do them in order within a tier; tiers can be parallelised across worktrees if needed.

---

## Pre-work: Reproduce and capture baseline

- [ ] **Step 0.1: Reproduce the playtest scenario**

  Run: `python -m dodgeball_sim`
  Create a new career with deterministic seed if possible (check `src/dodgeball_sim/rng.py` and `career_setup.py` for a `--seed` or env-var hook). If no seed hook exists, file a TODO note in this plan — don't add one as part of this task.
  Play one match, capture the postgame screen, and save the match's underlying `MatchResult` + replay JSON from `playtest_artifacts/` or by exporting via the save service.

- [ ] **Step 0.2: Stash the baseline artifacts**

  Save under `playtest_artifacts/rookie-run-baseline/` so later tasks can diff against it:
  - `match_result.json`
  - `replay.json`
  - `postgame_screenshot.png`
  - `roster_after_draft.json`

  Commit:
  ```bash
  git add playtest_artifacts/rookie-run-baseline
  git commit -m "test: capture rookie-run baseline artifacts for playtest-fix plan"
  ```

---

## Task 1 (P0): Single source of truth for postgame copy

**Problem (Codex bug #1 & #2):** Postgame headlines and loss copy contradict the actual final score and replay facts ("Win" / "So close" shown on a 0–5 blowout).

**Root cause hypothesis:** Postgame headline/aftermath copy is generated from a separate code path (e.g., narrative voice modules) rather than reading directly from the canonical `MatchResult` after the match has been fully resolved. The two paths can disagree if the narrative branch uses pre-resolution state (intent, projection, mid-match score).

**Files (investigation list — open each before editing):**
- `src/dodgeball_sim/voice_aftermath.py`
- `src/dodgeball_sim/voice_verdict.py`
- `src/dodgeball_sim/aftermath_context.py`
- `src/dodgeball_sim/copy_quality.py`
- `src/dodgeball_sim/match_lifecycle.py`
- `src/dodgeball_sim/replay_proof.py`
- `frontend/src/components/match-week/aftermath/Headline.tsx`
- `frontend/src/components/match-week/aftermath/MatchScoreHero.tsx`
- `frontend/src/components/match-week/aftermath/ComebackCard.tsx`

- [ ] **Step 1.1: Identify every input to postgame copy**

  Grep for uses of `headline`, `verdict`, `aftermath`, and `winner` across `src/dodgeball_sim/`. List, in a working note, every function that returns or composes postgame copy and what it reads. Look specifically for any place that uses projected/intended outcome rather than the final `MatchResult`.

- [ ] **Step 1.2: Write a failing test for "headline must match final score"**

  Create `tests/test_postgame_truth.py`:

  ```python
  import pytest
  from dodgeball_sim.match_lifecycle import resolve_match
  from dodgeball_sim.voice_aftermath import build_aftermath_copy
  from dodgeball_sim.sample_data import scripted_blowout_loss

  def test_aftermath_copy_matches_final_score_on_blowout_loss():
      result = scripted_blowout_loss(home_score=0, away_score=5)
      copy = build_aftermath_copy(result)
      assert copy.winner_team_id == result.winner_team_id
      assert "win" not in copy.headline.lower() or copy.headline.lower().startswith("opponent")
      assert "so close" not in copy.headline.lower()
      assert copy.player_score == 0
      assert copy.opponent_score == 5
  ```

  If `scripted_blowout_loss` doesn't exist in `sample_data.py`, add it as a deterministic factory that builds a fully resolved `MatchResult` with the given score.

- [ ] **Step 1.3: Run the test — confirm it fails**

  Run: `python -m pytest tests/test_postgame_truth.py -v`
  Expected: FAIL (either signature mismatch or copy contains "win"/"so close").

- [ ] **Step 1.4: Make `build_aftermath_copy` derive every field from `MatchResult`**

  In `voice_aftermath.py` (and any helper in `aftermath_context.py`):
  - Take a `MatchResult` (already resolved) as the single input.
  - Derive `winner_team_id`, `player_team_score`, `opponent_score`, `margin`, `survivor_diff`, `comeback_state` directly from result fields — no recomputation, no consulting in-progress state.
  - Branch headlines by margin sign and magnitude only after asserting consistency with `result.winner_team_id`.

- [ ] **Step 1.5: Run the test — confirm it passes**

  Run: `python -m pytest tests/test_postgame_truth.py -v`
  Expected: PASS.

- [ ] **Step 1.6: Add a contract check on the way out**

  In `match_lifecycle.py` (or wherever the API surface assembles the postgame payload), before returning, assert:

  ```python
  assert payload.headline.player_score == result.player_score
  assert payload.headline.opponent_score == result.opponent_score
  assert payload.headline.winner_team_id == result.winner_team_id
  ```

  These are cheap invariants and will hard-fail in tests if any future copy generator drifts.

- [ ] **Step 1.7: Commit**

  ```bash
  git add src/dodgeball_sim/voice_aftermath.py src/dodgeball_sim/aftermath_context.py src/dodgeball_sim/match_lifecycle.py src/dodgeball_sim/sample_data.py tests/test_postgame_truth.py
  git commit -m "fix(postgame): derive aftermath copy from resolved MatchResult only"
  ```

---

## Task 2 (P0): Postgame validation pass

**Problem (Codex fix #2):** Even with Task 1, future regressions are likely. We need a single validator the API runs before returning postgame data.

**Files:**
- Create: `src/dodgeball_sim/postgame_validator.py`
- Modify: `src/dodgeball_sim/match_lifecycle.py` (or whichever module is the API exit point for postgame — verify by grepping for the route that returns aftermath)
- Test: `tests/test_postgame_validator.py`

- [ ] **Step 2.1: Write the failing test for the validator**

  ```python
  from dodgeball_sim.postgame_validator import validate_postgame_payload, PostgameTruthError
  import pytest

  def test_validator_rejects_winner_mismatch(sample_payload):
      sample_payload.headline.winner_team_id = "wrong-team"
      with pytest.raises(PostgameTruthError):
          validate_postgame_payload(sample_payload, sample_payload.result)

  def test_validator_rejects_survivor_mismatch(sample_payload):
      sample_payload.survivor_summary.player_survivors = 99
      with pytest.raises(PostgameTruthError):
          validate_postgame_payload(sample_payload, sample_payload.result)

  def test_validator_rejects_catch_count_mismatch(sample_payload):
      sample_payload.key_players[0].catches = sample_payload.key_players[0].catches + 1
      with pytest.raises(PostgameTruthError):
          validate_postgame_payload(sample_payload, sample_payload.result)
  ```

  Fixture `sample_payload` builds a known-good payload from a deterministic match.

- [ ] **Step 2.2: Run — confirm fails**

  Run: `python -m pytest tests/test_postgame_validator.py -v`
  Expected: FAIL (module not found).

- [ ] **Step 2.3: Implement `postgame_validator.py`**

  Validate: winner team id, both scores, survivor differential, comeback state flag, each `key_player.catches` sums to ≤ replay catch events for that player. Raise `PostgameTruthError` on any mismatch with a message naming the field and both values.

- [ ] **Step 2.4: Wire validator into the API exit point**

  In `match_lifecycle.py` (or the FastAPI/route handler), call `validate_postgame_payload(payload, match_result)` before returning. On failure: log loudly and return a degraded but truthful payload (raw score only, no headline copy) rather than the lie. Add a test for the degraded path.

- [ ] **Step 2.5: Run tests, commit**

  ```bash
  python -m pytest tests/test_postgame_validator.py tests/test_postgame_truth.py -v
  git add src/dodgeball_sim/postgame_validator.py src/dodgeball_sim/match_lifecycle.py tests/test_postgame_validator.py
  git commit -m "feat(postgame): add validation pass to catch copy/result drift"
  ```

---

## Task 3 (P0): Founding roster identity continuity

**Problem (Codex bug #3):** Founding-draft picks (names, roles, ratings) don't clearly carry into the post-draft roster screen. Either the data is being rewritten between draft and persistence, or the two screens use different display strings.

**Files (investigate first):**
- `src/dodgeball_sim/career_setup.py`
- `src/dodgeball_sim/franchise.py`
- `src/dodgeball_sim/identity.py`
- `src/dodgeball_sim/archetype_derivation.py`
- `frontend/src/components/new-game/StartingRecruitmentStep.tsx`
- `frontend/src/components/roster/PlayerCompactRow.tsx`
- `frontend/src/components/roster/PlayerTheaterRow.tsx`

- [ ] **Step 3.1: Diff the draft payload vs the roster payload**

  Using the captured baseline (`playtest_artifacts/rookie-run-baseline/roster_after_draft.json`) and a fresh capture of the draft-step state, compare per-player: `display_name`, `primary_role`, `overall_rating`, `archetype`. Note exactly which fields differ and where.

- [ ] **Step 3.2: Write a regression test**

  `tests/test_founding_roster_continuity.py`:
  ```python
  def test_drafted_players_appear_unchanged_on_roster():
      career = build_career_with_drafted_roster(seed=42)
      drafted = career.draft_snapshot.players
      on_roster = career.team.roster
      assert len(drafted) == len(on_roster)
      for d in drafted:
          match = next(p for p in on_roster if p.player_id == d.player_id)
          assert match.display_name == d.display_name
          assert match.primary_role == d.primary_role
          assert match.overall_rating == d.overall_rating
          assert match.archetype == d.archetype
  ```

- [ ] **Step 3.3: Run, confirm fail**

- [ ] **Step 3.4: Fix root cause**

  Likely fixes (pick based on Step 3.1 findings):
  - If archetype is re-derived after draft, persist the draft-time archetype rather than re-running derivation.
  - If display names get reformatted (e.g., "First Last" vs "Last, First"), pick one and have a single formatter the roster row and draft row both call.
  - If role uses a different vocabulary on the two screens (e.g., "Catcher" vs "Defender"), normalise via a shared enum + `format_role()` helper.

- [ ] **Step 3.5: Frontend: shared display helper**

  Create `frontend/src/components/roster/playerDisplay.ts` with `formatPlayerName(p)`, `formatRole(p)`, `formatOverall(p)`. Use these in both `StartingRecruitmentStep.tsx` and `PlayerCompactRow.tsx` / `PlayerTheaterRow.tsx`. Delete any inline formatting.

- [ ] **Step 3.6: Run all tests, commit**

  ```bash
  python -m pytest -q
  npm --prefix frontend run build
  git add -A
  git commit -m "fix(roster): draft and roster screens share player display + persistence"
  ```

---

## Task 4 (P0): Recruiting state visibility (badges)

**Problem (Codex bug #4 & fix #4):** "Contact" and "Visit" actions don't appear to persist — no visible badge changes the player's card.

**Files (investigate):**
- `src/dodgeball_sim/recruiting_office.py`
- `src/dodgeball_sim/recruitment.py`
- `src/dodgeball_sim/recruitment_domain.py`
- `src/dodgeball_sim/scouting_center.py`
- Frontend — grep for "recruit" / "prospect" under `frontend/src/components/` and `frontend/src/features/`

- [ ] **Step 4.1: Confirm whether the backend is actually persisting the action**

  Write a Python test: call the "contact prospect" use case, then re-load the career, then read the prospect. Assert `prospect.interactions[-1].kind == "contact"` (or whatever the canonical structure is).

  If this passes, the bug is purely frontend display. If it fails, fix the persistence first.

- [ ] **Step 4.2: Define a canonical recruiting state enum**

  In `recruitment_domain.py`, ensure a single `RecruitingStatus` (or equivalent) value per prospect with at least: `UNSCOUTED`, `SCOUTED`, `CONTACTED`, `VISITED`, `INTERESTED`, `LOCKED_OUT`. Derive from interaction history if not stored directly.

- [ ] **Step 4.3: Surface status in the API**

  Whichever endpoint feeds the recruiting screen, include `status` and `last_interaction_at` per prospect.

- [ ] **Step 4.4: Frontend: badge component**

  Create `frontend/src/components/dynasty/RecruitingBadge.tsx` (or co-locate in the recruiting component) that renders status as a labeled pill with distinct colors. Render it on every prospect row.

- [ ] **Step 4.5: Frontend: optimistic update**

  When the user clicks Contact/Visit, immediately update the local state to the new status and re-fetch. Show a tiny inline spinner so the action visibly registers.

- [ ] **Step 4.6: Playwright smoke test**

  Extend an existing Playwright test (see `playwright.config.ts`, `run_playwright_test.mjs`) to: open recruiting, contact a prospect, assert the badge text changes to "Contacted" within 2s, reload, assert badge persists.

- [ ] **Step 4.7: Commit**

  ```bash
  git commit -am "feat(recruiting): visible badges + persisted state for prospect actions"
  ```

---

## Task 5 (P1): Signing Day payoff

**Problem (Codex bug #5 & fix #5):** Signing Day is dense text; it doesn't pay off the recruiting choices the user made.

**Files:**
- `src/dodgeball_sim/offseason_ceremony.py`
- `src/dodgeball_sim/offseason_presentation.py`
- `frontend/src/components/ceremonies/` (verify path; grep for "signing")

- [ ] **Step 5.1: Build the signing-day payload model**

  Each signing card shows: prospect name, the user's club, prospect OVR, the user's interaction history with this prospect (contact count, visits, scouting), and a one-line reason ("Signed because of repeated visits" / "Lost to <Rival> after no contact"). This is computed in `offseason_presentation.py` from `recruitment` offseason state.

- [ ] **Step 5.2: Replace text blob with a card grid in the frontend**

  Card per prospect. Filters for "My signings", "Rival signings", "Surprises". Empty state when there are zero prospects (don't fake content).

- [ ] **Step 5.3: Add a sort-by "OVR" / "Drama" toggle**

  Drama score = `abs(predicted_landing_school - actual_landing_school)` or similar. Keep it simple.

- [ ] **Step 5.4: Test + commit.**

---

## Task 6 (P1): First-roster guidance hint

**Problem (Codex fix #6):** Fresh players don't know why 6 vs 10 founder picks matters or what role balance to aim for.

**Files:**
- `frontend/src/components/new-game/StartingRecruitmentStep.tsx`

- [ ] **Step 6.1: Add a small "Recommended composition" sidebar**

  Static guidance (no AI): "Aim for 2 Catchers, 3 Throwers, 1 Defender" or whatever the docs say is canonical. Pull from `docs/specs/` if numbers are defined there; otherwise ask Maurice for the canonical numbers before hardcoding.

- [ ] **Step 6.2: Live tally**

  As the user picks, show running counts vs recommended.

- [ ] **Step 6.3: Don't block submission on imbalance.** Just warn.

- [ ] **Step 6.4: Commit.**

---

## Task 7 (P1): Clickable standings rows actually open something

**Problem (Codex bug #6):** UI tells the user to click rows; nothing happens.

**Files:**
- `frontend/src/components/standings/` and wherever the standings table lives (grep `Standings`)

- [ ] **Step 7.1: Decide the destination**

  Either:
  - (a) inline expand: click row → drop down with last 5 matches + season record vs this club, or
  - (b) modal/drawer to a "Club History" view.

  (a) is cheaper and matches the "history lane" wording in the report.

- [ ] **Step 7.2: Implement (a), with visible affordance**

  Row gets `cursor-pointer`, hover state, a chevron icon, and `aria-expanded`. On click, fetch (or use already-loaded data) the head-to-head and recent results.

- [ ] **Step 7.3: Remove the "click for history" hint** if no destination is ready in time — don't promise what isn't built.

- [ ] **Step 7.4: Playwright assertion + commit.**

---

## Task 8 (P1): Form/record continuity in playoff cards

**Problem (Codex bug #7):** Semifinal card shows "Form 3-2" after a 4-2 regular season.

**Files:**
- `src/dodgeball_sim/playoffs.py`
- `src/dodgeball_sim/analysis.py` (form computation likely here — verify)
- Frontend playoff bracket component

- [ ] **Step 8.1: Identify what "Form" means**

  Grep for `form` in `src/dodgeball_sim/`. Is it last-5 only? Last-5 weighted? Does it exclude byes? Whatever it is, document the definition in a docstring on the function that returns it.

- [ ] **Step 8.2: Match the definition to what the card claims**

  If the card says "Form" but really means "last 5 games", relabel. If the card means "season record", show the season record.

- [ ] **Step 8.3: Regression test that compares the rendered form string against the season record for a known fixture. Commit.**

---

## Task 9 (P2): Weekly development micro-feedback

**Problem (Codex bug #8 / fix #8):** "No growth logged this week" deflates the player every week; payoff happens in offseason.

**Files:**
- `src/dodgeball_sim/development.py`
- `src/dodgeball_sim/command_week_service.py`
- Frontend command center + weekly checklist components

- [ ] **Step 9.1: Surface incremental progress**

  Even when no skill ticked up, show the focus's "progress toward next tick" as a thin bar or "+1 unit toward Throwing growth" caption. Read from whatever counter `development.py` already maintains; if no counter exists, add one (commit-sized change) before the UI work.

- [ ] **Step 9.2: Recovery/fatigue feedback on bye weeks** — small line per player who recovered fatigue.

- [ ] **Step 9.3: Commit.**

---

## Task 10 (P2): Replay key-play highlighting

**Problem (Codex bug #9 / fix #9):** The replay log doesn't visually pin the current event next to the court.

**Files:**
- `frontend/src/features/replay/MatchHighlights.tsx`
- `frontend/src/components/match-week/aftermath/ReplayTimeline.tsx`

- [ ] **Step 10.1: Strong selected-row style on the log** — left border, accent background, smooth scroll-into-view when the playhead advances.

- [ ] **Step 10.2: Pinned "Current Event" card** to the right of the court showing the current event's actors, outcome, and resulting score delta.

- [ ] **Step 10.3: Commit.**

---

## Task 11 (P2): Staff interview affordance + season-default reconsideration

**Problem (Codex bug #10 / fix #10):** Staff candidates show "interview" as passive text. Also: new seasons default to Aggressive while the UI recommends Defensive.

**Files (investigate):**
- `src/dodgeball_sim/staff_market.py`
- `src/dodgeball_sim/ai_program_manager.py` (season defaults likely here or in `command_week_service.py`)
- Frontend staff component (grep `staff`)

- [ ] **Step 11.1: Make "Interview" a button** with clear state (Available / Scheduled / Completed).

- [ ] **Step 11.2: Reconcile the season default**

  Either change the default to Defensive (to match the recommendation), or stop recommending Defensive in the UI. Pick whichever matches the design intent in `docs/specs/MILESTONES.md` — don't guess. If unclear, ask Maurice before changing.

- [ ] **Step 11.3: Commit.**

---

## Final verification

- [ ] **Step F.1: Full Python suite**

  Run: `python -m pytest -q`
  Expected: all green.

- [ ] **Step F.2: Frontend build**

  Run: `npm --prefix frontend run build`
  Expected: clean build.

- [ ] **Step F.3: Playwright run-through**

  Run: `node run_playwright_test.mjs` (or the canonical command — check `package.json`).
  Expected: smoke season completes without postgame validation errors in logs.

- [ ] **Step F.4: Re-run the playtest scenario manually**

  Repeat Step 0.1's career creation and play one match end-to-end. Confirm: postgame copy matches score, recruiting badges update, draft → roster names are identical.

- [ ] **Step F.5: Update `docs/STATUS.md`** with a one-line note referencing this plan and the date completed.

---

## Out of scope (don't do here)

- Re-balancing match outcomes or AI difficulty.
- Adding new recruiting or development mechanics. We're surfacing existing state, not inventing new state.
- Rewriting the narrative voice modules beyond what Task 1 requires.
- Aurora-vs-Comets specific narrative or any per-team scripted content.
