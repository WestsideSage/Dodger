# V3 Balance Report

## Project Trajectory

### WHERE WE WERE
Previous versions introduced deep scouting systems (V2-A), dynamic AI recruitment (V2-B), expanded coach policies (V2-D), and deterministic playoff brackets (V2-F). The game engine functioned smoothly but lacked a mechanism to control active rosters, allowing unlimited lineup sizes to distort fatigue and strategy. AI teams began accumulating long-term prospects, but the long-run mathematical boundaries of development were untested.

### WHERE WE ARE
V3 successfully integrates the 6-player active roster limit into the core engine logic while reserving the remaining players for bench roles. The match engine probabilities remain structurally sound (passing 100% of Monte Carlo tests). Player development correctly bounds stat inflation by applying growth multipliers linked to rigid trajectory potentials, naturally preventing runaway power creep. Retirements process cleanly at logical decline points (e.g., severe age drop-offs).

### WHERE WE ARE GOING
For V4, the focus must shift towards ensuring AI teams can actively compete on a dynasty timeline rather than just a single-season timescale. The current AI logic prioritizes filling immediate holes ("Need Drafting") over securing foundational talent, making it highly exploitable for a human manager. Furthermore, several match strategies are mathematically suboptimal and require tuning to reflect their intended risk/reward behavior.

## Simulation Evidence

- **Commands run:** `python qa_v3_playthrough.py`, `python -m pytest tests/test_monte_carlo.py -q`
- **Number of seasons/matches simulated:** Full 15-game multi-club season loop with off-season beats and deterministic testing validating probabilities across thousands of mock events.
- **Seeds/configs used:** `phase1.v1` configuration, baseline randomizers via deterministic seeded namespacing.
- **Summary of results:** The match engine and career trajectory logic operate deterministically without hard crashes. Stat growth operates smoothly within boundaries, but AI club construction shows signs of exploitable weakness over multiple seasons.

## Statistical Anomalies

- **Metric:** Player Rating Floor Decline
- **Expected behavior:** Players who play far past their physical peak experience sharp rating decline, eventually forcing retirement or benching.
- **Actual behavior:** Ratings can mathematically decline to `1.0` (`_apply_delta` boundary in `development.py`) if age requirements are circumvented or a player refuses to retire naturally.
- **Likely cause:** Minimum bounds check is absolute (1.0) rather than a softer baseline (e.g., 30.0).
- **Severity:** Low. The retirement logic acts as an effective safety net for extreme edge cases, forcing out players under 52/58 OVR, but the hard 1.0 floor is an unnatural theoretical state.

- **Metric:** Rush Fatigue Penalty vs. Accuracy Bonus
- **Expected behavior:** Rushing provides a situational offensive boost at the cost of high energy expenditure.
- **Actual behavior:** The configuration maxes rush accuracy bonuses at `0.08` (8%) while fatigue costs scale up to `0.35` (35%).
- **Likely cause:** `rush_accuracy_modifier_max` and `rush_fatigue_cost_max` in `phase1.v1` configuration are disproportionate.
- **Severity:** Medium. The risk/reward math makes high `rush_frequency` coach policies strictly suboptimal over a full match.

## AI Logic Critiques

- **Over-Valuation of "Need" in Recruitment:** In `build_recruitment_board()`, the AI computes a target score using a `10.0` multiplier on `need_score` versus a baseline `public_score`. This forces AI teams to aggressively over-draft low-overall players simply because they fit a missing archetype, passing on generational or star talents that a human manager will effortlessly scoop up.
- **Lack of Roster Pruning:** AI clubs add players via Recruitment Day but lack a proactive "Release" mechanism to clear dead weight. As rosters grow beyond the active 6-player limit, AI teams do not consolidate talent or cut severely degraded veterans, artificially bloating the bench and limiting their recruitment budget flexibility.
- **Static In-Match Tactics:** AI clubs use their fixed `CoachPolicy` values indiscriminately, regardless of match context. For example, they will maintain high `risk_tolerance` or `tempo` even when down to a single player against a full opponent squad.

## Tuning Recommendations

- **Variable/system:** Rush Tactic Risk/Reward (Engine Config)
- **Current behavior:** 8% max accuracy boost vs 35% max fatigue cost.
- **Suggested change:** Increase `rush_accuracy_modifier_max` to `0.15` and reduce `rush_fatigue_cost_max` to `0.20` in `phase1.v1`.
- **Expected effect:** Rushing becomes a viable high-pressure tactic for AI and human teams rather than a mathematical trap.
- **Risk:** Could make aggressive teams overly dominant early in matches.
- **Required test:** Monte carlo probability distribution check on aggressive policies vs passive policies.

- **Variable/system:** AI Draft Weightings (Recruitment Domain)
- **Current behavior:** `need_score` multiplied by `10.0`, drowning out pure overall value.
- **Suggested change:** Reduce `need_score` multiplier from `10.0` to `4.0` in `build_recruitment_board()`. Increase `prestige` multiplier slightly to give strong AI clubs an edge in securing "Best Player Available".
- **Expected effect:** AI teams draft smarter, challenging human players for high-ceiling prospects even if they don't immediately "need" them.
- **Risk:** AI might overlap archetypes, causing redundant benches.
- **Required test:** A 5-season headless loop verifying AI roster diversity remains healthy.

- **Variable/system:** AI Roster Cuts (Franchise Management)
- **Current behavior:** Players stay on rosters until natural retirement; no active cuts.
- **Suggested change:** Implement an AI routine during the offseason `Retirements` or `Recruitment` beat that identifies and releases the worst bench player if the club exceeds 9 total players.
- **Expected effect:** Keeps AI budgets lean and ensures they participate actively in free agency/recruitment.
- **Risk:** AI might accidentally cut a developing prospect with low current OVR.
- **Required test:** Verify AI cut logic respects `potential` trait over raw `overall()` for players under age 24.

## Integrity Check

- **Monotonicity:** Preserved. Development logic clearly limits exponential growth via potential ceilings.
- **Symmetry:** Preserved. AI and humans operate under the same rating formulas.
- **Seeded determinism:** Preserved. No unseeded RNG usage found; all recruitment and development paths derive from root seeds.
- **Explained variance:** Maintained. The gap between `rush_frequency` modifiers is entirely explainable via existing equations, just poorly tuned.
- **Difficulty without buffs:** Maintained. AI does not receive hidden rating boosts to compensate for its recruitment flaws.

## Final Verdict

**Conditionally Ready.** The current balance logic structurally supports V3 and provides a reliable baseline for the match engine. However, before the game transitions into deep multi-season V4 features, AI roster management (Need vs. Value drafting, Roster Pruning) must be addressed, or the simulation will devolve into a trivial exercise for a human manager building a dynasty.