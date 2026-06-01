# Teardown Report — New Player Comprehension

## Verdict
The first-time experience is understandable but uneven. The game now has strong structural guidance around save setup, season preview, readiness gates, standings, and next-best actions, so a new player is not completely lost. The main comprehension failures happen when an action’s label promises learning but only clears a gate, and when the aftermath answers a narrow match-log question instead of the player’s real question: “why did I lose, and what should I change?”

I used the browser at `1440x900` with a fresh Build from Scratch save, `np-teardown-20260601`, and ran `npm run e2e -- tests/e2e/v14-legibility.spec.ts --project=chromium`, which passed. Pare MCP was not available, so I used normal shell/browser inspection. No code was changed.

## Highest-signal findings

### 1. Scout Opponent clears a gate but does not visibly teach new intel
- Severity: High
- Evidence: In browser, after clicking `Scout Opponent`, the sim lock advanced from `4/6` to `5/6` and showed `Opponent lineup reviewed`, but Tactical Diff still showed `Unscouted`. The backend route only clears the readiness state: [server.py](<C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/server.py:546>). The gate model treats scouting as a reviewed flag: [week_briefing.py](<C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/week_briefing.py:103>). Tactical Diff can still render `Unscouted`: [PreSimDashboard.tsx](<C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/match-week/command-center/PreSimDashboard.tsx:581>). Existing readiness tests assert only the gate clears: [test_readiness_gates.py](<C:/GPT5-Projects/Dodgeball Simulator/tests/test_readiness_gates.py:36>).
- Why it matters: A new player expects “Scout Opponent” to reveal usable opponent information. Instead, it mostly functions as a checklist button.
- Reproduction / inspection path: Fresh career → first command week → read Tactical Diff → click `Scout Opponent` → Tactical Diff remains unscouted.
- Suggested fix direction: Either rename the action to match reality, such as `Review Opponent File`, or make it reveal a concrete scouted delta and display a small “new intel revealed” result.
- Regression gate: E2E should click the scout action and assert either Tactical Diff changes from `Unscouted`, or the action copy explicitly says it is a review/readiness step rather than scouting.

### 2. First-loss aftermath can answer the wrong question
- Severity: High
- Evidence: In the fresh save, the pre-match screen said the club was an underdog by `-84 net starter OVR`, had `3 starters` low on stamina, and advised Defensive. After a `0-1` loss, Primary Factor said `INCONCLUSIVE` / `No dominant factor` / “There’s no one thing to fix here.” The factor engine ranks mostly match-event factors: [match_explanation.py](<C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/match_explanation.py:225>). Its close-match fallback is codified in tests: [test_match_explanation.py](<C:/GPT5-Projects/Dodgeball Simulator/tests/test_match_explanation.py:156>). The Primary Factor card renders that low-confidence result directly: [PrimaryFactorCard.tsx](<C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/match-week/aftermath/PrimaryFactorCard.tsx:3>).
- Why it matters: The player’s question is not only “what event dominated the match?” It is “what did I do wrong, and what should I improve?” The current answer conflicts with the same screen’s next-best improvement list.
- Reproduction / inspection path: Build weak/naive roster → ignore advised intent → simulate first match → inspect Primary Factor and Next Best Improvement together.
- Suggested fix direction: Split “match factor” from “manager lesson.” If the match factor is inconclusive, still surface a controllable prep lesson from roster edge, fatigue, ignored recommendation, or weakest role group.
- Regression gate: Synthetic or E2E aftermath where close loss plus large pre-match disadvantage must not render “there’s no one thing to fix” without an adjacent controllable improvement lesson.

### 3. Match replay still exposes placeholder targets
- Severity: High
- Evidence: The replay event log showed rows like “Remy Ramirez sends a screamer towards -” and “Remy Ramirez vs -: miss.” Replay service defaults missing targets to `-`: [replay_service.py](<C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/replay_service.py:473>). The replay UI renders event summary/detail directly: [MatchReplay.tsx](<C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/MatchReplay.tsx:390>).
- Why it matters: This looks like broken simulation data, exactly when the player is trying to understand why a point unfolded.
- Reproduction / inspection path: Simulate first match → open full replay → scan event log for miss events.
- Suggested fix direction: For events without a target, render player-facing language like “throws into space” or “misses wide,” and omit the versus detail.
- Regression gate: Replay E2E should assert no visible `towards -`, `vs -`, or `target -` appears in current event or event log text.

### 4. Founding roster draft allows early self-sabotage with weak warning
- Severity: Medium
- Evidence: Selecting the first six visible prospects allowed commit with only a generic imbalance warning. The resulting team immediately showed a `41 OVR` watch area and a severe first-week underdog matchup. The draft warning checks imbalance but does not explain projected first-six strength or stronger unselected players: [StartingRecruitmentStep.tsx](<C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/new-game/StartingRecruitmentStep.tsx:85>). The prospect list is internally scrollable: [StartingRecruitmentStep.tsx](<C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/new-game/StartingRecruitmentStep.tsx:213>).
- Why it matters: The first strategic decision can teach “pick any six” instead of “build a survivable first six.”
- Reproduction / inspection path: Build from Scratch → select the first six visible prospects → commit → inspect season preview and first matchup.
- Suggested fix direction: Add a founding-draft summary before commit: projected starter OVR, best unselected players, weakest role, and stronger warning when the projected six is far below league quality.
- Regression gate: E2E should create a weak founding roster and assert a specific “low projected strength / stronger players unselected” warning appears before commit.

### 5. Recruiting action feedback is mechanically real but not durable enough
- Severity: Medium
- Evidence: After scouting a recruit, the browser showed action budget changes, but no durable before/after explanation remained visible after the card refreshed. Source shows a temporary feedback overlay cleared after `3200ms`: [ProspectCard.tsx](<C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/dynasty/ProspectCard.tsx:82>). Backend tests confirm actions return meaningful deltas: [test_recruiting_actions.py](<C:/GPT5-Projects/Dodgeball Simulator/tests/test_recruiting_actions.py:59>). The recruit-board E2E explicitly does not retest action mechanics: [v15-recruit-board.spec.ts](<C:/GPT5-Projects/Dodgeball Simulator/tests/e2e/v15-recruit-board.spec.ts:5>).
- Why it matters: New players need to see what changed, not just spend a scarce action slot.
- Reproduction / inspection path: Dynasty Office → Recruit → click Scout → wait for refresh → inspect card for durable “what changed” record.
- Suggested fix direction: Add a persistent “last action this week” row or inline before/after chip per prospect.
- Regression gate: E2E should click Scout/Contact/Visit and assert a durable post-refresh result is visible for that prospect.

## First-Time Player Confusion Log

| Moment | What player sees | Likely question | Current answer | Better answer |
|---|---|---|---|---|
| Ruleset choice | `USA Dodgeball 2026.1 — Foam` | Does this matter? | Short ruleset explanation | Good enough for first play |
| Build from Scratch | Identity, coach, roster | What should I optimize first? | Fill required fields | Add “your first six strength matters most” |
| Coach archetype | Boosts/improves/drives text | How much does this change? | Flavor-level effect | Small quantified or scoped effect hint |
| Founding roster | OVR/archetype list | Which six are safe? | Generic imbalance warning | Projected first-six strength and best unselected warning |
| Season preview | 7 weeks, bye, top 4 cut | What is my first goal? | Finish top 4 | Strong answer |
| First command week | Underdog, stamina warning, Tactical Diff | What should I do first? | Department orders plus gates | Good, except scout action mismatch |
| Scout Opponent | Gate clears, Tactical Diff still unscouted | What did scouting reveal? | “Opponent lineup reviewed” | Show revealed intel or rename action |
| Confirm Lineup | Gate clears | Did I choose a lineup? | Confirms current lineup | Acceptable, but could say “using current starters” |
| After loss | No dominant factor | Why did I lose? | Variance/no one thing | Separate match factor from manager lesson |
| Replay | Events with `-` target | Is the sim missing data? | Raw placeholder visible | Player-facing miss language |
| Recruiting | Action spent | What changed? | Temporary overlay and budget decrement | Durable per-prospect result |
| Standings | Rank, playoff line, target | Am I still alive? | Clear rank and target | Strong answer |

## Teaching Opportunities

| Concept | Where to teach it | Minimal implementation direction |
|---|---|---|
| Starter strength | Founding roster commit | Projected first-six OVR and weakest role summary |
| Coach archetype | Coach setup | One sentence: when this archetype matters and what it never changes |
| Scout vs review | First command week | Rename or reveal actual scouted delta |
| Tactical Diff | Beside Tactical Diff | Tiny hint: “Your side is from your policy; opponent side requires intel.” |
| Match factor vs improvement | Aftermath | Separate “why this point swung” from “next controllable fix” |
| Recruiting action payoff | Recruit card | Persistent last-action chip with before/after |
| Development/growth | Dynasty Office / aftermath | Tie growth to one concrete player and recent action |
| Records/dynasty | History empty state | Current empty state is good; keep it milestone-oriented |
| Playoff race | Standings glance | Current cut-line and next target are good; keep prominent |

## Confirmed strengths

- Build-from-scratch identity setup has clear required fields, preview, and duplicate save-name handling: [IdentityStep.tsx](<C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/new-game/IdentityStep.tsx:88>).
- Season preview clearly teaches schedule length, bye week, playoff cut, goal, roster strength, and watch area: [SeasonPreview.tsx](<C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/match-week/command-center/SeasonPreview.tsx:66>).
- Readiness gates prevent blind simulation and are covered by tests: [week_briefing.py](<C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/week_briefing.py:96>), [test_readiness_gates.py](<C:/GPT5-Projects/Dodgeball Simulator/tests/test_readiness_gates.py:27>).
- Standings and playoff race answer “where am I?” well, with rank, cut line, recent results, and next target: [LeagueContext.tsx](<C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/LeagueContext.tsx:258>).
- Replay structure is useful despite the placeholder bug: current event, court state, event log, and key-play controls are all present: [MatchReplay.tsx](<C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/MatchReplay.tsx:390>).
- Staff market communicates role coverage and staff effects with concrete role lanes: [DynastyOffice.tsx](<C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/dynasty/DynastyOffice.tsx:250>).

## Open questions

- Should `Scout Opponent` become real intel discovery, or should it be renamed as a readiness review action? This is product direction, not just copy.
- Should Primary Factor remain strictly event-derived, with a separate “Manager Lesson,” or should it incorporate pre-match context?
- How much founding-roster guardrail is acceptable before it feels like the game is preventing intentional challenge builds?

## Suggested next prompt

Implement the three trust fixes from this teardown: make Scout Opponent either reveal visible intel or rename it, add an aftermath Manager Lesson when Primary Factor is inconclusive, and remove `-` target placeholders from replay player-facing text. Add focused regression tests for each.

Goal completed in about 11 minutes, using 240650 tokens.