# Subplan 06: Aftermath Blocks with Sequenced Reveal

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Read `../00-MAIN.md` first.

**Goal:** Replace Match Week's post-sim mode stub with the five-block Aftermath surface, revealed in sequence.

**Dependencies:** Subplan 02 (Wave 1). Parallel-safe with 05, 07, 08, 09.

**Acceptance criteria (from 00-MAIN.md):**
- Post-sim mode renders 5 stacked blocks in this order: Headline → Match Card → Player Growth → Standings Shift → Recruit Reactions.
- Each block fades in with a staggered delay (~1s between blocks).
- Reveal sequence skippable via spacebar or click-anywhere.
- Player Growth block pulls real player attribute deltas from the most recent match's effect on roster development.
- Recruit Reactions block pulls real prospect interest deltas tied to the match outcome (e.g., `interest_evidence` from `dynasty_office.recruiting.prospects`).
- `Advance to Next Week` is the single primary CTA at the bottom; no competing buttons.
- Headline copy may use a stub template in Wave 2; the rich voice library replaces it in Subplan 10.

---

- [ ] **Step 1: Write backend tests for aftermath payload**

Create `tests/test_aftermath_payload.py` with actual test logic:
```python
from fastapi.testclient import TestClient
from dodgeball_sim.server import app

def test_aftermath_payload_structure(setup_active_save): # use proper test fixture
    client = TestClient(app)
    # trigger sim
    res = client.post('/api/command-center/simulate', json={'intent': 'Win Now'})
    assert res.status_code == 200
    data = res.json()
    assert 'aftermath' in data
    assert 'headline' in data['aftermath']
    assert 'player_growth_deltas' in data['aftermath']
    assert 'recruit_reactions' in data['aftermath']
```
Run, fail.

- [ ] **Step 2: Modify backend to serve aftermath data**

Update `src/dodgeball_sim/server.py` `/api/command-center/simulate`. Map actual match stat diffs into `player_growth_deltas` and prospect updates to `recruit_reactions`. Add `aftermath` block to response. Pass tests. Commit.

- [ ] **Step 3: Create Headline & MatchCard Blocks**

Create `frontend/src/components/match-week/aftermath/Headline.tsx` and `MatchCard.tsx`. Use minimal structural JSX.
```tsx
export function Headline({ text }: { text: string }) {
  return <h1 className="dm-headline">{text}</h1>;
}
```
Commit.

- [ ] **Step 4: Create Growth & Reactions Blocks**

Create `PlayerGrowthBlock.tsx` and `RecruitReactions.tsx`. Ensure deltas show as explicit `+1` with arrows (e.g. `Catching: 45 ↑2`), never raw values. Commit.

- [ ] **Step 5: Create StandingsShift Block**

Create `StandingsShift.tsx`. Commit.

- [ ] **Step 6: Orchestrate the Sequenced Reveal in MatchWeek.tsx**

In `MatchWeek.tsx`'s `renderPostSimMode`, orchestrate the reveal.
```tsx
const [revealStage, setRevealStage] = useState(0);

useEffect(() => {
  if (revealStage >= 5) return;
  const t = setTimeout(() => setRevealStage(prev => prev + 1), 1000);
  return () => clearTimeout(t);
}, [revealStage]);

useEffect(() => {
  const skip = (e: KeyboardEvent | MouseEvent) => {
    if (e.type === 'keydown' && (e as KeyboardEvent).code !== 'Space') return;
    setRevealStage(5);
  };
  window.addEventListener('keydown', skip);
  window.addEventListener('click', skip);
  return () => { window.removeEventListener('keydown', skip); window.removeEventListener('click', skip); };
}, []);

return (
  <div className="dm-aftermath">
    {revealStage >= 0 && <Headline text={result.aftermath.headline} />}
    {revealStage >= 1 && <MatchCard data={result.aftermath.match_card} />}
    {/* ... down to stage 5 */}
    {revealStage >= 5 && <ActionButton onClick={onAdvanceWeek}>Advance to Next Week</ActionButton>}
  </div>
);
```
Commit.

- [ ] **Step 7: Cross-cutting principle check**

Run `npm run build` & `pytest -q`.
Verify spacebar triggers skip. Verify NO numbers are floats (e.g., if a growth delta is 0.5, ensure backend floors it or frontend rounds it).
```bash
git commit --amend --no-edit
```