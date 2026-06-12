# V23 — The World (implementation spec)

Date: 2026-06-12
Status: ACTIVE — Phase plan for the first Climb-Era milestone.
Authority: `docs/specs/2026-06-12-climb-era-vision.md` (owner-confirmed
2026-06-12). This spec makes the V23 open calls the vision doc deferred
("exact pyramid shape, witness strategy") and records what ships in each
phase. `docs/STATUS.md` stays build-state truth.

## What ships

A real **28-club world** for new careers, on the real engine end to end:

- **Three domestic tiers × 7 clubs**: D1 **Premier League** (the curated
  seven), D2 **Challenger League** (generated), D3 **District League**
  (generated; each club carries one of the seven district identities V24's
  Hometown motivation will reuse) — plus the **International Circuit**
  (7 generated clubs, the strongest field, its own annual round-robin).
- **Founding = bottom start**: build-from-scratch careers found in D3
  (the V22 founding-budget squeeze gets its narrative home). **Takeover =
  established start**: curated picks stay in the Premier League.
- **Movement, user included**: division champion (title-playoff winner)
  auto-promotes from D2/D3; the four best non-champion clubs by
  regular-season rank play a **promotion playoff** for the second slot;
  the **bottom two** of D1/D2 relegate — including the user club.
  Falling never fires you (founder-for-life). The Circuit is closed.
- **WORLDS from Season 1**: Premier champion + runner-up vs Circuit
  champion + runner-up (semis cross-paired: D1 champ vs Circuit RU,
  Circuit champ vs D1 RU), every season, recorded into history whether or
  not the player is anywhere near it.
- **Payouts scale by tier** (extends the V22 economy settlement): the
  District League is the 1.0× anchor — V22's payout/payroll squeeze was
  tuned at that scale and must keep holding where founders are born ("the
  squeeze, never a spiral"; a 0.35× D3 was measured to spiral a journeyman
  -staffed founder to −217k by season 3). D2 pays 1.35×, D1 1.8× — the
  climb's pull. V25's wage bills are what stop the top from un-squeezing.
  Disclosed in the finances ledger.

## Design decisions made here (within the vision's frame)

1. **Division champion = title-playoff winner** (the existing top-4
   single-elim per division). The promotion playoff field is the next four
   best clubs by *regular-season* standings after removing the champion.
2. **Worlds is a 4-club single-elim**, played after all domestic
   postseasons. Best-of-one matches, same as every playoff match today.
3. **Match-id scheme** (everything keeps the `{season}_p_` prefix so the
   regular-season standings exclusion works unchanged):
   - User's division title bracket: legacy ids (`_p_r1_m1`, `_p_r1_m2`,
     `_p_final`) — every existing surface (aftermath, ceremony, rivalry
     `was_championship`, economy bonus) keeps reading the user's title run.
   - AI division titles: `_p_div_{division}_r1_m1|_r1_m2|_final`.
   - Promotion playoffs: `_p_promo_{division}_sf1|_sf2|_final`.
   - Worlds: `_p_worlds_sf1|_sf2|_final`.
4. **The user plays every match they're in.** Promotion-playoff and Worlds
   matches are scheduled matches, so the existing weekly loop surfaces them
   interactively by construction; AI-only stages auto-sim at the same
   orchestration chokepoint as AI playoff matches today.
4b. **The user always plays week 1.** Seven-club divisions schedule one bye
   per week, and a new season must never open on "your bye week" — the
   user's division rotates its round labels (pure relabeling; pairings and
   seeded draws unchanged) at creation, at rollover, and in the
   schedule-reveal preview, which mirrors the rollover exactly.
5. **`season_outcomes` keeps meaning "the user's division champion"** (the
   celebrated outcome every ceremony surface reads). Pyramid facts —
   division champions, promotion/relegation, Worlds — live in a per-season
   postseason ledger + a `worlds_history` list, both JSON state.
6. **Back-compat by world flag**: `world_model = "pyramid"` state key, set
   at creation. Legacy saves (no key) run the exact current single-league
   code paths. No migration of old careers into the pyramid.
7. **Recruiting market stays the user's division** (the V24 Board frame:
   "25-prospect class, 7 clubs"). The AI Signing-Day sweep covers the
   user's division; all 28 clubs develop/age/retire and repair rosters.
   Honest scope line: deep cross-division recruiting is V24's milestone.
8. **Witness strategy (the honest cost)**: existing dynasty/balance gates
   pin the legacy 7-club world and stay green (engine-level gates are
   world-independent). New V23 gates pin the pyramid loop. Full witness
   re-derivation on the 28-club world is the LAST phase and may carry into
   a follow-up session — STATUS discloses until closed.

## Phases

- **Phase 1 — The world exists.** `world.py` (division defs, deterministic
  club/roster generation per tier), `division_membership` table (schema
  v18), both creation paths build the pyramid, 4 aligned round-robins in
  one season schedule. Gated by `tests/test_v23_world.py`.
- **Phase 2 — Division-aware surfaces.** Standings payload groups by
  division (`standings` = user's division for every existing consumer;
  `divisions` = the full pyramid + movement zones), user title bracket
  seeds from division-filtered standings, stage labels for new match ids.
- **Phase 3 — Postseason orchestration.** `pyramid_postseason.py`: AI
  division title brackets, promotion playoffs, Worlds — sequenced at the
  `_choose_next_user_match_after_automation` chokepoint; user-inclusive
  stages interactive; season completes only when the whole world's
  postseason is done. Gated by `tests/test_v23_postseason.py`.
- **Phase 4 — Movement + offseason truth.** Promotion/relegation computed
  and applied at `begin_next_season` (new memberships + new 4-division
  schedule), awards scoped to the user's division, payout tier scaling,
  postseason ledger + worlds history persisted, recap/news lines.
- **Phase 5 — Frontend.** Standings division tabs + promotion/relegation
  zones + pyramid view; offseason movement block; wizard founding copy;
  Worlds banner/history.
- **Phase 6 — Verification.** Full pytest, build+lint, live browser walk
  on a founded D3 career.

## Proof obligations (from the vision doc)

- Pyramid integrity: 4×7 world, intra-division schedules, determinism.
- Promotion/relegation flow gates incl. the user club both directions.
- Worlds-runs-from-S1 history gate.
- Determinism of the multi-season pyramid loop.
- Honest-disclosure fences: payout ledger names the tier multiplier;
  recruiting scope line; STATUS discloses the witness re-derivation state.
