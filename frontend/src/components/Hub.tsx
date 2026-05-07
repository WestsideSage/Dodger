import { useCallback, useEffect, useState } from 'react';
import type { MatchReplayResponse, StatusResponse, SimResponse } from '../types';
import MatchReplay from './MatchReplay';
import { ActionButton, KeyValueRow, Badge, PageHeader, StatChip, StatusMessage } from './ui';

function formatState(value: string) {
  return value.replaceAll('_', ' ');
}

// War-room variant styles for sim action tiles
const simTileVariantStyle: Record<'primary' | 'accent' | 'secondary', React.CSSProperties> = {
  primary: {
    background: 'rgba(249,115,22,0.08)',
    border: '1px solid rgba(249,115,22,0.35)',
    color: '#f97316',
  },
  accent: {
    background: 'rgba(34,211,238,0.07)',
    border: '1px solid rgba(34,211,238,0.3)',
    color: '#22d3ee',
  },
  secondary: {
    background: '#0f172a',
    border: '1px solid #1e293b',
    color: '#94a3b8',
  },
};

function SimAction({
  title,
  detail,
  disabled,
  loading,
  variant,
  onClick,
}: {
  title: string;
  detail: string;
  disabled: boolean;
  loading?: boolean;
  variant: 'primary' | 'accent' | 'secondary';
  onClick: () => void;
}) {
  const varStyle = simTileVariantStyle[variant];
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        ...varStyle,
        borderRadius: '4px',
        padding: '0.875rem 1rem',
        textAlign: 'left',
        cursor: 'pointer',
        transition: 'all 0.15s',
        opacity: disabled ? 0.45 : 1,
        width: '100%',
      }}
    >
      <span style={{
        display: 'block',
        fontFamily: 'var(--font-display)',
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        fontSize: '0.8125rem',
        fontWeight: 700,
        color: varStyle.color,
      }}>
        {loading ? 'Simulating...' : title}
      </span>
      <span style={{
        display: 'block',
        marginTop: '0.25rem',
        fontSize: '0.75rem',
        color: '#475569',
        fontFamily: 'var(--font-body)',
      }}>
        {detail}
      </span>
    </button>
  );
}

export function Hub() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [, setAcknowledging] = useState(false);
  const [simResult, setSimResult] = useState<SimResponse | null>(null);
  const [replay, setReplay] = useState<MatchReplayResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadReplay = useCallback((matchId: string) => {
    return fetch(`/api/matches/${encodeURIComponent(matchId)}/replay`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch match replay');
        return res.json();
      })
      .then(setReplay);
  }, []);

  const refreshStatus = useCallback((showLoading = false) => {
    if (showLoading) setLoading(true);
    return fetch('/api/status')
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch status');
        return res.json();
      })
      .then(data => {
        setStatus(data);
        if (data.state?.state === 'season_active_match_report_pending' && data.state.match_id) {
          return loadReplay(data.state.match_id);
        }
        setReplay(null);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [loadReplay]);

  useEffect(() => {
    let cancelled = false;

    fetch('/api/status')
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch status');
        return res.json();
      })
      .then(data => {
        if (!cancelled) setStatus(data);
        if (!cancelled && data.state?.state === 'season_active_match_report_pending' && data.state.match_id) {
          return loadReplay(data.state.match_id);
        }
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
  }, [loadReplay]);

  const handleSimulate = (mode = 'week', body: Record<string, string | number> = {}) => {
    setSimulating(true);
    setSimResult(null);
    setError(null);
    fetch('/api/sim', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, ...body })
    })
      .then(res => {
        if (!res.ok) throw new Error('Simulation failed');
        return res.json();
      })
      .then(res => {
        setSimResult(res);
        if (res.match_id && res.next_state === 'season_active_match_report_pending') {
          return loadReplay(res.match_id).then(() => refreshStatus());
        }
        return refreshStatus();
      })
      .catch(err => setError(err.message))
      .finally(() => setSimulating(false));
  };

  const handleAcknowledge = () => {
    if (!replay) return;
    setAcknowledging(true);
    setError(null);
    fetch(`/api/matches/${encodeURIComponent(replay.match_id)}/acknowledge`, { method: 'POST' })
      .then(res => {
        if (!res.ok) throw new Error('Failed to close match report');
        return res.json();
      })
      .then(() => {
        setReplay(null);
        setSimResult(null);
        return refreshStatus(true);
      })
      .catch(err => setError(err.message))
      .finally(() => setAcknowledging(false));
  };

  if (loading && !status) return <StatusMessage title="Loading hub">Opening the manager desk.</StatusMessage>;
  if (error) return <StatusMessage title="Hub unavailable" tone="danger">{error}</StatusMessage>;
  if (!status) return null;
  if (replay) return <MatchReplay data={replay} onContinue={handleAcknowledge} />;

  const canSimulate = status.state.state === 'season_active_pre_match';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

      {/* Page header */}
      <PageHeader
        eyebrow="War Room"
        title="Season Hub"
        description="Advance the schedule from the same workspace, with single-match play separated from bulk simulation."
        stats={
          <>
            <StatChip label="Season" value={status.state.season_number} />
            <StatChip label="Week" value={status.state.week} tone="warning" />
            <StatChip label="State" value={formatState(status.state.state)} tone={canSimulate ? 'success' : 'info'} />
          </>
        }
      />

      {/* Pre-match state alert */}
      {!canSimulate && (
        <StatusMessage title="No playable match" tone="warning">
          The backend reports {formatState(status.state.state)}. Simulation actions are held until a pre-match state is available.
        </StatusMessage>
      )}

      {/* Match Controls + Club Status row */}
      <div className="lg-two-col-hub">

        {/* Match Controls */}
        <div className="dm-panel">
          <div className="dm-panel-header" style={{ borderBottom: '1px solid #1e293b' }}>
            <p className="dm-kicker">Simulation Console</p>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
              <div>
                <h2 className="dm-panel-title">Match Controls</h2>
                <p className="dm-panel-subtitle">Choose how aggressively to move time forward.</p>
              </div>
              <Badge tone={canSimulate ? 'success' : 'warning'}>{canSimulate ? 'Ready' : 'Waiting'}</Badge>
            </div>
          </div>

          <div className="dm-section">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '0.75rem' }}>
              <SimAction
                title="Play Next Match"
                detail={`Stops at the Week ${status.state.week} report.`}
                variant="primary"
                loading={simulating}
                disabled={simulating || !canSimulate}
                onClick={() => handleSimulate('user_match')}
              />
              <SimAction
                title="Sim Week"
                detail="Advances the current league week."
                variant="accent"
                disabled={simulating || !canSimulate}
                onClick={() => handleSimulate('week')}
              />
              <SimAction
                title="Sim To User Match"
                detail="Runs neutral fixtures until your club is due."
                variant="secondary"
                disabled={simulating || !canSimulate}
                onClick={() => handleSimulate('next_user_match')}
              />
              <SimAction
                title="Sim 2 Weeks"
                detail="Bulk advance, stopping for required reports."
                variant="secondary"
                disabled={simulating || !canSimulate}
                onClick={() => handleSimulate('multiple_weeks', { weeks: 2 })}
              />
              <div style={{ gridColumn: '1 / -1' }}>
                <SimAction
                  title="Sim To Playoffs"
                  detail="Fastest option; may skip quiet weeks until a milestone blocks progress."
                  variant="secondary"
                  disabled={simulating || !canSimulate}
                  onClick={() => handleSimulate('milestone', { milestone: 'playoffs' })}
                />
              </div>
            </div>

            {simResult && (
              <div style={{ marginTop: '0.75rem' }}>
                <StatusMessage title="Simulation complete" tone="success">
                  {simResult.message || `Simulated ${simResult.simulated_count} matches.`}
                </StatusMessage>
              </div>
            )}
          </div>
        </div>

        {/* Club Status */}
        <div className="dm-panel">
          <div className="dm-panel-header">
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem' }}>
              <div>
                <p className="dm-kicker">Save Cursor</p>
                <h2 className="dm-panel-title">Club Status</h2>
                <p className="dm-panel-subtitle">Current save cursor and club context.</p>
              </div>
              <ActionButton variant="ghost" onClick={() => refreshStatus(true)} disabled={loading}>
                Refresh
              </ActionButton>
            </div>
          </div>
          <div className="dm-section">
            <KeyValueRow
              label="Active Season"
              value={status.context.season_id ? (status.context.season_id.split('-')[0] || status.context.season_id) : 'None'}
            />
            <KeyValueRow
              label="Your Club"
              value={status.context.player_club_name || status.context.player_club_id || 'None'}
            />
            <KeyValueRow label="Cursor" value={formatState(status.state.state)} />
            {status.state.match_id && (
              <KeyValueRow label="Last Match" value={`${status.state.match_id.substring(0, 8)}...`} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
