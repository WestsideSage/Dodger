# Post-V16 Greenlit Backlog — Sequencing Plan + V17 Sprint Plan

Date: 2026-06-10. Author: product-director sequencing pass requested by
`docs/fable/2026-06-10-owner-decision-log.md` ("Execution notes") and
`docs/STATUS.md` Open Work #7.

## 1. Current truth

- `main` = `origin/main` = `4020e1c` (V16 Contested Offseason shipped `0c9bf28`,
  retro in `docs/retrospectives/2026-06-10-v16-contested-offseason-retrospective.md`).
- Every open owner decision from the seven 2026-06-09 `docs/fable/` reports is
  answered and greenlit — dispositions in
  `docs/fable/2026-06-10-owner-decision-log.md`. Standing directive: *every
  unhooked system is hookup-able now; no mocks; wire it for real.*
- Already closed (do not re-plan): contested Signing Day, scouted-band picker,
  AI offseason signings, `season_id` string-sort family across history
  queries, credibility-fallback fix, saves/screenshot purges.
- Verified still open while writing this plan: `_CATCH_BIAS = 0.9` /
  accuracy+dodge negative EV (`official_resolution.py`), No Blocking is
  activation-logged but `no_blocking.resolve_contact_with_held_ball` has no
  engine caller enforcing Section 27 outcomes, `_HEADROOM_CLOSE_RATE = 0.9`
  (`development.py`), the All-Time Record "(incl. current)" suffix
  (`MyProgramView.tsx:295`, `server.py:1120`).

## 2. Backlog → milestone mapping

Every greenlit item, grouped so that each milestone is one coherent risk
surface and golden-log churn is consolidated instead of repeated.

| Milestone | Contents (decision-log refs) |
|---|---|
| **V17 — Official Engine Truth** (this sprint) | Catch-economy retune (§5.1); WT-20 No Blocking / throw clock / opening rush enforcement (§1.1); even-rung draw-texture gate folds in (§5.6) |
| **V18 — Development & Mortality** | Dev-ceiling overhaul: players actually reach ceilings (§2.3); 31–33yo vet seeding in curated rosters (§2.4); AI-symmetric development Monte Carlo re-run (§4.1) |
| **V19 — Decision Wiring** | Department orders / staff real effects (§1.3); promises revive + rename + real consumer (§1.2/§1.5); slot-role engine effects (§5.3); stamina + tactical_iq consumers (§5.4); rec rush targeting (§5.5); scouting yields real intel week 1 (§4.3) |
| **V20 — Broadcast Truth II** | Official replay live-per-event strip (§4.4); official intent frames (§7.4); stats truth: returns + `revivals_caused` (§7.7); survivors-column cleanup (§7.3); `test_server_save_boundary` flake investigation (§7.5) |
| **V21 — Presentation & Voice** | App-wide vague-language purge + voice upgrade (§4.2/§6.5); information-dedup pass (§3.4); zero-floats sweep incl. HoF legacy line (§3.3); Class Brief redesign (§4.6); records middle milestone tier (§6.4); All-Time Record completed-seasons-only (§6.7); loss-screen / scenario browser coverage, main ruleset first (§4.5/§7.6) |

Quick-win note: §6.7 (All-Time completed-only) is a two-file fix and may ride
along with whichever milestone next touches `server.py`'s history payloads.

## 3. Why this order

1. **Engine first (V17).** The catch economy currently makes two of the five
   displayed core skills (accuracy, dodge) *negative* EV at even strength —
   a trust hole in every official match — and WT-20 is the longest-standing
   open roadmap item. Both rewrite official-engine outcomes, so they share
   one golden-log/WT-7/parity re-pin cycle. Everything later that measures
   win rates (dev probes, decision wiring, intent frames) should measure
   against the settled engine, not the pre-retune one.
2. **Development second (V18).** Owner calls it "pivotal." It is independent
   of the match engines (offseason math), so it slots cleanly after the
   engine settles, and its instrument (`dynasty_health_probe` dev-arc trace)
   then reads true win-rate context.
3. **Decision wiring third (V19).** Wiring staff/roles/stamina/tactical_iq
   adds *new* engine consumers — done after V17 so each new consumer is
   measured once against the final economy. This is the widest milestone and
   may split (V19a engine-knob consumers / V19b management lanes) at its own
   planning pass.
4. **Broadcast truth fourth (V20).** Intent frames persist decision context;
   their shape depends on what decisions exist (V19) and what the engine
   resolves (V17). The per-event strip is display-side but joins on the same
   event metadata the engine work may extend.
5. **Voice last (V21).** Copy passes describe mechanics; run them after the
   mechanics stop moving so the purge doesn't have to repeat.

## 4. V17 — Official Engine Truth (sprint plan)

**Goal:** the official engine's economy rewards every displayed core skill,
and the three announced-only live rules (No Blocking, throw clock, opening
rush) mechanically resolve, with draws at even strength reduced to a
measured, honest texture.

**Non-goals:** rec-engine changes (beyond byte-identity verification), dev
math, recruiting, any UI redesign beyond disclosure copy that the
enforcement flips make true.

**At-risk/deferred temptations:** champion-parity *perfection* (gate is
"materially less defense-skewed", not 33/33/33); modeling fatigue for
officials (V19 stamina consumer decides this); replay presentation of the
new rule events beyond honest event labels (V20).

### Task 0 — Land the planning pass
Commit this plan + the seven untracked `.agents/skills/dodgeball-*` personas
(repo already tracks `.agents/skills/dodger-ui-teardown`).

### Task 1 — Catch-economy retune (outcome-affecting, measured)
- Baseline capture (BEFORE): `tools/decision_impact_probe.py` (attribute
  matrix + posture spread), `tools/tier_engine_health_probe.py --driver
  official`, `tools/archetype_champion_parity_probe.py`,
  `tools/official_match_probe.py`.
- Levers, in audit-recommended order (`2026-06-09-systems-balance-audit.md`
  §7.1): shade `p(catch|attempt)` by throw quality so accuracy buys
  catchability reduction (gives accuracy a defensive-economy answer); raise
  `_CATCH_BIAS` toward 1.2–1.3; optional catch-drop band only if the first
  two can't clear the gates.
- Acceptance gates (AFTER, on the same probes):
  - +12 accuracy and +12 dodge win% ≥ even-strength baseline (CI-overlap or
    better; was −8 to −10pp).
  - +12 catch stays clearly positive but its dominance shrinks (< +31pp).
  - OVR slope ≥ +10pp, +72 floor ≥ 56%, +72 draw rate ≤ 25% (existing gate).
  - `play_safe` floor ≥ 25% (existing gate).
  - Champion parity: Defensive Specialist title share materially down from
    73.8% (target ≤ 0.60), ≥ 3 distinct champions.
  - `TestDynastyHealthGate` still green (title share ≤ 0.35 etc.).
- Re-pin in the same change: WT-7 frozen winners/baselines in
  `tests/test_official_engine_balance.py`, any frozen-seed official
  byte-identity pins, golden logs if touched — documented as an intentional
  outcome change per `AGENTS.md`.
- New permanent gates: attribute-EV non-negativity for accuracy/dodge.

### Task 2 — WT-20 Official Live Rules enforcement + draw texture
- Re-read `docs/specs/2026-06-01-workflow0-primary-source-rule-verification.md`;
  the reduced-blocking resolution params are OPEN there — propose them
  *with measurement* in the implementation (owner ungated 2026-06-10).
- Wire `no_blocking` outcomes into the official engine (held-ball protection
  ends, body-extension outs), enforce the throw clock (violations already
  have event vocabulary), enforce opening rush on officials.
- Draw-texture gate: measure even-rung draws before/after (baseline 23–31%);
  propose and pin a ceiling with the measurement attached.
- Flip conformance-matrix rows announced-only → enforced; update Policy
  Editor disclosures and terms-registry entries the flip makes true; re-pin
  WT-7 winners/golden logs again.
- Update `docs/STATUS.md` Open Work #1.

### Task 3 — Verification sweep + retro
Full `python -m pytest -q`; `npm run build` + `npm run lint`; targeted
Playwright (official replay, aftermath, score parity); live prod-server
browser walk including loss screens on the main division ruleset; probe
records in the retro (`docs/retrospectives/`); STATUS update; push.

## 5. First implementation handoff

Implement V17 Task 1 now (this session continues into it): capture probe
baselines, retune `official_resolution.compute_throw_probabilities`, iterate
against the acceptance gates, re-pin, document.
