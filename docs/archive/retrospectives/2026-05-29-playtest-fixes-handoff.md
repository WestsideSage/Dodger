# Handoff — Playtest Fixes Plan (next session jump-start)

Paste the block below to start the next session. Everything it references is on
disk; no conversation memory needed.

---

You are resuming planned work on Dodgeball Manager. A planning + verification
session on 2026-05-29 produced a multi-phase plan and surfaced a measured
blocker. Do NOT re-plan from scratch and do NOT re-open settled decisions.

## Read first, in order
1. `docs/specs/2026-05-29-playtest-fixes-multi-phase-plan.md` — THE plan. Read the
   "Resolved design decisions" table (D1–D9), the phases, and especially the
   "2026-05-29 — Gemini report verification note" at the end.
2. `AGENTS.md`, `docs/STATUS.md` — repo rules + current state.
3. The two research reports (treat as inputs, already verified — see note in #1):
   - `docs/reviews/2026-05-29-phase4-balance-baseline.md` (Gemini Flash — evidence
     invalid, conclusion vindicated)
   - `docs/reviews/2026-05-29-phase4-rules-and-moments-research.md` (Gemini Pro —
     usable; spot-check rulebook citations before quoting)

## What's decided (do not relitigate)
- D1 canonical fielded-6 (best-by-role/OVR auto + manual persists across seasons).
- D2 banded Favorite/Even/Underdog tag; net OVR → advisory detail.
- D3 readiness: scout + new confirm-lineup gate earnable; rest default-satisfied;
  bye auto-clears scout.
- D4 new careers default foam-official for set scoring — **GATED, see blocker.**
- D5 records league-wide + honest empty-state + My Club/League filter.
- D6 straddlers logic-first. D7 multi-week sim auto-pilot. D8 §4 = Claude Design
  briefs (not finished UI). D9 growth legibility = Player Card + Dev beat +
  Roster Lab.

## The blocker (measured 2026-05-29)
The official match engine (`run_autonomous_match`, the path real matches ship
through) does NOT reward OVR. Corrected probe `tools/official_match_probe.py`
(300 trials/rung): win rate +0→40.3%, +24→44.3%, +48→47.7%, +72→43.7%. Slope
+3.3pp (gate needs +10), top floor 43.7% (needs 60%), 21.6% draws. Rec driver
hits ~70% on identical inputs → engine-attributable. Prime suspect:
catch-dominance in `official_resolution.resolve_throw` (~68% catch at even
ratings; a catch outs the thrower and resurrects a defender).
**Trap:** `OfficialDriver` (`official_driver.py`) is a single-game STUB
(`run_autonomous_game`, `moment_events=()`) — NOT the shipping engine. The old
probe `tools/tier_engine_health_probe.py` imports it from the wrong module and
measures the stub; don't trust its official numbers.

## Suggested first actions (pick with the owner, Maurice)
This is still PLANNING/diagnostic posture unless Maurice says build. Likely order:
1. **Confirm the probe result is reproducible** — re-run
   `python tools/official_match_probe.py --trials 300` (deterministic seeds; should
   match). Optionally bump trials.
2. **Diagnose the OVR-flatness** in `official_resolution.resolve_throw` /
   `official_tactics.decide_catch_attempt`: is the catch-dominance hypothesis the
   real cause? (accuracy/dodge also scale with OVR and may offset.) Read before
   touching math.
3. Decide whether to start implementation at **Phase 0/1** (independent of the D4
   blocker — canonical fielded-6 is the highest-trust root) while the official
   balance retune (Phase 4a) is scoped separately.
4. If implementing: one scoped phase at a time, TDD where risk warrants, full
   `python -m pytest -q` for broad/engine changes, and the stale-server guard
   (fresh PID on port 8000) before any browser verification.

## Guardrails
No new dependencies, no public-API/routing/auth changes without explicit
justification. Engine math changes update golden logs + document why (AGENTS.md).
Keep `tools/official_match_probe.py` — Phase 4a graduates it into the OVR gate.

---
