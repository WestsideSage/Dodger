# Subplan 09: Standings Polish

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Read `../00-MAIN.md` first.

**Goal:** Replace cryptic column abbreviations with full words and add a recent-matches sidebar that absorbs old NewsWire-style "team beat team" content.

**Dependencies:** Subplan 01. Parallel-safe with 05-08.

**Acceptance criteria (from 00-MAIN.md):**
- Table column headers use full words: `Wins`, `Losses`, `Ties`, `Points For`, `Points Against`, `Differential`, `Streak`.
- Compact display in narrow viewports may collapse to abbreviations (`W`, `L`, `T`).
- Recent matches sidebar lists last ~5 league results across all teams, written in templated voice.
- Each row in Standings is clickable; deep-links to placeholder team detail view.
- Visual treatment: clear separation between user's team row and the rest.

---

- [ ] **Step 1: Write backend tests for recent matches payload**

Create `tests/test_standings_recent_matches.py`:
```python
from fastapi.testclient import TestClient
from dodgeball_sim.server import app

def test_standings_includes_recent_matches(setup_active_save):
    client = TestClient(app)
    res = client.get('/api/standings')
    data = res.json()
    assert 'recent_matches' in data
    assert type(data['recent_matches']) == list
```
Run, fail.

- [ ] **Step 2: Modify backend to serve recent matches**

Update `src/dodgeball_sim/server.py` Standings endpoint to fetch the latest ~5 league-wide matches from the history/db.
Run tests, see them pass. Commit.

- [ ] **Step 3: Create RecentMatchesSidebar**

Create `frontend/src/components/standings/RecentMatchesSidebar.tsx`:
```tsx
export function RecentMatchesSidebar({ matches }: { matches: any[] }) {
  return (
    <div className="dm-panel" style={{ flex: '1 1 300px' }}>
      <h3>Around the League</h3>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {matches.map(m => (
          <li key={m.id} style={{ padding: '0.5rem 0', borderBottom: '1px solid #334155' }}>
            {m.winner_name} def. {m.loser_name} ({m.score})
          </li>
        ))}
      </ul>
    </div>
  );
}
```
Commit.

- [ ] **Step 4: Table Headers & Responsive Abbreviations**

In `frontend/src/components/LeagueContext.tsx` (`Standings` component), update the `<TableHeadCell>` entries:
```tsx
<TableHeadCell><span className="hidden md:inline">Wins</span><span className="md:hidden">W</span></TableHeadCell>
```
Commit.

- [ ] **Step 5: Click-through Routing & Visual Separation**

Wrap each `<tr>` content (or add an `onClick` to the `<tr>` with cursor-pointer) that pushes `?tab=dynasty&subtab=history&team_id=${team.id}` to the URL.
Add styling to highlight the user's team row:
```tsx
<tr style={{ backgroundColor: isUserTeam ? 'rgba(34, 211, 238, 0.1)' : 'transparent', cursor: 'pointer' }} onClick={...}>
```
Assemble the sidebar alongside the table. Commit.

- [ ] **Step 6: Cross-cutting principle check**

Run `npm run build` & `pytest -q`.
Ensure the click-through doesn't break the application (placeholder routing is safe).
```bash
git commit --amend --no-edit
```