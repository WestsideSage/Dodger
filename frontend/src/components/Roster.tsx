import { useMemo, useState, useEffect } from 'react';
import type { RosterResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { PageHeader, StatChip, StatusMessage } from './ui';
import { PlayerTheaterRow } from './roster/PlayerTheaterRow';
import { PlayerCompactRow } from './roster/PlayerCompactRow';

const DEV_FOCUS_OPTIONS = ['BALANCED', 'YOUTH_ACCELERATION', 'TACTICAL_DRILLS', 'STRENGTH_AND_CONDITIONING'];

function DevFocusChip({
  current,
  intent,
  onUpdated,
}: {
  current: string;
  intent: string;
  onUpdated: () => void;
}) {
  const [open, setOpen] = useState(false);
  const update = (next: string) => {
    fetch('/api/command-center/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ intent, department_orders: { dev_focus: next } }),
    })
      .then(() => { setOpen(false); onUpdated(); });
  };

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button
        onClick={() => setOpen(o => !o)}
        className="dm-kicker"
        style={{ padding: '0.5rem 0.75rem', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', color: '#22d3ee', fontWeight: 700, cursor: 'pointer' }}
      >
        Dev Focus: {current.replace(/_/g, ' ')}
      </button>
      {open && (
        <div style={{ position: 'absolute', top: '100%', left: 0, marginTop: '0.25rem', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', zIndex: 10, minWidth: '200px' }}>
          {DEV_FOCUS_OPTIONS.map(opt => (
            <button
              key={opt}
              onClick={() => update(opt)}
              style={{ display: 'block', width: '100%', padding: '0.5rem 0.75rem', background: opt === current ? '#1e293b' : 'transparent', border: 'none', color: '#e2e8f0', textAlign: 'left', cursor: 'pointer', fontFamily: 'var(--font-display)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}
            >
              {opt.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function Roster() {
  const { data, loading, error } = useApiResource<RosterResponse>('/api/roster');
  const [planContext, setPlanContext] = useState<{ intent: string; dev_focus: string } | null>(null);
  const [isCompact, setIsCompact] = useState(false);

  const fetchPlan = () => {
    fetch('/api/command-center')
      .then(r => r.json())
      .then((d: any) => setPlanContext({
        intent: d.plan.intent,
        dev_focus: d.plan.department_orders?.dev_focus ?? 'BALANCED',
      }));
  };

  useEffect(() => {
    fetchPlan();
  }, []);

  const defaultLineupIds = useMemo(
    () => new Set(data?.default_lineup ?? []),
    [data?.default_lineup]
  );

  const roster = useMemo(
    () => (data?.roster ?? [])
      .map(player => ({ player, starter: defaultLineupIds.has(player.id) }))
      .sort((a, b) => Number(b.starter) - Number(a.starter) || b.player.overall - a.player.overall || a.player.age - b.player.age),
    [data?.roster, defaultLineupIds]
  );

  if (loading) return <StatusMessage title="Loading roster">Building the club sheet.</StatusMessage>;
  if (error) return <StatusMessage title="Roster unavailable" tone="danger">{error}</StatusMessage>;
  if (!data) return <StatusMessage title="No roster">No roster data returned.</StatusMessage>;

  const averageAge = Math.round(roster.reduce((sum, r) => sum + r.player.age, 0) / roster.length);
  const averageOverall = Math.round(roster.reduce((sum, r) => sum + r.player.overall, 0) / roster.length);

  return (
    <div className="dm-panel">
      <PageHeader
        eyebrow="Roster Lab"
        title="Team Roster"
        description="Player condition, role fit, and match readiness"
        stats={
          <>
            <StatChip label="Avg Age" value={averageAge} />
            <StatChip label="Avg OVR" value={averageOverall} tone="info" />
            <StatChip label="Trend" value="↑" tone="success" />
            {planContext && (
              <DevFocusChip
                current={planContext.dev_focus}
                intent={planContext.intent}
                onUpdated={fetchPlan}
              />
            )}
            <button 
              onClick={() => setIsCompact(!isCompact)}
              style={{ padding: '0.5rem 0.75rem', background: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#cbd5e1', cursor: 'pointer', fontSize: '0.75rem', textTransform: 'uppercase' }}
            >
              {isCompact ? 'Theater View' : 'Compact View'}
            </button>
          </>
        }
      />

      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
        {!isCompact && (
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid #1e293b' }}>
              <th style={{ padding: '1rem', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>Player</th>
              <th style={{ padding: '1rem', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>Ratings</th>
              <th style={{ padding: '1rem', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>Potential</th>
              <th style={{ padding: '1rem', textAlign: 'right', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>OVR</th>
              <th style={{ padding: '1rem', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>Status</th>
            </tr>
          </thead>
        )}
        {isCompact && (
          <thead>
             <tr style={{ textAlign: 'left', borderBottom: '1px solid #1e293b' }}>
               <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>Name</th>
               <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>ACC</th>
               <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>POW</th>
               <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>DOD</th>
               <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>CAT</th>
               <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>OVR</th>
               <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>Status</th>
             </tr>
          </thead>
        )}
        <tbody>
          {roster.map(({ player, starter }) => (
            isCompact ? (
              <PlayerCompactRow key={player.id} player={player} starter={starter} />
            ) : (
              <PlayerTheaterRow key={player.id} player={player} starter={starter} />
            )
          ))}
        </tbody>
      </table>
    </div>
  );
}
