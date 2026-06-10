# V19 — Decision Wiring (sprint plan)

Date: 2026-06-10. Sequenced by
`docs/specs/2026-06-10-post-v16-greenlit-backlog-sequencing-plan.md` (§2 row
V19, §3 item 3 — "may split at its own planning pass"; this is that pass).
Owner dispositions: `docs/fable/2026-06-10-owner-decision-log.md` §1.2/§1.3/
§1.5 (promises revive+rename+consumer; staff/department orders get real
effects), §5.3 (slot roles WIRE), §5.4 (stamina + tactical_iq WIRE), §5.5
(rec rush targeting WIRE), §4.3 (week-1 scouting yields real intel). Plus
two V18-queued items decided/delegated 2026-06-10 in-session: the auto-pilot
lineup default and the ceiling-scarcity/OVR-integrity watch.

## Relation to Prior Specs

- Follows V18 Development & Mortality (shipped 2026-06-10; retro
  `docs/retrospectives/2026-06-10-v18-development-mortality-retrospective.md`).
  Every consumer wired here is measured against the SETTLED V17 official
  economy and V18 development/mortality/parity league — that ordering was
  the point of the sequence.
- System truth sources (do not re-derive; verified 2026-06-09/10):
  department orders flavor-only except dev_focus
  (`docs/fable/2026-06-09-adversarial-qa-trust-audit.md`), promises
  backend-complete with no UI and no mechanical consumer (same report),
  slot-role liability model consumer-less in shipping engines
  (`docs/fable/2026-06-09-systems-balance-audit.md`), stamina/tactical_iq
  measured dead-flat on officials (V17 attribute matrix), rec
  `rush_target` disclosed-dead (`rec_engine.py`), week-1 scouting yields
  0/5 tendency reads (`docs/fable/2026-06-09-first-hour-onboarding-review.md`).

## Goal

Every knob the game presents is a real, disclosed, measured lever: staff and
department orders do something, promises bind, roles and the remaining
attributes resolve in the engines, scouting buys information, and the
fast-forward path stops silently punishing players for a hidden lineup
default.

## Non-goals

- No new match-rule fidelity work (entering-player micro-fouls stay V20+).
- No replay/broadcast presentation work (V20) beyond honest event labels for
  newly-wired effects.
- No copy/voice passes (V21) beyond the disclosures the wiring makes true.
- Champion-shape parity perfection — re-measured after V19a, gates are
  "no trap, no dominant option", not 33/33/33.

## Split decision (this planning pass)

**V19a — engine consumers** (one consolidated golden-log/WT-7/balance-pin
churn cycle, mirroring V17's lesson):

1. **Slot-role effects**: the four court roles get real, disclosed engine
   effects in both shipping engines (officials + rec), replacing the
   advisory-only fit notes. Design constraint: effects keyed on role-fit
   must not resurrect the "liability fiction" — they are bonuses/tradeoffs
   the Lineup Editor discloses, not hidden penalties.
2. **Stamina consumer**: stamina already prices OVR (1 of 5); wire its
   per-stat effect (late-game/4th-quarter-of-match fatigue shading on
   throw/dodge quality is the natural official-engine consumer; rec engine
   analog via round-depth). Must NOT double-price stamina into a dominant
   stat — measure with the attribute matrix.
3. **Tactical_iq consumer**: shades decision quality (target selection /
   catch-attempt judgment), the stat the archetype copy already claims.
4. **Rec rush targeting**: honor `rush_target` on rec careers the way V17
   wired officials; flip the Policy Editor disclosure.

V19a instruments + gates: `tools/decision_impact_probe.py` attribute matrix
(no displayed stat materially below even baseline; no stat > catch's
dominance), posture/tactic spreads stay trap-free, OVR slope/floor gates
hold, WT-7 + frozen-seed pins re-captured once as a documented intentional
change, dead-attribute invariance pins in `tests/test_attribute_consumers.py`
FLIP to consumer pins (same-seed invariance must now FAIL for wired stats —
the pin inverts), dynasty health gate green.

**V19b — management lanes** (no engine churn; each lands with its own
measurement):

5. **Department orders / staff real effects**: each weekly order gets ONE
   real, disclosed, measured mechanical effect (e.g., conditioning →
   stamina-drain modifier, medical → recovery, training → small dev-pool
   shading, scouting → intel cadence below, culture → interest/credibility
   shading). Anything we choose not to wire is REMOVED from the UI rather
   than left as flavor (owner: "staff is basically meaningless right now" —
   the fix is meaning, not better flavor copy).
6. **Promises revive + rename + real consumer**: player-facing surface with
   plain language (the term "Promise Lane" failed owner comprehension);
   promise kept/broken feeds the now-mechanical recruiting economy
   (interest/credibility deltas into contested offers) so results bind.
7. **Week-1 scouting intel**: a scout action yields actual information
   (tendency reads / band narrowing on day one); where it can't, the UI
   never displays ambiguity (the "Scouted · no tape yet" badge stays only
   while honest).
8. **Auto-pilot lineup default** (V18-queued, designed below).
9. **Ceiling scarcity / OVR integrity** (owner philosophy, measured tune —
   below).

Order within the milestone: V19a first (engine settles, one pin churn),
then V19b measured against it. V19b items 5–7 may land in any order; 8 and
9 are independent and may ride early.

## Task 8 design — auto-pilot lineup default

V18 measured the cliff: one offseason lineup-optimize click separates 22.5%
from 2.5% title share, because the auto-pilot keeps the creation lineup
order and seats every signing at slot 6 forever. The product decision
(recommended default, implement unless the owner objects):

- At season rollover (`begin_next_season`), the user lineup default is
  **repaired or re-seated**:
  - If it references retired/departed players → always repaired (it is
    mechanically broken).
  - If the user has NEVER manually saved a lineup (no `/api/lineup` save on
    record — add a `user_lineup_customized` state marker set by the manual
    save path) → re-seat via the same optimizer the AI uses. Riding the
    beats without ever opening the Lineup Editor means delegating the
    lineup, the same way auto-piloted weeks delegate tactics.
  - If the user HAS saved a custom lineup of still-active players → respect
    it exactly, even if suboptimal. Their decision is the product.
- Disclosed: the offseason flow states when the staff re-seated the lineup
  (one honest line; no silent changes), and the Lineup Editor reflects it.
- Measurement: re-run the passive 8×10 sweep — passive title share should
  move from 2.5% toward the engaged curve; the engaged sweep must not
  change (it already optimizes).

## Task 9 design — ceiling scarcity / OVR integrity (owner philosophy)

Owner (2026-06-10): *"OVR should be really telling of how strong the roster
is… If you only have one elite dev and a whole bunch of low ceiling players,
even if you have the best development you shouldn't have a high OVR. Your
OVR should be a reward and monument to the effort it took to build the
roster"* — citing College Football 26's star-inflated team OVR as the
anti-pattern.

Current truth (verified): player OVR is the flat mean of the five core
skills (`models.py:100`) and every team-strength representation uses the
fielded-six mean — there is NO star-weighting anywhere, so the CFB26
inflation cannot happen structurally. The V18 watch item is different:
delivered development + a prospect pool whose effective potential averages
~87 converges the whole league to high-80s OVR by S10, compressing
differentiation (final-season OVR edges ~±1.5).

The honest lever is **ceiling scarcity at generation**: elite potential
should be rare, so assembling a high-OVR roster requires sustained
scouting/courtship/retention work — OVR as a monument to roster-building.
Measured tune of the prospect-pool potential distribution (config layer:
`prospect_class_size`, trajectory shares, potential roll bands):

- Gates: dev-arc delivery stays ≥95% (the V18 promise is untouchable —
  scarcity lives in the CEILINGS, never in delivery); league mean fielded
  OVR at S10 stays differentiated (target: best-vs-mean AI spread at S10
  ≥ ~4 OVR, up from ~2.5); contested Signing Day targets re-verified
  (scarcer elites make top picks MORE contested — re-run
  `contested_offer_probe.py`, expect a BASE re-tune per the pinned
  procedure); dynasty health gate green.
- Trap (V18 lesson, twice): ANY change to seeded/generated player
  distributions moves the contested market — re-derive witnesses in the
  same change.

## Verification matrix

- V19a: full `python -m pytest -q` (pin churn documented per AGENTS
  golden-log rule), `decision_impact_probe` matrices BEFORE/AFTER in this
  doc, dynasty sweep spot-check.
- V19b per task: focused tests + the task's named probe; frontend changes
  ride `npm run build`/`lint` + targeted Playwright on touched surfaces +
  a live prod-server walk for the promises/orders surfaces (new UI).
- Milestone close: retro in `docs/retrospectives/`, STATUS + MILESTONES,
  push.

## Task 0 — Land this plan

Commit this document; add the V19 "Planned" row to
`docs/specs/MILESTONES.md`; link from `docs/STATUS.md`.
