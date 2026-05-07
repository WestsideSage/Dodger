import { useEffect, useState } from 'react';
import type { CommandCenterResponse, CommandCenterSimResponse } from '../types';
import { ActionButton, Badge, KeyValueRow, PageHeader, StatChip, StatusMessage } from './ui';

const devFocusOptions = ['BALANCED', 'YOUTH_ACCELERATION', 'TACTICAL_DRILLS', 'STRENGTH_AND_CONDITIONING'];

const departmentLabels: Record<string, string> = {
  tactics: 'Tactics',
  training: 'Training',
  conditioning: 'Conditioning',
  medical: 'Medical',
  scouting: 'Scouting',
  culture: 'Culture',
};

function formatTactic(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function CommandCenter({ onOpenReplay }: { onOpenReplay?: (matchId: string) => void }) {
  const [data, setData] = useState<CommandCenterResponse | null>(null);
  const [selectedIntent, setSelectedIntent] = useState('Win Now');
  const [selectedDevFocus, setSelectedDevFocus] = useState('BALANCED');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [result, setResult] = useState<CommandCenterSimResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = (showLoading = false) => {
    if (showLoading) setLoading(true);
    return fetch('/api/command-center')
      .then(res => {
        if (!res.ok) throw new Error('Command center unavailable');
        return res.json();
      })
      .then((payload: CommandCenterResponse) => {
        setData(payload);
        setSelectedIntent(payload.plan.intent);
        setSelectedDevFocus(payload.plan.department_orders?.dev_focus ?? 'BALANCED');
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    let cancelled = false;
    fetch('/api/command-center')
      .then(res => {
        if (!res.ok) throw new Error('Command center unavailable');
        return res.json();
      })
      .then((payload: CommandCenterResponse) => {
        if (cancelled) return;
        setData(payload);
        setSelectedIntent(payload.plan.intent);
        setSelectedDevFocus(payload.plan.department_orders?.dev_focus ?? 'BALANCED');
      })
      .catch(err => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const savePlan = (intent = selectedIntent, devFocus = selectedDevFocus) => {
    setSaving(true);
    setError(null);
    return fetch('/api/command-center/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ intent, department_orders: { dev_focus: devFocus } }),
    })
      .then(res => {
        if (!res.ok) throw new Error('Plan save failed');
        return res.json();
      })
      .then((payload: CommandCenterResponse) => {
        setData(payload);
        setSelectedIntent(payload.plan.intent);
        setSelectedDevFocus(payload.plan.department_orders?.dev_focus ?? 'BALANCED');
      })
      .catch(err => setError(err.message))
      .finally(() => setSaving(false));
  };

  const simulate = () => {
    setSimulating(true);
    setError(null);
    fetch('/api/command-center/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ intent: selectedIntent }),
    })
      .then(res => {
        if (!res.ok) throw new Error('Command simulation failed');
        return res.json();
      })
      .then((payload: CommandCenterSimResponse) => {
        setResult(payload);
        return load();
      })
      .catch(err => setError(err.message))
      .finally(() => setSimulating(false));
  };

  if (loading && !data) return <StatusMessage title="Loading command center">Opening the weekly desk.</StatusMessage>;
  if (error) return <StatusMessage title="Command center unavailable" tone="danger">{error}</StatusMessage>;
  if (!data) return null;

  const plan = data.plan;
  const dashboard = result?.dashboard || data.latest_dashboard;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }} data-testid="weekly-command-center">

      {/* Page header */}
      <PageHeader
        eyebrow="War Room"
        title="Command Center"
        description={data.current_objective}
        stats={
          <>
            <StatChip label="Week" value={data.week} tone="warning" />
            <StatChip label="Club" value={data.player_club_name} />
            <StatChip label="Opponent" value={plan.opponent.name} tone="info" />
          </>
        }
      />

      {/* Weekly Plan + Staff Room row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.25rem' }}
        className="xl-two-col">
        {/* Weekly Plan */}
        <div className="dm-panel">
          <div className="dm-panel-header">
            <p className="dm-kicker">Tactical Directive</p>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem' }}>
              <div>
                <h2 className="dm-panel-title">Weekly Plan</h2>
                <p className="dm-panel-subtitle">Set the program intent, then accept the staff plan or adjust supporting tabs.</p>
              </div>
              <Badge tone="success">Playable</Badge>
            </div>
          </div>

          <div className="dm-section">
            {/* Intent + Dev Focus selects */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
              <label style={{ display: 'block' }}>
                <span className="dm-kicker" style={{ display: 'block', marginBottom: '0.375rem' }}>Intent</span>
                <select
                  aria-label="Weekly intent"
                  value={selectedIntent}
                  onChange={(event) => {
                    setSelectedIntent(event.target.value);
                    savePlan(event.target.value, selectedDevFocus);
                  }}
                  style={{
                    width: '100%',
                    background: '#0f172a',
                    border: '1px solid #334155',
                    borderRadius: '4px',
                    padding: '0.5rem 0.75rem',
                    color: '#e2e8f0',
                    fontFamily: 'var(--font-display)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                  }}
                >
                  {plan.available_intents.map(intent => <option key={intent}>{intent}</option>)}
                </select>
              </label>

              <label style={{ display: 'block' }}>
                <span className="dm-kicker" style={{ display: 'block', marginBottom: '0.375rem' }}>Dev Focus</span>
                <select
                  aria-label="Development Focus"
                  value={selectedDevFocus}
                  onChange={(event) => {
                    setSelectedDevFocus(event.target.value);
                    savePlan(selectedIntent, event.target.value);
                  }}
                  style={{
                    width: '100%',
                    background: '#0f172a',
                    border: '1px solid #334155',
                    borderRadius: '4px',
                    padding: '0.5rem 0.75rem',
                    color: '#e2e8f0',
                    fontFamily: 'var(--font-display)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                  }}
                >
                  {devFocusOptions.map(focus => <option key={focus} value={focus}>{focus.replace(/_/g, ' ')}</option>)}
                </select>
              </label>
            </div>

            {/* Department orders */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.75rem', marginTop: '1rem' }}>
              {Object.entries(plan.department_orders).filter(([key]) => key !== 'dev_focus').map(([key, value]) => (
                <div key={key} style={{
                  background: '#0f172a',
                  border: '1px solid #1e293b',
                  borderRadius: '4px',
                  padding: '0.75rem',
                }}>
                  <p className="dm-kicker" style={{ marginBottom: '0.25rem' }}>{departmentLabels[key] || key}</p>
                  <p className="dm-data" style={{ color: '#22d3ee', fontSize: '0.75rem', fontWeight: 700, textTransform: 'capitalize' }}>{String(value)}</p>
                </div>
              ))}
            </div>

            {/* Action buttons */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' }}>
              <ActionButton variant="primary" onClick={() => savePlan()} disabled={saving || simulating}>
                {saving ? 'Saving...' : 'Accept Recommended Plan'}
              </ActionButton>
              <ActionButton variant="accent" onClick={simulate} disabled={simulating || saving} data-testid="simulate-command-week">
                {simulating ? 'Simulating...' : 'Simulate Command Week'}
              </ActionButton>
              <ActionButton variant="ghost" onClick={() => load(true)} disabled={loading || simulating}>
                Refresh
              </ActionButton>
            </div>
          </div>
        </div>

        {/* Staff Room */}
        <div className="dm-panel">
          <div className="dm-panel-header">
            <p className="dm-kicker">Personnel Briefing</p>
            <h2 className="dm-panel-title">Staff Room</h2>
          </div>
          <div className="dm-section" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {plan.recommendations.map(item => (
              <div key={item.department} style={{
                background: '#0f172a',
                border: '1px solid #1e293b',
                borderRadius: '4px',
                padding: '0.75rem',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', marginBottom: '0.375rem' }}>
                  <span className="dm-kicker">{item.department}</span>
                  <span style={{ fontSize: '0.6875rem', color: '#475569', fontFamily: 'var(--font-body)' }}>{item.voice}</span>
                </div>
                <p style={{ fontSize: '0.875rem', color: '#cbd5e1', fontFamily: 'var(--font-body)' }}>{item.text}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Lineup + Tactics Evidence row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.25rem' }}
        className="lg-two-col-roster">
        {/* Lineup Accountability */}
        <div className="dm-panel">
          <div className="dm-panel-header">
            <p className="dm-kicker">Selection</p>
            <h2 className="dm-panel-title">Lineup Accountability</h2>
            <p className="dm-panel-subtitle">{plan.lineup.summary}</p>
          </div>
          <div className="dm-section">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.625rem' }}>
              {plan.lineup.players.map(player => (
                <div key={player.id} style={{
                  background: '#0f172a',
                  border: '1px solid #1e293b',
                  borderRadius: '4px',
                  padding: '0.625rem 0.75rem',
                }}>
                  <div style={{ fontWeight: 700, color: '#e2e8f0', fontSize: '0.875rem' }}>{player.name}</div>
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
                    <span className="dm-badge dm-badge-slate">OVR {player.overall}</span>
                    {player.potential != null && (
                      <span className="dm-badge dm-badge-violet">POT {player.potential}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
            {plan.warnings.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.75rem' }}>
                {plan.warnings.map(warning => (
                  <StatusMessage key={warning} title="Staff warning" tone="warning">{warning}</StatusMessage>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Tactics Evidence */}
        <div className="dm-panel">
          <div className="dm-panel-header">
            <p className="dm-kicker">Match Strategy</p>
            <h2 className="dm-panel-title">Tactics Evidence</h2>
          </div>
          <div className="dm-section">
            <KeyValueRow label="Target Stars" value={formatTactic(plan.tactics.target_stars)} />
            <KeyValueRow label="Ball Holder" value={formatTactic(plan.tactics.target_ball_holder)} />
            <KeyValueRow label="Rush Freq." value={formatTactic(plan.tactics.rush_frequency)} />
            <KeyValueRow label="Catch Bias" value={formatTactic(plan.tactics.catch_bias)} />
            <p style={{ marginTop: '0.75rem', fontSize: '0.8125rem', color: '#475569', fontFamily: 'var(--font-body)' }}>
              Dashboard notes only cite effects that are tracked in the saved plan or match stats.
            </p>
          </div>
        </div>
      </div>

      {/* Post-Week Dashboard */}
      {dashboard && (
        <div className="dm-panel" data-testid="post-week-dashboard" style={{ overflow: 'hidden' }}>
          <div className="dm-panel-header" style={{ borderBottom: '1px solid #1e293b' }}>
            <p className="dm-kicker">Match Report</p>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
              <div>
                <h2 className="dm-panel-title">Post-Week Dashboard</h2>
                <p className="dm-panel-subtitle">
                  Week {dashboard.week} · {dashboard.result} vs {dashboard.opponent_name}
                </p>
              </div>
              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <Badge tone={dashboard.result === 'Win' ? 'success' : dashboard.result === 'Loss' ? 'danger' : 'warning'}>
                  {dashboard.result}
                </Badge>
                {dashboard.match_id && onOpenReplay && (
                  <ActionButton variant="accent" onClick={() => onOpenReplay(dashboard.match_id)}>
                    Open Replay Proof
                  </ActionButton>
                )}
              </div>
            </div>
          </div>
          <div className="dm-section" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.75rem' }}>
            {dashboard.lanes.map(lane => (
              <div key={lane.title} style={{
                background: '#0f172a',
                border: '1px solid #1e293b',
                borderRadius: '4px',
                padding: '0.75rem',
              }}>
                <p className="dm-kicker" style={{ color: '#22d3ee', marginBottom: '0.375rem' }}>{lane.title}</p>
                <p style={{ fontSize: '0.875rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '0.5rem' }}>{lane.summary}</p>
                <ul style={{ paddingLeft: '1.125rem', margin: 0, display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  {lane.items.map(item => (
                    <li key={item} style={{ fontSize: '0.75rem', color: '#64748b', fontFamily: 'var(--font-body)' }}>{item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Command History */}
      <div className="dm-panel">
        <div className="dm-panel-header">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
            <div>
              <p className="dm-kicker">Session Log</p>
              <h2 className="dm-panel-title">Command History</h2>
            </div>
            <Badge tone="info">{data.history.length} records</Badge>
          </div>
        </div>
        <div className="dm-section">
          {data.history.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table className="dm-table" style={{ width: '100%' }}>
                <thead>
                  <tr>
                    <th>Week</th>
                    <th>Intent</th>
                    <th>Result</th>
                    <th>Opponent</th>
                    <th style={{ textAlign: 'right' }}>Replay</th>
                  </tr>
                </thead>
                <tbody>
                  {data.history.slice(-6).reverse().map(record => (
                    <tr key={record.history_id}>
                      <td>
                        <span className="dm-data" style={{ color: '#22d3ee' }}>W{record.week}</span>
                      </td>
                      <td style={{ color: '#94a3b8' }}>{record.intent}</td>
                      <td>
                        <span className={`dm-badge ${record.dashboard.result === 'Win' ? 'dm-badge-emerald' : record.dashboard.result === 'Loss' ? 'dm-badge-rose' : 'dm-badge-amber'}`}>
                          {record.dashboard.result}
                        </span>
                      </td>
                      <td style={{ color: '#cbd5e1' }}>{record.dashboard.opponent_name}</td>
                      <td style={{ textAlign: 'right' }}>
                        {record.match_id && onOpenReplay ? (
                          <button
                            type="button"
                            onClick={() => onOpenReplay(record.match_id as string)}
                            style={{
                              background: 'none',
                              border: 'none',
                              cursor: 'pointer',
                              fontFamily: 'var(--font-display)',
                              fontSize: '0.6875rem',
                              textTransform: 'uppercase',
                              letterSpacing: '0.075em',
                              color: '#22d3ee',
                              padding: '0.25rem 0',
                            }}
                          >
                            View
                          </button>
                        ) : (
                          <span style={{ color: '#334155', fontSize: '0.75rem' }}>—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p style={{ fontSize: '0.875rem', color: '#475569', fontFamily: 'var(--font-body)' }}>No command weeks simulated yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
