# The Climb-Era Arc (V23–V28) — Complete

Date: 2026-06-19
Status: **Arc complete.** V23–V28 + the PT3–PT6 trust audits ship to `main` as a
unit. This is the capstone note; per-milestone detail lives in the individual
specs/retrospectives, and the V28 retro
(`docs/retrospectives/2026-06-18-v28-the-weather-retrospective.md`) carries the
arc close-out table.

## What the arc built

The post-V22 direction decided 2026-06-12
(`docs/specs/2026-06-12-climb-era-vision.md`): turn a single-league sim into a
living pyramid you climb, on a CFB-recruiting spine.

| Milestone | Added |
|---|---|
| **V23 The World** | 28-club pyramid (3 domestic tiers + International Circuit), real promotion/relegation incl. the user club, WORLDS from Season 1, tier-scaled payouts. |
| **V24 The Board** | Recruiting as the centerpiece: whole-world AI recruiting, district-rooted caliber-banded classes, receipts-backed motivations + dealbreaker veto, the Open→Shortlist→Top3→Verbal funnel + focus list, visible rival suitors + interest race, the money-gated Scouting Network, the class wire. |
| **V25 The Market** | Contracts: per-player salary + term, the wage bill, the Transfer Period beat, retention as recruiting's mirror, uphill poaching, AI symmetry via a tier wage-budget cap. |
| **V26 The Crowd** | Fans / facilities / bench roles / media, mostly reviving dormant code; the first Climb-Era schema migration; append-only receipted fan ledgers. |
| **V27 The Calendar** | A season calendar of real auto-simmed knockouts: the revived Domestic Cup, balance-gated Ruleset Invitationals, MSI + Founders' Exhibition, and the elevated Worlds-crowning ceremony beat. |
| **V28 The Weather** | The ecosystem's own weather: data-derived meta journalism, emergent AI tactic drift + a contrarian generation, and officiating points of emphasis — so the game never fully solves. |

## The trust audits (the other half of the work)

Every milestone shipped behind `pyramid_world_active` with legacy byte-identical,
but the real hardening came from four fresh-eyes trust playtests, each driven by
the project's north star — **decision traceability**: every on-screen claim must
trace to a visible outcome/receipt, or it's a bug.

- **PT3 (Orphanage Run)** and **PT4 (V23 pyramid)** — answered same-day during the
  build (release/sign-over-cut, scout reveals, climb pacing cap, the PT4 trust
  sweep).
- **PT5 (Codex, both paths, 4+2 seasons)** — 9 trust-breaks fixed, headlined by a
  **P0 falsifying final score** (debrief 0-0 + League Wire "0-0 survivors" — the
  V20 survivors-vs-game-points family resurfacing, partly surfaced by V28's own
  `wire_headlines` fold). Plus the takeover "roster collapse" that **investigation
  proved was a misread** (every club fields 6; 12 is capacity, not a target) — a
  legibility fix, not the mechanics change it looked like.
- **PT6 (Codex, regression-confirm + new hunt)** — all 9 PT5 fixes confirmed on
  screen; 3 new P1s fixed, **including a regression PT5 introduced** (the
  Transfer selected-state badge lying on a vetoed "won't re-sign" player). The
  others: the Command Center wire (a *second* League Wire surface, never migrated,
  showing bare Win/Loss with no scoreline + a reduced-motion duplicate) and the
  **Worlds recap never receipting the user's own run** when they reached Worlds
  but lost the semifinal. A P2 survivors-leak in the Primary Factor chip closed
  the V20 family on its last surface.

## The throughline

The integrity contract (ADR 0002) held end to end: every surface derivable from
real data; sourced USAD rules stay sourced and sim-design stays disclosed
(officiating emphasis is announced, symmetric, logged, and byte-identical by
default — no new RNG draw); `meta.py`/MetaPatch stayed retired; determinism
preserved; legacy single-league saves byte-identical. The recurring villain was
the **survivors-vs-game-points falsifying-score family** (V20) — it reappeared on
the debrief hero, the League Wire (twice), and the Primary Factor chip, and is now
fixed on every surface a playtest reached. Two of PT6's findings traced back to
work *this arc* introduced (the V28 wire fold, the PT5 badge) — caught by the
audits, not shipped.

## Disclosed deferrals (carried forward, not blockers)

- The V28 emphasis effect is real but subtle per game (bounded ±0.08; per-game
  noise dominates) — visible over a season, not a single match.
- AI tactic drift works mechanically (proven by `meta_drift_probe`) but is not yet
  *surfaced* on the standings plan rows; the meta-report ticker only fires when a
  trend crosses `trend_notable_delta`. Both are legibility enhancements, not
  falsifications.
- The emphasis DISCRETION log lives in the event stream + conformance ledger but
  is not yet rendered in the player-facing replay UI.

## State

Full `python -m pytest -q` green; `npm run build` + `npm run lint` clean; the
three V28 probes (`meta_journalism` / `meta_drift` / `emphasis`) plus the
recruiting/transfer/facility/scouting probes pass. PT5 (9) + PT6 (4) fixes each
ship with a RED→GREEN regression test. The whole arc lands on `main` as a unit;
the next arc starts from a hardened, trust-audited base.
