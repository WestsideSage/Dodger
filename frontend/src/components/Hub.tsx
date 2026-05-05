import { useCallback, useEffect, useState } from 'react';
import type { MatchReplayResponse, StatusResponse, SimResponse } from '../types';
import { MatchReplay } from './MatchReplay';
import { ActionButton, Badge, Card, KeyValueRow, PageHeader, StatChip, StatusMessage } from './ui';

function formatState(value: string) {
  return value.replaceAll('_', ' ');
}

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
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`group rounded-md border border-[var(--color-border)] p-4 text-left shadow-[var(--shadow-button)] transition-all duration-150 cursor-pointer disabled:cursor-not-allowed disabled:opacity-45 ${
        variant === 'primary'
          ? 'bg-[var(--color-gym)] text-[var(--color-paper)] hover:-translate-y-0.5 hover:bg-[var(--color-teal)]'
          : variant === 'accent'
            ? 'bg-[var(--color-brick)] text-[var(--color-paper)] hover:-translate-y-0.5 hover:bg-[var(--color-orange)]'
            : 'bg-[var(--color-paper)] text-[var(--color-charcoal)] hover:-translate-y-0.5 hover:bg-[var(--color-cream)]'
      }`}
    >
      <span className="block font-display uppercase tracking-widest text-sm">{loading ? 'Simulating...' : title}</span>
      <span className={`mt-1 block text-xs ${variant === 'secondary' ? 'text-[var(--color-muted)]' : 'text-[color-mix(in_srgb,var(--color-paper)_82%,transparent)]'}`}>
        {detail}
      </span>
    </button>
  );
}

export function Hub() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [acknowledging, setAcknowledging] = useState(false);
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
  if (replay) return <MatchReplay replay={replay} acknowledging={acknowledging} onAcknowledge={handleAcknowledge} />;

  const canSimulate = status.state.state === 'season_active_pre_match';

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        eyebrow="Manager desk"
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

      {!canSimulate && (
        <StatusMessage title="No playable match" tone="warning">
          The backend reports {formatState(status.state.state)}. Simulation actions are held until a pre-match state is available.
        </StatusMessage>
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.15fr_0.85fr]">
        <Card className="overflow-hidden">
          <div className="border-b border-[var(--color-border)] bg-[var(--color-charcoal)] p-4 text-[var(--color-paper)]">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="font-display uppercase tracking-widest text-lg">Match Controls</h3>
                <p className="text-sm text-[color-mix(in_srgb,var(--color-paper)_75%,transparent)]">
                  Choose how aggressively to move time forward.
                </p>
              </div>
              <Badge tone={canSimulate ? 'success' : 'warning'}>{canSimulate ? 'Ready' : 'Waiting'}</Badge>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 p-4 md:grid-cols-2">
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
            <div className="md:col-span-2">
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
            <div className="border-t border-[var(--color-border)] bg-[var(--color-cream)] p-4">
              <StatusMessage title="Simulation complete" tone="success">
                {simResult.message || `Simulated ${simResult.simulated_count} matches.`}
              </StatusMessage>
            </div>
          )}
        </Card>

        <Card className="p-4">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <h3 className="font-display uppercase tracking-widest text-lg">Club Status</h3>
              <p className="text-sm text-[var(--color-muted)]">Current save cursor and club context.</p>
            </div>
            <ActionButton variant="ghost" onClick={() => refreshStatus(true)} disabled={loading}>
              Refresh
            </ActionButton>
          </div>
          <div>
            <KeyValueRow label="Active Season" value={status.context.season_id ? (status.context.season_id.split('-')[0] || status.context.season_id) : 'None'} />
            <KeyValueRow label="Your Club" value={status.context.player_club_name || status.context.player_club_id || 'None'} />
            <KeyValueRow label="Cursor" value={formatState(status.state.state)} />
            {status.state.match_id && <KeyValueRow label="Last Match" value={`${status.state.match_id.substring(0, 8)}...`} />}
          </div>
        </Card>
      </div>
    </div>
  );
}
