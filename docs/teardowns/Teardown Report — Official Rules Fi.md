# Teardown Report — Official Rules Fidelity

## Verdict
Official-rules fidelity is **partially covered but trust-risky**. The repo has a solid deterministic rules substrate for profiles, scoring, sequence resolution, catch queues, ball-state events, warnings, and blue cards, and the focused official test suite is green. The trust risk is that the live autonomous official engine does not actually exercise some must-have rule mechanics it claims through V11 docs and player-facing “USA Dodgeball 2026.1” selection: opening rush/activation is bypassed, throw-clock penalties are not wired into autonomous play, and No Blocking is logged/visible but does not change autonomous outcome resolution.

## Highest-signal findings

### Finding 1
- Severity: **High**
- Rulebook basis: USA Dodgeball 2026.1 sections 10-11: opening rush controls designated ball retrieval; balls become active only after crossing the clear line.
- Repo evidence: [official_engine.py](/C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/official_engine.py:470) immediately creates initial balls, assigns every ball to a holder, and calls `activate_ball()` for each. For cloth, the neutral center ball falls through to `a_starters[0]`.
- Why it matters: Autonomous official matches skip the actual opening-rush/activation state and give cloth’s neutral ball to Team A by construction.
- Reproduction / inspection path: inspect `run_autonomous_game()` lines 470-485; compare [ball_state.py](/C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/ball_state.py:75) `initial_balls()` with the autonomous activation loop.
- Suggested fix direction: model an explicit rush/activation phase or document that autonomous official mode uses a simplified pre-activated abstraction; for cloth, avoid deterministic Team A neutral-ball ownership.
- Regression gate: autonomous official test asserting initial cloth neutral-ball handling is fair/explicit and that inactive balls are not all activated before an opening-rush step.

### Finding 2
- Severity: **High**
- Rulebook basis: section 14: throw clock starts when burden is established; failure has foam/no-sting ball-forfeit and cloth play-n-balls penalties.
- Repo evidence: [burden.py](/C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/burden.py:226) implements `foam_failure_forfeit()` and [burden.py](/C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/burden.py:245) implements cloth play-n helpers, but `rg` shows these are only used in tests. [official_engine.py](/C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/official_engine.py:570) establishes burden, then uses it mainly to weight action choice.
- Why it matters: Section 14 is marked V11 must-have, but the live autonomous engine does not appear to enforce zero-called penalties.
- Reproduction / inspection path: `rg "foam_failure_forfeit|cloth_play_n_call|cloth_play_n_failure|ZERO_CALLED" src tests`.
- Suggested fix direction: add an autonomous clock state transition from established burden to warning/zero/play-n and emit penalty events from the same event log.
- Regression gate: a deterministic autonomous scenario where a burden side cannot/will not throw and the correct foam or cloth penalty lands.

### Finding 3
- Severity: **High**
- Rulebook basis: section 27: in No Blocking, held balls are body extensions; blocks no longer protect players.
- Repo evidence: [no_blocking.py](/C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/no_blocking.py:72) implements `resolve_contact_with_held_ball()`, and [official_engine.py](/C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/official_engine.py:589) activates No Blocking, but `resolve_contact_with_held_ball()` is never called outside its unit test.
- Why it matters: V11 acceptance explicitly says “No-blocking changes outcome resolution,” but autonomous matches only surface the mode.
- Reproduction / inspection path: `rg "resolve_contact_with_held_ball|no_blocking_state" src tests`.
- Suggested fix direction: pass No Blocking state into throw/block resolution and create at least one scripted plus autonomous regression.
- Regression gate: same throw/block sequence resolves differently before vs during No Blocking.

### Finding 4
- Severity: **Medium**
- Rulebook basis: section 1 says cloth uses five balls; foam/no-sting use six.
- Repo evidence: [rulesets.py](/C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/rulesets.py:122) correctly sets `CLOTH_OPEN.ball_count = 5`, but [SaveMenu.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/SaveMenu.tsx:46) tells players cloth is “6x” balls and uses flavor like “lethal direct hits.” No-sting copy also claims superior grip/strategic possession that is not reflected in the rules profile beyond material identity.
- Why it matters: Player-facing setup overpromises material differences and is factually wrong for cloth ball count.
- Reproduction / inspection path: create/new save ruleset selector or inspect `rulesetExplanations`.
- Suggested fix direction: make setup copy rules-accurate: foam/no-sting share six-ball structure; cloth has five balls and different scoring/burden/no-blocking behavior.
- Regression gate: frontend text test or snapshot for ruleset explanation facts.

### Finding 5
- Severity: **Medium**
- Rulebook basis: conformance should prove rule behavior, not just file existence.
- Repo evidence: [test_official_conformance_matrix.py](/C:/GPT5-Projects/Dodgeball%20Simulator/tests/test_official_conformance_matrix.py:40) only checks that mapped test files exist and contain `def test_`.
- Why it matters: Docs say “complete conformance matrix verification,” but the matrix can stay green while live behavior drifts.
- Reproduction / inspection path: inspect the test body at lines 40-47.
- Suggested fix direction: convert the matrix into named behavioral assertions or require section-specific marker/test ids.
- Regression gate: each must-have section maps to at least one explicit test name and, for engine-affecting rules, one live engine integration test.

## Rule Coverage Matrix

| Rule area | Implemented? | Tested? | Player-facing? | Risk | Recommendation |
|---|---|---|---|---|---|
| Match timing/scoring | Partial | Yes | Yes | Medium | Keep; add live bracket/overtime gates. |
| Foam/no-sting/cloth differences | Partial | Yes | Yes | Medium | Fix cloth/no-sting copy; prove live differences. |
| Opening rush | Partial/simplified | Weak | Implied | High | Add explicit rush phase or disclose simplification. |
| Ball activation | Partial | Yes | Replay state | High | Stop pre-activating all autonomous balls. |
| False starts | Deferred/nice-to-have | No | No | Low | Honest deferral unless UI starts claiming it. |
| Burden to throw | Partial | Yes | Replay state | Medium | Wire deeper into autonomous timing. |
| Throw clock | Partial | Unit only | Replay state | High | Enforce penalties in autonomous engine. |
| Stoppage of play | Deferred/nice-to-have | No | No | Low | Honest deferral. |
| Ball states | Mostly | Yes | Replay state | Medium | Integrate initial inactive states into live play. |
| Valid/invalid throws | Partial | Yes | Rule calls | Medium | Add autonomous invalid-release paths. |
| Ball collision | Deferred advanced | No | No | Low | Honest deferral. |
| Hitting/blocking/catching | Partial | Yes | Replay | Medium | Good scripted coverage; broaden live integration. |
| Player entry queue | Mostly | Yes | Replay | Low | Strength; add autonomous edge cases. |
| Ball retrieval | Core partial | Yes | Replay | Medium | Keep core; retriever realism deferred. |
| Out of bounds | Partial | Yes | Rule calls | Medium | Add live autonomous OOB scenario. |
| One-versus-one | Partial/moment | Limited | Moment | Low | Fine as non-core, but not full rule resolver. |
| No Blocking | Partial | Unit only | Yes | High | Make it change live outcomes. |
| Pinching/flight kills/injuries/interference/collision | Deferred advanced | Discipline scaffold only | No | Low | Honest deferral. |
| Verbal warnings/blue cards | Mostly | Yes | Rule calls | Low | Solid within V11 scope. |
| Yellow/red cards | Placeholder/deferred | Yes for placeholder | No | Low | Honest deferral. |
| Bracket/overtime | Partial/deferred | Some lifecycle | Playoffs | Medium | Avoid full-USAD bracket claims. |

## Deferred-but-honest scope
Clearly documented deferred scope includes yellow/red tournament persistence, designated retriever realism, pinching, flight kills, injuries, interference, player collision, full bracket expansion, and administrative rules. That is consistent across [STATUS.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/STATUS.md:52), the V11 handoff, and the V11 design classification.

## Confirmed strengths
Focused official verification passed: conformance matrix, rulesets, lifecycle, ball state, burden, sequence, No Blocking unit tests, catch queue, scoring, autonomous game, and balance tests. The official probe also passed small smoke runs for `official_foam` and `official_cloth`. Scoring presentation is strong: frontend code deliberately uses official game points instead of survivor count for official matches.

## Open questions
No blocker questions. The main product decision is whether “official ruleset” should mean fully enforced live rules, or an officially inspired deterministic abstraction with honest player-facing limits.

## Suggested next prompt
Implement a read-only-to-code-followed-by-fix pass for V11 official fidelity: wire No Blocking and throw-clock penalties into `run_autonomous_game`, stop pre-activating all opening-rush balls, correct ruleset selector copy, and add integration regressions proving the live autonomous engine changes behavior for sections 11, 14, and 27.

Verification run: focused official pytest subset passed; `tools/official_match_probe.py --trials 20 --ruleset official_foam` and `official_cloth` both passed probe gates. Pare was unavailable, so I used normal shell/search commands as fallback.

Goal usage: 157,588 tokens, about 5m41s elapsed.