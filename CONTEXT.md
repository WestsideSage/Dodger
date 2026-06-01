# Dodgeball Manager — Domain Context

The shared language of the dodgeball management sim: the terms a player or
designer reasons about, and the canonical direction/meaning of each so that
UI copy, backend math, and tests cannot silently disagree. This file records
domain vocabulary, not implementation detail.

## Language

**Pipeline Tier**:
A prospect's recruiting-pipeline strength, shown to the player as a 1–5 star-style
emblem. **Canonical direction: ascending — Tier 5 ("Elite") is the strongest,
Tier 1 the weakest.** This is the player-facing 5-star mental model and the
backend signing math must agree (a higher tier number must start a prospect
*warmer*). Resolved 2026-05-31 (WT-25): flip the backend so `base_interest()`
treats higher tier as stronger, rather than relabel the UI to 1-is-best.
_Avoid_: "tier 1 is best", "low tier = elite".

**Scouted (fog-of-war)**:
A prospect whose public OVR band the player has tightened by spending a scout
action. Scouting narrows the visible band toward the midpoint; it never reveals
the true rating. (Distinct from **Scout Opponent**, below — same verb, different
object.)

**Scout Opponent**:
A pre-match readiness action that reveals real, derivable intel about the week's
opponent. Resolved 2026-05-31 (WT-30): the reveal is **observed tendencies from
tape** — the opponent's historical tactical tendencies aggregated from their past
`matches.box_score_json` (which persists each team's `coach_policy` per match,
persistence.py:186). It must **never** read the opponent's hidden upcoming
`CoachPolicy`. Because tape is finalized match history, this does **not** ride the
live-sim stale-club path (WT-11) — no dependency. **Cold-start:** when there is no tape
(week 1, first meeting, fresh league), Scout still reveals derivable non-tape facts
(roster shape, threat by OVR, program identity) and layers tendencies on once tape
exists — never empty, each source labeled. Distinct from prospect **Scouting**.

**Official mode (officially-inspired)**:
The `official_foam`/`official_no_sting`/`official_cloth` rulesets, modeled on the
USA Dodgeball 2026.1 spec. **Governing principle (2026-05-31): player-facing claims
must be maximally faithful and precise — zero ambiguity — and any fix needed to
preserve that is prioritized over cheap deferral.** Concretely, a rule is in one of
three honest states and copy/docs must say which: **enforced** (changes outcomes in
`official_resolution`), **announced-only** (an event is emitted but it does not affect
resolution — e.g. No Blocking, activated at official_engine.py:593 but absent from
resolution), or **absent** (e.g. throw-clock = config-only `throw_clock_seconds`;
opening-rush = rec-driver only, not in the official engine). Naming the "2026.1"
lineage is faithful; implying full live enforcement of it is not.

**No Blocking** (the real decisiveness mechanism):
Primary source (usadodgeball.com/rules, 2026) **confirms the trigger and the terminal
game only**: a game that has not concluded within the time limit **enters No Blocking**,
and if the match clock expires during it the current game becomes a terminal "match-end
No Blocking game." **What "reduced blocking" changes in resolution is NOT specified by the
primary source** (verified 2026-06-01 — see
`docs/specs/2026-06-01-workflow0-primary-source-rule-verification.md`): that resolution
parameter is **OPEN**, so enforcing No Blocking (WT-20) cannot ship faithfully and stays
the honest interim. There is **no** separate sudden-death overtime (the primary states
none; a conflicting "1-minute-then-No-Blocking" tiebreak exists only in secondary league
sources and is excluded per ADR 0002). In the sim, No Blocking is
currently *announced but not enforced* (official_engine.py:593) — enforcing it (WT-20) is
the faithful fix that makes games decisive in both regular season and playoffs.

**No-point game**:
An official foam/no-sting game the sim currently scores **0 points to both**
(official_scoring.py:56–66) when the clock expires with both sides alive — a symptom of
**No Blocking** not being enforced yet. Once enforced, most such games resolve to an
elimination. A genuinely still-tied regular-season game is an honest draw; the standings
resolve ranking via **game-point differential** (the sim's standings rule — **not**
corroborated by the primary rules page, which is silent on residual ties; see Workflow 0).
_Avoid_: calling it "a stall bug"; bolting on a seeded tiebreak; or canonizing draw
fidelity from the sim's own code instead of the rulebook.

**Playoff decisiveness**:
A bracket never ends drawn. Target (trigger primary-confirmed; the resolution mechanics
are OPEN — Workflow 0): enforced **No Blocking** runs a
tied playoff game to an elimination — the rulebook mechanism, **not** a separate
sudden-death period. The dormant `PLAYOFF_OVERTIME` enum is reinterpreted as the
terminal "match-end No Blocking game." Interim (pre-WT-20): `resolve_playoff_match` picks
a winner by a **disclosed** tiebreak (`decided_by` + `narrative_note`), never a silent
seed fallback.

**Primary Factor** vs **Manager Lesson**:
**Primary Factor** is the strictly *event-derived* dominant cause of a match result
(catch disparity, stamina collapse, …). **Manager Lesson** is a *separate* surface,
shown only when the Primary Factor is inconclusive, drawn from *controllable prep*
(ignored recommendation, roster edge, fatigue, weakest role group). They are never
merged. If nothing was controllable, the lesson says so honestly.

**Ruleset display name**:
The single canonical player-facing name for a ruleset/scoring model, with a full form
("USA Dodgeball 2026.1 — Foam", selector) and a short form ("Foam Division", compact
chips), from one source of truth — mirroring `archetype_display_name`. No surface
invents its own (no `USAD FOAM` / `OFFICIAL_FOAM` keys leaking to players).

## Relationships

- A **Prospect** has one **Pipeline Tier**; higher tier ⇒ higher starting interest.
- **Scouting a prospect** narrows a band; **Scout Opponent** reveals tape tendencies. Same verb, two unrelated mechanics.
- A match result has exactly one **Primary Factor** (event-derived); it *may* also carry one **Manager Lesson** (controllable-prep), never folded together.
- A regular-season game may end an honest draw; a playoff game must produce a winner — via enforced **No Blocking** running to elimination (the rulebook mechanism), not a bolt-on tiebreak.

## Example dialogue

> **Dev:** "The official match ended 0–0 — should the headline call it a draw or pick a survivor-count winner?"
> **Designer:** "Today it's a **no-point game** because we don't enforce **No Blocking** yet — that's why draws pile up. The rulebook's fix isn't a tiebreak, it's No Blocking running the game to an elimination. Once that's enforced, real draws are rare; when one happens in the regular season it's honest, and standings sort it by game-point differential. A playoff never ends drawn. And never let the replay headline read survivor counts as the score."

## Flagged ambiguities

- **"Tier" direction** was inverted between UI (5 = Elite/best) and backend
  (`base_interest`: tier 1 strongest, tier 5 floored to weakest). Resolved
  2026-05-31: **ascending — 5 is strongest**; backend flips to match the UI.
- **"Scout"** overloads two mechanics (narrow a prospect's band vs. reveal
  opponent intel). Kept distinct as **Scouting (prospect)** and **Scout Opponent**.
