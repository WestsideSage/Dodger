# V18 — Development & Mortality (retrospective)

Date: 2026-06-10. Sprint plan (all measurements, BEFORE/AFTER tables, gate
results): `docs/specs/2026-06-10-v18-development-mortality-sprint-plan.md`.
Commits: `5fb72d4` (Task 0 plan + MILESTONES V17 doc-lag), `b236fc0` (Task 1
dev-arc probe + BEFORE baseline), `bacd4b1` (Task 2 dev-ceiling overhaul),
plus the Task 3/D3 ship commit.

## What shipped

1. **Dev-ceiling overhaul** (`development.py`): growth budgeted directly in
   OVR points as a fraction of remaining headroom (close rate 0.40, arrival
   floor 3.0), spent gap-proportionally on the five OVR skills with an
   archetype-primary bias; identity stats on a half-pace parallel track;
   decline path and upgrade-branch RNG stream unchanged. Full-time starters:
   headroom closure 20–34% → **96–100%**, ceiling shortfall ~10 OVR →
   **≤0.5**, archetype-independent (was 82%-vs-52% pool efficiency by
   archetype), AI symmetric.
2. **Vet seeding + honest mortality** (`career_setup.py`,
   `offseason_ceremony.py`, `development.should_retire`): role-banded
   curated ages (Captain 31–33 … Rookie 18–20, owner-cited Teamfight
   Manager 2 mix), synthetic `seasons_played_prior = age − 19` consumed ONLY
   by retirement biology (recorded history stays honest on every display
   surface), and the stale-recent fix (benched-all-season vets read
   recent_eliminations 0). First league retirement: season 9 on 8/8 seeds →
   **season 3.0–3.1**, steady ~1.8 retirements/season, HoF cadence revived.
3. **Recruiting parity (owner D3, decided 2026-06-10)**: AI clubs sign up to
   3/offseason against a 12 ceiling — the same plays as the player. League
   churn 5.0 → **15.0 signings/offseason**; the engaged-user snowball that
   Task 2 escalated (41% title share) resolved to **22.5%** (parity 16.7%),
   with the AI league overtaking a non-improving user by S8.
4. **Knock-on re-tune**: the vet mix moved club recruitment profiles
   (uncourted snipe rate collapsed 54% → 16%); `CONTESTED_USER_OFFER_BASE`
   90 → 85 restored the V16 targets (43% uncourted / 12% courted), witnesses
   re-derived per the pinned procedure.

## What we learned

- **Pace is not a snowball knob.** Close rate 0.40 vs 0.35 produced the same
  engaged OVR-edge curve; the snowball was the structural 3-vs-1 signing
  asymmetry expressing through delivered ceilings. Measuring the knob's
  non-effect was what turned the escalation into a crisp owner decision.
- **Symmetry is the honest fix.** No dev-side handicap could have closed the
  gap without violating the no-hidden-boosts rule; giving the AI the same
  plays fixed the league and made engagement worth ~6pp above parity instead
  of 24pp.
- **Seeding changes move markets.** Roster ages feed recruitment profiles;
  any future curated-seed change should re-run `contested_offer_probe.py`
  before trusting the witness pins.
- **Aggregate-derived "recent" fields lie about absentees.** The
  `recent_eliminations` stale-read had silently disabled the age-36
  retirement gate for benched vets since V1.

## Flagged for V19 planning

- **Passive lineup cliff**: one offseason lineup-optimize click separates
  22.5% from 2.5% title share; the auto-pilot default (creation order,
  signings at slot 6) needs a product decision.
- **S5 retirement cohort wave** (~5 in one offseason, fresh careers only) —
  fixed same-day after the owner delegated it: vet age bands widened
  (Captain 30–34, Anchor 27–31), spike 5.1 → 4.0 with mortality spread
  S2–S10; contested market re-probed byte-stable.
- **League OVR inflation watch**: delivered ceilings converge the league to
  high-80s OVR by S10; presentation consideration for V20/V21.

## Verification

Full `python -m pytest -q` green (incl. 14 new permanent gates in
`tests/test_v18_ceiling_delivery.py` + `tests/test_v18_mortality_seeding.py`;
all existing development/dynasty/contested pins). 8-seed × 10-season probe
sweeps, engaged + passive, BEFORE and AFTER, recorded in the sprint plan. No
match-engine, golden-log, or frontend changes (build/lint and Playwright not
applicable per the plan's Task 5 scope).
