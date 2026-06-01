# Teardown Report — Simulation Balance

## Verdict
Balance is **blocked for official-foam tactics trust**, even though the broad OVR curves are much healthier than the old flat baseline. The biggest issue is not favorite scaling: both rec and official pass the supported OVR probe. The blocker is that official catch posture is wired through the throwing team’s policy, so “go for catches” appears to help the opponent catch your throws. That creates a perverse, player-visible EV incentive in the default official engine. Read-only audit completed; Pare was unavailable, so I used normal read-only shell/probe commands. Goal usage: 169,703 tokens, about 5m24s.

## Highest-signal findings

### Finding 1
- Severity: **Blocker**
- Evidence: [official_engine.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/official_engine.py:681>) passes `policy=policies[offense_team]` into `resolve_throw()`. [official_resolution.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/official_resolution.py:108>) then uses that policy for the target’s catch decision. Rec does the expected opposite at [rec_engine.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/rec_engine.py:640>), using the defending team’s catch posture.
- Why it matters: Official tactics are inverted for catch posture. Equal-rating official probe, 200 trials: `fav go_for_catches / dog play_safe` produced `fav 0.0%, dog 92.5%, draw 7.5%`; reversed posture produced `fav 98.5%, dog 0.0%, draw 1.5%`.
- Reproduction / inspection path: run a small `OfficialMatchEngineDriver` sweep with equal ratings and only `CoachPolicy(catch_posture=...)` changed.
- Suggested fix direction: in `run_autonomous_game`, pass the defense team’s policy into `resolve_throw()` for target catch decisions, while keeping offense policy for thrower/target selection.
- Regression gate: add an official integration test proving `policy_b.catch_posture` changes B’s catch attempts when B is defending, and that equal-rating “go for catches” is not catastrophically worse for the team selecting it.

### Finding 2
- Severity: **High**
- Evidence: 400-trial supported probe: official moments emitted `dramatic_catch 24.48 per match`, `late_game_escape 4.63 per match`, `comeback 1.42 per match`. Code emits `DramaticCatch` on every catch-return at [official_engine.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/official_engine.py:727>) with no cap or rarity threshold.
- Why it matters: Moment events risk becoming replay spam rather than recognition. Tests only require presence of moment kinds, not upper bounds.
- Reproduction / inspection path: `python tools\tier_engine_health_probe.py --driver both --trials 400`.
- Suggested fix direction: promote only unusually high-leverage catches/late escapes to moments; keep routine catches in the canonical event log.
- Regression gate: add moment-rate upper bands per driver, especially official `dramatic_catch` and `late_game_escape`.

### Finding 3
- Severity: **Medium**
- Evidence: Official probe at 400 trials/rung: draws were `30.25%` at +0, `25.75%` at +24, `19.25%` at +48, `17.0%` at +72. Foam scoring awards 0 points for unresolved games at [official_scoring.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/official_scoring.py:56>), and `run_autonomous_match()` labels those as `no_point` at [official_engine.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/official_engine.py:974>).
- Why it matters: The edge curve is monotonic, but regular-season standings can still feel draw-heavy at even or near-even matchups.
- Reproduction / inspection path: same 400-trial probe, plus per-rung outcome count.
- Suggested fix direction: either tune official elimination decisiveness further or add honest survivor-clock framing/tiebreak policy where the product wants fewer standings draws.
- Regression gate: add even-rung and +24 draw-rate gates, not only top-rung draw cap.

### Finding 4
- Severity: **Medium**
- Evidence: Rec opening rush context reports `proximity_modifier` and `fatigue_delta` at [rec_engine.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/rec_engine.py:837>), but those values are not used in hit math or fatigue application. Search found use in presentation/tests, while generic `engine.py` does apply rush modifier/fatigue.
- Why it matters: Some rush-target/rush-risk controls are partly recap/context flavor in the rec driver. `rush_commit` affects sprinters and tick-0 throw cap, but `rush_target` and the shown rush modifiers do not materially change resolution.
- Reproduction / inspection path: inspect `rec_engine._rush_context_for_throw()` and `_resolve_throw()`.
- Suggested fix direction: either wire these values into rec resolution/fatigue, or stop presenting them as mechanical proof.
- Regression gate: policy A/B probe where `rush_target` changes measurable early possession/first-hit outcomes.

### Finding 5
- Severity: **Medium**
- Evidence: Existing focused tests passed: `34 passed`. Current gates cover rec OVR slope/floor, official OVR slope/floor/top draw cap, and moment presence. They do not catch official catch-posture inversion, moment spam upper bounds, even-rung draw density, or rec rush-target inertness.
- Why it matters: The current test suite protects against old flat-OVR regressions but misses player-trust regressions in tactics and replay pacing.
- Reproduction / inspection path: [test_official_engine_balance.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_official_engine_balance.py:24>), [test_engine_health.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_engine_health.py:17>).
- Suggested fix direction: add small policy-differential probes beside OVR probes.
- Regression gate: one official tactics integration test, one rec rush-target test, and moment upper/lower rate bands.

## Balance Matrix

| Area | Current evidence | Risk | Recommended probe/test |
|---|---|---|---|
| Official OVR curve | 400 trials: +0 36.0%, +24 49.5%, +48 63.2%, +72 72.0% | Healthy curve, but tactics bug contaminates interpretation | Keep OVR gate; add tactic-neutral and tactic-variant curves |
| Rec OVR curve | 400 trials: +0 50.7%, +24 57.5%, +48 64.5%, +72 67.2% | Healthy, slightly soft top-end but acceptable | Keep `test_ovr_curve_rec_driver_smoke` |
| Official draws | 30.25% at even, 17% at +72 | Standings/replay trust risk | Per-rung draw cap, especially +0/+24 |
| Rec draws/stalls | 2.2% aggregate draws; stall reset exists | Low draw risk; rush/stall proof needs coverage | Count `stall_reset` and match length distribution |
| Throws/catches | Official catch retune fixed OVR slope; catch posture is inverted | Blocker | Defense-policy catch posture integration test |
| Tactics | Rec has meaningful approach/catch/target tests; official mapping unit tests exist | Official integration broken | Outcome-level policy probes |
| Moments | Rec and official emit plenty | Official and rec moment spam risk | Upper/lower bands per moment kind |
| Ratings | Rating fields feed throw/catch/dodge/fatigue math | Strong | Preserve OVR curve probes |
| Archetypes | Engine reads ratings, not archetype enum directly | Mainly presentation/lineup identity, not direct match identity | Only test direct archetype influence if product wants it |
| Constants/config | Many constants are top-level helpers, not config | Tunability friction | Centralize balance constants or document owner layer |

## Confirmed strengths
The engine driver split is clean: `DriverMatchInput`/`DriverMatchOutput` isolate rec and official drivers in [engine_driver.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/engine_driver.py:14>). Seeded probes are reproducible through `tools/probe_lib.py`. Rec balance is currently credible: low draw rate, monotonic OVR curve, and rating-fed fatigue/throw/catch/dodge math. Official OVR reward is real after the catch retune, and focused tests passed.

## Open questions
Should official foam regular-season matches preserve real no-point draw density, or should the manager game add a product-level tiebreak/framing rule? Also, should archetypes directly affect match behavior, or remain derived labels over ratings plus lineup/development semantics?

## Suggested next prompt
“Fix the official catch-posture policy inversion, then add balance regression gates for official defensive catch posture, official moment-rate upper bounds, and even-rung foam draw density. Keep the audit read/write scope limited to engine code and focused tests.”