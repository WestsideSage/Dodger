# Teardown Report — Copy, Voice, and Narrative Truth

## Verdict
The copy is directionally much more truthful than the older playtest notes suggested, but it is still uneven and has a few trust-risky seams where one surface has been corrected and another still speaks in the old model. The biggest risks are official-match aftermath headlines still narrating survivor counts while score cards use game points, Pipeline copy saying higher tiers are better while backend tests say tier 1 is stronger, and tactical/readiness copy leaning on confident labels or tooltips where visible proof should carry the explanation.

## Highest-signal findings

### Finding 1
- Severity: High
- Evidence: [use_cases.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/use_cases.py:644>) calls `voice_verdict.render_headline`; [voice_verdict.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/voice_verdict.py:192>) builds headline score text from survivor counts; [matchResult.ts](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/match-week/matchResult.ts:32>) correctly uses game points for official scores.
- Why it matters: An official 0-0 game-point draw can still produce a survivor-based headline like a lopsided result. That directly violates the “official scoring vs survivor wording” truth contract.
- Reproduction / inspection path: Inspect `_build_aftermath` -> `render_headline` -> `_margin_fallback`, then compare to `formatScoreline`.
- Suggested fix direction: Give headline generation the same scoring-model facts as `formatScoreline`, or suppress scoreline adjectives in official headlines unless they use game points.
- Regression gate: Add a postgame test with `winner_team_id=None`, official game points `0-0`, survivor counts `0-3`, asserting headline does not say `0-3`.

### Finding 2
- Severity: High
- Evidence: [terms.ts](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/legibility/terms.ts:138>) says stronger Pipeline tier means easier closes; [PipelineEmblem.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/legibility/PipelineEmblem.tsx:3>) labels tier 5 “Elite”; but [recruiting_actions.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/recruiting_actions.py:37>) gives lower tier numbers warmer base interest, and [test_recruiting_actions.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_recruiting_actions.py:73>) asserts tier 1 is stronger than tier 4.
- Why it matters: Recruiting copy teaches players to sort and value prospects backwards.
- Reproduction / inspection path: Compare `PipelineEmblem` labels with `base_interest()` and `test_base_interest_warmer_for_better_pipeline`.
- Suggested fix direction: Either invert the frontend labels/copy or change backend semantics, but make “stronger pipeline” mean the same tier direction everywhere.
- Regression gate: Add a UI/contract test asserting the displayed label for the mechanically strongest tier matches `base_interest()` ordering.

### Finding 3
- Severity: Medium
- Evidence: [command_center.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/command_center.py:384>) titles a lane “Why it happened” and says the clearest tactical read came from pressure; [TacticalSummaryCard.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/match-week/aftermath/TacticalSummaryCard.tsx:26>) displays “Based on {first lane title}.”
- Why it matters: The data supports “who absorbed pressure,” not necessarily “why the match was decided.” This overclaims causality after the Primary Factor system already exists.
- Reproduction / inspection path: Build post-week dashboard and view aftermath tactical summary.
- Suggested fix direction: Rename to “What the replay showed” or “Tactical evidence,” and let Primary Factor own causal language.
- Regression gate: Copy-quality test banning “Why it happened” for pressure-only dashboard lanes unless tied to `primary_factor`.

### Finding 4
- Severity: Medium
- Evidence: [PreSimDashboard.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/match-week/command-center/PreSimDashboard.tsx:717>) renders readiness gate detail only in `title={check.detail}`; the visible chip is just short label plus `!` or check.
- Why it matters: Readiness gates block simulation. Blocking reasons should be visible, not hidden in hover-only text.
- Reproduction / inspection path: Fresh weekly Command Center before Scout Opponent / Confirm Lineup.
- Suggested fix direction: Show the next blocking gate detail inline in the lock panel, using tooltip only as supplemental copy.
- Regression gate: E2E assertion that an unmet gate’s human-readable detail is visible without hover.

### Finding 5
- Severity: Low
- Evidence: [MatchReplay.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/MatchReplay.tsx:247>) displays `USAD ${data.scoring_model?.toUpperCase()}`; [matchResult.ts](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/match-week/matchResult.ts:36>) does the same in aftermath center label.
- Why it matters: `FOAM`, `CLOTH`, and earlier `OFFICIAL_FOAM` style labels read like implementation keys, not ruleset names.
- Reproduction / inspection path: Open an official replay or aftermath score hero.
- Suggested fix direction: Map scoring model to “USAD Foam” / “USAD Cloth” / “Legacy survivor scoring.”
- Regression gate: Snapshot or unit test for score labels disallowing underscores and all-caps ruleset keys.

## Copy Findings

| Surface | Existing copy/problem | Why it misleads or weakens clarity | Suggested direction |
|---|---|---|---|
| Official aftermath headline | Survivor-score headline can diverge from official game-point result | Contradicts the score hero and official rules model | Use game points or avoid score in official headline |
| Recruiting Pipeline | “Higher/Elite tier” frontend copy conflicts with tier 1 backend strength | Teaches the wrong sort/value heuristic | Align tier direction across backend, emblem, tooltip |
| Tactical summary | “Why it happened” from pressure lane | Turns evidence into causality | Rename as evidence, not explanation |
| Readiness gates | Gate details hidden in `title` | Blocking state is not visible enough | Inline the next required action/reason |
| Official score labels | `USAD FOAM` / `OFFICIAL_FOAM` style labels | Raw-ish implementation register | Use player-facing scoring names |
| Replay missing actors | `_player_name(None)` returns `-` in replay proof | If target-less events occur, copy can feel synthetic | Replace `-` with “no target recorded” or suppress actor slot |

## Best copy patterns to preserve

| Surface | Why it works |
|---|---|
| Primary Factor | `derive_match_explanation` softens weak evidence and uses explicit chips, with tests for decisive official results. |
| Match score hero | `formatScoreline` centralizes official game-point vs legacy survivor display. |
| Verdict fallback | `MatchWeek.tsx` correctly hides verdict when `primary_factor` exists, avoiding duplicate explanations. |
| Records Ratified | Empty states distinguish empty book, no club records, and no new records. |
| Rookie Class Preview | Replaces hover-only meaning with visible explanation for 70+ OVR floor. |
| Policy Editor | Preserves voice-register labels and removed the duplicate selected-label echo. |

## Confirmed strengths

Focused checks passed: `python -m pytest tests/test_command_center.py tests/test_match_explanation.py tests/test_postgame_truth.py tests/test_recruiting_actions.py tests/test_official_replay_scoreboard.py -q` passed 45 tests. Pytest warned it could not write cache files under `.pytest_cache`, but the tests themselves passed.

The strongest truth infrastructure is already in place: score formatting is centralized in `matchResult.ts`, Primary Factor has decisive official-result tests, recruiting actions expose before/after deltas, and records/offseason empty states are explicitly tested.

## Open questions

- Should Pipeline semantics remain “tier 1 is strongest” because backend tests say so, or should the backend be changed to match the more intuitive “tier 5 is Elite” UI?
- Should official aftermath headlines ever include a numeric score, or should the score hero be the only numeric result surface?

## Suggested next prompt

Fix the confirmed copy-truth issues from the teardown: align official aftermath headlines with game-point scoring, reconcile Pipeline tier semantics across backend/frontend/tests, rename pressure-only tactical causality copy, and surface readiness gate details visibly. Keep changes scoped and add regression tests for each.

Goal usage: 202,152 tokens over about 4 minutes 27 seconds.