# Workflow 0 — Primary-Source Rule Verification (engine-milestone gate)

Date: 2026-06-01
Status: **GATE RESULT — partial. The keystone parameter for WT-20 is OPEN.**
Authority: This is the primary-source verification required by ADR 0002 and the
ultracode roadmap's "Workflow 0" gate. It governs whether the *Official Live Rules*
engine milestone (WT-20 / WT-31, and WT-8's official-mode framing) may ship.

Primary source consulted: **usadodgeball.com/rules** (inline rules content; the site
exposes **no downloadable rulebook PDF** — the `/rules/usa-dodgeball-rules-pdf` URL
returns only a title heading, and the page link inventory contains no PDF href).
Method honesty caveat: the page text reached me via the harness's page-to-markdown
fetch (a fast summarizing model), **not** a hand-verified verbatim PDF. Rows below are
therefore "sourced-as-read," and the *exact* verbatim wording carries that caveat. No
row is upgraded to "verbatim-confirmed." Secondary sources (Pride Sports USA, CSL,
Underdog Portland, Cactus) were **excluded by rule** (ADR 0002) and in fact *conflict*
with the primary on the tie mechanism — see "Adversarial cross-check."

## Verified parameter table

| Parameter the engine milestone needs | Primary-source finding | State | Source phrase (as read) |
|---|---|---|---|
| **No Blocking — trigger** | A game that has not concluded within the time limit enters No Blocking. | **SOURCED** | "If a game has not concluded within the time limit, it will enter No Blocking." |
| **No Blocking — ball reset per side** | Balls do **not** reset on entering No Blocking. Corrects the task's "ball-reset count per side" framing — there is **no reset count to source**. | **SOURCED (negative)** | "Balls do not reset." |
| **No Blocking — terminal / match-end** | If the match clock expires during No Blocking, play continues and the current game becomes a "match-end No Blocking game." Confirms the `PLAYOFF_OVERTIME`→match-end reinterpretation. | **SOURCED** | "play continues without interruption and the current game becomes a match-end No Blocking game." |
| **No Blocking — what "reduced blocking" changes in resolution** | **NOT detailed on the page.** The mechanic that WT-20 must enforce (how blocking is reduced/removed and how that changes throw/catch resolution) is named but its parameters are absent. | **OPEN** | page provides no section describing modified blocking rules during No Blocking |
| **Regular-season still-tied-after-No-Blocking outcome** | **NOT addressed.** No further tiebreak, no "game-point differential" seeding rule is stated on the page. The spec's "game-point differential (primary-confirmed)" claim is **not** corroborated here. | **OPEN** | "The page does not address how tied games are resolved when time expires." |
| **Throw clock — cloth** | 10-second throw clock; burdened team gets 5 seconds to relinquish majority possession; ball-holders who fail to attempt are out. | **SOURCED (cloth only)** | "Throw clock starts at 10 seconds. Burdened team gets 5 seconds… players controlling balls… who failed to attempt are out." |
| **Throw clock / stalling — foam & no-sting** | No 10s/5s throw clock. Stalling is governed by "burden resets on every valid throw by either team." No explicit stalling-out penalty path stated. | **SOURCED (mechanic) / OPEN (penalty path)** | "Burden resets on every valid throw by either team." |
| **Opening rush / opening sprint activation** | **No separate opening-sprint rule.** Opening play is governed only by: possession of a ball belongs to the team that brought it across the center line. WT-20's "opening-rush activation" is **not a primary-source rule.** | **OPEN (as a USAD rule)** | "Once a ball fully crosses center line, possession belongs to the team that brought it to that side." |
| **Foam/no-sting game length & scoring** | Game = 3 minutes within the overall match timer; a game point is earned only by eliminating the entire opposing team. | **SOURCED** | "3 minutes within the overall match timer"; "A game point is earned only by eliminating the entire opposing team." |
| **Foam vs no-sting material difference (for the above)** | Not detailed beyond shared burden/scoring; no parameter difference sourced. | **OPEN (no diff to source)** | "material distinctions between foam and no-sting are not detailed." |

## Adversarial cross-check (the ADR-0002 discipline, applied)

- The web search surfaced **Pride Sports USA**: "a tie breaker game: 1 minute with
  blocking, then NO BLOCKING." This is a **secondary** source and it **conflicts** with
  the primary (primary: No Blocking is entered when a game has not concluded within the
  time limit — *not* a separate 1-minute blocking pre-period). Per ADR 0002 it is
  excluded. Its existence is the proof of *why* the rule says "verify against the primary,
  not a plausible secondary": the two disagree on the exact mechanism.
- The spec (CONTEXT.md, resolutions log, ADR 0002 itself) asserts as
  **"PRIMARY-SOURCE CONFIRMED"** that No Blocking means "play continues with **reduced
  blocking** until a team is eliminated." The primary source confirms the **trigger** and
  the **match-end game**, but the **"reduced blocking" resolution mechanics are not on the
  page.** The spec therefore claims *more* primary confirmation than the primary provides.
  This is recorded here, not silently inherited.

### Firming fetch (advisor-recommended, locked)

A second full-section fetch of the same primary page was run specifically to guard
against a fast-model "not detailed" false-OPEN. It reproduced the **entire** No Blocking
section as exactly three statements: (a) "If a game has not concluded within the time
limit, it will enter No Blocking. The game is briefly stopped and resumes with the same
players. Balls do not reset." (b) "After transitioning to No Blocking, at the end of a
game or match, the burden count will reset." (c) "If the match clock expires during No
Blocking, play continues without interruption and the current game becomes a match-end No
Blocking game." It explicitly confirmed: "no additional details… no specifications about
which blocking techniques become disallowed, how players are eliminated during No Blocking
phases, what occurs if teams remain tied after No Blocking, or any formal overtime
procedures." The OPEN keystone is therefore **locked**, not a fetch artifact.

## Gate decision (binding, per the HARD RULE)

> "never ship an engine rule whose parameters Workflow 0 could not source. The honest
> interim (announce-not-enforce + precise copy) ships instead, and the item stays OPEN."

- **WT-20 (enforce No Blocking in resolution): DOES NOT SHIP.** Its keystone parameter —
  what reduced blocking changes — is OPEN. Inventing it would be the exact faithfulness
  violation the gate exists to prevent. **WT-20 stays OPEN** with the three OPEN rows above.
- **WT-31 (folds into WT-20): DOES NOT SHIP** as enforcement. The disclosed
  `resolve_playoff_match` tiebreak **interim** stays (already honest: `decided_by` +
  `narrative_note`). No sudden-death overtime is added (primary: none exists; secondary
  conflicts — excluded).
- **WT-8 official-mode wiring: DOES NOT SHIP as official-rule fidelity.** Opening-rush is
  not a USAD rule (OPEN). **Correction (2026-06-01 review):** the inert `proximity_modifier`
  opening-rush copy is surfaced **only in the rec/legacy replay path** (`rush_context` is
  populated by `engine.py` / `rec_engine.py`, never the official engine), where the rush is a
  real computed mechanic and the note is faithful — so **no inert false-proof persists in
  official replays**, and the "stop displaying" interim was neither required nor implemented
  in code this pass. Any future official wiring is a *sim-design* choice that must **not** be
  presented to the player as USA Dodgeball fidelity.
- **What the engine pass CAN still do faithfully (no unsourced *rule* involved):**
  - **WT-6** catch-posture policy inversion — an internal correctness/balance fix, gated
    by `test_official_engine_balance` + the probes. Not a rule-parameter claim.
  - **WT-7** DRAMATIC_CATCH context-gating — presentation rate only; outcomes unchanged.
  - The **honest cloth throw-clock penalty** (10s/5s, holders-out) *is* sourced, but
    wiring it is still net-new engine behavior with golden-log risk → it belongs to the
    deferred milestone, not this pass; recorded SOURCED so a future milestone can use it
    without re-deriving.

## Known latent engine inaccuracy (for the WT-20 implementer, not player-facing)

The official engine hardcodes a No Blocking ball reset of `three_per_side`
(`no_blocking.py:29`, `official_engine.py:595`) and bakes it into a
`replay_summary` string. This **contradicts** the primary source's "Balls do not
reset" (the SOURCED-negative row above). It is recorded here because it is *latent*:
the No Blocking events are non-SEQUENCE, so `translate_events` drops them and the
string never reaches a player-facing `MatchResult` (verified: `collect_official_metadata`
is only called in a translator test; the web replay state carries no `ball_reset`
field; a frontend grep for `three_per_side` is empty). Unlike the inert
`proximity_modifier` (which *is* shown), this never surfaces, so it is not an artifact
faithfulness violation — but it must be corrected to "balls do not reset" when No
Blocking is genuinely enforced.

## Net effect on the plan

The "Official Live Rules" milestone's headline deliverable (No Blocking enforcement,
expected to collapse the ~30% draw rate) is **blocked at the primary-source gate** and
must remain the honest interim. The engine pass reduces to WT-6 (balance correctness)
and WT-7 (presentation), each independently gated — plus the WT-8 *interim* (stop the
inert proof). Draw density is therefore addressed by WT-6's catch-posture fix and honest
framing, **not** by enforcing an unsourced No Blocking mechanic.
