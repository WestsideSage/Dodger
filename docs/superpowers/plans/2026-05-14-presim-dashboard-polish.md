# PreSim Dashboard Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the pre-match Command Center screen with Key Threat insight rows, a Match Card head-to-head comparison replacing the Starter Readiness list, and a smart pre-lock flag replacing the useless stat strip.

**Architecture:** Backend exposes opponent lineup in `build_default_weekly_plan()`; a new `MatchCard` React component renders the head-to-head comparison; all three UI changes land in `PreSimDashboard.tsx`.

**Tech Stack:** Python (backend), React 18 + TypeScript (frontend), inline CSS-in-JS via style attributes (matches existing component patterns)

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/dodgeball_sim/command_center.py` | Modify | Add `opponent_roster` to state, add `opponent_lineup` to plan response |
| `frontend/src/types.ts` | Modify | Add `LineupPlayer` named type; add `opponent_lineup` to `CommandCenterPlan` |
| `frontend/src/components/match-week/command-center/MatchCard.tsx` | Create | Self-contained head-to-head comparison card with OVR/STA toggle |
| `frontend/src/components/match-week/command-center/PreSimDashboard.tsx` | Modify | Add Key Threat insight rows, swap Starter Readiness for MatchCard, add smart pre-lock flag |

---

## Task 1: Backend — expose `opponent_lineup`

**Files:**
- Modify: `src/dodgeball_sim/command_center.py`
- Test: `tests/test_command_center.py`

### Context

`build_command_center_state()` already calls `load_all_rosters(conn)` which fetches all team rosters. It passes only the player's own roster in `state["roster"]`. We need to also pass the opponent roster so `build_default_weekly_plan()` can include it in the plan response.

The opponent's starting 6 = their full roster sorted by `overall()` descending, first 6. No default lineup is used — just raw ratings.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_command_center.py`:

```python
def test_weekly_plan_includes_opponent_lineup():
    conn = _career_conn()
    state = build_command_center_state(conn)
    plan = build_default_weekly_plan(state)

    opponent_lineup = plan.get("opponent_lineup")
    assert opponent_lineup is not None, "opponent_lineup missing from plan"
    players = opponent_lineup.get("players", [])
    assert len(players) <= 6
    if players:
        for player in players:
            assert "id" in player
            assert "name" in player
            assert "overall" in player
            assert "stamina" in player
        # sorted by overall descending
        overalls = [p["overall"] for p in players]
        assert overalls == sorted(overalls, reverse=True)
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest tests/test_command_center.py::test_weekly_plan_includes_opponent_lineup -v
```

Expected: FAIL — `KeyError` or `AssertionError: opponent_lineup missing from plan`

- [ ] **Step 3: Add `opponent_roster` to `build_command_center_state()`**

In `src/dodgeball_sim/command_center.py`, locate the `return` dict inside `build_command_center_state()` (around line 109). Add one line:

Before (lines 109-122):
```python
    return {
        "season_id": season_id,
        "week": week,
        "root_seed": int(root_seed),
        "player_club_id": player_club_id,
        "player_club": clubs[player_club_id],
        "opponent": clubs.get(opponent_id) if opponent_id else None,
        "upcoming_match": upcoming,
        "matchup_details": build_matchup_details(conn, season_id=season_id, player_club_id=player_club_id, opponent_id=opponent_id, rosters=rosters),
        "roster": list(rosters.get(player_club_id, [])),
        "default_lineup": load_lineup_default(conn, player_club_id),
        "department_heads": load_department_heads(conn),
        "history": load_command_history(conn, season_id),
    }
```

After:
```python
    return {
        "season_id": season_id,
        "week": week,
        "root_seed": int(root_seed),
        "player_club_id": player_club_id,
        "player_club": clubs[player_club_id],
        "opponent": clubs.get(opponent_id) if opponent_id else None,
        "upcoming_match": upcoming,
        "matchup_details": build_matchup_details(conn, season_id=season_id, player_club_id=player_club_id, opponent_id=opponent_id, rosters=rosters),
        "roster": list(rosters.get(player_club_id, [])),
        "opponent_roster": list(rosters.get(opponent_id, [])) if opponent_id else [],
        "default_lineup": load_lineup_default(conn, player_club_id),
        "department_heads": load_department_heads(conn),
        "history": load_command_history(conn, season_id),
    }
```

- [ ] **Step 4: Add `opponent_lineup` to `build_default_weekly_plan()`**

In `src/dodgeball_sim/command_center.py`, locate `build_default_weekly_plan()` (line 125). After the `lineup` variable is built (line 131), add:

```python
    opponent_roster = list(state.get("opponent_roster", []))
    opp_top_six = sorted(opponent_roster, key=lambda p: (-p.overall(), p.id))[:6]
    opponent_lineup = {
        "players": [_player_summary(p) for p in opp_top_six],
    }
```

Then add `"opponent_lineup": opponent_lineup` to the returned dict (at line 160, inside the `return {` block):

```python
    return {
        "season_id": state["season_id"],
        "week": state["week"],
        "player_club_id": state["player_club_id"],
        "intent": intent,
        "available_intents": list(INTENTS),
        "opponent": {
            "club_id": opponent.club_id if opponent else None,
            "name": opponent.name if opponent else "Season complete",
        },
        "department_heads": heads,
        "department_orders": dict(DEFAULT_DEPARTMENT_ORDERS),
        "recommendations": recommendations,
        "warnings": warnings,
        "lineup": lineup,
        "opponent_lineup": opponent_lineup,
        "tactics": tactics,
        "history_count": len(state.get("history", [])),
        "matchup_details": matchup_details,
    }
```

- [ ] **Step 5: Run tests**

```
python -m pytest tests/test_command_center.py -v
```

Expected: all tests pass including the new one.

- [ ] **Step 6: Commit**

```
git add src/dodgeball_sim/command_center.py tests/test_command_center.py
git commit -m "feat: expose opponent_lineup in weekly plan response"
```

---

## Task 2: Frontend types — `LineupPlayer` and `opponent_lineup`

**Files:**
- Modify: `frontend/src/types.ts`

### Context

`CommandCenterPlan.lineup.players` is currently an inline anonymous type. We need a named `LineupPlayer` type to share between `lineup.players` and the new `opponent_lineup.players`. Add it directly above `CommandCenterPlan` (line 252).

- [ ] **Step 1: Add `LineupPlayer` type and update `CommandCenterPlan`**

In `frontend/src/types.ts`, locate line 252 (`export interface CommandCenterPlan`). Insert before it:

```typescript
export interface LineupPlayer {
    id: string;
    name: string;
    overall: number;
    age?: number;
    potential?: number;
    stamina?: number;
}
```

Then update `CommandCenterPlan.lineup.players` from the inline type to `LineupPlayer[]`, and add `opponent_lineup`:

```typescript
export interface CommandCenterPlan {
    season_id: string;
    week: number;
    player_club_id: string;
    intent: string;
    available_intents: string[];
    opponent: {
        club_id: string | null;
        name: string;
    };
    department_heads: Array<{
        department: string;
        name: string;
        rating_primary: number;
        rating_secondary: number;
        voice: string;
    }>;
    department_orders: Record<string, string>;
    recommendations: Array<{
        department: string;
        voice: string;
        text: string;
    }>;
    warnings: string[];
    lineup: {
        player_ids: string[];
        players: LineupPlayer[];
        summary: string;
    };
    opponent_lineup?: {
        players: LineupPlayer[];
    };
    tactics: CoachPolicy;
    history_count: number;
    matchup_details?: MatchupDetails;
}
```

- [ ] **Step 2: Build frontend to verify no type errors**

```
cd frontend && npm run build
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 3: Commit**

```
git add frontend/src/types.ts
git commit -m "feat: add LineupPlayer type and opponent_lineup to CommandCenterPlan"
```

---

## Task 3: Key Threat insight rows

**Files:**
- Modify: `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`

### Context

The Key Threat card (lines 324–337) currently shows name, role, and OVR with empty space below. We need three full-width insight rows: OVR gap, approach conflict, and counter hint. All logic is derived from existing data — no new props.

The role→counter map:
- `Tactical` → `Control`
- `Pressure` → `Defensive`
- `Balanced` → `Balanced`
- All others → `Control`

Approach conflict: `selectedIntent === 'Win Now'` AND `threat.role` is `'Tactical'` or `'Pressure'`.

OVR gap: `gap = parseInt(threat.ovr) - Math.round(Math.max(...activePlayers.map(p => p.overall)))`
- If `gap > 0`: chip = **DANGER** (red `#ef4444`)
- If `gap <= 0`: chip = **COVERED** (green `#10b981`); gap value shown as positive `|gap|`

- [ ] **Step 1: Add derived threat values to the computation block**

In `PreSimDashboard.tsx`, after line 133 (`const threat = parseKeyMatchup(details.key_matchup);`), add:

```tsx
  const roleCounterMap: Record<string, string> = {
    Tactical: 'Control',
    Pressure: 'Defensive',
    Balanced: 'Balanced',
  };

  const topOvr = activePlayers.length > 0 ? Math.max(...activePlayers.map(p => p.overall)) : 0;
  const topPlayer = activePlayers.find(p => p.overall === topOvr);
  const ovrGap = threat.ovr ? parseInt(threat.ovr) - Math.round(topOvr) : null;

  const hasApproachConflict = selectedIntent === 'Win Now' &&
    (threat.role === 'Tactical' || threat.role === 'Pressure');

  const counterApproach = threat.role ? (roleCounterMap[threat.role] ?? 'Control') : 'Control';
```

- [ ] **Step 2: Add insight rows after the threat card**

`.command-threat-card` in `index.css` uses `display: flex; align-items: center` — a horizontal row layout for icon + body + OVR badge. The insight rows must go **outside** that div to span full width. Locate the closing `</div>` of the `command-threat-card` div (after line 337). Insert a new `<div>` containing the three rows immediately after it, **before** the `<p className="command-field-label"...>` Scouting label:

```tsx
                </div>{/* end command-threat-card */}

                {/* Key Threat insight rows */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '10px' }}>
                  {threat.ovr && ovrGap !== null && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '13px', flexShrink: 0 }}>⚡</span>
                      <span style={{ flex: 1, fontSize: '11px', color: '#94a3b8' }}>
                        {ovrGap > 0
                          ? `Outrates your top starter${topPlayer ? ` (${topPlayer.name})` : ''} by +${ovrGap} OVR`
                          : `Your top starter${topPlayer ? ` (${topPlayer.name})` : ''} covers this threat by +${Math.abs(ovrGap)} OVR`}
                      </span>
                      <span style={{
                        fontSize: '9px', fontWeight: 700, letterSpacing: '0.06em',
                        padding: '2px 6px', borderRadius: '3px',
                        background: ovrGap > 0 ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)',
                        color: ovrGap > 0 ? '#ef4444' : '#10b981',
                        border: `1px solid ${ovrGap > 0 ? 'rgba(239,68,68,0.3)' : 'rgba(16,185,129,0.3)'}`,
                        whiteSpace: 'nowrap', flexShrink: 0,
                      }}>
                        {ovrGap > 0 ? 'DANGER' : 'COVERED'}
                      </span>
                    </div>
                  )}
                  {threat.role && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '13px', flexShrink: 0 }}>🎯</span>
                      <span style={{ flex: 1, fontSize: '11px', color: '#94a3b8' }}>
                        {hasApproachConflict
                          ? `Aggressive approach vs. ${threat.role} threat — expect direct pressure`
                          : `Approach is compatible with this role`}
                      </span>
                      <span style={{
                        fontSize: '9px', fontWeight: 700, letterSpacing: '0.06em',
                        padding: '2px 6px', borderRadius: '3px',
                        background: hasApproachConflict ? 'rgba(249,115,22,0.15)' : 'rgba(16,185,129,0.15)',
                        color: hasApproachConflict ? '#f97316' : '#10b981',
                        border: `1px solid ${hasApproachConflict ? 'rgba(249,115,22,0.3)' : 'rgba(16,185,129,0.3)'}`,
                        whiteSpace: 'nowrap', flexShrink: 0,
                      }}>
                        {hasApproachConflict ? 'EXPOSED' : 'ALIGNED'}
                      </span>
                    </div>
                  )}
                  {threat.role && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '13px', flexShrink: 0 }}>🛡️</span>
                      <span style={{ flex: 1, fontSize: '11px', color: '#94a3b8' }}>
                        Counter: switch to {counterApproach} to neutralize {threat.role} threats
                      </span>
                      <span style={{
                        fontSize: '9px', fontWeight: 700, letterSpacing: '0.06em',
                        padding: '2px 6px', borderRadius: '3px',
                        background: 'rgba(34,211,238,0.1)',
                        color: '#22d3ee',
                        border: '1px solid rgba(34,211,238,0.2)',
                        whiteSpace: 'nowrap', flexShrink: 0,
                      }}>
                        COUNTER
                      </span>
                    </div>
                  )}
                </div>
```

- [ ] **Step 3: Build frontend to verify**

```
cd frontend && npm run build
```

Expected: build succeeds, no TypeScript errors.

- [ ] **Step 4: Commit**

```
git add frontend/src/components/match-week/command-center/PreSimDashboard.tsx
git commit -m "feat: add Key Threat insight rows (OVR gap, approach conflict, counter hint)"
```

---

## Task 4: MatchCard component

**Files:**
- Create: `frontend/src/components/match-week/command-center/MatchCard.tsx`
- Modify: `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`

### Context

Replace the `command-control-squad` div (lines 258–278 of `PreSimDashboard.tsx`) with a self-contained `<MatchCard>` component. The card shows your top 6 starters vs the opponent's top 6 in a head-to-head table with proportional advantage bars. Rows sort by gap magnitude (biggest mismatch first). OVR/STA toggle re-sorts by stamina gap magnitude.

**Bar math:**
- `maxGap = Math.max(...slots.map(s => Math.abs(gap)), 1)`
- `barWidth = (Math.abs(gap) / maxGap) * 50` → value in `%`
- Your team wins slot (`gap > 0`): cyan bar (`#22d3ee`) with `right: 50%; left: auto` (grows left from center)
- Opponent wins slot (`gap < 0`): red bar (`#f43f5e`) with `left: 50%; right: auto` (grows right from center)

**Team abbreviation:** `name.trim().split(/\s+/).at(-1)!.slice(0, 4).toUpperCase()`

**Fallback:** When `oppPlayers` is empty, render your starters only with "Opponent lineup unavailable" text in the right column.

- [ ] **Step 1: Create `MatchCard.tsx`**

Create `frontend/src/components/match-week/command-center/MatchCard.tsx`:

```tsx
import { useMemo, useState } from 'react';
import type { LineupPlayer } from '../../../types';

interface MatchCardProps {
  yourPlayers: LineupPlayer[];
  oppPlayers: LineupPlayer[];
  yourTeamName: string;
  oppTeamName: string;
}

type Mode = 'ovr' | 'sta';

function teamAbbr(name: string): string {
  const words = name.trim().split(/\s+/);
  return (words.at(-1) ?? name).slice(0, 4).toUpperCase();
}

export function MatchCard({ yourPlayers, oppPlayers, yourTeamName, oppTeamName }: MatchCardProps) {
  const [mode, setMode] = useState<Mode>('ovr');

  const youAbbr = teamAbbr(yourTeamName);
  const oppAbbr = teamAbbr(oppTeamName);
  const hasopp = oppPlayers.length > 0;

  const slots = useMemo(() => {
    return yourPlayers.slice(0, 6).map((you, i) => {
      const opp = oppPlayers[i];
      const ovrGap = opp ? Math.round(you.overall) - Math.round(opp.overall) : 0;
      const staGap = opp ? (you.stamina ?? 100) - (opp.stamina ?? 100) : 0;
      return { you, opp, ovrGap, staGap };
    });
  }, [yourPlayers, oppPlayers]);

  const sorted = useMemo(
    () => [...slots].sort((a, b) => {
      const ag = Math.abs(mode === 'ovr' ? a.ovrGap : a.staGap);
      const bg = Math.abs(mode === 'ovr' ? b.ovrGap : b.staGap);
      return bg - ag;
    }),
    [slots, mode],
  );

  const maxGap = Math.max(...sorted.map(s => Math.abs(mode === 'ovr' ? s.ovrGap : s.staGap)), 1);

  const netOvr = slots.reduce((sum, s) => sum + s.ovrGap, 0);
  const netSta = slots.reduce((sum, s) => sum + s.staGap, 0);
  const net = mode === 'ovr' ? netOvr : netSta;
  const netLeader = net >= 0 ? yourTeamName : oppTeamName;
  const edgeLabel = mode === 'ovr' ? 'OVERALL EDGE' : 'STAMINA EDGE';

  const advantages = sorted.filter(s => (mode === 'ovr' ? s.ovrGap : s.staGap) > 0).length;
  const disadvantages = sorted.filter(s => (mode === 'ovr' ? s.ovrGap : s.staGap) < 0).length;

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
        <span style={{ fontSize: '10px', fontWeight: 700, color: '#22d3ee', letterSpacing: '0.08em' }}>{yourTeamName.toUpperCase()}</span>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '3px' }}>
          <span style={{ fontSize: '10px', color: '#334155', letterSpacing: '0.1em' }}>VS</span>
          <div style={{ display: 'flex', gap: '4px' }}>
            <button
              type="button"
              onClick={() => setMode('ovr')}
              style={{
                fontSize: '8px', fontWeight: 700, padding: '2px 6px', borderRadius: '3px', border: 'none', cursor: 'pointer',
                background: mode === 'ovr' ? '#22d3ee' : '#1e293b',
                color: mode === 'ovr' ? '#0a1220' : '#334155',
                letterSpacing: '0.06em',
              }}
            >OVR</button>
            <button
              type="button"
              onClick={() => setMode('sta')}
              style={{
                fontSize: '8px', fontWeight: 700, padding: '2px 6px', borderRadius: '3px', border: 'none', cursor: 'pointer',
                background: mode === 'sta' ? '#22d3ee' : '#1e293b',
                color: mode === 'sta' ? '#0a1220' : '#334155',
                letterSpacing: '0.06em',
              }}
            >STA</button>
          </div>
        </div>
        <span style={{ fontSize: '10px', fontWeight: 700, color: '#f43f5e', letterSpacing: '0.08em', textAlign: 'right' }}>{oppTeamName.toUpperCase()}</span>
      </div>

      {/* Net summary strip */}
      {hasopp && (
        <div style={{
          background: 'rgba(34,211,238,0.07)', border: '1px solid rgba(34,211,238,0.15)',
          borderRadius: '5px', padding: '6px 12px', marginBottom: '10px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span style={{ fontSize: '9px', color: '#334155', letterSpacing: '0.1em', fontWeight: 700 }}>{edgeLabel}</span>
          <span style={{ fontSize: '13px', fontWeight: 800, color: net >= 0 ? '#22d3ee' : '#f43f5e' }}>
            {netLeader} {net >= 0 ? `+${net}` : `+${Math.abs(net)}`} net {mode.toUpperCase()}
          </span>
        </div>
      )}

      {/* Legend */}
      {hasopp && (
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          fontSize: '9px', letterSpacing: '0.05em',
          paddingBottom: '8px', borderBottom: '1px solid #1e2d3d', marginBottom: '2px',
        }}>
          <span style={{ color: '#164e63' }}>◀ {youAbbr} ADVANTAGE</span>
          <span style={{ color: '#1e293b' }}>Longer bar = larger {mode.toUpperCase()} edge</span>
          <span style={{ color: '#4c0519' }}>{oppAbbr} ADVANTAGE ▶</span>
        </div>
      )}

      {/* Rows */}
      {sorted.map((slot, i) => {
        const gap = mode === 'ovr' ? slot.ovrGap : slot.staGap;
        const barWidth = (Math.abs(gap) / maxGap) * 50;
        const youWin = gap > 0;
        const youVal = mode === 'ovr' ? Math.round(slot.you.overall) : (slot.you.stamina ?? '—');
        const oppVal = slot.opp ? (mode === 'ovr' ? Math.round(slot.opp.overall) : (slot.opp.stamina ?? '—')) : '—';

        return (
          <div
            key={slot.you.id}
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 36% 1fr',
              alignItems: 'center',
              padding: '6px 0',
              borderBottom: i < sorted.length - 1 ? '1px solid #0d1a26' : 'none',
            }}
          >
            {/* Your side */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '4px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span style={{ fontSize: '8px', color: '#1e3a4a', letterSpacing: '0.06em', lineHeight: 1 }}>
                  {mode === 'ovr' ? 'OVR' : 'STA'}
                </span>
                <span style={{ fontSize: '11px', fontWeight: 700, lineHeight: 1.2, color: hasopp && youWin ? '#22d3ee' : hasopp ? '#f43f5e' : '#e2e8f0' }}>
                  {youVal}
                </span>
              </div>
              <span style={{ fontSize: '12px', fontWeight: 600, color: '#e2e8f0' }}>{slot.you.name}</span>
            </div>

            {/* Center: gap label + bar */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '3px', padding: '0 8px' }}>
              {hasopp ? (
                <>
                  <span style={{
                    fontSize: '10px', fontWeight: 700, letterSpacing: '0.04em', lineHeight: 1,
                    color: youWin ? '#22d3ee' : '#f43f5e',
                  }}>
                    {youWin ? `◀ ${youAbbr} +${Math.abs(gap)}` : `${oppAbbr} +${Math.abs(gap)} ▶`}
                  </span>
                  <div style={{ position: 'relative', width: '100%', height: '6px', background: '#1e293b', borderRadius: '3px', overflow: 'hidden' }}>
                    {/* Center divider */}
                    <div style={{ position: 'absolute', left: '50%', top: 0, width: '2px', height: '100%', background: '#0a1220', transform: 'translateX(-50%)', zIndex: 2 }} />
                    {/* Bar fill */}
                    {gap !== 0 && (
                      <div style={{
                        position: 'absolute', top: 0, height: '100%',
                        width: `${barWidth}%`,
                        background: youWin ? '#22d3ee' : '#f43f5e',
                        ...(youWin ? { right: '50%', left: 'auto' } : { left: '50%', right: 'auto' }),
                      }} />
                    )}
                  </div>
                </>
              ) : (
                <span style={{ fontSize: '9px', color: '#334155' }}>—</span>
              )}
            </div>

            {/* Opponent side */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-start', gap: '4px' }}>
              {slot.opp ? (
                <>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: '#e2e8f0' }}>{slot.opp.name}</span>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <span style={{ fontSize: '8px', color: '#2d1a1a', letterSpacing: '0.06em', lineHeight: 1 }}>
                      {mode === 'ovr' ? 'OVR' : 'STA'}
                    </span>
                    <span style={{ fontSize: '11px', fontWeight: 700, lineHeight: 1.2, color: youWin ? '#f43f5e' : '#22d3ee' }}>
                      {oppVal}
                    </span>
                  </div>
                </>
              ) : (
                <span style={{ fontSize: '11px', color: '#334155', fontStyle: 'italic' }}>Unavailable</span>
              )}
            </div>
          </div>
        );
      })}

      {/* Fallback message if no opp data */}
      {!hasopp && (
        <p style={{ fontSize: '10px', color: '#334155', textAlign: 'center', padding: '8px 0', fontStyle: 'italic' }}>
          Opponent lineup unavailable
        </p>
      )}

      {/* Tally */}
      {hasopp && (
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#334155', marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #1e2d3d' }}>
          <span><span style={{ color: '#22d3ee', fontWeight: 700 }}>{advantages}</span> slot advantages</span>
          <span><span style={{ color: '#f43f5e', fontWeight: 700 }}>{disadvantages}</span> slot disadvantages</span>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Replace Starter Readiness section in `PreSimDashboard.tsx`**

Import `MatchCard` at the top of `PreSimDashboard.tsx`, after the existing import:

```tsx
import { MatchCard } from './MatchCard';
```

Locate the `command-control-squad` div (lines 258–278). Replace the entire div (from `<div className="command-control-squad">` through the closing `</div>` that includes `command-control-form`) with:

```tsx
          <div className="command-control-squad">
            <div className="command-panel-heading">
              <p className="command-field-label">Match Card</p>
            </div>
            <MatchCard
              yourPlayers={activePlayers}
              oppPlayers={plan.opponent_lineup?.players ?? []}
              yourTeamName={data.player_club_name}
              oppTeamName={plan.opponent.name}
            />
          </div>
```

Also remove the `userStanding ? \`${userStanding.points} pts\` : recentRecord` span from the heading (line 261) — the new heading above replaces it entirely.

- [ ] **Step 3: Build frontend**

```
cd frontend && npm run build
```

Expected: build succeeds, no TypeScript errors.

- [ ] **Step 4: Commit**

```
git add frontend/src/components/match-week/command-center/MatchCard.tsx frontend/src/components/match-week/command-center/PreSimDashboard.tsx
git commit -m "feat: add MatchCard head-to-head comparison, replace Starter Readiness"
```

---

## Task 5: Smart pre-lock flag — replace stat strip

**Files:**
- Modify: `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`

### Context

The three-stat strip (`command-control-form` div, lines 273–277) duplicates information available elsewhere. Replace it with a single contextual flag row that appears just above the Lock button. The flag shows either a warning (orange) if there's a plan/matchup conflict or a fatigue issue, or an OK state (green) if everything looks aligned.

**Flag logic:**
1. Approach conflict: same `hasApproachConflict` derived in Task 3
2. Fatigue: `activePlayers.filter(p => p.stamina !== undefined && p.stamina < 60).length > 1`
3. Warning if either is true. OK otherwise.

The `command-control-form` div was already removed in Task 4 when we replaced the `command-control-squad` div. The flag inserts above the lock button.

- [ ] **Step 1: Add `hasFatigueIssue` and `hasPlanConflict` derived values**

After the `hasApproachConflict` and `counterApproach` definitions added in Task 3, add:

```tsx
  const hasFatigueIssue = activePlayers.filter(
    p => p.stamina !== undefined && p.stamina < 60
  ).length > 1;

  const hasPlanConflict = hasApproachConflict || hasFatigueIssue;
```

- [ ] **Step 2: Add the flag row above the lock button**

Locate the `{!planConfirmed ? (` block (line 279). Inside the `<>` fragment for the unlocked state, insert the flag row **before** the existing `{!isReadyToLock && <p ...>}` paragraph:

```tsx
            {/* Smart pre-lock flag */}
            <div style={{
              display: 'flex', alignItems: 'flex-start', gap: '10px',
              padding: '9px 12px', borderRadius: '6px', marginBottom: '10px',
              background: hasPlanConflict ? 'rgba(249,115,22,0.1)' : 'rgba(16,185,129,0.1)',
              border: `1px solid ${hasPlanConflict ? 'rgba(249,115,22,0.2)' : 'rgba(16,185,129,0.2)'}`,
              fontSize: '11px', lineHeight: 1.5,
            }}>
              <span>{hasPlanConflict ? '⚠️' : '✓'}</span>
              <span style={{ color: '#94a3b8' }}>
                {hasPlanConflict ? (
                  <>
                    <strong style={{ color: '#f1f5f9' }}>Plan conflict:</strong>{' '}
                    {hasApproachConflict
                      ? <><em style={{ fontStyle: 'normal', color: '#f97316' }}>Aggressive</em> approach vs. {threat.role} threat — consider {counterApproach}.</>
                      : <>Multiple starters have low stamina — consider <em style={{ fontStyle: 'normal', color: '#f97316' }}>Preserve Health</em>.</>
                    }
                  </>
                ) : (
                  <>
                    <strong style={{ color: '#f1f5f9' }}>Plan looks solid.</strong>{' '}
                    {currentApproach} approach aligns with the {threat.role ?? 'opponent'} threat. Stamina is healthy.
                  </>
                )}
              </span>
            </div>
```

- [ ] **Step 3: Build frontend**

```
cd frontend && npm run build
```

Expected: build succeeds, no TypeScript errors.

- [ ] **Step 4: Run full Python test suite**

```
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```
git add frontend/src/components/match-week/command-center/PreSimDashboard.tsx
git commit -m "feat: add smart pre-lock flag, remove useless stat strip"
```

---

## Verification Checklist

After all 5 tasks are committed, start the web app (`python -m dodgeball_sim`) and check:

- [ ] **Key Threat card:** Three insight rows visible below the OVR badge. Rows show correct chip colors (DANGER red / COVERED green / EXPOSED orange / ALIGNED green / COUNTER cyan).
- [ ] **Match Card:** Both team names shown in header. Net summary strip shows correct leader. All 6 rows visible, sorted by biggest gap first. Bars extend from center outward — your wins cyan left, their wins red right.
- [ ] **OVR/STA toggle:** Clicking STA re-sorts rows by stamina gap magnitude. Bar widths update. Summary strip updates to stamina values. Clicking back to OVR restores original sort.
- [ ] **Opponent unavailable fallback:** Can be tested by temporarily passing `oppPlayers={[]}` — should show "Opponent lineup unavailable" placeholder without crashing.
- [ ] **Smart flag (warning):** Select "Aggressive" approach when opponent threat is Tactical/Pressure — flag shows orange warning.
- [ ] **Smart flag (OK):** Select "Control" or "Defensive" approach — flag shows green OK.
- [ ] **Stat strip removed:** The old Elim Diff / Last / Plans row is gone.
- [ ] **"3 pts" label removed:** The `${userStanding.points} pts` span in the Starter Readiness heading is gone.
