# V16 — Contested Offseason: Sprint Plan

Status: planned 2026-06-09 (product-director pass). Active milestone authority
once Task 0 (land the working tree) is complete.

Relation to prior specs: consumes the dormant V2-B recruitment-round system
(`docs/archive/specs/v2/2026-04-28-v2-b-recruitment/design.md`) as the
contested-resolution mechanism; executes the convergent #1/#2 recommendations
of all five 2026-06-09 cross-disciplinary reports in `docs/fable/`
(dynasty-retention §8.1–8.2, systems-balance §7.2, UI/UX-v2 §12.1); inherits
the integrity contract in `docs/specs/AGENTS.md` and ADR 0002
(faithfulness-first). Supersedes nothing — it wires existing, honest systems
into the shipping loop.

---

## 1. Current-state summary (verified 2026-06-09)

- `main` = `origin/main` = `6bfc775`. Master-roadmap Phases 0–7, Section 4
  (briefs 4.1–4.8), V15, the tokenless-e2e sweep, and the Command Center
  redesign are all SHIPPED. Section 4 is closed; do not reopen.
- The working tree holds six verified-but-uncommitted 2026-06-09 passes
  (trust audit, first-hour, watchability, systems balance, dynasty retention,
  UI/UX v2): ~58 modified + 11 untracked files. Each pass recorded full-suite
  green; this planning pass re-ran `python -m pytest -q` on the exact tree:
  **green, exit 0**. Landing this tree is Task 0 — nothing else starts first.
- The five reports converge on the same two product failures, both measured:
  1. **The league is static.** AI clubs cannot sign prospects in the shipping
     path (zero roster churn over 7 probed seasons); an engaged user wins
     ~60% of titles at a compounding +8–9 fielded-OVR edge
     (`docs/fable/2026-06-09-dynasty-progression-retention-review.md`).
  2. **Recruiting is solved.** The offseason picker exposes
     `prospect.true_overall()` sorted descending
     (`offseason_ceremony.available_recruitment_choices`, lines ~693–708), so
     scouting is strategically void and the in-season Scout/Contact/Visit
     loop buys nothing (interest has no consumer — disclosed as flavor by the
     balance pass).
- The mechanism to fix both **already exists and is test-covered but
  dormant**: `recruitment.conduct_recruitment_round` (recruitment.py:580)
  prepares AI offers, computes user offer strength from real persisted
  interest + real program credibility (fixed by the 2026-06-09 trust audit),
  resolves contested rounds with sniping, and records signings. Its own code
  comment says: "Kept correct for when a contested Signing Day is wired in."
  The fog-of-war display machinery also exists: `recruiting_office.py:156`
  already computes `public_ovr_band [low, high]`, and the frontend legibility
  toolkit has `KnownValue` states.

## 2. Candidate comparison (scored 1–5; risk/dependency scored 5 = safest)

| Candidate | Player impact | Trust impact | Impl. risk | Testability | Scope containment | Dependency risk | Alignment | Total |
|---|---|---|---|---|---|---|---|---|
| **A. Contested Offseason (this plan)** | 5 | 4 | 3 | 5 | 4 | 4 | 5 | **30** |
| B. Official catch-economy retune | 4 | 4 | 2 | 4 | 3 | 2 | 4 | 23 |
| C. Replay intent frames ("V16A" research) | 4 | 3 | 2 | 3 | 2 | 3 | 4 | 21 |
| D. WT-20 Official Live Rules | 3 | 4 | 2 | 4 | 3 | 1 | 3 | 20 |
| E. Trust cleanup pack (promises, dept orders, stats truth) | 2 | 5 | 4 | 4 | 4 | 3 | 4 | 26 |
| F. Dynasty texture (veteran seeding, record milestones) | 3 | 3 | 4 | 4 | 4 | 3 | 4 | 25 |
| G. First-hour leftovers | 2 | 3 | 4 | 3 | 4 | 4 | 3 | 23 |

Why the alternatives lose:

- **B** is explicitly owner-gated by its own audit ("needs golden-log
  strategy + owner sign-off"); outcome-changing engine work with frozen-winner
  churn. Queue it as the *next* milestone after V16, with the posture-spread
  and attribute-sign gates from the balance report.
- **C** is a research draft by its own header ("not an implementation plan
  yet"); engine persistence changes; premature.
- **D** is hard-blocked: the reduced-blocking resolution parameters are OPEN
  per `docs/specs/2026-06-01-workflow0-primary-source-rule-verification.md`.
  Constraint honored: it does not ship until the owner resolves them.
- **E** scores well on trust but is low player-impact maintenance; its two
  biggest items (promises, department orders) are owner keep/drop decisions,
  not buildable today. One small E item (season-id sort) is folded in here
  because it protects this milestone's own multi-season verification.
- **F** items are real but secondary; veteran seeding changes new-career RNG
  streams and deserves its own measured pass.

## 3. Recommended milestone

**V16 — Contested Offseason.** Playable thesis: *the offseason class is a
market, not a menu — AI clubs sign real prospects, scouting determines what
you know, and your in-season courtship changes what you can land.*

Why it beats the field: it is the only candidate that (a) all five
independent reports rank first or second, (b) consumes dormant tested code
instead of building a new system, (c) touches no match engine (no golden-log
risk; existing invariance pins protect it), (d) has its measurement
instrument already committed (`tools/dynasty_health_probe.py` +
`tools/decision_impact_probe.py`), and (e) directly serves the
decision-traceability north star — it turns four honest-but-flavor terms
(interest, fit, pipeline, credibility) back into mechanical truths.

## 4. Goals / non-goals

In scope:

1. AI clubs sign prospects in the offseason (league churn + snowball cap).
2. Signing Day shows scouted knowledge, not `true_overall()` (fog-of-war
   truth; reveal at signing).
3. The user's pick resolves through the contested round system so interest +
   credibility buy real odds (sniping possible, honestly explained).
4. Recruiting terms flip back from `flavor` to mechanical in
   `frontend/src/legibility/terms.ts`, with copy naming the actual consumer.
5. A dynasty-health CI gate pinning the probe bounds.
6. One hygiene fix: the `/api/history/my-program` `season_id` string-sort trap
   (`season_10 < season_2`), because this milestone's verification is
   multi-season.

Out of scope (explicit non-goals — do not let them creep in):

- WT-20 Official Live Rules (owner-blocked; unchanged).
- Official catch-economy retune (next milestone candidate; owner-gated).
- Replay intent frames / watchability engine work (research stage).
- Promises lane and department orders wire-or-drop (separate owner
  decisions; STATUS Open Work #5/#6).
- Development close-rate retune, veteran age seeding, records-milestone
  presentation, `biggest_upset_win` ratification (dynasty report §7.3–7.5 —
  later texture passes).
- Any match-engine change. Rec and official engines must stay byte-identical
  on frozen seeds.
- In-season weekly recruiting chores; multi-promise contracts; NIL-style
  economy (roadmap non-goals, still binding).

## 5. Prerequisites

- **Task 0 below (land the working tree) is mandatory before any V16 work.**
- Owner decisions needed at Task 3 (defaults proposed so work is not
  blocked; the implementing agent should confirm in the handoff):
  - **D1 — Signing Day information model. OWNER-CONFIRMED 2026-06-10:
    scouted band** (`public_ovr_band` + `KnownValue` states), truth revealed
    only after signing ("A, for sure" —
    `docs/fable/2026-06-10-owner-decision-log.md` §2.2). Free agents keep
    visible true OVR — they are league veterans with public history.
  - **D2 — Snipe model.** Recommended: the user's pick is contested in the
    same round, interest-weighted (the existing
    `offer_strength = 100 + interest * 0.2` user advantage stands; tune via
    deterministic tests so an uncourted top prospect is genuinely losable
    and a heavily-courted one is near-safe). Zero-frustration alternative
    (user pick always succeeds, AI signs from the remainder) is the fallback
    if playtests show rage-quit risk.
  - **D3 — AI volume.** Recommended: at most 1 prospect signing per AI club
    per offseason (MVP knob, config-layer constant, not hardcoded in engine
    logic).

## 6. At-risk / deferred scope

- If the milestone runs hot, **cut Task 6 (CI gate bounds) last, Task 3's
  snipe tension to the D2 fallback second**. Do not cut Task 2 (AI roster
  mutation) — it is the milestone.
- `origin/playtest-fixes-2026-05-27` keep/delete decision (STATUS Open Work
  #3): 5-minute owner call, not blocking, not part of this milestone.
- Stray root screenshots `replay-official-strip-before/after.png`: **deleted
  2026-06-10** (together with the stale-save purge and the tracked playtest
  screenshot removal — see the owner decision log §6.3).

## 7. Ordered atomic tasks

**Task 0 — Land the six-pass working tree.**
Commit the current working tree to `main` (the six 2026-06-09 passes +
this plan's doc updates), excluding the two stray root PNGs and any local DB
files. Suite re-verified green (exit 0) on this exact tree 2026-06-09 by the
planning pass; `npm run build` + `npm run lint` were clean per the latest
handoff. One sweep commit is acceptable (file overlap across passes makes
per-pass splitting error-prone); push after commit. Update the STATUS header
commit pointer in the same commit.

**Task 1 — Signing Day payload truth (backend).**
In `offseason_ceremony.available_recruitment_choices`: stop emitting
`true_overall()`-derived fields for prospects (`overall`, `fit_score`, and
the descending-true-OVR *sort order*, which leaks the same information).
Emit `public_ovr_band` + scout-state fields (reuse the
`recruiting_office.py` band logic so the picker and the in-season board can
never disagree about the same prospect). Free agents unchanged (public OVR).
Pin at the serialization layer: a response-model test proving an unscouted
prospect's payload contains no true-OVR-derived value. Reveal truth at
signing: the existing scouted-estimate-vs-verified-OVR disclosure on Signing
Day (shipped in UI/UX v2) becomes the universal post-signing reveal.

**Task 2 — AI offseason signings (the league churn fix).**
Wire AI clubs into the offseason class. Resolution source:
`recruitment_domain.resolve_recruitment_round` prepared-offer machinery (via
`_ensure_recruitment_prepared`). Verify-and-close the known gap: confirm
whether AI signings recorded by `save_recruitment_signings` mutate AI
rosters in the shipping web path — the dynasty report measured that they do
not; wire roster mutation (`sign_prospect_to_club` semantics) for AI clubs,
keeping AI lineup-default convention (roster order, per the D1 fielded-six
decision history). Volume per D3. Respect AI roster caps and the existing
roster-repair floor. Determinism: all draws via `derive_seed(root_seed, ...)`
namespaces; same-seed careers must produce identical league-wide signings
(extend the existing dynasty determinism test).

**Task 3 — Contested user pick (the tension fix).**
Route the user's Signing Day pick through `conduct_recruitment_round`
(adapter in `offseason_ceremony` / `offseason_service`; keep
`sign_chosen_rookie` as the free-agent and fallback path). Interest +
credibility already feed the user offer. On a snipe: honest outcome UI in
`RecruitmentChoice.tsx` ("X signed with Y — their offer beat yours; your
interest was N%, built from M actions"), then re-pick from the remainder.
Roster-floor 409 behavior unchanged. Deterministic tests: (a) same seed →
same round outcome; (b) a courted prospect signs with the user where the
uncourted same-seed control is sniped — the cause→effect proof that
interest is now a real consumer.

**Task 4 — Term registry truth flip (frontend + copy).**
Flip `interest`, `fit`, `pipeline`, `credibility` in
`frontend/src/legibility/terms.ts` from `flavor` back to mechanical, with
copy naming the consumer ("strengthens your Signing Day offer in the
contested round"). Update the Recruit Board courtship disclosures the
balance pass added. Frontend has no test runner: verify via build/lint +
Python guards on any backend-rendered strings + the e2e specs in Task 7.

**Task 5 — `season_id` sort hygiene fix.**
Apply the `game_loop.season_sort_key` pattern to
`/api/history/my-program` (`hero.current` latest-season selection).
Regression test with a `season_10`-vs-`season_2` fixture. (Pre-existing trap
flagged by UI/UX v2 §10.1; in scope because V16 verification is
multi-season.)

**Task 6 — Dynasty-health CI gate.**
Pin `tools/dynasty_health_probe.py` small config (4 seeds × 6 seasons) in a
test with bounds from the dynasty report: engaged-user title share ≤ 0.70;
AI clubs never below 6 players; ≥ 2 distinct champions per 6 seasons (scale
of the report's ≥3/10); NEW: ≥ 1 league-wide AI prospect signing per
offseason while the pool is non-empty. Bounds are owner-tunable constants.

**Task 7 — Verification + docs closeout.**
Full `python -m pytest -q`; `npm run build` + `npm run lint`; targeted
Playwright (recruit board, maximized playthrough, offseason/ceremony specs —
update `RecruitmentChoice`-touching specs for the band display); live
prod-server browser walk across two offseasons on a throwaway career
(delete after), exercising: band display, a real snipe, the post-signing
reveal, and an AI club's roster visibly changing in Standings/History.
Update `docs/STATUS.md` (new top Shipped entry + close the static-league
and solved-recruiting findings), flip the V16 row in
`docs/specs/MILESTONES.md` to Shipped, retrospective per MILESTONES
conventions, session handoff in `docs/fable/`.

## 8. Acceptance criteria

1. **No information leak:** unscouted prospects' picker payload contains no
   `true_overall()`-derived field or ordering; pinned at the FastAPI
   response-model layer (the WT-2/3 field-stripping family taught us to pin
   serialization, not just builders).
2. **Scouting matters:** a max-scouted prospect renders a strictly narrower
   band than an unscouted one, picker and board bands agree, and signing
   reveals verified OVR with the scouted-estimate delta line.
3. **Courtship matters:** the Task 3(b) cause→effect test passes — interest
   changes a signing outcome on fixed seeds; sniped picks render the honest
   explanation with the interest evidence.
4. **The league moves:** probe runs show ≥ 1 AI prospect signing per
   offseason (pool permitting) and AI fielded-6 OVRs change across seasons;
   engaged-user title share ≤ 0.70 over the gate config.
5. **No engine drift:** existing frozen-seed/invariance pins for both match
   engines stay green untouched; no golden-log updates in this milestone.
6. **Determinism:** same `root_seed` careers produce identical league-wide
   offseason signings.
7. **Honest copy everywhere:** no UI string claims a recruiting effect
   without a wired consumer; the four terms are mechanical again.
8. **Suite + surfaces:** full pytest green; build/lint clean; targeted
   Playwright green; live two-offseason browser walk with zero console
   errors and zero horizontal overflow at 1440×900 and 1280×720.

## 9. Verification gate (run in this order before claiming done)

1. `python -m pytest -q` (full, green, no new flakes; note
   `test_server_save_boundary` known order-dependent flake — re-run in
   isolation if it fires).
2. `npm run build` + `npm run lint` (frontend/).
3. `tools/dynasty_health_probe.py` before/after comparison attached to the
   handoff (title-share curve, churn, roster floor, champions).
4. Targeted Playwright specs (chromium, live prod server with launch token).
5. Live browser walk per Task 7.
6. Docs updated in the same pass (STATUS, MILESTONES, retrospective).

## 10. Rollback / safety

- No schema migration is expected (`recruitment_offers`/`recruitment_signings`
  persistence shipped with V2-B). If one becomes necessary, bump
  `CURRENT_SCHEMA_VERSION` through `persistence.connect()` migrations only.
- `sign_chosen_rookie` remains intact as the free-agent/fallback path, so a
  revert of the contested-round adapter restores today's behavior without
  data damage. Legacy saves: contested flow engages at their next offseason;
  no retroactive changes to recorded history.
- Engine invariance pins (`tests/test_attribute_consumers.py`, WT-7 frozen
  winners, golden logs) are the tripwire against accidental outcome drift.

## 11. First implementation handoff prompt

> Read root `AGENTS.md`, `docs/README.md`, `docs/STATUS.md`, then
> `docs/specs/2026-06-09-v16-contested-offseason-sprint-plan.md` (this is the
> active milestone authority). Confirm `main` is at or past the Task 0 sweep
> commit (the six 2026-06-09 passes must be committed first — if the working
> tree is still dirty, STOP and land Task 0 per the plan instead).
> Then implement **Task 1 only** (Signing Day payload truth): make
> `offseason_ceremony.available_recruitment_choices` stop emitting
> `true_overall()`-derived fields and descending-true-OVR ordering for
> prospects; emit the scouted `public_ovr_band` reusing the
> `recruiting_office.py` band logic; keep free agents on public OVR; render
> `KnownValue` band states in `RecruitmentChoice.tsx`; pin the no-leak
> guarantee at the FastAPI response-model layer with a serialization test.
> Do not touch match engines, `conduct_recruitment_round` wiring (Task 3),
> or AI signings (Task 2). Verify with the focused new tests plus
> `python -m pytest -q`, `npm run build`, `npm run lint`, and update
> `docs/STATUS.md` in the same pass. Honest-reporting rules apply: if a
> claim in the plan disagrees with source, the source wins — report the
> discrepancy in your handoff.
