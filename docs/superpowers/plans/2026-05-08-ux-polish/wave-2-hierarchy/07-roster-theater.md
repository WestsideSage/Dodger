# Subplan 07 (STUB): Roster Theater Redesign + Tier-Stars Potential

> **Status:** STUB. Detailed task breakdown authored after Wave 1 ships. Read `../00-MAIN.md` first.

**Goal:** Convert Roster from a personnel ledger to a development theater — rich per-player cards with deltas, sparklines, full attribute names, and a tier+stars potential display that NEVER shows a numeric value.

**Dependencies:** Subplan 03 (Dev Focus chip already on Roster header strip). Parallel-safe with 05, 06, 08, 09.

**Acceptance criteria:**
- Theater mode is the default render. A `Compact` toggle (button in the header strip) collapses to dense rows.
- Each theater row shows: jersey + name + class/captain/newcomer tags · full attribute names with current value + delta arrow + this-season delta · `Potential: <Tier> ★★★★☆` · OVR with this-season delta · sparkline of weekly OVR · Status (Starter/Bench/Reserve/Injured).
- **Potential is NEVER shown numerically.** Tier labels: `Elite` / `High` / `Solid` / `Limited`. Confidence: 1-5 stars based on player age and applied scouting passes.
- Stat abbreviations (POW, ACC, DOD, POT) are removed from theater view. Compact view may use abbreviations.
- Header strip replaces the existing 3-number corner card with: `Avg Age · Avg OVR · OVR Trend ↑ · Players Improving (X/Y) · Dev Focus chip` (chip relocated in Subplan 03).
- Newcomer is shown as a tag in the player's name line; Status shows role only — no Newcomer/Status redundancy.
- Sparkline is computed from `player.weekly_ovr_history` or equivalent; if the sim doesn't currently track weekly OVR, this subplan extends it.

**Files anticipated:**
- `frontend/src/components/Roster.tsx` (substantial rewrite)
- New: `frontend/src/components/roster/PlayerTheaterRow.tsx`
- New: `frontend/src/components/roster/PlayerCompactRow.tsx`
- New: `frontend/src/components/roster/PotentialBadge.tsx`
- New: `frontend/src/components/roster/Sparkline.tsx`
- `src/dodgeball_sim/server.py` (Roster endpoint payload extended with weekly OVR history, deltas, scouting confidence)
- `src/dodgeball_sim/development.py` and/or `src/dodgeball_sim/scouting.py` (potential tier mapping, confidence calculation, OVR history tracking)

**Critical constraint:** This subplan must NOT leak internal sim float values (potential, fit_score, raw OVR with decimals) into UI rendering. All numbers shown to the player are integers; potential is never a number at all.

**Verification gates:** build + pytest green; tests for tier mapping logic; tests for partial-reveal scouting confidence; manual smoke confirms no decimals visible anywhere on Roster.
