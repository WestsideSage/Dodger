# ADR 0002 — Faithfulness of claims outranks integrity of restraint

**Status:** accepted (2026-06-01)

## Context

The `2026-05-31-master-implementation-roadmap-audit-synthesis.md` roadmap is built
on a deliberate **no-scope-creep / integrity contract**: it argues that *scope
discipline is itself a form of integrity*, and on that basis walls off engine work
behind "do-not-do-yet" (WT-20 live rule enforcement, WT-27 architecture refactor),
keeps balance changes minimal and gated, and treats golden-log/conformance regression
risk as a reason to defer.

A `/grill-with-docs` review (2026-06-01) surfaced a competing integrity claim: several
deferrals leave a **residual lie or ambiguity** in front of the player — copy that
names "USA Dodgeball 2026.1" while the engine only *announces* (does not enforce) those
rules; a `proximity_modifier` shown as proof but never applied; a "conformance" gate
that asserts only file existence; replay copy that would narrate a headshot foul as a
wild miss. The owner articulated a governing principle: **player-facing claims must be
maximally faithful and precise — zero ambiguity — and any fix needed to preserve that
is prioritized** ("wise men plant trees whose shade they will never sit in").

These two integrities genuinely conflict. Honoring faithfulness here means *un*-deferring
work the roadmap deliberately deferred.

## Decision

When **integrity-of-faithfulness** (player-facing claims are precisely true) conflicts
with **integrity-of-restraint** (contain scope and regression risk), **faithfulness
wins.** This was chosen with the aggregate cost made explicit: in total, the review's
resolutions reverse the roadmap's no-scope-creep contract and convert a contained,
gated trust-fix pass into a multi-milestone effort (a new "Official Live Rules" engine
milestone: WT-8 rush wiring, WT-20 enforcement, WT-31 playoff overtime) that takes on
the golden-log/balance regression risk the original walled off. The owner affirmed this
knowingly.

**Bounding mitigations (the decision is not "unbounded scope"):**

1. **Cheap honest interims ship inside the contained pass.** Where the faithful fix is a
   milestone, a truthful *interim* still lands now so no lie persists in the meantime:
   stop displaying the inert `proximity_modifier`; add the precise "announced but not
   outcome-affecting" copy qualifier; keep the disclosed playoff tiebreak until overtime
   is wired.
2. **Engine expansions are isolated and gated.** They live in a separate milestone
   sequenced *after* the Phase 0–7 trust pass, each step attributable (the WT-6
   discipline: one balance change at a time, re-run the probe, never blur effects).
3. **Faithfulness must be grounded in the primary source, not the artifact.** "Faithful"
   means *verified against the real rulebook / spec*, not derived from the sim's own
   code. (Worked example: the review first derived WT-31 tie-fidelity from
   `official_scoring.py`, then asserted a secondary-source "sudden-death overtime." The
   primary source (usadodgeball.com/rules, 2026) overturned both: the real mechanism is
   **enforced No Blocking**, no separate overtime. The decision held — playoffs must be
   decisive — but the *mechanism* and *evidence* were corrected, and WT-31 folded into
   WT-20. This is the mitigation working as intended.)

## Considered and rejected

- **Keep the no-scope-creep contract as written** (ship contained pass, queue the
  faithful engine work as a fully separate future decision). Rejected by the owner:
  leaving a known player-facing overclaim standing for another milestone is the exact
  trust violation the whole effort exists to fix.
- **A one-sided "always prefer faithfulness" principle.** Rejected — it would be quoted
  to justify unbounded scope on every future task and would read as flatly contradicting
  the roadmap's integrity contract. The decision is a *trade-off with bounding
  mitigations*, not a blank check.

## Consequences

- Future scope decisions should weigh both integrities and default to faithfulness, but
  must apply the three bounding mitigations — especially: **an interim must keep the
  product honest while the faithful version is deferred**, and **fidelity claims require
  primary-source verification.**
- The plan now carries balance/golden-log regression risk it originally avoided. This is
  accepted, contained to a gated milestone, and is the reason that milestone is sequenced
  last.
- This ADR is the standing tie-breaker; the per-item resolutions live in
  `docs/specs/2026-06-01-master-roadmap-grill-resolutions.md`.
