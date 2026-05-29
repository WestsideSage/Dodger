# V14 — First Season Retention & Sim Legibility: Sprint Plan

## 1. Relation to Prior Specs
This milestone follows the completion of the V11 (Official Rules), V12 (AI Program Managers), and V13 (Broadcast & Presentation) cycle, as well as the recent Rookie Run playtest polish (Tasks 6-11). It intentionally defers further expansion of the V11 rulebook and V13 broadcast features. Instead, it builds on the Plan C v2 `CoachPolicy` and Plan B v2 player attributes to translate existing simulation math into legible, actionable feedback for first-season players.

## 2. Current State Summary
The game is playable end-to-end with high structural integrity. The V12 AI adaptation loop provides realistic rivalry pressure, and V13 gives matches a broadcast feel. The recent Rookie Run polish successfully removed major blockers for fresh players (e.g., roster guidance, default command plans). However, while the engine produces believable, nuanced outcomes (OVR curves top out at 66% favorites, maintaining upset potential), the *reasons* for those outcomes are often hidden in the raw event logs.

## 3. Readiness Verdict
**READY FOR CLAUDE IMPLEMENTATION.**
The repo's foundational architecture (Hybrid Driver, Tier 1 Engine, `probe_lib.py`) is stable and verified. The necessary engine hooks (moments, v2 attributes, v2 policies) exist and simply need to be surfaced to the frontend presentation layer.

## 4. Product Thesis
A robust simulation is useless if the player cannot understand causality. V14 exists to ensure that every win or loss can be explained through visible, proof-backed factors connected to tactics, roster, staff, opponent pressure, or variance. By making the simulation's logic highly visible—without adding artificial boosts or rubber-banding—we will significantly increase first-season retention and strategic stickiness.

## 5. Non-Goals / Deferred Scope
Explicitly deferred (Do Not Implement):
- Full yellow/red card tournament persistence
- Full designated retriever realism
- Pinching, flight kills, injuries, interference, or player collision
- Bracket expansion or new tournament types
- Giant new economy systems or unrelated UI redesigns
- Hidden AI buffs or comeback aura logic

## 6. Evidence Inspected
- `tests/test_engine_health.py` (Passed 2/2, confirming O1 rebalancing is active).
- `tools/tier_engine_health_probe.py` (Output shows realistic win rate progression: Net +0 OVR is 54%, Net +72 OVR is 66%; Moment occurrence frequencies are healthy).
- `docs/STATUS.md` (Confirmed post-V13 state and Rookie Run polish fixes).
- `tests/e2e/` (Confirmed existing coverage for Command Center, Aftermath, and Tier 1 Recognition).

## 7. Findings
- **First-time player comprehension:** Roster guidance and default plans exist, but v2 attributes like `throw_selection_iq` and `catch_courage` lack in-game explanation.
- **Weekly decision loop:** Staff effects are summarized off-engine, but their match-day impact is not transparently previewed.
- **Match/replay/aftermath legibility:** The engine generates dramatic catches and stamina collapses, but the Aftermath screen does not provide a definitive "Primary Factor" explaining the outcome.
- **Roster/recruiting/staff agency:** Lineup liabilities are generated but rarely highlighted as the explicit reason a team lost.
- **Sim/balance health:** Excellent. The OVR curve floor is >= 66% and moment occurrence is balanced.
- **AI program manager pressure:** V12 adaptation is working well.
- **UX/browser risk:** High risk of UI clutter; changes must respect existing CSS grids and responsive layouts.

## 8. Ordered Atomic Tasks

### Task 1: Aftermath Primary Factor
**Goal:** Implement a deterministic backend `MatchExplanation` / `PrimaryFactor` contract based on `MatchResult` and moment event data.
**Files:** `src/dodgeball_sim/voice_aftermath.py`, `frontend/src/components/CommandCenter/Aftermath.tsx` (or equivalent).
**Contract Details:** Return a structured payload containing `code`, `title`, `sentence`, `confidence`, and `evidence_chips`. The frontend renders localized copy, but it must be strictly backed by the backend data.
**Ranking Rules & Categories:** Evaluate and rank factors deterministically.
- Categories: Late stamina collapse, catch disparity, flood throws punished, opening rush deficit, liability involvement, upset variance / no dominant factor.
- Tie-breakers: Use severity of disparity (e.g., massive catch diff > minor stamina loss) and chronological finality (late-game events outweigh early ones).
- Fallback: For close matches with no dominant stat, use "upset variance / no dominant factor" with softer language (avoid absolute causal language when evidence is weak).
**Acceptance Criteria:** Aftermath identifies the highest-leverage supported statistical disparity or moment event, or falls back to no dominant factor when evidence is weak.
**Regression Gate:** Add focused backend unit tests for explanation selection ranking. `npm run e2e` (`command-center-aftermath.spec.ts`).
**Risk:** Medium. Requires careful weighting logic.

### Task 2: Tactical Matchup Diff
**Goal:** Expose a comparative UI panel in the Matchup Preview showing the player's `CoachPolicy` against the AI's known tendencies.
**Fog-of-War Rule:** May only expose public, scouted, prior-match, or already player-facing V12 adaptation tendencies. Do not leak exact hidden AI `CoachPolicy` values unless the current UI/scouting model already reveals them.
**Files:** `src/dodgeball_sim/matchup_details.py`, `frontend/src/components/Matchup/MatchupPreview.tsx`.
**Acceptance Criteria:** Pre-match preview clearly indicates if a policy choice is countered by or counters the opponent, strictly respecting fog-of-war.
**Regression Gate:** Add unit tests enforcing the fog-of-war / scouted visibility rules. `npm run build`, `npm run lint`, `tier1_recognition.spec.ts`.
**Risk:** Medium. Requires frontend layout updates and strict state-leaking controls.

### Task 3: V2 Attribute Tooltips
**Goal:** Add informative, tier-1-specific tooltips for `throw_selection_iq` and `catch_courage`.
**Files:** `frontend/src/components/Roster/PlayerProfile.tsx` (or equivalent).
**Acceptance Criteria:** Hovering, focusing, or tapping these attributes explains their exact impact on the hybrid driver (e.g., "Reduces flood throws").
**Regression Gate:** `npm run build`, `npm run lint`.
**Risk:** Low. Pure frontend documentation.

### Task 4: Match-Day Staff Impact Visibility
**Goal:** Inject active staff effects directly into the pre-match preview rather than leaving them buried in the Dynasty Office.
**Files:** `src/dodgeball_sim/command_center.py`, `src/dodgeball_sim/staff_market.py`. Likely also inspect `src/dodgeball_sim/matchup_details.py` depending on current preview data flow.
**Acceptance Criteria:** If a hired staff member affects match-day stats (e.g., stamina), their bonus is explicitly listed in the match preview.
**Regression Gate:** `python -m pytest -q`.
**Risk:** Low. Backend data routing.

### Task 5: Lineup Liability Exploitation Tags
**Goal:** Tag replay events in `ReplayTimeline` when an engine-defined `Lineup Liability` is actively targeted and punished.
**Strict Proof Rule:** May only render when the event payload proves the target player had the liability AND the outcome directly punished it. If proof is partial, use softer language like "Liability involved" or do not tag the event at all.
**Files:** `src/dodgeball_sim/events.py`, `src/dodgeball_sim/replay_service.py`.
**Acceptance Criteria:** Replays show a "Liability Exploited" or "Liability involved" badge on relevant events based on strict proof.
**Regression Gate:** Add unit tests preventing unsupported liability exploitation tags. `python -m pytest tests/test_tier_1_integration.py -q`.
**Risk:** Medium-High. Must be purely read-only over existing payloads, but inference logic requires high strictness.

### Task 6: Playwright Hardening
**Goal:** Assert that the Primary Factor and Tactical Diff render correctly for a brand-new save.
**Files:** `tests/e2e/playable-loop-diagnostics.spec.ts` or `naive_playtest_runner.spec.ts`.
**Acceptance Criteria:** E2E suite passes with the new elements present.
**Regression Gate:** `npm run e2e`.
**Risk:** Low. Test authoring.

## 9. Recommended Implementation Order
1. **Claude:** Spec hardening mini-pass (if minor file alignment is needed).
2. **Claude:** Task 1 (Aftermath Primary Factor)
3. **Claude:** Task 3 (V2 attribute explanations)
4. **Claude:** Task 4 (Staff impact visibility)
5. **Claude:** Task 2 (Tactical matchup diff)
6. **Claude:** Task 5 (Liability tags)
7. **Codex:** Task 6 (Playwright hardening)

## 10. First Claude Handoff Prompt

```text
You are picking up implementation for V14 — First Season Retention & Sim Legibility.

Read `docs/specs/2026-05-28-v14-first-season-retention-sim-legibility/sprint-plan.md` to orient yourself.
Your objective is to execute the **Spec hardening mini-pass** and **Task 1: Aftermath Primary Factor**.

1. Inspect `src/dodgeball_sim/voice_aftermath.py` and the corresponding frontend Aftermath component.
2. Implement the deterministic backend `MatchExplanation` / `PrimaryFactor` contract (`code`, `title`, `sentence`, `confidence`, `evidence_chips`).
3. Implement the ranking rules and tie-breakers (stamina collapse, catch disparity, flood throws, etc.), falling back to "no dominant factor" with softer language for close matches.
4. Add focused backend unit tests for the explanation selection and ranking logic.
5. Do not alter match outcomes or engine randomness.
6. Verify your work with `python -m pytest -q` and `npm run e2e` (ensure `command-center-aftermath.spec.ts` passes).
```

## 11. Regression Gate
Before the milestone can be declared done, the following must pass:
- `python -m pytest -q` (Including the new explanation ranking, fog-of-war, and liability tag unit tests)
- `python tools/tier_engine_health_probe.py --driver rec --trials 50` (Must maintain ~66% top floor).
- `npm run build` && `npm run lint` inside `frontend/`
- `npm run e2e` (Zero Playwright failures)

## 12. Readiness Verdict
**READY FOR CLAUDE IMPLEMENTATION**
