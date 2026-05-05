# V4 Balance Report

**Date:** 2026-04-30  
**Milestone:** V4 Web Architecture Foundation  
**Role:** Lead Game Systems & Balance Analyst  
**Scope:** Read-only engine, AI, tactics, progression, scouting, and web-playability audit before V5 planning.

## Project Trajectory

### WHERE WE WERE

V3's balance report identified two meaningful pre-V4 risks:

- Rush was mathematically unattractive: the old report called out an 8% max accuracy bonus against a 35% max fatigue cost.
- AI dynasty competition could be exploitable because recruitment over-weighted immediate roster need and AI rosters lacked pruning.

V4 has partially closed both gaps. `phase1.v1` now uses `rush_accuracy_modifier_max = 0.15` and `rush_fatigue_cost_max = 0.20`, and AI roster pruning now exists through `trim_ai_roster_for_offseason()`. Recruitment need weighting is now `4.0`, matching the prior recommendation.

### WHERE WE ARE

The match engine is structurally healthy at the extremes. In a controlled 500-match test, a 99 OVR team beat a 56 OVR team 498 times, with only 2 weak-team wins. That is a good sign: superior teams are not being randomly blasted by far weaker teams under normal seed variance.

The curated league, however, is statistically flat. Across 20 full regular seasons and 300 matches, favorite win rate was only 51%, and active roster OVR had effectively no correlation with points in the generated league sample. This is not a match-engine failure by itself; the curated clubs are all tightly clustered around the mid-60s, so randomness and policy shape the table more than raw roster quality.

The web replay flow exposes the right underlying math when it can reach a fresh match. In a fresh API-equivalent web career, saving max-risk tactics produced a replay payload where Aurora's policy snapshot showed maxed `risk_tolerance`, `sync_throws`, `rush_frequency`, `rush_proximity`, `tempo`, and `catch_bias`; the first throw included `rush_context.proximity_modifier = 0.075` and `fatigue_delta = 0.1`.

The live browser playthrough against the current local DB hit a known V4 recovery problem: Hub showed Week 5 as playable, but `Play Next Match` returned "No matches simulated." That means the current local web surface can prevent a player from validating replay balance if the save cursor is stale.

### WHERE WE ARE GOING

V5 should target a feel where:

- Ratings matter more clearly across a full season without turning every upset into a bug.
- Every visible tactics slider has an observable, named engine effect.
- Roster management becomes a real web loop, not only a read-only table.
- Scouting/recruitment becomes a playable information economy in React rather than mostly hidden persistence/domain machinery.

## Simulation Evidence

- Read first: `AGENTS.md`, `docs/specs/MILESTONES.md`, and `docs/retrospectives/v4/2026-04-29-web-architecture-handoff.md`.
- Prior baseline: `docs/retrospectives/v3/2026-04-29-v3-balance-report.md`.
- Headless simulation: 20 regular seasons, 300 matches.
- Controlled mismatch: 500 matches of 99 OVR vs 56 OVR.
- Tactics matrix: 400 matches per policy variant against a baseline mirror team.
- Browser/API artifacts:
  - `output/v4_balance_simulation_summary.json`
  - `output/v4_balance_api_playthrough.json`

## Statistical Anomalies

### 1. Curated League OVR Does Not Predict Standings

Across the 20-season sample, active roster OVR to points correlation was approximately `0.002`. This is mostly caused by the current curated rosters being too compressed: most active averages sit in the low-to-mid 60s.

Impact: V4 parity is good for a demo league, but poor for a manager game where roster-building needs to feel causal.

Recommendation: For V5, widen default club identity bands. Let true contenders average roughly 70-74 active OVR, mid-table clubs 63-68, and rebuilders 56-62. Keep single-match variance, but make season-long tables read more like roster quality plus policy.

### 2. Rush Frequency Is Binary, Not a Frequency

`rush_frequency = 0.01` and `rush_frequency = 1.0` produced identical controlled results when `rush_proximity = 1.0`: both went 184-216 against baseline over 400 matches, with identical average event count and rush modifiers.

Cause: engine rush context treats any positive `rush_frequency` as active. The magnitude of `rush_frequency` is recorded but does not scale chance, modifier, or fatigue.

Impact: The slider is misleading. The player can set "barely rush" or "always rush" and get the same math if proximity is unchanged.

### 3. Sync Throws Has No Engine Effect

`sync_throws = 0.0` and `sync_throws = 1.0` produced exactly identical controlled outcomes against baseline: 195-205, identical average ticks, identical resolution counts.

Cause: `sync_throws` is stored, displayed, and serialized, but the engine does not consume it in throw selection, tick pacing, accuracy, fatigue, or target logic.

Impact: This is the highest-priority tactics honesty issue. A visible slider promises coordinated volleys but currently changes no gameplay.

### 4. Catch Bias Is Often Masked By Roster Shape

Catch decisions are mathematically wired, but many equal-rating matchups attempt catches at a 100% rate regardless of policy because catch ratings clear both threshold and dodge guard. This makes the slider feel less distinct in average-roster play than the UI implies.

Impact: Catch bias may work in edge cases while remaining hard for players to observe in normal matches.

## Gameplay Inspection

The extreme mismatch test passed the "99 OVR should not be blasted by 56 OVR" check. A 0.4% weak-team win rate is acceptable for a chaotic dodgeball model.

The live web inspection surfaced a different player-facing problem: the current local DB can display a playable pre-match state when no match is actually available. That does not corrupt engine math, but it blocks practical balance inspection through the browser and makes a healthy engine look broken.

## Tactics

Tactics saving works through the browser. I set several sliders to 100%, saw the UI switch from Saved to Unsaved, saved the policy, and confirmed the saved policy in the replay payload on a fresh career.

The mathematical issue is slider honesty:

- `tempo` changes tick advance and therefore match pacing.
- `risk_tolerance` changes thrower choice and catch threshold behavior.
- `rush_proximity` changes accuracy and fatigue while rushing.
- `catch_bias` changes catch-attempt thresholds, but can be masked.
- `target_stars` and `target_ball_holder` affect target scoring.
- `rush_frequency` is effectively an on/off switch.
- `sync_throws` is currently inert.

## Club Management and Progression

V4 web roster management is read-only. The Roster page shows six players, all starters, with ratings and roles, but there are no web controls to reorder lineups, release players, sign prospects, or execute scouting/recruitment decisions.

The backend and older GUI/CLI code contain lineup, signing, AI trimming, and recruitment hooks, but the web product surface does not expose them yet. Therefore V4 cannot fully prove that player roster moves translate into gameplay through the supported web path.

## Economy and Scouting Cost

The scouting point economy is coherent on paper:

- Baseline scout throughput is around 5 points per axis per week.
- KNOWN at 35 points typically takes 5-9 weeks depending on scout/prospect fit.
- VERIFIED at 70 points typically takes 10-18 weeks.
- With 3 scouts and a 25-prospect class, the player can deeply know a small shortlist, not the full class.

This is a good strategic cost profile for V5, but it is not yet web-playable. There is no V4 React Scouting Center loop where the player spends assignment time and sees the opportunity cost unfold.

## AI Logic Critiques

### AI Tactics Are Static

AI clubs run fixed `CoachPolicy` values. They do not adapt to current score, living player count, matchup ratings, fatigue, or opponent policy. This is acceptable for V4 parity, but V5 needs situational policy adjustments if the AI is expected to challenge a human manager.

### Inert Sliders Weaken AI Differentiation

Because `sync_throws` is unused and `rush_frequency` is binary, clubs that differ mainly on those fields are less distinct than their profiles imply.

### AI Roster Improvements Exist But Are Not Web-Visible

AI roster trimming now protects starters and cuts low-value bench players, which addresses a V3 concern. But because web recruitment/progression is not yet surfaced, the player cannot observe the AI roster economy directly in V4.

## Tuning Recommendations

### 1. Make Sync Throws Real

Suggested V5 implementation:

- Low sync: current single-player throw behavior.
- Medium sync: small accuracy bonus when multiple living teammates remain, small tempo cost.
- High sync: larger accuracy or catch-pressure bonus, but higher fatigue and slower tick advance.

Suggested initial constants:

- `sync_accuracy_modifier_max = 0.05`
- `sync_tick_penalty_max = 1`
- `sync_fatigue_cost_max = 0.08`

Required test: `sync_throws=0.0` and `sync_throws=1.0` should produce statistically different event distributions over 300+ mirror matches.

### 2. Convert Rush Frequency From Boolean To Rate

Suggested V5 behavior:

- Roll a deterministic per-throw rush activation chance from `rush_frequency`.
- Apply proximity modifier and fatigue only when that throw is a rush.

Suggested initial formula:

- `rush_active = rng.unit() < rush_frequency`
- `rush_accuracy = (rush_proximity - 0.5) * rush_accuracy_modifier_max`
- `rush_fatigue = max(0, rush_proximity - 0.5) * rush_fatigue_cost_max`

Required test: `rush_frequency=0.25` should produce roughly one quarter of throws with active rush context.

### 3. Widen Curated Club Strength Bands

V4's demo league is too flat for season-long statistical readability. V5 should give clubs sharper identity:

- Contenders: 70-74 active OVR
- Mid-table: 63-68 active OVR
- Rebuilders: 56-62 active OVR

Required test: over 20 simulated seasons, active OVR should have a positive points correlation while preserving meaningful upset rate.

### 4. Add Web Roster/Lineup Controls Before Judging Progression Feel

The engine already honors default lineup order and active starters. V5 needs web controls to reorder starters, bench players, sign prospects, and release fringe players before progression balance can be honestly evaluated from the supported player surface.

Required test: change a starter through the web UI, simulate the next user match, and verify the replay roster snapshot uses the new starter set.

### 5. Bring Scouting Into The Web Loop

Keep current thresholds for the first V5 playable pass. They appear strategically sound: KNOWN is achievable for focused targets, VERIFIED is expensive, and weaknesses matter.

Do not tune scout costs downward until the React loop exists. The current numbers should be tested with actual assignment friction before changing the economy.

## Final Verdict

**Mathematically sound, but not yet tactically honest enough for V5.**

The core match engine respects major rating differences and no obvious hidden boost was found. V4's main balance debt is not raw probability failure; it is that some visible tactics do not map to real gameplay, the curated league is too statistically flat to make roster strength legible, and the web product does not yet expose the progression systems needed to judge long-term manager balance.
