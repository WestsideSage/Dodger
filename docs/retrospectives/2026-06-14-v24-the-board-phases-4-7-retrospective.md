# V24 — The Board: Phases 4-remainder, 5, 6, 7 retrospective

Date: 2026-06-14
Branch: `feature/v24-the-board` (not yet on main)
Spec: `docs/specs/2026-06-12-v24-the-board-spec.md`
Era authority: `docs/specs/2026-06-12-climb-era-vision.md` (§ "V24 — The Board")

This session closed the remaining V24 phases on top of the already-shipped
Phases 1–4 (whole-world AI recruiting, districts, motivations, funnel + focus
list). Each phase was built test-first, full `python -m pytest -q` green at each
boundary, FE `npm run build` + `npm run lint` clean.

## What shipped (one commit per phase)

- **Phase 4 remainder — visit scheduling (`7a41522`).** A campus visit is hosted
  at one of the user club's upcoming HOME fixtures (`select_visit_fixture`, a pure
  helper picking the earliest unbound home game at/after the current week).
  `apply_recruiting_action` binds it (pyramid), persists the prospect→fixture map
  (`recruiting_visit_fixtures_json`), reports it on the action result, mirrors it
  on the board, and refuses a visit when no home fixture remains. Legacy keeps the
  unscheduled visit.

- **Phase 5 — visible rival suitors + interest race (`3ffbcd3`).** New
  `prospect_market.py` derives named rival suitors per focused prospect
  deterministically: a DAMPENED talent read (`RIVAL_PURSUIT_TALENT_WEIGHT = 0.65`,
  so the race is winnable rather than theater) + the division tier's upside
  appetite + a stable per-(prospect, club) jitter, gated by WILLINGNESS (a club
  the prospect would veto is not a real suitor). The dormant
  `prospect_market_signal` table is revived (written on each courtship action) and
  surfaced on focused board rows. Leading compounds: a contact/visit while leading
  lands a momentum bonus scaled by the weeks left (`RIVAL_MOMENTUM_PER_WEEK = 0.8`,
  capped at 12). **Measured** (`tools/rival_momentum_probe.py`): early-beats-late
  **8/8 seeds, +5 interest edge** — the momentum constant made visible.

- **Phase 6 — money-gated Scouting Network (`05b9437`).** New
  `scouting_network.py` (kept DISTINCT from the Scout verb and the named-scout
  engine — the spec's trap #2). A per-club L1/L2/L3 level gates a full sheet vs a
  bare name. Reach band derives PURELY from `hidden_trajectory` (no new draw):
  STAR/GEN = NATIONAL, IMPACT = REGIONAL, else DISTRICT. L1 = home + neighbor
  districts (`world.district_neighbors` ring), L2 adds regional + district-anywhere,
  L3 adds national; a non-district founder runs a generic local net (so a fresh
  founder is never blinded to the whole class). The user's level starts by division
  tier (Premier takeover inherits L3, a D3 founder L1) and upgrades are a treasury
  sink COMPRESSED by the scouting head
  (`staff_effects.scouting_network_cost_compression` — the staff cost-compression
  consumer). New `POST /api/recruiting/network/upgrade` + `scouting_network` board
  status. AI clubs carry a tier-based level with a deterministic blind-spot jitter
  (`AI_NETWORK_BLINDSPOT_RATE = 0.25`), so gems fall through. **Measured**
  (`ai_board_coverage_probe`, blind spots active): still **100% coverage / new
  blood in every division every seed**. Live-stack check on a seeded D3 founding
  career: L1, next L2 @ 127k (140 × head compression), 15 visible + 6 name-only.

- **Phase 7 — frontend + class wire + Signing-Day motivations
  (`459823f`, `b2fb658`).** `ProspectCard` / `DynastyOffice` render name-only
  cards (redacted, null-safe sort/filter), the Scouting Network panel + upgrade
  button, the rival interest race, and the scheduled visit fixture. The class wire
  (`_emit_class_wire` at the shared `_apply_round_signings` chokepoint → a
  league-wide `news_headlines` line on any STAR/GENERATIONAL signing, surfaced atop
  the `/api/news` wire). Signing-Day picker carries the same motivation grades +
  dealbreaker the board showed (`available_recruitment_choices` reuses
  `_motivation_fields`), rendered in `RecruitmentChoice.tsx`.

## Traps hit and recorded

- **Function-local-import shadowing.** A redundant `from .persistence import
  load_career_state_cursor` inside `apply_recruiting_action` shadowed the
  module-level import, raising `UnboundLocalError` when I referenced it earlier in
  the function. Removed the local import. Lesson: a function-local import makes a
  name local for the WHOLE function, including lines above it.

- **The blind-founder bug (found via a broken PT4 test).** A Premier-tier user at
  L1 — or any club whose home isn't a recognized district — was blinded to the
  entire class. Fixed two ways: the user's network DEFAULTS by division tier
  (Premier inherits L3), and a non-district home runs a generic local net at L1
  (`home_recognized=False`). Two PT4 Prospect-Pulse tests were courting `pool[0]`,
  now sometimes beyond reach — updated to court a network-visible prospect (an
  intentional-change witness update, exactly the spec's discipline).

- **Rival pursuit scale.** Pursuit keyed directly off ceiling made every good
  prospect's rivals sit near 100 → the race was unwinnable and momentum never
  fired. Dampened with `RIVAL_PURSUIT_TALENT_WEIGHT` so courtship can win winnable
  races; documented as probe-tuned sim-design.

- **`/api/news` does not read `news_headlines`.** The wire payload builds from
  `match_records`; the class wire needed an explicit merge in `build_news_payload`
  plus a world-wide signing chokepoint (`_apply_round_signings`, not just the
  user's contested round).

## Remaining (disclosed)

- The milestone-close **deep interactive browser walk** of a founding D3 career
  across several seasons (the recruiting board PAYLOAD is verified correct
  end-to-end on a seeded career; the click-through is the one piece not yet driven
  live).
- Disclosed deferrals carried from earlier phases: AI motivation symmetry, the
  Development ceiling-delivery ledger, in-season interest momentum from fit.
- V24 is on the branch, not main. The full Worlds-parity end-state residual is
  closed by V25's uphill poaching, exactly as the vision states.
