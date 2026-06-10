# Dynasty Progression / Economy / Retention Review — 2026-06-09

Role: dynasty-mode designer, progression/economy analyst, long-term simulation
health reviewer. Question under review: **does a player have strong reasons to
care about season 2, season 5, and season 10 — and do the systems create earned
stories over time?**

Method note (per `AGENTS.md`): Pare MCP was not used for the simulation sweeps
and pytest runs in this pass — the evidence required custom probe CLIs run
through the project venv and raw sweep output; normal shell commands were used
and are recorded below.

---

## 1. Dynasty-health verdict

**The skeleton is real, but the league is a wax museum and the player's
structural advantages compound unanswered.** Every long-term surface is fed by
honest data (standings, champions, awards, career stats, HoF, records,
trophies, trajectories — no fabrication anywhere), and the multi-season loop is
deterministic end to end. But before this pass:

- The **AI league had zero roster movement for seven straight seasons** (no
  retirements until S8, no signings above the 6-player floor, no trades), so
  "rival programs" were six frozen faces.
- **Only the user can sign prospects** (the contested recruiting round system
  is dormant), and the Signing Day picker hands the player every prospect's
  TRUE overall sorted descending — recruiting is solved by clicking the top of
  a list, and it alone moves title share from ~21% to ~41% of seasons.
- **Development could not deliver its own promise**: the reps gate divided by
  a 1000-minute denominator that never matched either engine's measured scale,
  so every player past their practice window grew at 1–20% of the intended
  rate and stalled 15–22 OVR below the ceiling the Roster page advertises.
- Two of the three league-memory texture systems (**rivalries** and **team
  records**) were only ever written by the retired sandbox CLI — the web game
  read tables it never fed, so the Dynasty Office rivalry board and club
  record book stayed empty forever.

This pass fixed the broken truth/feeding paths (rivalries, team records,
reps gate, official-draw aftermath, roster-floor trap, "scouted" label lie)
and measured the rest. The remaining season-5 risks are design decisions —
chiefly AI recruiting access and the true-OVR reveal — listed in §7.

## 2. Multi-season evidence inspected / generated

All sweeps: new `tools/dynasty_health_probe.py`, which drives the SHIPPING
loop (`initialize_curated_manager_career` → `auto_pilot_weeks` per season →
`finalize_season` → `initialize_manager_offseason` → `sign_best_rookie` ×N →
`begin_next_season`) on in-memory saves. 8 seeds × 10 seasons per
configuration (80 simulated seasons per cell), official_foam, curated takeover
("aurora"), auto-pilot defaults. Deterministic (two identical runs pinned by
test). The probe measures STRUCTURAL asymmetries — the user club plays with
the same default plans as the AI; an engaged player's tactical/staff edge
comes on top of these numbers.

| Config (8×10 seasons) | User title share | S10 fielded-6 edge vs best AI |
|---|---|---|
| BEFORE — no recruiting | 21.2% | −3.0 |
| BEFORE — sign best 3/yr (auto-pilot lineup) | 35.0% | +0.9 |
| BEFORE — sign best 3/yr + lineup re-optimized each offseason | **52.5%** | +6.9 (peak +8.3) |
| AFTER fixes — no recruiting | 25.0% | −2.4 |
| AFTER — sign best 3/yr (auto-pilot lineup) | 41.2% | +1.4 |
| AFTER — sign best 3/yr + lineup optimized | **60.0%** | +8.2 (peak +9.2) |

Parity baseline: 1 of 6 clubs = 16.7% of seasons.

Other measured facts (consistent across configs):

- **League stasis:** AI roster churn was literally zero in seasons 1–7 of a
  single-seed detail trace; first league retirements arrive at S8 (mean 2.25
  league-wide), because curated ages cap at 29 and `should_retire` starts at
  34+. The Hall of Fame then opens in a bulk wave (cumulative ~1.6 → ~5 → ~8
  inductees across S8–S10) after seven silent seasons.
- **Reps starvation (root measurement):** a starter fielded in EVERY match of
  a season accrues 64–206 event-tick "minutes" on the official engine (league
  median 77) and 10–27 on the rec engine, against a `reps/1000` divisor —
  reps_factor 0.06–0.21 / 0.01–0.03. Development arcs confirmed it: a
  96-potential signing froze at 74 OVR from age 25 onward (pre-fix); post-fix
  the same player climbs 74→77 through the peak window. Stars still land
  12–20 short of ceiling — residual cause is the growth-pool design itself
  (pool split across 9 stats while OVR is the 5-skill mean, with geometric
  headroom decay), which is an owner tuning call, not a unit bug (§7.3).
- **Aftermath degradation:** 17 of 80 auto-piloted seasons hit "Postgame
  payload failed structural validation" — every instance was the
  survivor-derived winner contradicting a genuine official game-points draw.
  Root branch removed (it could ONLY ever contradict the result).
- **User roster collapse trap:** with recruiting skipped every year, the user
  club (exempt from every AI roster-repair path) bled to **4 players** by S10
  and 1.2–3.2 seasons; the engine floor protects AI clubs only. The UI now
  blocks the skip below a fieldable six (§5.4).
- **Records noise:** the three individual records are accumulation counters,
  so the same leaders re-break their own records ~2.5×/season, every season —
  steady noise rather than events. Team records (added, §5.3) change holders
  meaningfully; the unbeaten-run record in particular breaks rarely.
- Live prod-server proof on a throwaway save (created, verified, deleted):
  one fast-forwarded season produced 15 rivalry pairs in
  `/api/history/league`; the Records Ratified beat rendered "Longest Unbeaten
  Run 0→7" and "Most Titles 0→1" club cards with the My Club scope toggle;
  Signing Day shows the corrected "OVR" label; zero console errors.

## 3. Top long-term retention strengths

1. **Nothing is fake.** Champions, awards, career totals, HoF cases, records,
   trophies, and program trajectories all derive from persisted match truth.
   That is rare and is the foundation everything else can safely build on.
2. **The full loop runs unattended and deterministically** — 10-season
   careers complete through the real state machine with zero crashes across
   all 48 sweep runs, and same-seed runs reproduce byte-identical dynasties.
   Long-term play is mechanically trustworthy.
3. **Champion texture exists at honest strength levels**: in the no-recruiting
   config the title spreads 18/17/15/12/11/7 across six clubs over 80 seasons
   — upsets, droughts, and repeat champions all occur without any rubber-band.
4. **The offseason ceremony is a real annual ritual** (10 beats, real data,
   honest empty states), and with rivalries + club records now flowing it has
   more once-a-year texture than before.
5. **Prospect potential is now a deliverable promise** for fielded players
   through their peak window — the development → lineup → next-season loop
   pays back attention.

## 4. Top long-term retention risks

1. **The league is static (biggest season-5 risk).** Zero AI transactions for
   seven seasons; AI clubs sit at the 6-player floor with no bench, no
   succession, no identity drift. Rival programs cannot produce "they reloaded
   / they rebuilt" stories because they never acquire anyone unless someone
   retires. V12 archetypes color INTENT, not rosters.
2. **Recruiting is solved.** True OVR, sorted descending, uncontested, 3 picks
   a year, ~92 mean potential per signing. It is the single largest lever in
   the game (+14–19pp title share alone) and requires no thought. The entire
   V2-A scouting investment loop is strategically void in the shipping path
   because Signing Day reveals the answer for free.
3. **Snowball compounds unanswered.** An engaged player (recruit + one lineup
   click) wins 60% of all titles and ~7 of 8 by season 8–10 at +8–9 fielded
   OVR. Nothing in the league pushes back (no contested signings, no AI
   poaching, no cap/economy friction).
4. **The first 7 seasons have no mortality.** No retirements, no HoF, no
   farewell arcs until the initial age cohort hits 34+ — then it all arrives
   in one wave. Retention beats that depend on player mortality (succession
   crunches, HoF nights, records by departed legends) are absent exactly when
   the player is deciding whether the game has long-term texture.
5. **Records cadence is noise.** Career-counter records re-break every season;
   nothing distinguishes a milestone night from bookkeeping.

## 5. Implemented changes, grouped by system

All changes verified by the full Python suite + new tests; no golden logs
affected; no engine match outcomes changed (development is an offseason
system; its change is measured in §2).

1. **Development (reps truth)** — `development.py`,
   `offseason_ceremony.initialize_manager_offseason`.
   `apply_season_development` accepts additive `matches_played` /
   `club_matches`; when provided, the reps gate is the fraction of the club's
   recorded matches the player appeared in (engine-agnostic; full-season
   starter = 1.0). The offseason caller now passes real appearance counts.
   Legacy path (params absent) is byte-identical for existing callers/tests.
2. **Rivalries fed by the web path** — `rivalries.py` (pure
   `rivalries_from_match_rows` + `rivalry_payload`), `game_loop.py`
   (`rebuild_rivalry_records`, `season_sort_key`), wired into
   `recompute_regular_season_standings` (the single post-match chokepoint) and
   `finalize_season` (covers tie-resolved playoff finals). Recompute-from-truth
   = idempotent; legacy saves gain their full rivalry history retroactively on
   the next simulated week. Feeds three existing consumers: Dynasty Office
   league memory, `/api/history/league` (LeagueView), broadcast rivalry tags.
   Note: numeric-aware season ordering fixes a latent `season_10 < season_2`
   string-sort hazard.
3. **Team records ratify on the web** — `offseason_beats.py`
   (`_team_record_candidates`, `_longest_unbeaten_runs`): `most_titles` (from
   club trophies) and `longest_unbeaten_run` (no-loss streak across all
   seasons from match records) now flow through the same ratify → ceremony →
   My Club scope pipeline. `biggest_upset_win` deferred (needs at-match OVR
   reconstruction from roster snapshots — honest data exists; see §8).
4. **Roster-floor skip guard** — `offseason_service.recruit_offseason_payload`
   rejects "skip" (409) while the user roster is below `STARTERS_COUNT` and
   signable players exist (empty pool still allows the skip).
   `frontend/src/components/Offseason.tsx` now renders action errors inline
   (previously a rejected action was silently swallowed when a beat was
   loaded).
5. **Official-draw aftermath truth** — `use_cases._build_aftermath` no longer
   derives a winner from survivors; the resolved `MatchResult` is canon. The
   removed branch could only ever contradict the result (legacy records are
   winner-patched upstream in `franchise.simulate_match`) and was the sole
   source of the measured 17-degraded-aftermaths-per-80-seasons.
6. **Signing Day label truth** — `RecruitmentChoice.tsx`: the rating badge was
   labeled "scouted" but is the prospect's actual overall from the payload,
   shown identically with zero scouting performed. Relabeled "OVR" (the
   value-vs-band question is an owner call, §7.2).
7. **Instrumentation** — `tools/dynasty_health_probe.py` (seeded multi-season
   sweep CLI: title share, OVR edge curve, roster sizes, signings,
   retirements, records/HoF cadence; `--signings`, `--optimize-lineup`,
   `--ruleset`, `--seeds/--seasons`); `tests/test_dynasty_progression_health.py`
   (16 tests pinning all of the above + 2-season dynasty determinism).

## 6. Measurements / probes / tests run — exact status

| Check | Command | Result |
|---|---|---|
| Full Python suite (post-change) | `python -m pytest -q` | **PASS** (exit 0, 1,320 tests incl. 16 new; includes WT-23 parity gate + official balance gates) |
| New dynasty guards | `pytest tests/test_dynasty_progression_health.py -q` | **PASS** 16/16 |
| Dynasty sweeps (6 cells, 480 seasons total) | `python tools/dynasty_health_probe.py --seeds 8 --seasons 10 [--signings 0/3] [--optimize-lineup]` | Completed; numbers in §2 |
| Frontend build | `npm run build` | **PASS** (pre-existing chunk-size warning only) |
| Frontend lint | `npm run lint` | **PASS** |
| Playwright (offseason-touching) | `npx playwright test v13_broadcast_layer maximized-playthrough-qa --project=chromium` | **PASS** 3/3 (incl. offseason record-cards spec against the new team records) |
| Live prod-server walk | throwaway save via API; UI screenshots | **PASS** — 15 rivalry pairs in history; team-record cards + My Club scope render; "OVR" label; zero console errors/warnings; probe save deleted after |
| Not run | full 3-browser e2e matrix | Disclosed: changed strings grepped against all specs (no pins on "scouted"/aftermath winner); `Offseason.tsx` restructure is DOM-neutral unless an action error occurs |

## 7. Open owner-decision calls

1. **AI recruiting access (the static-league decision).** AI clubs cannot sign
   prospects in the shipping path; `conduct_recruitment_round` (contested
   offers, sniping, interest) is built and dormant. Wiring AI clubs into the
   offseason class — even 1 pick each after the user picks — is the single
   highest-impact dynasty change available, would consume the dormant system,
   and would directly counter the measured 60% snowball. It changes balance
   materially, so it needs its own measured pass (the probe is ready for
   before/after).
2. **The true-OVR reveal at Signing Day.** The picker exposes
   `prospect.true_overall()` for unscouted prospects, which makes the entire
   scouting center strategically void. Honest options: (a) show the scouted
   band/estimate (`KnownValue` fog states already exist in the legibility
   toolkit) with truth revealed only after signing; (b) keep the reveal and
   accept scouting as flavor. This pass fixed only the label lie.
3. **Development ceiling shortfall (residual).** Post-fix, a full-time starter
   still closes only ~half their remaining headroom before peak-end (pool
   diluted across 9 stats vs the 5-skill OVR; geometric decay). If "Ceiling
   96" should be *reachable* for a career starter, `_HEADROOM_CLOSE_RATE`
   and/or OVR-stat weighting need a measured retune — the dev-arc trace in
   the probe gives the before/after instrument.
4. **Early-career mortality.** Seeding a couple of 31–33-year-old veterans per
   curated roster would start the retirement/HoF/succession texture in seasons
   2–4 instead of season 8 — but it changes new-career rosters (RNG stream),
   so it is a deliberate design change, not a bugfix.
5. **Records cadence.** Career-counter records re-breaking every season could
   be presented as "milestones" (only new-holder changes get the marquee
   card). Presentation-only; data already distinguishes holder changes.
6. Pre-existing open items that this pass's findings reinforce: promises have
   no UI (STATUS #5) — promise evaluation runs every offseason and its results
   feed nothing; decide revive-or-remove before season-5 players notice.

## 8. Ranked next improvements for season-5 retention

1. **AI offseason signings** (owner call §7.1) — kills league stasis AND
   caps the snowball with one mechanism; dormant code exists; probe ready.
2. **Scouted-band Signing Day** (§7.2) — turns the scouting loop + fog-of-war
   into the game's actual recruiting skill expression.
3. **Development close-rate retune** (§7.3) — makes Elite ceilings reachable
   for committed development projects; measured instrument in place.
4. **Veteran age seeding at career creation** (§7.4) — brings mortality, HoF
   nights, and succession crunches into seasons 2–4.
5. **`biggest_upset_win` ratification from roster snapshots** — the data is
   persisted per match; high-drama club record with a real holder story.
6. **Milestone-vs-bookkeeping records presentation** (§7.5).
7. **Dynasty-health gate in CI**: pin `tools/dynasty_health_probe.py` small
   config (e.g. 4 seeds × 6 seasons) with bounds on (a) user-title share with
   recruiting+lineup ≤ 70%, (b) AI clubs never below 6 players, (c) ≥3
   distinct champions — the determinism test already runs in the suite; the
   bounds gate is the natural next step once the owner settles §7.1.

### Continuously-measured dynasty-health metrics (the gate, answered)

Title-share curve by season index (snowball), fielded-6 OVR edge curve,
distinct champions per 10 seasons, AI roster floor, retirements/HoF/records
cadence per season, and signed-prospect potential delivery (peak OVR vs stored
ceiling). All emitted by the probe today.

---

## Analysis questions, answered directly

- **Strongest long-term hook today:** the honest, deterministic history layer
  — champions/awards/records/HoF accrue from real play, and now rivalries and
  club records visibly accumulate with them.
- **Where the loop loses tension:** seasons 3–7 — no league mortality, no AI
  roster movement, recruiting already solved, development formerly frozen.
- **Can a smart player solve recruiting too easily?** Yes — definitively
  (true OVR, sorted, uncontested; +14–19pp title share for clicking the top
  of a list).
- **Does development create meaningful roster planning?** Partially now. The
  age <peak window is genuinely strategic (sign young, field them, they
  grow); post-fix the peak window keeps paying. Decline/retirement planning
  only exists from season ~7 because nobody old exists earlier.
- **Do AI programs keep the league alive?** Mechanically yes (they win 40% of
  titles even vs an engaged user), narratively no (frozen rosters, intent-only
  archetypes).
- **Are records/awards meaningful enough?** Awards yes (real stats, champion
  bonus, newcomer). Records were noise + missing the club dimension; club
  records now land, cadence framing remains (§7.5).
- **Biggest risk to season-5 retention:** the static league (§4.1) compounded
  by solved recruiting (§4.2).
- **What to measure continuously:** the six probe metrics above.
