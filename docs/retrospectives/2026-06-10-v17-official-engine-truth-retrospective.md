# V17 — Official Engine Truth: Retrospective (2026-06-10)

Plan: `docs/specs/2026-06-10-post-v16-greenlit-backlog-sequencing-plan.md`
(the product-director sequencing pass over the owner-greenlit post-V16
backlog, `docs/fable/2026-06-10-owner-decision-log.md`). Commits: `e235326`
(plan + skill personas), `2dfc4a0` (Task 1 catch-economy retune), `bb07fda`
(Task 2 WT-20 enforcement + draw texture), plus this verification commit.

## What shipped

### Task 1 — Catch-economy retune (`2dfc4a0`)

The even-strength p(catch|attempt) was ~0.527 — far above the 1/3 EV-neutral
line (a catch is a −2 swing vs +1 for a hit) — so an on-target throw was
net-negative EV and two of the five displayed core skills were measured
liabilities. The retune shades catchability by throw quality (new
`_CATCH_THROW_QUALITY_SLOPE = 2.0`) and rebalances `_CATCH_BIAS` 0.9 → 0.7;
`_PLAY_SAFE_EVASION_BONUS` 0.25 → 0.10 in the same change (the old value was
priced for the old economy and made play_safe the new dominant posture).

| Probe (400 trials) | Before | After T1 |
|---|---|---|
| +12 accuracy vs baseline | 31.2 vs 38.2 (**−7.0**) | 54.2 vs 35.5 (**+18.7**) |
| +12 dodge | 30.5 (**−7.7**) | 39.2 (+3.7) |
| +12 catch | 71.5 (+33.3) | 62.7 (+27.2, still premium) |
| OVR slope / +72 floor | +36.0pp / 72.0% | +44.8pp / 79.8% |
| Champion parity max | Defensive 65.0% | Defensive 37.5% (near-parity) |

New permanent gates: `test_v17_no_displayed_core_skill_is_a_liability`,
`test_v17_catch_remains_the_premium_skill`.

### Task 2 — WT-20 Official Live Rules + draw texture (`bb07fda`)

**The stall autopsy (root cause of the draw artifact).** Stalled games had
6-9 throws in 200 ticks: when a holder was ruled out, their held balls
stayed assigned to them forever; once every ball was zombie-held, neither
side could throw and the game dead-aired to the tick cap. Measured: 552 of
1,572 uniform-even games stalled with both sides alive, each eating ~20 of
the 24 match minutes (matches played only 2-4 games).

**Fixes shipped:**
- *Ball lifecycle:* out players forfeit held balls (Section 24-core —
  `queue_player_holds_ball_forfeit`, finally invoked by the live loop);
  loose/forfeited balls re-enter via a per-tick retrieval pass; the thrown
  ball can no longer be handed to the player it just put out.
- *No Blocking (Section 27) enforced:* regulation models held-ball blocking
  (p≈0.65 at evens, keyed on blocker CATCH vs thrower power); the branch is
  disabled while No Blocking is active. Activation carries the sourced
  "balls do not reset" (fixing the unsourced `three_per_side`) and the
  sourced match-end source. Blocked throws are honest replay events.
- *Throw clock:* honestly dispositioned — the autonomous loop throws every
  ≤6s tick whenever a side controls a ball, so the sourced 10s/5s failure
  windows are structurally unreachable; no enforcement theater (ledger note).
- *Opening rush (disclosed sim-design, NOT USAD fidelity):* `rush_target`
  orders designated-ball holders; `rush_commit` shades the opening-exchange
  catch economy both ways; first offense is a seeded coin flip (retired a
  hardcoded team-A first-throw asymmetry).

| Draw texture (400 trials/fixture) | Before | After T2 |
|---|---|---|
| Uniform-even match draws | 33.5% (mostly 0-0/1-1 stalls) | **10.5%**, all equal splits |
| Spread-even match draws | 8.0% | 11.0%, all equal splits |
| Stalled games (both alive at cap) | 552 / 1,572 | **0 / 5,321** |
| Games per match | 2-4 | 12-14 |
| Draws across OVR rungs | 22.2% | 4.7% |

## Measured re-tunes during Task 2 (the honest tuning ledger)

1. **Initiative model rejected.** rush_commit as rank-based first-throw
   initiative measured hold_back +17pp dominant (first-mover DISADVANTAGE —
   the opening thrower feeds the catch economy in now-short games). Replaced
   with symmetric opening-exchange shading.
2. **go_for trap killed.** With blocking available, threshold 0.20 forced
   weak catchers into ~17-25% attempts instead of blocks: −15pp. Fixed by
   modernizing go_for thresholds (0.35/−0.25) and applying holder
   selectivity to the BINDING attempt bar (`_HOLDER_BLOCK_PREFERENCE`,
   final 0.06 — 0.12 over-suppressed the defensive shapes' catch economy).
3. **Block strength softened + re-keyed.** p≈0.74 power-keyed blocks made
   holders near-unattackable (BALL_HOLDERS targeting −10pp) and
   double-dipped the throwing shapes; final: p≈0.65, keyed on CATCH.

Final 400-trial tactic table: every axis within CI overlap (postures
40.8-49.5, rush_commit 44.0-46.2, targeting 45.8-47.2, baseline 49.0) — no
trap options, no dominant options. Final attribute matrix vs 47.5 baseline:
accuracy 78.2 / power 70.5 / dodge 61.8 / catch 85.8; stamina, tactical_iq
and the identity traits remain flat (V19 wires them).

## Known texture changes (deliberate, recorded)

- **Matches are full-length.** ~13 real games and ~860 replay events per
  match (was ~180). This is the faithful 24-minute / 3-minute-game USAD
  structure; replay speed controls (1x/2x/4x/skip) exist. Watch first real
  playtests for pacing complaints.
- **OVR expresses strongly.** +24 net OVR → 82.5% match win (best-of-13
  aggregation). League texture remains healthy (dynasty health gate green),
  but season-level snowball should be watched in V18's probes.
- **Champion-shape skew flipped.** Matched-OVR titles: Defensive 65-73.8%
  (pre-V17) → Power Throwers 63.8%. Gate passes (3 distinct, max ≤ 0.85).
  Carried as a V19 design item — the roles/stamina/tactical_iq wiring will
  reshape this economy and should target shape parity explicitly.
- **Rec careers unchanged** (no rec-engine edits; rec rush_target advisory
  retained — V19).

## Traps for future passes

- The WT-7/watchability pins are uniform-rating fixtures: posture/holder/
  block tuning doesn't bind there (everyone attempts), so those pins survive
  knob changes that DO move real-roster outcomes. Don't read "pins
  unchanged" as "no balance change."
- `CoachPolicy()` default `rush_target` is CENTER (overall-desc holder
  order), not NEAREST (slot order) — a power-only gradient makes CENTER and
  STRONGEST_SIDE coincide; divergence tests must vary a non-power stat or
  compare against NEAREST.
- PowerShell `*>` redirects write UTF-16; read probe outputs with
  `-Encoding Unicode`.

## Verification

- Full `python -m pytest -q` green twice (1,352 tests post-T1; **1,363
  post-T2**, zero failures), including 11 new WT-20 gates and the
  re-captured outcome pins. The first post-T2 full run caught a latent
  cloth bug the new ball lifecycle exposed: the equal-ball reachability
  discretion path had never executed in autonomous play (every ball stayed
  controlled forever), and its `to_official_event` call was missing the
  required `event_id` — fixed and re-run green.
- `npm run build` + `npm run lint` clean.
- Targeted Playwright **9/9 passed** (chromium, self-launched prod server:
  official-rules-replay, replay-score-parity, command-center-aftermath,
  wt22-decision-proof, tier1_recognition, v13_broadcast_layer ×2,
  maximized-playthrough-qa).
- Live prod-server browser walk (fresh official-foam takeover career):
  career creation → Command Center → Policy Editor (the
  enforced-sim-design rush note renders; the stale announced-only note is
  gone) → readiness gates → week sim → **win aftermath** (11-game set
  strip, 6-5 game points) → **full replay** (530 events; BLOCKED kicker
  with honest voice/detail lines; set strip; MODE "No blocking";
  ACTIVATED FREE ball state) → **loss aftermath** explicitly exercised
  (2-8 defeat: WINNER badge on the opponent, truthful "Outclassed across
  the sets" PRIMARY FACTOR) — zero console errors throughout. The walk
  also caught and fixed two stale truth surfaces: the ruleset-selector
  description and the replay MODE tooltip both still said No Blocking /
  throw clock were "not yet outcome-enforced." Walk save + e2e saves
  deleted afterwards (owner purge directive).
