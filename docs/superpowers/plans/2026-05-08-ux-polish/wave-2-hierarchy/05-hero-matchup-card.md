# Subplan 05 (STUB): Hero Matchup Card + Checklist + Program Status Strip

> **Status:** STUB. Detailed task breakdown will be authored AFTER Wave 1 ships.
>
> **For the orchestrator:** When all Wave 1 subplans (01-04) have merged, invoke `superpowers:writing-plans` against this file with the acceptance criteria below + the merged Wave 1 reality (file paths, data shapes, props) as input. The skill will produce the detailed task content. Do NOT pre-author this content while Wave 1 is in flight — Wave 1's actual implementation may shift assumptions.

**Read first:** `../00-MAIN.md` for design pillars and cross-cutting principles.

**Goal:** Replace the Match Week pre-sim mode's existing layout with the locked design from `00-MAIN.md`: a top-50% hero matchup card and a bottom 60/40 split (checklist on the left, program status strip on the right).

**Dependencies:**
- Subplan 02 must have merged (Match Week shell exists with `pre-sim` mode renderer).
- Subplan 03 must have merged (Dev Focus moved off Match Week).
- Subplan 04 must have merged (department orders moved off Match Week).

**Parallel-safe with:** Subplans 06, 07, 09. Touches `MatchWeek.tsx`'s pre-sim render only — coordinates with Subplan 06 which touches the post-sim render.

**Acceptance criteria (from `00-MAIN.md`):**
- Pre-sim mode renders top-50% hero matchup card with team logos, records, written framing line (template stub OK in Wave 2; voice library lands in Subplan 10), key matchup, last meeting, Sim button, speed toggle.
- Bottom 60/40 split for checklist (with required items gated, optional items showing slot costs) and program status strip.
- `Accept Recommended Plan` shows a diff toast listing what changed.
- Hard gates enforced: Sim button disabled until valid 6-player lineup + tactic selected.
- Speed toggle (Fast / Normal / Slow) lives next to the Sim button on the matchup card.
- Right column (program status strip) is glanceable, non-interactive — clicks deep-link to other tabs.

**Files anticipated for modification:**
- `frontend/src/components/MatchWeek.tsx` (rewrite the `renderPreSimMode` function)
- New: `frontend/src/components/match-week/MatchupCard.tsx`
- New: `frontend/src/components/match-week/WeeklyChecklist.tsx`
- New: `frontend/src/components/match-week/ProgramStatusStrip.tsx`
- `frontend/src/types.ts` (likely new fields for matchup framing data)
- `src/dodgeball_sim/server.py` (likely new endpoint or extension for matchup card data: opponent record, last meeting, key matchup heuristic)

**Verification gates (when authored):**
- `cd frontend && npm run build` exits 0
- `python -m pytest -q` exits 0 with new tests for any added endpoint
- Manual smoke: pre-sim mode visually matches the locked design; Sim button gating works; Accept Recommended diff toast renders.
