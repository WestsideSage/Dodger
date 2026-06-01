# Teardown Report — Product Coherence and Game Loop

## Verdict
The loop is **partially coherent, trending coherent**. The current build now has real connective tissue from first career creation into season preview, weekly readiness, match simulation, Primary Factor, standings, recruiting, staff, history, and offseason. The biggest remaining coherence break is not the loop structure; it is trust inside the watchable sim itself: full replay still shows placeholder `-` targets on miss events, which makes a proof-driven match report feel synthetic at the exact moment the player is supposed to believe the sim.

## Highest-signal findings

### 1. Replay proof still leaks placeholder targets
- Severity: High
- Evidence: Browser-observed in a fresh `Build from Scratch` career, first full replay: repeated entries like `Yuki Rodriguez winds up and targets -` and `Yuki Rodriguez vs -: miss.` Source path: [replay_proof.py](/c:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/replay_proof.py:170) returns `"-"` for missing targets, then [replay_proof.py](/c:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/replay_proof.py:176) uses that in event labels/details.
- Why it matters: This directly attacks the “watchable sim majority of playtime” promise. The replay is otherwise one of the game’s strongest surfaces, so malformed play-by-play is high-impact.
- Reproduction / inspection path: Fresh career -> simulate Week 1 -> `VIEW FULL REPLAY` -> inspect event log miss events.
- Suggested fix direction: For misses with no concrete target, render no-target language: “throws into space,” “misses wide,” or “fires high” instead of inventing a target placeholder.
- Regression gate: Add a replay proof unit test asserting no player-facing replay label/detail contains `targets -`, `vs -`, or `toward -` for miss events.

### 2. Fast-forward is mechanically valid but emotionally premature
- Severity: Medium
- Evidence: Browser-observed before first Week 1 lock: `Fast-forward Season` was available while readiness was `4 of 6 ready · 2 pending`. Source confirms auto-pilot intentionally bypasses readiness because gates are “advisory” in [use_cases.py](/c:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/use_cases.py:1174), while the UI renders the button alongside blocked `Lock Plan` in [PreSimDashboard.tsx](/c:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/match-week/command-center/PreSimDashboard.tsx:822).
- Why it matters: New players can skip the very loop that teaches scout, confirm lineup, match, aftermath, and standings. For a management sim, fast-forward should be a confidence tool after the loop is understood, not a competing first-week CTA.
- Reproduction / inspection path: Fresh career -> season preview -> Command Center before Scout/Confirm -> observe disabled `Lock Plan` but enabled `Fast-forward Season`.
- Suggested fix direction: Keep fast-forward, but gate or de-emphasize it until at least one completed match, or require a small confirmation explaining it will reuse persisted defaults and skip weekly ceremony.
- Regression gate: E2E fresh-career test: first pre-match week should not expose primary fast-forward before the first completed match, or should require explicit confirmation.

### 3. Staff market is honest but mostly advisory
- Severity: Medium
- Evidence: [staff_market.py](/c:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/staff_market.py:12) says only Training has a real mechanical hook. [staff_market.py](/c:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/staff_market.py:74) explicitly states scouting, recovery, and deeper staff economy effects remain future hooks. Training feeds offseason growth in [offseason_ceremony.py](/c:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/offseason_ceremony.py:487).
- Why it matters: Staff looks like a full management arm, but five of six departments are currently identity/advice surfaces. That is acceptable if presented as advisory, but it is underconnected relative to recruiting, lineup, and tactics.
- Reproduction / inspection path: Dynasty Office -> Staff tab; inspect source `build_staff_market_state`.
- Suggested fix direction: Do not add a new staff economy. Tighten copy and ordering so Training is clearly the only current mechanical staff lever, while other departments are “advisory lenses.”
- Regression gate: Unit/e2e assertion that non-training departments do not display fake mechanical bonuses; Training displays the growth modifier.

### 4. Recruiting loop is now mechanically connected, but payoff timing is delayed
- Severity: Low
- Evidence: Source confirms Scout narrows OVR, Contact/Visit raise interest in [recruiting_actions.py](/c:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/recruiting_actions.py:1), and interest strengthens signing offers in [recruitment.py](/c:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/recruitment.py:611). Tests pin visible deltas in [test_recruiting_actions.py](/c:/GPT5-Projects/Dodgeball%20Simulator/tests/test_recruiting_actions.py:18) and same-class offseason signability in [test_recruiting_interest_transfer.py](/c:/GPT5-Projects/Dodgeball%20Simulator/tests/test_recruiting_interest_transfer.py:32).
- Why it matters: This is no longer decorative, but the player’s “did that matter?” answer is still split across weekly actions and later Signing Day.
- Reproduction / inspection path: Dynasty Office -> Recruit -> inspect OVR bands, interest, action slots; continue to offseason recruitment.
- Suggested fix direction: Add a compact “Signing Day leverage” line on each prospect after contact/visit using existing interest and same-class data.
- Regression gate: E2E: Contact or Visit updates visible interest delta and later offseason choice list includes courted prospects.

## Loop Map

| Phase | Player question | Current answer | Missing connection | Fix direction |
|---|---|---|---|---|
| Create club | What am I building? | Clear ruleset, identity, coach, roster flow; browser-observed fresh custom club worked. | Roster foundation helps, but role coverage is still conceptual. | Keep; no major system change. |
| First command week | What should I do now? | Season preview and Command Center answer week, opponent, stakes, watch player. | Fast-forward competes too early. | Delay or confirm fast-forward. |
| Readiness gates | Why can’t I sim? | Scout + Confirm Lineup gates are visible and tested in [test_readiness_gates.py](/c:/GPT5-Projects/Dodgeball%20Simulator/tests/test_readiness_gates.py:27). | Fast-forward bypass creates mixed signal. | Align fast-forward with onboarding state. |
| Match preview | Who are we facing? | Opponent file, key threat, edge, tactical read. | Mostly coherent. | Continue refinement only. |
| Match replay | Can I watch and trust it? | Court, event log, current event, controls are strong. | Placeholder target `-` breaks trust. | Fix miss-event copy. |
| Aftermath | Why did we win/lose/draw? | Primary Factor rendered in browser; ranking tests in [test_match_explanation.py](/c:/GPT5-Projects/Dodgeball%20Simulator/tests/test_match_explanation.py:63). | Replay bug can undermine the proof. | Repair replay proof text. |
| Next improvement | What should I do next? | Loss panel helper exists and is tested in [test_next_best_improvement.py](/c:/GPT5-Projects/Dodgeball%20Simulator/tests/test_next_best_improvement.py:17). | Needs more browser validation after losses. | Follow-up playthrough focused on losses. |
| Standings/playoff race | Where are we in the league? | Strong answer: rank, cut line, target, clickable program history in [LeagueContext.tsx](/c:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/LeagueContext.tsx:194). | None confirmed. | Keep as source of league truth. |
| Recruiting/scouting | Does this affect signing? | Yes, source/tests say yes. | Payoff is delayed. | Show signing leverage inline. |
| Staff market | Does hiring matter? | Training matters; others are advisory. | Five departments are underconnected. | Label as advisory, don’t overpromise. |
| Offseason/next season | Why continue? | Ordered ceremony beats exist: recap, champion, awards, records, HOF, development, rookie class, recruitment, schedule in [offseason_ceremony.py](/c:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/offseason_ceremony.py:55). | Not browser-revalidated end to end in this pass. | Run a playoffs/offseason-only pass. |

## Orphaned / Underconnected Systems

| System | Why it feels detached | Evidence | Recommendation |
|---|---|---|---|
| Non-training staff departments | Advisory without mechanical hooks. | [staff_market.py](/c:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/staff_market.py:12) | Present as advice lanes until real hooks exist. |
| Fast-forward | Can skip the teaching loop before first match. | Browser-observed; [use_cases.py](/c:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/use_cases.py:1174) | Gate or confirm in first season. |
| Replay miss targets | Missing data rendered as player-facing placeholder. | Browser-observed; [replay_proof.py](/c:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/replay_proof.py:170) | Render no-target miss language. |

## Confirmed strengths
Fresh-career onboarding worked in browser from ruleset -> Build from Scratch -> identity -> coach -> roster -> season preview -> Command Center. Readiness gates are clear and backed by persistence tests. Primary Factor is a real backend contract, rendered in aftermath, and tested. Standings is currently one of the most coherent product surfaces: it answers rank, playoff line, target, and program identity. Recruiting has moved from decorative to mechanically connected. Long-term history is visible early with honest empty states: “archive is live” and first banner/alumni still ahead.

## Open questions
I did not complete a fresh browser pass through playoffs, offseason ceremony, signing day, and next-season re-entry in this run. Source strongly supports that path, but final product confidence there needs a dedicated browser pass. I also did not verify whether the next-best improvement panel appears with enough clarity across multiple loss types, only that the source/tests support it.

## Suggested next prompt
Run a browser-only playoffs/offseason coherence pass from a progressed save: verify playoff race closure, elimination/champion ceremony, records/HOF/development/recruitment beats, signing payoff from in-season recruiting, and next-season re-entry. Do not inspect source unless the UI hard-crashes.

Verification run: focused pytest set passed (`46` tests), frontend build passed. Pare MCP was not available in the toolset, so I used normal shell/source inspection as the fallback. Final goal usage: 241,537 tokens, about 9 minutes 23 seconds.