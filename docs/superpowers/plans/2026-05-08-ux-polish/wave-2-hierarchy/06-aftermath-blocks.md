# Subplan 06 (STUB): Aftermath Blocks with Sequenced Reveal

> **Status:** STUB. Detailed task breakdown authored after Wave 1 ships. Read `../00-MAIN.md` first.

**Goal:** Replace Match Week's post-sim mode stub with the five-block Aftermath surface, revealed in sequence.

**Dependencies:** Subplan 02. Parallel-safe with 05, 07, 08, 09.

**Acceptance criteria:**
- Post-sim mode renders 5 stacked blocks in this order: Headline → Match Card → Player Growth → Standings Shift → Recruit Reactions.
- Each block fades in with a staggered delay (~1s between blocks).
- Reveal sequence skippable via spacebar or click-anywhere.
- Player Growth block pulls real player attribute deltas from the most recent match's effect on roster development.
- Recruit Reactions block pulls real prospect interest deltas tied to the match outcome (e.g., `interest_evidence` from `dynasty_office.recruiting.prospects`).
- `Advance to Next Week` is the single primary CTA at the bottom; no competing buttons.
- Headline copy may use a stub template in Wave 2; the rich voice library replaces it in Subplan 10.

**Files anticipated:**
- `frontend/src/components/MatchWeek.tsx` (rewrite `renderPostSimMode`)
- New: `frontend/src/components/match-week/aftermath/Headline.tsx`
- New: `frontend/src/components/match-week/aftermath/MatchCard.tsx`
- New: `frontend/src/components/match-week/aftermath/PlayerGrowthBlock.tsx`
- New: `frontend/src/components/match-week/aftermath/StandingsShift.tsx`
- New: `frontend/src/components/match-week/aftermath/RecruitReactions.tsx`
- `src/dodgeball_sim/server.py` (likely new aftermath payload endpoint that consolidates the data the blocks need — single round-trip)
- `src/dodgeball_sim/development.py` (may need to expose per-match attribute deltas)

**Verification gates:** build + pytest green; new endpoint covered by tests; manual smoke confirms reveal sequence and skip behavior.
