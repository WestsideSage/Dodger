# Subplan 05: Hero Matchup Card + Checklist + Program Status Strip

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Read `../00-MAIN.md` first. Depends on Wave 1 subplans merging.

**Goal:** Replace the Match Week pre-sim mode's existing layout with the locked design from `00-MAIN.md`: a top-50% hero matchup card and a bottom 60/40 split (checklist on the left, program status strip on the right).

**Dependencies:** Wave 1 (Subplans 01-04) must be merged. Parallel-safe with 06, 07, 09.

**Acceptance criteria (from 00-MAIN.md):**
- Pre-sim mode renders top-50% hero matchup card with team logos, records, written framing line (template stub OK in Wave 2; voice library lands in Subplan 10), key matchup, last meeting, Sim button, speed toggle.
- Bottom 60/40 split for checklist (with required items gated, optional items showing slot costs) and program status strip.
- `Accept Recommended Plan` shows a diff toast listing what changed.
- Hard gates enforced: Sim button disabled until valid 6-player lineup + tactic selected.
- Speed toggle (Fast / Normal / Slow) lives next to the Sim button on the matchup card.
- Right column (program status strip) is glanceable, non-interactive — clicks deep-link to other tabs.

**Files anticipated for modification:**
- Modify: `frontend/src/components/MatchWeek.tsx`
- New: `frontend/src/components/match-week/MatchupCard.tsx`
- New: `frontend/src/components/match-week/WeeklyChecklist.tsx`
- New: `frontend/src/components/match-week/ProgramStatusStrip.tsx`
- Modify: `frontend/src/types.ts`
- Modify: `src/dodgeball_sim/server.py`
- New: `tests/test_matchup_payload.py`

---

- [ ] **Step 1: Write Python tests for matchup data payload**

Create `tests/test_matchup_payload.py`:
```python
from fastapi.testclient import TestClient
from dodgeball_sim.server import app
import sqlite3
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import create_schema
from dodgeball_sim import server

def test_matchup_details_payload():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)
        response = client.get('/api/command-center')
        assert response.status_code == 200
        plan = response.json()['plan']
        
        assert 'matchup_details' in plan
        details = plan['matchup_details']
        assert 'opponent_record' in details
        assert 'last_meeting' in details
        assert 'key_matchup' in details
        assert 'framing_line' in details
    finally:
        server.app.dependency_overrides.clear()
```
Run `python -m pytest tests/test_matchup_payload.py -v`. Expect failure.

- [ ] **Step 2: Modify backend to serve matchup data**

In `src/dodgeball_sim/command_center.py` (or where the command center payload is built), add the `matchup_details` dict to the output payload. Use stub values for now (e.g., `framing_line: "A tough matchup against a conference rival."`).
Run tests, see them pass. Commit.

- [ ] **Step 3: Update TypeScript types**

In `frontend/src/types.ts`, add:
```ts
export interface MatchupDetails {
  opponent_record: string;
  last_meeting: string;
  key_matchup: string;
  framing_line: string;
}
```
Add `matchup_details?: MatchupDetails` to `CommandCenterPlan` (or equivalent). Commit.

- [ ] **Step 4: Create MatchupCard component**

Create `frontend/src/components/match-week/MatchupCard.tsx`.
```tsx
import { useState } from 'react';
import { ActionButton } from '../ui';

// Note: Speed toggle state is UI-only for Wave 2. Real wiring lands in Subplan 12.
export function MatchupCard({ plan, onSimulate, disabled }: { plan: any, onSimulate: () => void, disabled: boolean }) {
  const [speed, setSpeed] = useState<'Fast' | 'Normal' | 'Slow'>('Normal');
  const details = plan.matchup_details || {
      opponent_record: "0-0", last_meeting: "None", key_matchup: "TBD", framing_line: "Matchup pending."
  };

  return (
    <div className="dm-panel" style={{ minHeight: '300px' }}>
      <h2>Matchup</h2>
      <p><i>{details.framing_line}</i></p>
      <div style={{ display: 'flex', gap: '2rem' }}>
        <div><b>Opponent Record:</b> {details.opponent_record}</div>
        <div><b>Last Meeting:</b> {details.last_meeting}</div>
        <div><b>Key Matchup:</b> {details.key_matchup}</div>
      </div>
      <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <ActionButton variant="accent" disabled={disabled} onClick={onSimulate}>Simulate Match</ActionButton>
        <select value={speed} onChange={e => setSpeed(e.target.value as any)}>
          <option value="Fast">Fast</option>
          <option value="Normal">Normal</option>
          <option value="Slow">Slow</option>
        </select>
      </div>
    </div>
  );
}
```
Commit.

- [ ] **Step 5: Create Diff Toast logic & Weekly Checklist**

Create `frontend/src/components/match-week/WeeklyChecklist.tsx`.
```tsx
import { useState } from 'react';
import { ActionButton } from '../ui';

export function WeeklyChecklist({ plan, onAcceptPlan }: { plan: any, onAcceptPlan: () => void }) {
  const [toast, setToast] = useState<string | null>(null);

  const handleAccept = () => {
    // Basic diff logic for Wave 2
    const diff = ["Tactic updated", "Lineup optimized"];
    setToast(`Plan accepted: ${diff.join(', ')}`);
    onAcceptPlan();
    setTimeout(() => setToast(null), 3000);
  };

  return (
    <div className="dm-panel" style={{ flex: 6 }}>
      <h3>Weekly Checklist</h3>
      {toast && <div style={{ padding: '0.5rem', background: '#10b981', color: 'white', marginBottom: '1rem' }}>{toast}</div>}
      <ActionButton onClick={handleAccept}>Accept Recommended Plan</ActionButton>
      {/* Checklist items here */}
    </div>
  );
}
```
Commit.

- [ ] **Step 6: Create ProgramStatusStrip & assemble MatchWeek**

Create `frontend/src/components/match-week/ProgramStatusStrip.tsx` (a simple flex container with placeholders linking to `?tab=roster`, etc.).
Update `MatchWeek.tsx` to render the 3 components.
```tsx
const isSimReady = data.plan.lineup.warnings?.length === 0; // Or specific lineup/tactic check
return (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
    <MatchupCard plan={data.plan} onSimulate={simulate} disabled={!isSimReady} />
    <div style={{ display: 'flex', gap: '1.25rem' }}>
      <WeeklyChecklist plan={data.plan} onAcceptPlan={() => savePlan()} />
      <ProgramStatusStrip />
    </div>
  </div>
);
```
Commit.

- [ ] **Step 7: Cross-cutting principle check**

Run `npm run build` and `pytest -q`.
Grep or visually inspect the UI to ensure:
- Only ONE primary action per screen (Sim button is the visual hero).
- Speed toggle is purely presentational in UI.
- No float leaked.
```bash
git commit --amend --no-edit  # if fixes applied
```