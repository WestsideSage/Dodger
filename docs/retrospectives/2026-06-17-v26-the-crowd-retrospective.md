# V26 — The Crowd: Retrospective

Date: 2026-06-17
Spec: `docs/specs/2026-06-17-v26-the-crowd-spec.md`
Plan: `docs/specs/2026-06-17-v26-the-crowd-sprint-plan.md`
Branch: `feature/v24-the-board` (the Climb-Era arc; merges to main as a unit).

## What shipped (7 phases)

The world got a crowd — built mostly by **reviving dormant-but-built code** and
wiring it to the V22–V25 economy, all behind `world.pyramid_world_active()` so
legacy / non-pyramid saves stay byte-identical.

1. **Facilities revival + modernization.** The web offseason fed `facilities=()`
   for every club, silently suppressing every effect. Now facilities are
   PERMANENT user-owned buildings bought with treasury (`facilities_office.py`,
   the V24 network-upgrade pattern), stored in `dynasty_state`; the legacy CLI
   per-season path is untouched. New types: Training Hall (a meaningful
   headroom-capped practice-credit dev effect), Stadium, Merch Center. Removed
   the dead `scouting_*`/`sync_throw` `DevelopmentModifiers` fields (no web
   consumers). `FacilitiesUpgradePanel` in the Dynasty Office.
2. **Club fan ledger + web prestige growth.** First Climb-Era migration
   (`_migrate_v19`): `club_fans` / `player_fans` running totals + an append-only
   `fan_ledger` receipt log. `fan_economy.award_season_fans` grows the user
   club's fans from real events (wins, promotion, titles/cups, Worlds finals),
   each a receipt. Ported the **dormant CLI prestige award to the web** offseason
   so V24 Contender/credibility finally rise on web saves.
3. **Player followings** from persisted award moments (MVP +
   best-thrower/catcher/newcomer in `signature_moments`) — a star accrues a
   following a benchwarmer / AI player does not.
4. **Fan income** — matchday (fans drawn, capped by stadium) + merch (club fans +
   star followings, ×1.5 with a Merch Center) join `apply_season_finances` + the
   Recap finances block.
5. **Bench roles** (one per non-starter, per season): Mentor (per-youngster
   practice growth scaled by the mentor's identity traits — their **first honest
   consumer**), Analyst (a `targeting_read_bonus` on the user's preps scaling
   with `tactical_iq`), Ambassador (monetizes his following into merch income).
6. **Media mini-events** — a conditional `media_event` offseason choice beat whose
   effects land ONLY in fans / prestige / a one-season credibility bonus.
7. **Balance + verification.**

## Measured evidence (probes)

- `tools/fan_income_probe.py` — fan income is **3%→42%** of a competitive finish's
  prize money across District/Challenger/Premier and a founder→beloved-dynasty fan
  curve; **never reaches prize money** at any tier (a meaningful margin, never
  tyranny). Pinned permanently by `test_v26_fan_income::test_fan_income_never_rivals_prize_money`.
- Phase gates prove every effect is real, not flavor: a Training Hall raises a
  youngster's development delta; a Mentor lifts a youngster scaled by identity
  traits (and a weaker-identity mentor lifts less); an Analyst's targeting bonus
  scales with `tactical_iq`; an Ambassador's income scales with his following; a
  media choice changes only fans/prestige/credibility (the isolation fence).

## Findings / decisions

- **The facility effects were sub-rounding.** The existing `DevelopmentModifiers`
  give ~0.13–0.2 OVR/season (invisible, and capped by the +9 season cap). So the
  Training Hall's effect routes through the **practice-credit channel** (a real,
  headroom-capped ~2 OVR), and 3 of the 6 legacy facilities (Film Room / Analytics
  / Chemistry Lounge) are web-no-ops kept CLI-legacy and excluded from the web
  catalog (disclosed).
- **Prestige growth was CLI-only** — a latent bug (V24 Contender read a frozen
  prestige on web). Ported to the web offseason, pyramid-gated.
- **`_MAX_OFFSEASON_BEAT_INDEX` again.** The media beat made it the second beat to
  trip the V25 clamp lesson — bumped 10→11 with the canonical tuple + the guard
  test, and the pinned beat-tuple witness updated.
- **Schema-witness churn.** The v18→v19 bump broke seven `== 18` version pins;
  fixed (canonical `19` for the one version test, drift-proof
  `CURRENT_SCHEMA_VERSION` for the "reaches current" checks).

## Disclosed deferrals

- **Bench-role visual assignment control.** The engine + API + endpoint + office
  payload are done and tested; the dropdown UI rides a follow-up (needs the bench
  roster surfaced in the payload).
- **Player district / in-game moments for followings.** Players carry no district
  and `MomentKind` events are replay-only (not persisted) — followings draw from
  the persisted award moments instead. A player-district field + moment
  persistence would extend them.
- **Records/milestone followers** — Phase 3 used award moments; record-based
  followers would need a post-`ratify_records` placement.
- **Info/tactical facilities** (Film Room / Analytics / Chemistry Lounge) stay
  CLI-legacy until their web effects are wired.
- **In-season media events** — offseason beat only in v1.
- **Live prod-server browser walk** — recommended for the owner's first
  playthrough; the engine, the live offseason service flow, and the FE build are
  all verified in-process.

## Verification

- `python -m pytest -q` green (real exit code, no pipe), incl. 6 new V26 test
  files (facilities, club fans, player fans, fan income, bench roles, media).
- `npm run build` + `npm run lint` clean.
- The fan-income probe passes with the measured margins above.
