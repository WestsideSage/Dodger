# V2-E — Off-season Beats Completion — Design Spec

**Date:** 2026-04-28
**Status:** Design approved, ready for implementation planning
**Scope:** Complete the off-season ceremony with Records Ratified, Hall of Fame Induction, and Rookie Class Preview beats. These are fact-driven read/confirm surfaces powered by persisted season state.

---

## 0. Relation to Prior Specs

This document is the canonical V2-E spec. It should be implemented after V2-F because V2-F changes champion source-of-truth from regular-season standings to playoff outcome.

V2-E consumes:

- V2-A / V2-B prospect and recruitment state,
- V2-F `season_outcome` champion truth,
- existing `records.py`,
- existing `career.py`,
- Manager Mode off-season ceremony.

V2-E explicitly does not cover:

- AI recruitment competition — V2-B.
- Playoffs — V2-F.
- New awards categories.
- New match-engine behavior.
- Hidden HoF or record facts generated only for UI.

---

## 1. Goals

Add three beats to create a ten-beat off-season ceremony:

1. Champion.
2. Recap.
3. Awards.
4. Records Ratified.
5. Hall of Fame Induction.
6. Development.
7. Retirements.
8. Rookie Class Preview.
9. Recruitment / Draft.
10. Schedule Reveal.

The new beats must be computed once per completed season, persisted, and safely re-rendered.

---

## 2. Records Ratified

Records Ratified shows newly set or improved league records.

Inputs:

- player career stats,
- team stats,
- existing league records,
- current season id,
- persisted champion / standings context where relevant.

Rules:

- Compare candidate records against persisted current records.
- Persist improved records once.
- Store a season-specific off-season payload for display.
- Re-entering the ceremony reads the stored payload, not a fresh "new record" calculation.

Same-season collisions: ratification is computed exactly once, on first off-season entry, against end-of-season values. If multiple players or teams improved the same record during the season, only the best end-of-season value is ratified — no in-season intermediate improvements are surfaced or persisted as their own ratification events. The previous value shown is the record as it stood at season start.

Biggest-upset records are only in scope if the required pre-match overall data is already available. Otherwise, the beat should omit that record type until a later data milestone.

---

## 3. Hall of Fame Induction

Hall of Fame beat evaluates retired players.

Inputs:

- retired players for the completed season,
- player career summaries,
- awards,
- signature moments where available,
- existing HoF entries.

Rules:

- Use `career.evaluate_hall_of_fame`.
- Persist new inductees once.
- Skip already-inducted players.
- Show a dignified empty state if nobody qualifies.

---

## 4. Rookie Class Preview

Rookie Class Preview shows the public shape of the incoming pool before Recruitment Day.

Inputs:

- V2-A/V2-B prospect pool when present,
- legacy free agents only as fallback for old saves.

Allowed display:

- class size,
- public archetype guesses,
- public OVR bands,
- broad market storylines (derived facts only — see below),
- free-agent count.

Broad market storylines are short, deterministic, fact-derived sentences computed from V2-A/V2-B aggregate signals available at off-season entry. Each storyline must be backed by an underlying numeric fact and tagged with that fact in the persisted payload (so the same numbers always produce the same sentence and the source is auditable).

Permitted source signals:

- archetype distribution of the prospect pool (e.g., "Strikers in heavy demand: 4 of 8 clubs prioritizing them this off-season").
- public OVR band thresholds vs prior classes (e.g., "Deepest top-band class in N seasons", computed only against persisted prior-class summaries — omit if no prior class data exists).
- AI club preference clustering from V2-B (counts only — never name a specific AI club's private preferences).
- free-agent count vs prior off-season (e.g., "Lightest free-agent crop in N seasons" — omit if no comparable history).

Storylines are emitted only when the threshold for a given template is met (concrete inequality on the source signal). When no template fires, the slot is omitted — never padded with filler text. No LLM. No invented narrative. No facts that aren't already legal under V2-A's public-info rules.

Forbidden display:

- hidden trajectory,
- hidden traits,
- exact ratings beyond authorized tier,
- private scouting facts not already allowed by V2-A UI,
- any storyline whose underlying fact is not stored alongside it.

The preview must not generate or mutate the pool.

---

## 5. Persistence and Idempotency

Use existing tables where possible:

- `league_records`,
- `hall_of_fame`,
- `dynasty_state`,
- prospect/free-agent tables.

Suggested `dynasty_state` keys:

- `offseason_records_ratified_for`,
- `offseason_records_ratified_json`,
- `offseason_hof_inducted_for`,
- `offseason_hof_inducted_json`,
- `offseason_rookie_preview_for`,
- `offseason_rookie_preview_json`.

Re-entering off-season must not:

- duplicate HoF entries,
- re-ratify the same records as newly broken,
- regenerate rookie/prospect pools,
- alter recruitment results,
- alter scouting state.

---

## 6. UI

Each beat uses the existing off-season ceremony shell.

Records Ratified:

- list new records,
- previous value,
- new value,
- holder,
- season detail.

Hall of Fame:

- inductee cards,
- legacy score,
- reasons,
- career summary.

Rookie Class Preview:

- public class summary,
- top public bands,
- archetype distribution,
- free-agent count,
- call-to-action into Recruitment Day.

---

## 7. Testing

Required coverage:

- Off-season beat order has ten entries.
- Records Ratified persists new records once.
- Records empty state renders.
- HoF inducts eligible retired player once.
- HoF empty state renders.
- Rookie Preview uses prospect pool when present.
- Rookie Preview falls back to legacy free agents for old saves.
- Rookie Preview does not leak hidden prospect data.
- Rookie Preview storylines fire only when their underlying fact threshold is met, and the fact is stored alongside the sentence in the persisted payload.
- Records Ratified surfaces only end-of-season improvements (no in-season intermediate ratifications) when the same record was improved multiple times in one season.
- Resume at each inserted beat renders the correct payload.

---

## 8. Acceptance Criteria

V2-E ships when:

1. Manager Mode ceremony has ten beats in the approved order.
2. Records Ratified is fact-driven and idempotent.
3. Hall of Fame Induction is fact-driven and idempotent.
4. Rookie Class Preview reads canonical pool state without mutation.
5. Save/resume works at every new beat.
6. V2-F playoff champion truth is honored in off-season context.

---

*End of V2-E Off-season Beats Completion design spec.*
