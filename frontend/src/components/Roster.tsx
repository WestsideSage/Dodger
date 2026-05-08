import { useMemo, useState, useEffect } from 'react';
import type { Player, RosterResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { DataTable, PageHeader, RatingBar, StatChip, StatusMessage, TableCell, TableHeadCell } from './ui';

function overallRating(player: Player): number {
  if (Number.isFinite(player.overall)) return Math.round(player.overall);
  const ratings = player.ratings;
  return Math.round((ratings.accuracy + ratings.power + ratings.dodge + ratings.catch + (ratings.tactical_iq ?? 50)) / 5);
}

function overallColor(value: number): string {
  if (value >= 80) return '#22d3ee';
  if (value >= 65) return '#10b981';
  if (value >= 50) return '#f59e0b';
  return '#f43f5e';
}

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
      .map(player => ({ player, overall: overallRating(player), starter: defaultLineupIds.has(player.id) }))
      .sort((a, b) => Number(b.starter) - Number(a.starter) || b.overall - a.overall || a.player.age - b.player.age),
    [data?.roster, defaultLineupIds]
  );

  if (loading) return <StatusMessage title="Loading roster">Building the club sheet.</StatusMessage>;
  if (error) return <StatusMessage title="Roster unavailable" tone="danger">{error}</StatusMessage>;
  if (!data) return <StatusMessage title="No roster">No roster data returned.</StatusMessage>;

  const starters = roster.filter(row => row.starter).length;
  const averageOverall = roster.length
    ? Math.round(roster.reduce((total, row) => total + row.overall, 0) / roster.length)
    : 0;

  return (
    <div className="dm-panel">
      <PageHeader
        eyebrow="Roster Lab"
        title="Team Roster"
        description="Player condition, role fit, and match readiness"
        stats={
          <>
            <StatChip label="Players" value={roster.length} />
            <StatChip label="Starters" value={starters} tone="warning" />
            <StatChip label="Avg OVR" value={averageOverall} tone="info" />
            {planContext && (
              <DevFocusChip
                current={planContext.dev_focus}
                intent={planContext.intent}
                onUpdated={fetchPlan}
              />
            )}
          </>
        }
      />

      <DataTable>
        <thead>
          <tr>
            <TableHeadCell sticky>Player</TableHeadCell>
            <TableHeadCell>Role</TableHeadCell>
            <TableHeadCell align="center">Age</TableHeadCell>
            <TableHeadCell align="right">OVR</TableHeadCell>
            <TableHeadCell align="right">POT</TableHeadCell>
            <TableHeadCell>POW</TableHeadCell>
            <TableHeadCell>ACC</TableHeadCell>
            <TableHeadCell>DOD</TableHeadCell>
            <TableHeadCell>CAT</TableHeadCell>
            <TableHeadCell>IQ</TableHeadCell>
            <TableHeadCell>STA</TableHeadCell>
            <TableHeadCell>Status</TableHeadCell>
          </tr>
        </thead>
        <tbody>
          {roster.map(({ player, overall, starter }) => (
            <tr
              key={player.id}
              style={{ background: starter ? 'rgba(34,211,238,0.06)' : undefined }}
            >
              <TableCell sticky className="min-w-44">
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.125rem' }}>
                  <span>{player.name}</span>
                  {player.newcomer && (
                    <span style={{ fontSize: '0.6875rem', fontFamily: 'var(--font-mono-data)', color: '#a78bfa', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Newcomer
                    </span>
                  )}
                </div>
              </TableCell>

              <TableCell>
                {(player.role || player.archetype) ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.125rem' }}>
                    {player.role && (
                      <span style={{ fontFamily: 'var(--font-display)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.075em', color: '#22d3ee' }}>
                        {player.role}
                      </span>
                    )}
                    {player.archetype && (
                      <span style={{ fontFamily: 'var(--font-display)', fontSize: '0.625rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#475569' }}>
                        {player.archetype}
                      </span>
                    )}
                  </div>
                ) : (
                  <span style={{ color: '#334155' }}>—</span>
                )}
              </TableCell>

              <TableCell align="center">
                <span className="dm-data" style={{ fontSize: '0.8125rem', color: '#94a3b8' }}>{player.age}</span>
              </TableCell>

              <TableCell align="right">
                <span className="dm-data" style={{ fontSize: '1rem', fontWeight: 700, color: overallColor(overall) }}>
                  {overall}
                </span>
              </TableCell>

              <TableCell align="right">
                <span className="dm-data" style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#cbd5e1' }}>
                  {player.traits.potential}
                </span>
              </TableCell>

              <TableCell className="min-w-24">
                <RatingBar rating={player.ratings.power} compact />
              </TableCell>
              <TableCell className="min-w-24">
                <RatingBar rating={player.ratings.accuracy} compact />
              </TableCell>
              <TableCell className="min-w-24">
                <RatingBar rating={player.ratings.dodge} compact />
              </TableCell>
              <TableCell className="min-w-24">
                <RatingBar rating={player.ratings.catch} compact />
              </TableCell>
              <TableCell className="min-w-24">
                <RatingBar rating={player.ratings.tactical_iq ?? 50} compact />
              </TableCell>
              <TableCell className="min-w-24">
                <RatingBar rating={player.ratings.stamina} compact />
              </TableCell>

              <TableCell>
                <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                  {starter ? (
                    <span className="dm-badge dm-badge-cyan">STARTER</span>
                  ) : (
                    <span className="dm-badge dm-badge-slate">BENCH</span>
                  )}
                  {player.newcomer && (
                    <span className="dm-badge dm-badge-violet">NEW</span>
                  )}
                </div>
              </TableCell>
            </tr>
          ))}
        </tbody>
      </DataTable>
    </div>
  );
}
