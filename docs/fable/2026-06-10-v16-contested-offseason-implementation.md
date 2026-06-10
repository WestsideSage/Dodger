# V16 — Contested Offseason: Implementation Handoff (2026-06-10)

One-session implementation of all seven V16 plan tasks
(`docs/specs/2026-06-09-v16-contested-offseason-sprint-plan.md`), directly
after the Task 0 sweep (`2969271`) landed. Retro with the measured
before/after and design narrative:
`docs/retrospectives/2026-06-10-v16-contested-offseason-retrospective.md`.
Learnings: `docs/learnings/2026-06-10-v16-contested-offseason-learnings.md`.

## Process (how this was built)

1. **Understand workflow** — nine parallel subagent readers mapped every
   touchpoint (picker, band machinery, dormant round system, roster
   mutation, frontend, history queries, probes, test landscape, service
   glue) to exact symbols/lines before any edit.
2. **TDD per task** — each task's plan-prescribed test was written first and
   watched fail: the no-leak serialization pin, band narrowing, public-order
   pin, same-seed determinism, the courted-vs-uncourted cause→effect proof,
   AI-churn and cap pins, the season_10-vs-season_2 regression, and the
   dynasty gate.
3. **Measured tuning** — `tools/contested_offer_probe.py` (new) swept 60
   seeds to characterize rival offers on the top prospect (84.9–111.7,
   median 99.0) and tune `CONTESTED_USER_OFFER_BASE/WEIGHT` to the D2
   semantics: uncourted star pick sniped 54%, contact+visit 22%, interest-100
   7%. Witness seeds for the cause→effect tests come from the probe's
   printed list.
4. **Adversarial review** — a six-lens review workflow ran over the diff;
   the tests lens completed with measured findings (three majors: auto-pick
   behavioral-leak unpinned, interest-100 flow pins balance-dependent, gate
   bounds toothless vs revert — ALL fixed, plus six minors). The remaining
   five lenses (leak/determinism/flow/copy/drift) were re-audited inline
   after the subagent pool hit its session limit: drift clean (zero engine
   files in the diff), leak clean (only dormant V2-A modules still read
   true_overall), determinism/flow/copy audited against the final code.

## Key implementation facts (for the next agent)

- `recruitment.conduct_recruitment_round` now returns `ContestedPickOutcome`
  (wraps the round result + user offer/interest/rival context). Its old
  callers were test-only and were updated.
- `recruitment._eligible_ai_offer_clubs` is the single gate for who bids:
  under the D3 cap (`AI_OFFSEASON_SIGNINGS_PER_CLUB`), below the roster
  ceiling (`AI_OFFSEASON_MAX_ROSTER`), never the user. Flow tests that need
  uncontested picks monkeypatch THIS to `set()` — never re-introduce
  interest-based "guarantees" (balance-dependent, margins as thin as 3.7).
- `offseason_ceremony.sign_chosen_rookie_contested` returns
  `(player|None, outcome_dict|None)`; outcome kinds: `signed` /
  `free_agent_signed` / `sniped`. `(None, None)` = unknown id (the 409).
- `offseason_ceremony.ensure_ai_offseason_signings` is the idempotent AI
  sweep (state key `offseason_ai_signings_done_for`), called at every
  recruitment-close path AND inside `begin_next_season` as the safety net.
- The signing-outcome rides ON the recruit response (the SPA replaces the
  beat wholesale — `OffseasonBeatBase.signing_outcome`); the class-report
  cards persist rival signings permanently.
- `offseason_presentation` recruitment beat: `other_signings` is now real
  (AI moves) and the signing-cards pool join was fixed from class_year+1 to
  the CURRENT class (the +1 join could never resolve a prospect).
- Prospect band generation is center-jittered
  (`ScoutingBalanceConfig.public_band_center_jitter = 8.0`) — this adds an
  RNG draw per prospect, so **new-career prospect pools differ from pre-V16
  at the same root seed** (existing saves keep their persisted pools).
  Witness-seed tests document re-derivation via the probe.
- `tools/dynasty_health_probe.py` drives the shipping contested path and
  records `user_snipes` + `ai_signings` per season; `TestDynastyHealthGate`
  consumes it (runtime ~30s for 4×6 with churn).

## Plan deviations (source wins — full detail in the retro)

symmetric-band fix (required, unplanned); D2 user-offer retune (plan's
"stands" was unsatisfiable); `recruit.fit` stays flavor (no consumer);
no-leak pin at the HTTP wire instead of a response_model (WT-2/3 stripping
hazard); round credibility unified to career-wide history.

## Verification gate (all fresh, this session)

1. `python -m pytest -q`: **1,350 passed, exit 0** (25 net-new tests; the
   known `test_server_save_boundary` flake did not fire across four full
   runs this session).
2. `npm run build` exit 0; `npm run lint` exit 0.
3. Dynasty probe before/after attached in the retro (title share 41.7% →
   12.5%; churn 0 → 5.0/offseason; AI rosters 6 → 10; snipes 0 → 5/24).
4. Targeted Playwright (chromium, auto-started uvicorn): recruit board,
   legibility surfaces, maximized playthrough QA, API smoke,
   standings/history — see "Live verification" below.
5. Live prod-server browser walk across two offseasons — see below.
6. Docs updated in the same pass: STATUS (top Shipped entry + Open Work #7
   closed + header), MILESTONES (V16 Shipped + retro-path convention fixed
   per AGENTS.md), V16 plan status header, retro + learnings, this handoff.

## Live verification evidence (prod server, fresh build, throwaway career, deleted after)

Targeted Playwright (chromium, 21 tests): recruit board ×9, legibility
surfaces ×8, maximized playthrough QA, API smoke, standings/history lane —
**21/21 green** after fixing one PRE-EXISTING stale spec
(`standings-history-lane.spec.ts` still expected the pre-UI/UX-v2 "Archive
Through"/"Current Record" glance labels; updated to the shipped "Season
Range"/"All-Time Record" copy — not a V16 break).

Two-offseason browser walk (default seed 20260426, `v16-walkthrough` save):

1. **Band display** — Signing Day rendered every prospect as a `KnownValue`
   estimated band ("OVR 43–93 · Scout to narrow") with interest %, the new
   fog-of-war disclosure, and zero bare prospect OVRs (accessibility-tree
   verified).
2. **A real snipe** — picking top prospect Noor Perez produced the live
   snipe banner: *"Lunar Syndicate signed Noor Perez — their offer 101.9
   beat yours 100.1. Your interest was 56%, built from 0 recruiting
   actions. Your signing slot was not used — pick from the remaining
   class."* No error, no slot consumed, list re-rendered minus the prospect.
3. **Post-signing reveal** — the next pick won uncontested ("your offer
   97.2 stood alone") with the reveal line *"Scouted 38–88 → verified OVR
   57"* and the Latest Signing panel showing the verified number.
4. **The market moves mid-round** — by pick 2, five other prospects had
   already signed with AI clubs inside round 1 (the class report showed
   "Your Picks (1) / Rival Picks (5)" with per-club cards).
5. **AI roster change → visible fate change** — Northwood Ironclads went
   1-2-2 in season 1, signed Callum Saito (verified OVR 70) on Signing Day,
   and went **5-0-0 and won the season-2 championship** (standings/history
   endpoint, numeric season ordering correct).
6. **Second offseason, user skips entirely** — the AI sweep still fired:
   five fresh signings (incl. Rowan Cole, OVR 77, to Lunar) in
   `other_signings` and the class report.
7. **Zero console errors or warnings** across the entire walk.

One found-and-fixed during the walk: the class-report card for a sniped
pick said "never on your board" (the pre-V16 reason classifier only knew
courtship flags, not bids). The user's Signing Day offer is now persisted
(`recruitment_offer`, source='user', saved post-resolution for clean crash
retries), `load_user_bid_player_ids` feeds `build_signing_cards`, and a
lost bid is classified as a "surprise" with the honest reason *"{club}'s
offer beat yours on Signing Day."* — pinned in
`tests/test_signing_day_payload.py`.
