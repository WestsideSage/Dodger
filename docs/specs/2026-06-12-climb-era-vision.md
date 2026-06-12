# The Climb Era — Post-V22 Direction (V23–V28)

Date: 2026-06-12
Status: **DECIDED direction record** — owner-confirmed decision-by-decision in the
2026-06-12 grill session. This is the long-range planning authority for the era,
not an implementation spec: each milestone gets its own spec in `docs/specs/`
when it goes active, and `docs/STATUS.md` remains build-state truth.

## The question this answers

"What is this game missing compared to Teamfight Manager 1/2 and college-football
dynasty games?" Short answer: the engine and the dynasty record are real, but
there was no **world** for the dynasty to matter in (one static 7-club league, no
north star), no **want** inside the people (prospects/players have no motivations,
contracts, or market), and no **money loop** connecting decisions to consequences
(treasury exists; almost nothing to earn it with or spend it on). TFM supplies
the world-shape (the climb), CFB supplies the want (recruiting as the main
event), the economy threads them together.

## Spine and design laws

1. **Spine: CFB-style program builder. Recruiting is the centerpiece system.**
   Failure condition: recruiting feels like a menu errand instead of the main event.
2. **The game IS the climb.** Every save aims at the World Championship. The
   summit is a ceremony, not an ending — post-summit play is legacy (defense,
   records, HoF), never NG+ or difficulty ratchets.
3. **The AI plays the game alongside the player, not through them.** Every match
   in the universe runs the real engine (seeded, deterministic). AI clubs
   recruit, develop, manage wages, promote, and relegate on merit. No abstracted
   or fake results anywhere. Rivalries and stories emerge from real play
   (co-traveler rivals ride the existing rivalry-rebuild system).
4. **Receipts or it doesn't ship.** Every imported mechanic passes the
   decision-traceability filter: CFB's opaque pitch grades become proof-backed
   grades; TFM's injected patches become journalism about real events; morale
   becomes motivations with evidence. No hidden dials, ever (ADR 0002 lineage).
5. **Economy is a supporting layer.** Present enough to feel like running a
   program; never bookkeeping. One treasury, no earmarks (TFM2 budget freedom):
   staff, network, facilities, wages, buyouts all compete for the same money.
6. **Foam-official stays the one spine ruleset.** League, promotion, Worlds are
   foam. Cloth/No-Sting live only in opt-in invitational events.

## V23 — The World

3 domestic tiers × 7 clubs (D3 **District League** → D2 → D1 **Premier**) plus a
real **International Circuit** division (~7 clubs, its own annual round-robin on
the real engine) ≈ 28 clubs. The Circuit represents the rest of the world the
same way 3 tiers represent a nation — disclosed simplification, zero fake matches.

- Movement: champion auto-promotes; 2nd–5th **promotion playoff** for the second
  slot; bottom two relegate — **including the user club** (owner: "you SHOULD be
  relegated"). Falling never fires you; founder-for-life holds.
- **Worlds** caps every season from Season 1 (Premier champion + runner-up vs the
  Circuit's best). It crowns real champions before the player arrives; news and
  league history accumulate its legend while the player grinds D3.
- Creation paths: build-from-scratch founds at the bottom of D3 (the V22
  founding-budget squeeze finally gets its narrative home — TFM1 start);
  takeover picks an existing club higher up with a tradeoff identity (rich but
  talent-poor, storied but broke — TFM2 start).
- League payouts scale by tier and finish (extends the V22 economy settlement).
- Why 7 per tier: scheduler, byes, playoff bracket, and the balance-gate suite
  all reuse unchanged; the milestone cost is the pyramid, not new league formats.
- **Honest cost:** the biggest balance re-derivation of the era — V16 title-share
  parity, V18 mortality cadence, contested-offer witnesses all move at 28 clubs.
- Proof obligations: dynasty health probe across tiers; promotion/relegation flow
  gates; Worlds-runs-from-S1 history gate; determinism preserved.

## V24 — The Board (recruiting apparatus)

Battles, not hauls (college-basketball framing): 25-prospect class, 7 clubs,
you sign 1–3 — every signing is a head-to-head war.

- **Chassis kept, deepened:** the existing slot budget (3 scout / 5 contact /
  1 visit, staff-wired) stays the currency. Added: funnel stages gating stronger
  verbs (Open → Shortlist → Top 3 → Verbal), a persistent focus list (no weekly
  re-clicking), and visits scheduled against real home fixtures.
- **Six receipts-backed motivations** — every grade computed from real save data
  with ProofChip receipts: Court Time (lineup projection), Contender (trophies/
  standings), Development (measured ceiling-delivery of past signees), Legacy
  (records/HoF), Staff (department-head ratings), Scheme Fit (archetype vs
  actually-fielded tactics) — plus **Hometown** (7 districts mirroring D3; new
  data). 2–3 motivations visible; the **dealbreaker** is hidden until scouted;
  below ~C grade in it = never verbals, with the honest why shown.
- **Visible rivals + interest race:** named suitors per prospect; early leads are
  defensible momentum. **AI blind spots are REQUIRED** (AI networks have levels
  and district biases too) so unrecruited gems happen organically.
- **Scouting Network — money gates visibility (TFM1):** persistent club
  investment; L1 = district + neighbors, L2 = regional, L3 = national. Below
  your level, prospects are names without sheets. Division gates *willingness*
  organically via grades (no hard locks — the D3 club courting a national
  prodigy is visible, courtable, heartbreaking, and occasionally wins via
  Local + Development receipts). FA pool stays ungated (TFM2 hope layer).
- Class story = the league-wide **class wire** (where did the Generational kid
  land), not volume class rankings.
- Proof obligations: courtship→outcome traceability gates; AI board-coverage gap
  probe; network visibility fences; staff cost-compression consumers.

## V25 — The Market (contracts)

- Every player: **salary + term (1–5y) chosen at signing**. Entry salaries are
  division-standardized — recruiting stays a courtship game; money enters a
  player's story at his second contract.
- **Offseason Transfer Period beat:** re-signs for expiring deals using the SAME
  motivation grades as recruiting (retention is recruiting's mirror);
  extensions/renegotiations; **incoming buyout offers you can refuse** (the
  "couldn't let him fall into another team's hands" beat); **outgoing buyout
  bids** against AI asking prices — rich-club privilege by construction.
  Accepting a buyout is treasury income. No mid-season movement.
- **Poaching is real and flows uphill.** Higher-tier money hunts your expiring
  stars; motivations break ties; every departure carries a receipt ("outbid
  ×2.1, and your Contender grade is D"). Modest development-compensation credit
  when a bigger club takes a homegrown player.
- Salaries scale with division, ability, and (post-V26) a fan premium.
  Promotion inflates payroll as it raises prize money — climbing never
  unsqueezes the treasury. AI symmetric: AI wage bills, AI mistakes, news fodder.
- Proof obligations: poach/retention probe (grades demonstrably flip outcomes);
  squeeze-never-spiral invariants extended; roster-fortress gate (league-wide
  veteran movement > 0 per offseason).

## V26 — The Crowd (fans, facilities, roles, media spice)

- **Two fan ledgers** (club + per-player), grown ONLY from real logged events:
  club fans from wins/promotions/titles/rivalry wins/Worlds runs; player fans
  from MVPs, moment events, records, milestones, district ties. Every change
  receipted ("+400 after the promotion final").
- Income: **matchday** (fans drawn, capped by stadium capacity) and **merch**
  (club fans + star personal followings × merch level). Tuning law: fan income
  is a meaningful *margin*, never rivaling prize money — tension, not tyranny.
- **Facilities:** training hall (revive the dormant `facilities.py` effects —
  already coded into the shipping development path, currently fed `()`),
  stadium capacity, merch center.
- **Bench roles** (one per non-starter, per-season, no weekly micro):
  **Ambassador** (monetizes his own fan ledger — the TFM2 "streaming vet"),
  **Mentor** (measured dev-rate modifier on paired youngsters; the identity
  traits' first honest consumer), **Analyst** (deepens playbook reads /
  counter-read; effectiveness scales with `tactical_iq` — the cerebral vet's
  third act). Scouting stays a staff job.
- **Media mini-events** (TFM spice, owner-requested): occasional choice-based
  beats whose effects land ONLY in fans/courtship/credibility — never match
  outcomes.
- Proof obligations: fan-ledger receipt audit; facility effect probes; role
  consumer tests (nothing flavor-only).

## V27 — The Calendar (events)

Season skeleton: Preseason (Founders' Exhibition, ruleset invitational) → league
with Domestic Cup rounds at 2–3 dedicated breaks → Midseason window (MSI +
invitational) → run-in → domestic playoffs → **WORLDS** → offseason beats
(finances → transfer period → Signing Day → development → ceremonies).

- **Domestic Cup:** all three divisions, foam, knockout — the giant-killing engine.
- **Ruleset Invitationals** ("Cloth Classic", "No-Sting Open"): the ONLY home of
  alternate rulesets; invitation by standing/fame; purse + prospect-showcase
  warmth. Entry price: per-profile decision-impact/health probes and fixes
  (the V17 full-run cloth crash is the precedent — played content must be
  balanced content). Roster-variety pressure ("carry a cloth specialist?") is
  the honest TFM different-map tension.
- **Midseason International:** Premier + Circuit leaders; prestige, purse, a
  Worlds seeding edge.
- **Founders' Exhibition:** invited by FAN COUNT, money only, declared
  no-seeding — being beloved is the ticket.
- **Worlds crowning ceremony:** first Worlds win = the save's crowning beat (the
  dynasty's story retold, credits-roll energy), then the legacy game.
- Event windows are dedicated calendar breaks; the weekly league rhythm never bloats.
- Proof obligations: calendar integrity gates; declared-stakes honesty fences;
  per-ruleset balance gates.

## V28 — The Weather (anti-solvedness)

- **Emergent meta (load-bearing half):** AI programs drift toward what is
  actually winning across the live ecosystem (V12 adaptation generalized from
  "react to the player" to "react to the world"), until a new generation breaks
  the orthodoxy. Nothing injected — the world generates its own weather.
- **Meta journalism:** league trend reports computed from real match records
  ("D1 catch rates up 11%; three of four semifinalists ran go-for-catches").
  News ticker = the meta channel; every claim derivable from data.
- **Officiating points of emphasis:** a seasonal League Bulletin shifting call
  tendencies within the sourced rulebook's discretion space (`rule_discretion.py`),
  announced preseason, applied symmetrically, logged in matches.
- **`MetaPatch` stat-dials stay retired.** Owner-confirmed: no patch knobs.
- Proof obligations: journalism derived-from-data fences; emphasis symmetry +
  logging gates.

## Sequencing rationale (owner-confirmed 2026-06-12)

V23 → V24 → V25 → V26 → V27 → V28. North star and stage first (everything
references tiers, districts, payouts); the spine system second; money-for-people
third (reuses V24's grades); money-for-things + fans fourth; calendar spice
fifth (needs Circuit + fan invitations); weather last (journalism needs history
to report). Each milestone independently playable. V23 deliberately eats the
balance re-derivation before five systems sit on top of it.

## Rejected and deferred ledger

**Rejected on principle:** morale engine (revisit only as a fully transparent,
receipted design if the game feels sterile post-V26), interactive press
conferences (media stays one-way journalism), in-match coaching (HARD no —
between-match tactics only; event log stays canon), MetaPatch dials, NG+,
abstracted match results, foreign full pyramids, volume class rankings,
mid-season transfer windows, a pick/ban draft phase (the prep layer + Analyst
absorb that fantasy).

**Deferred with a seat saved:** Nations Cup analog (needs player nationality —
design it properly in v2 of the calendar), retired-legends-into-the-staff-market
(hiring-pool feature once roles exist), international recruiting ("go global"
once you're a Worlds regular), coaching carousel (someday-drawer; founder-for-
life is the identity until then).

## Dormant prototypes this era revives

| Module | Built for | Revived as |
|---|---|---|
| `facilities.py` | CLI-era facility dev effects (already in the shipping dev path, fed `()`) | V26 training facility |
| `cup.py` | CLI-era cup bracket | V27 Domestic Cup skeleton |
| `news.py` (matchday news) | CLI-era news generation | V27/V28 event + meta journalism feeds |
| `meta.py` | CLI-era seasonal patches | **Not revived as dials** — superseded by V28's emergent meta + officiating emphasis |

## Open questions intentionally left to milestone specs

Exact pyramid balance targets and witness re-derivation (V23); network pricing
tiers and AI network distributions (V24); salary scale constants, buyout-fee
formula, compensation size (V25); fan-gain constants and facility prices/tiers
(V26); event purses, invitational qualification rules, Worlds bracket format
(V27); emphasis rotation cadence (V28). Per repo law, every constant ships with
its probe evidence, and intentional outcome changes update golden logs in the
same pass.
