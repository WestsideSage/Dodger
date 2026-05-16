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
  const hasOpp = oppPlayers.length > 0;

  const slots = useMemo(() => {
    return yourPlayers.slice(0, 6).map((you, i) => {
      const opp = oppPlayers[i];
      const ovrGap = opp ? Math.round(you.overall) - Math.round(opp.overall) : 0;
      const staGap = opp && you.stamina !== undefined && opp.stamina !== undefined
        ? Math.round(you.stamina) - Math.round(opp.stamina)
        : 0;
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
      {hasOpp && (
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
      {hasOpp && (
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
        const youVal = mode === 'ovr' ? Math.round(slot.you.overall) : (slot.you.stamina !== undefined ? Math.round(slot.you.stamina) : '—');
        const oppVal = slot.opp ? (mode === 'ovr' ? Math.round(slot.opp.overall) : (slot.opp.stamina !== undefined ? Math.round(slot.opp.stamina) : '—')) : '—';

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
                <span style={{ fontSize: '11px', fontWeight: 700, lineHeight: 1.2, color: !hasOpp ? '#e2e8f0' : gap === 0 ? '#e2e8f0' : youWin ? '#22d3ee' : '#f43f5e' }}>
                  {youVal}
                </span>
              </div>
              <span style={{ fontSize: '12px', fontWeight: 600, color: '#e2e8f0' }}>{slot.you.name}</span>
            </div>

            {/* Center: gap label + bar */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '3px', padding: '0 8px' }}>
              {hasOpp ? (
                <>
                  <span style={{
                    fontSize: '10px', fontWeight: 700, letterSpacing: '0.04em', lineHeight: 1,
                    color: gap === 0 ? '#475569' : youWin ? '#22d3ee' : '#f43f5e',
                  }}>
                    {gap === 0 ? 'EVEN' : youWin ? `◀ ${youAbbr} +${Math.abs(gap)}` : `−${Math.abs(gap)} ▶`}
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
                    <span style={{ fontSize: '11px', fontWeight: 700, lineHeight: 1.2, color: gap === 0 ? '#e2e8f0' : youWin ? '#f43f5e' : '#22d3ee' }}>
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
      {!hasOpp && (
        <p style={{ fontSize: '10px', color: '#334155', textAlign: 'center', padding: '8px 0', fontStyle: 'italic' }}>
          Opponent lineup unavailable
        </p>
      )}

      {/* Tally */}
      {hasOpp && (
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#334155', marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #1e2d3d' }}>
          <span><span style={{ color: '#22d3ee', fontWeight: 700 }}>{advantages}</span> slot advantages</span>
          <span><span style={{ color: '#f43f5e', fontWeight: 700 }}>{disadvantages}</span> slot disadvantages</span>
        </div>
      )}
    </div>
  );
}
