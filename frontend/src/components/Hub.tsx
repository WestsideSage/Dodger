import { useCallback, useState } from 'react';
import type { MatchReplayResponse, ScheduleResponse, StatusResponse, SimResponse } from '../types';
import MatchReplay from './MatchReplay';
import { useApiResource } from '../hooks/useApiResource';
import { ActionButton, KeyValueRow, Badge, StatusMessage } from './ui';

function formatState(value: string) {
  return value.replaceAll('_', ' ');
}

function formatPhaseLabel(value: string) {
  const labels: Record<string, string> = {
    season_active_pre_match: 'Matchday ready',
    season_active_in_match: 'Match in progress',
    season_active_match_report_pending: 'Match report ready',
    season_complete_offseason_beat: 'Offseason review',
    season_complete_recruitment_pending: 'Recruitment day',
    next_season_ready: 'Next season ready',
  };
  return labels[value] ?? formatState(value);
}

function formatSeasonLabel(seasonId: string | null | undefined, seasonNumber: number) {
  if (seasonNumber > 0) return `Season ${seasonNumber}`;
  const parsed = seasonId?.match(/(\d+)$/)?.[1];
  return parsed ? `Season ${parsed}` : 'No active season';
}

function formatMatchStatus(value: string) {
  const labels: Record<string, string> = {
    open: 'Scheduled',
    scheduled: 'Scheduled',
    played: 'Final',
    completed: 'Final',
    final: 'Final',
  };
  return labels[value.toLowerCase()] ?? formatState(value);
}

function isUnplayedStatus(value: string) {
  return !['played', 'completed', 'final'].includes(value.toLowerCase());
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
      type="button"
      className={`dm-hub-action dm-hub-action-${variant}`}
      onClick={onClick}
      disabled={disabled}
    >
      <span className="dm-hub-action-title">
        {loading ? 'Simulating...' : title}
      </span>
      <span className="dm-hub-action-detail">{detail}</span>
    </button>
  );
}

export function Hub() {
  const [simulating, setSimulating] = useState(false);
  const [, setAcknowledging] = useState(false);
  const [simResult, setSimResult] = useState<SimResponse | null>(null);
  const [replay, setReplay] = useState<MatchReplayResponse | null>(null);

  const loadReplay = useCallback((matchId: string) => {
    return fetch(`/api/matches/${encodeURIComponent(matchId)}/replay`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch match replay');
        return res.json();
      })
      .then(setReplay);
  }, []);

  const handleLoad = useCallback((data: StatusResponse) => {
    if (data.state?.state === 'season_active_match_report_pending' && data.state.match_id) {
      loadReplay(data.state.match_id).catch(() => {});
    }
  }, [loadReplay]);

  const { data: status, error, loading, setData: setStatus, setError, setLoading } = useApiResource<StatusResponse>('/api/status', handleLoad);
  const { data: schedule } = useApiResource<ScheduleResponse>('/api/schedule');

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
          loadReplay(data.state.match_id).catch(err => setError(err.message));
        } else {
          setReplay(null);
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [setStatus, setError, setLoading, loadReplay]);

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
  const nextUserMatch = schedule?.schedule.find(row => row.is_user_match && isUnplayedStatus(row.status)) ?? null;
  const upcomingRows = schedule?.schedule.filter(row => isUnplayedStatus(row.status)).slice(0, 4) ?? [];
  const playerClubId = status.context.player_club_id;
  const opponentName = nextUserMatch
    ? nextUserMatch.home_club_id === playerClubId
      ? nextUserMatch.away_club_name
      : nextUserMatch.home_club_name
    : null;
  const matchupLine = nextUserMatch
    ? `${nextUserMatch.home_club_name} vs ${nextUserMatch.away_club_name}`
    : 'No user match queued';
  const phaseLabel = formatPhaseLabel(status.state.state);
  const seasonLabel = formatSeasonLabel(status.context.season_id, status.state.season_number);

  return (
    <div className="dm-hub-page">
      <section className="dm-hub-hero">
        <div className="dm-hub-court-mark" aria-hidden="true">
          <div />
          <div />
          <div />
        </div>
        <div className="dm-hub-hero-main">
          <p className="dm-kicker">Season Hub</p>
          <h1>{status.context.player_club_name || 'Club Office'}</h1>
          <p>{phaseLabel}</p>
          <div className="dm-hub-score-strip">
            <div>
              <span>Season</span>
              <strong>{seasonLabel}</strong>
            </div>
            <div>
              <span>Match Week</span>
              <strong>Week {status.state.week}</strong>
            </div>
            <div>
              <span>Next Opponent</span>
              <strong>{opponentName || 'Pending'}</strong>
            </div>
          </div>
        </div>
        <div className="dm-hub-match-card">
          <span className="dm-hub-match-label">Next User Match</span>
          <strong>{matchupLine}</strong>
          {nextUserMatch && <span>Week {nextUserMatch.week} &middot; {formatMatchStatus(nextUserMatch.status)}</span>}
          <ActionButton
            variant="primary"
            onClick={() => handleSimulate('user_match')}
            disabled={simulating || !canSimulate}
            style={{ width: '100%', marginTop: '1rem' }}
          >
            {simulating ? 'Simulating...' : 'Play Next Match'}
          </ActionButton>
        </div>
      </section>

      {/* Pre-match state alert */}
      {!canSimulate && (
        <StatusMessage title="No playable match" tone="warning">
          {phaseLabel}. Simulation actions are held until the next matchday is available.
        </StatusMessage>
      )}

      {/* Match Controls + Club Status row */}
      <div className="dm-hub-grid">

        {/* Match Controls */}
        <section className="dm-panel dm-hub-operations">
          <div className="dm-panel-header">
            <p className="dm-kicker">Operations</p>
            <div className="dm-hub-section-title">
              <div>
                <h2 className="dm-panel-title">Advance Time</h2>
                <p className="dm-panel-subtitle">Choose the smallest jump that matches what you want to review next.</p>
              </div>
              <Badge tone={canSimulate ? 'success' : 'warning'}>{canSimulate ? 'Ready' : 'Waiting'}</Badge>
            </div>
          </div>

          <div className="dm-section">
            <div className="dm-hub-action-grid">
              <SimAction
                title="Sim Week"
                detail="Advances the current league week."
                variant="primary"
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
              <SimAction
                title="Sim To Playoffs"
                detail="Fastest option; may skip quiet weeks until a milestone blocks progress."
                variant="secondary"
                disabled={simulating || !canSimulate}
                onClick={() => handleSimulate('milestone', { milestone: 'playoffs' })}
              />
            </div>

            {simResult && (
              <div style={{ marginTop: '0.75rem' }}>
                <StatusMessage title="Simulation complete" tone="success">
                  {simResult.message || `Simulated ${simResult.simulated_count} matches.`}
                </StatusMessage>
              </div>
            )}
          </div>
        </section>

        {/* Club Status */}
        <section className="dm-panel dm-hub-side">
          <div className="dm-panel-header">
            <div className="dm-hub-section-title">
              <div>
                <p className="dm-kicker">Manager Desk</p>
                <h2 className="dm-panel-title">Club Status</h2>
                <p className="dm-panel-subtitle">Your club, season, and the next thing waiting for attention.</p>
              </div>
              <ActionButton variant="ghost" onClick={() => refreshStatus(true)} disabled={loading}>
                Refresh
              </ActionButton>
            </div>
          </div>
          <div className="dm-section">
            <KeyValueRow
              label="Season"
              value={seasonLabel}
            />
            <KeyValueRow
              label="Your Club"
              value={status.context.player_club_name || status.context.player_club_id || 'None'}
            />
            <KeyValueRow label="Current Step" value={phaseLabel} />
          </div>
          <div className="dm-hub-fixtures">
            <p className="dm-kicker">Upcoming</p>
            {upcomingRows.length > 0 ? upcomingRows.map(row => (
              <div key={row.match_id} className={row.is_user_match ? 'dm-hub-fixture dm-hub-fixture-user' : 'dm-hub-fixture'}>
                <span>W{row.week}</span>
                <strong>{row.home_club_name} vs {row.away_club_name}</strong>
              </div>
            )) : (
              <p className="dm-panel-subtitle">No scheduled fixtures remain.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
