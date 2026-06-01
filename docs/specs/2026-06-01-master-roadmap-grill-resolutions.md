# Master Roadmap — Grill Resolutions

Date: 2026-06-01
Status: Active. Decision log from a `/grill-with-docs` review of
`docs/specs/2026-05-31-master-implementation-roadmap-audit-synthesis.md`.
Authority: subordinate to `AGENTS.md`, `docs/STATUS.md`, source/tests. These
resolutions **amend** the roadmap; where they conflict with the 2026-05-31
roadmap text, these win and the roadmap should be edited to match.

> **Governing principle established this session:** player-facing claims must be
> **maximally faithful and precise — zero ambiguity — and any fix needed to
> preserve that is prioritized over cheap deferral.** "Wise men plant trees whose
> shade they will never sit in": prefer higher-scope-but-honest over cheap-but-
> approximate. Several resolutions below overturn the roadmap toward more work
> because the cheap option left a residual lie or ambiguity.

> **Aggregate-scope decision (made with the cost explicit, 2026-06-01):** in total
> these resolutions **reverse the roadmap's deliberate no-scope-creep / integrity
> contract**, converting a contained, gated trust-fix pass into a multi-milestone
> effort that takes on the golden-log/balance regression risk the original walled
> off. The owner chose this knowingly: **faithfulness-of-claims outranks
> integrity-of-restraint.** Mitigation: cheap honest **interims** still ship inside
> the contained Phase 0–7 pass; the engine expansions are isolated in a separate,
> gated **Official Live Rules** milestone sequenced *after* the trust pass, each step
> attributable (WT-6 discipline). See ADR 0002.

---

> **⚠ CORRECTION (2026-06-01, Workflow 0 primary-source verification).** This log's
> WT-31 row and the "New: Official Live Rules" section state, as **"PRIMARY-SOURCE
> CONFIRMED,"** that No Blocking means "play continues (reduced blocking) until
> elimination." A direct re-verification against usadodgeball.com/rules
> (`docs/specs/2026-06-01-workflow0-primary-source-rule-verification.md`) found the
> primary source confirms only the **trigger** and the **terminal "match-end No Blocking
> game"** — it does **not** specify *what reduced blocking changes in resolution*, nor the
> regular-season residual-tie outcome. **The design decision stands** (playoffs must be
> decisive; no separate sudden-death overtime; `PLAYOFF_OVERTIME` = match-end game). What
> was overstated is the *evidence*: the reduced-blocking resolution parameter is **OPEN**.
> Per the HARD RULE, **WT-20 enforcement does not ship**; the honest interim
> (announce-not-enforce + precise copy + disclosed playoff tiebreak) remains. The
> equivalent "primary-confirmed" wording in `CONTEXT.md` has been corrected; a narrow
> amendment to ADR 0002's worked example is **proposed** (owner's call — see the final
> report), not unilaterally applied.

## Resolutions by work item

| WT | Roadmap said | Resolved | Why / consequence |
|----|--------------|----------|-------------------|
| **WT-25** | Flip backend ("higher-scope") | **Flip backend — Tier 5 = Elite = strongest** | Justified by the 5-star mental model (player sees the raw number), not "higher-scope." Backend `base_interest` flips so higher tier starts warmer. **WT-23 probe must land in the same phase** — it is the only parity safety net for the flip. |
| **WT-30** | Reveal real intel; "flips Tactical Diff from Unscouted" | **Observed tendencies from tape, LAYERED over always-available facts** | Aggregate the opponent's *historical* `coach_policy` from past `matches.box_score_json` (persistence.py:186 — verified). Never read the hidden upcoming `CoachPolicy`. **Cold-start (week 1 / first meeting / fresh league):** Scout ALWAYS reveals derivable non-tape facts — roster shape, threat player by OVR, program archetype/identity (already player-facing) — and layers observed tendencies on top once tape exists, each clearly labeled. Without this, Scout is empty exactly when WT-30's bug bites. **Removes the latent WT-30→WT-11 dependency** (tape is finalized history). |
| **WT-18 / WT-20** | Fix ball counts; defer enforcement; doc-only honesty note | **Faithfulness taxonomy + precise copy** | Keep the "USA Dodgeball 2026.1" lineage (true) but add a precise player-facing qualifier: live officiating is **announced but not outcome-affecting**. **Correct WT-20's wording** (verified): No Blocking is *activated/announced* at official_engine.py:593 but **not enforced** in resolution; throw-clock is config-only (`throw_clock_seconds`, no penalty path); opening-rush is absent from the official engine. |
| **WT-6** | Phase 2, "may be parallelized" with Phase 1 | **Strictly after Phase 1** | Keep the balance retune isolated in time so OVR-curve movement is attributable to WT-6 alone. |
| **WT-7** | Cap/rarity for `dramatic_catch` | **Context-gate deterministically** | Emit DRAMATIC_CATCH only when the catch is genuinely clutch (even-or-behind active count / late / low-count). No random throttle. Throttle **presentation only** — leave `comeback_catches` (outcome-relevant, line 744) untouched. |
| **WT-9** | Editor saves a lineup the plan ignores | **Sim re-resolves the six from `lineup_default` unless an explicit in-week override exists** | The override path (`use_cases.py:1009`) must also run WT-10 validation. Preserves the season-default rollover/signing persistence. |
| **WT-1** | Render generic "throws into space" for `-` targets | **Event-type-aware faithful copy** | `target=None` is a real `headshot_thrower_out` foul (rec_engine.py:611), not a missing target. Generic "miss" copy would mislabel a foul — a new lie. **Enumerate every** target-less producer (rec + official) and narrate each truthfully. |
| **WT-5** | Map to "USAD Foam" etc. | **Single source of truth (long + short forms)** | There are 3+ names for each ruleset across surfaces. Create one canonical ruleset display-name module (mirroring `archetype_display_name`, commit 37e8491) with a full form (selector) and short form (compact chips). WT-5, WT-18, scoreline, voice all consume it. |
| **WT-8** | Safe variant: stop presenting inert rush modifiers | **Make it real (new mini-milestone)** | `proximity_modifier` is shown but never applied; `rush_target` **is** applied (opening ball assignment — roadmap text wrong). Wire `proximity_modifier` into resolution **legibly**, in a new **Official Live Rules mini-milestone**. *Interim (now):* stop displaying the inert modifier so no false proof persists until the milestone makes it real. |
| **WT-31** | Accept draws + framing; maybe seeded tiebreak if "uncomfortable" | **Decisiveness = enforce No Blocking (folds into WT-20); regular-season residual draws stay + framing; NO separate sudden-death OT** | **PRIMARY-SOURCE CONFIRMED (usadodgeball.com/rules, 2026):** the rulebook's tie-resolution mechanism is **No Blocking** — "if a game has not concluded within the time limit, it will enter No Blocking," play continues (reduced blocking) until elimination, incl. a terminal "match-end No Blocking game." There is **no** separate ro-sham-bo/4-min overtime — that was secondary league house-rules; **drop it.** ∴ The sim's ~30% draws are a direct symptom of No Blocking being announced-but-not-enforced (WT-20). **Faithful fix for draws (regular AND playoff) = enforce No Blocking** in `official_resolution` → this is now WT-20's job; WT-31 no longer adds a distinct mechanism. The dormant `PLAYOFF_OVERTIME` enum maps to "match-end No Blocking game," not a sudden-death period. **Regular-season residual tie** (still tied after No Blocking): excerpt is silent, but standings use **game-point differential** tiebreakers → honest no-point draws are defensible, resolved at standings level. Interim (pre-WT-20): keep honest draws + framing + the disclosed `resolve_playoff_match` tiebreak for brackets. |
| **WT-32** | Manager Lesson on inconclusive loss | **Hybrid selection: ignored-recommendation always wins, else strongest-by-magnitude** | Guard (forced by faithfulness): when **no** controllable signal applies, the lesson honestly says "nothing you controlled would have changed this" — no fabricated lessons. Primary Factor stays event-derived. |
| **WT-29** | Confirm dialog disclosing skipped decisions | **Player sets the stop point** ('next bye' / 'pre-playoffs' / 'offseason') | One dialog for the whole skip; stop options align to genuine decision boundaries; enumerates what's auto-decided. Choosing "to offseason" is an explicit, disclosed acceptance of defaults through playoffs. |
| **WT-12** | CSRF/launch token (shape TBD) | **Per-process launch token injected into the page** | Server mints a random token at startup → served into index.html → SPA sends it as a header on every mutating POST; missing/mismatched → 403. Cross-origin drive-by can't read or forge it. No user action. |
| **WT-19** | Map sections to named tests | **Three-state honesty ledger** | Each must-have section → named test + state: **enforced / announced-only / absent**. "Complete conformance" claimable only for enforced. The single honest source the WT-18 copy and the CONTEXT official-mode taxonomy both read from. Announced-only/absent rows = Official Live Rules milestone scope, surfaced not hidden. |
| **WT-21** | Per-surface accessibility cluster | **Shared accessible primitives, wrap the healthy ones** | Build tested Dialog (focus-trap/restore/Escape), segmented/radiogroup, and StatusMessage primitives; migrate broken surfaces onto them. **Wrap, never rewrite** PolicyEditor radiogroup and CeremonyShell. |
| **WT-23** | Parity probe (gate vs nightly TBD) | **Build it, run it on the WT-25 flip, set gate-vs-nightly + thresholds from measured runtime/variance** | Lean toward a standing gate if fast: deterministic N-season sweep, ≥3 champion archetypes, no archetype over a measured cap. Numbers set empirically, not guessed. |
| **WT-26** | Docs first; land WT-23 before restating parity claim | **Restate the parity claim honestly in Phase 0 now** | Correcting ("a one-time manual sweep was run; no standing probe yet") is not deleting-into-a-vacuum, so Phase 0 is not hostage to Phase 7. WT-23 later upgrades the line. |

**Clear-cut, no fork (confirmed as written):** WT-2, WT-3, WT-4, WT-10, WT-11,
WT-13, WT-14, WT-15, WT-16, WT-17, WT-22, WT-24, WT-28. **WT-27** stays deferred to
tracked issues (internal, behavior-neutral, no faithfulness angle).

---

## New: "Official Live Rules" mini-milestone (deferred engine work, now coherent)

The faithfulness lens consolidated the deferred engine work into one scoped milestone
(own spec, own gates), rather than scattered "do-not-do-yet" items:

1. **WT-8** — wire rec `proximity_modifier` into resolution (legible opening-rush
   accuracy edge + fatigue cost), with its own balance gate.
2. **WT-20 (keystone)** — **enforce No Blocking in resolution** (the rulebook's actual
   tie-resolution mechanism — primary-confirmed); throw-clock penalties; official-engine
   opening-rush activation. Enforcing No Blocking is what makes games decisive and is
   expected to collapse the ~30% draw rate on its own.
3. **WT-31 — folded into WT-20**, not a separate item. Decisiveness (regular season AND
   playoffs) comes from enforced No Blocking, including the terminal "match-end No
   Blocking game." No separate sudden-death overtime (secondary-source house-rule, dropped).
   `PLAYOFF_OVERTIME` enum = match-end No Blocking, not a ro-sham-bo period.

Each carries golden-log/probe regression risk → gated, sequenced after the Phase 0–7
trust pass, isolated for attribution (same discipline as WT-6).

---

## Sequencing amendments

- **WT-6 strictly after Phase 1** (not parallel).
- **WT-8 + WT-31-playoff + WT-20 → Official Live Rules mini-milestone** (out of Phases 2/5).
- **WT-25 and WT-23 must land in the same phase** (probe is the flip's only safety net).
- **WT-26 parity-claim restatement happens in Phase 0** (no longer waits on WT-23).
- Interim honesty patches that must ship *before* their milestone: WT-8 (stop showing
  the inert modifier), WT-18 (precise qualifier), WT-31 (disclosed playoff tiebreak).
