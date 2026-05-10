# Subplan 07: Roster Theater Redesign + Tier-Stars Potential

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Read `../00-MAIN.md` first.

**Goal:** Convert Roster from a personnel ledger to a development theater — rich per-player cards with deltas, sparklines, full attribute names, and a tier+stars potential display that NEVER shows a numeric value.

**Dependencies:** Subplan 03 (Dev Focus chip already on Roster header strip). Parallel-safe with 05, 06, 08, 09.

**Acceptance criteria (from 00-MAIN.md):**
- Theater mode is the default render. A `Compact` toggle (button in the header strip) collapses to dense rows.
- Each theater row shows: jersey + name + class/captain/newcomer tags · full attribute names with current value + delta arrow + this-season delta · `Potential: <Tier> ★★★★☆` · OVR with this-season delta · sparkline of weekly OVR · Status (Starter/Bench/Reserve/Injured).
- **Potential is NEVER shown numerically.** Tier labels: `Elite` / `High` / `Solid` / `Limited`. Confidence: 1-5 stars based on player age and applied scouting passes.
- Stat abbreviations (POW, ACC, DOD, POT) are removed from theater view. Compact view may use abbreviations.
- Header strip replaces the existing 3-number corner card with: `Avg Age · Avg OVR · OVR Trend ↑ · Players Improving (X/Y) · Dev Focus chip` (chip relocated in Subplan 03).
- Newcomer is shown as a tag in the player's name line; Status shows role only — no Newcomer/Status redundancy.
- Sparkline is computed from `player.weekly_ovr_history` or equivalent; if the sim doesn't currently track weekly OVR, this subplan extends it.

---

- [ ] **Step 1: Write backend tests for potential tiers and OVR history**

Create `tests/test_roster_payload.py`:
```python
def test_potential_tier_mapping():
    # Elite >= 90, High 80-89, Solid 65-79, Limited < 65
    from dodgeball_sim.development import calculate_potential_tier
    assert calculate_potential_tier(92) == "Elite"
    assert calculate_potential_tier(85) == "High"
    assert calculate_potential_tier(75) == "Solid"
    assert calculate_potential_tier(50) == "Limited"

def test_roster_endpoint_payload_structure(setup_active_save):
    # Verify api returns potential_tier, scouting_confidence, and weekly_ovr_history
    # Verify potential (float) is omitted or safely ignored
```
Run, fail.

- [ ] **Step 2: Modify backend to serve theater data**

In `src/dodgeball_sim/development.py`, implement `calculate_potential_tier` using the `90 / 80 / 65` boundaries.
In `server.py` Roster endpoint, map `player.traits.potential` out and insert `potential_tier`, `scouting_confidence` (1-5 int), and `weekly_ovr_history` (list of ints). Pass tests. Commit.

- [ ] **Step 3: Build Sub-components (Sparkline & PotentialBadge)**

Create `frontend/src/components/roster/PotentialBadge.tsx`:
```tsx
export function PotentialBadge({ tier, confidence }: { tier: string, confidence: number }) {
  const stars = '★'.repeat(confidence) + '☆'.repeat(5 - confidence);
  return <div className="dm-potential-badge">Potential: {tier} <span style={{ color: 'gold' }}>{stars}</span></div>;
}
```
Create `Sparkline.tsx` (simple SVG polyline of OVR history). Commit.

- [ ] **Step 4: Create Theater and Compact Rows**

Create `PlayerTheaterRow.tsx` displaying full words (`Power: 80`, `Catching: 60`).
Create `PlayerCompactRow.tsx` displaying abbreviations (`POW`, `CAT`).
Commit.

- [ ] **Step 5: Rewrite Roster.tsx**

Add the `Compact` toggle to the header:
```tsx
const [isCompact, setIsCompact] = useState(false);
// ...
<button onClick={() => setIsCompact(!isCompact)}>{isCompact ? 'Theater View' : 'Compact View'}</button>
```
Update header strip stats to include `Players Improving (X/Y)`. Wire row mapping. Commit.

- [ ] **Step 6: Cross-cutting principle check (No Float Leaks)**

Run `cd frontend && npm run build`. Run `pytest -q`.
**Critical Check:** Grep the codebase. Are there any `toFixed()` calls on `potential` or `fit_score` in the frontend? There shouldn't be — they shouldn't even arrive from the backend. The backend must floor/round all OVR history arrays to integers before transmission.
```bash
git commit --amend --no-edit
```