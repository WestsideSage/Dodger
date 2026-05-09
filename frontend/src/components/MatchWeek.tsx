import { MatchupCard } from './match-week/MatchupCard';
import { WeeklyChecklist } from './match-week/WeeklyChecklist';
import { ProgramStatusStrip } from './match-week/ProgramStatusStrip';
import { useState } from 'react';
import type { CommandCenterResponse, CommandCenterSimResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { ActionButton, PageHeader, StatChip, StatusMessage } from './ui';
import { Offseason } from './Offseason';

type MatchWeekMode = 'pre-sim' | 'post-sim' | 'offseason';

export function MatchWeek({
  mode,
  onSimComplete,
  onAdvanceWeek,
}: {
  onOpenReplay?: (matchId: string) => void;
  mode: MatchWeekMode;
  onSimComplete?: () => void;
  onAdvanceWeek?: () => void;
}) {
  const { data, setData, error, setError, loading, setLoading } = useApiResource<CommandCenterResponse>('/api/command-center');
  const [localIntent, setLocalIntent] = useState<string | undefined>(undefined);
  const [result, setResult] = useState<CommandCenterSimResponse | null>(null);

  const selectedIntent = localIntent ?? data?.plan.intent ?? 'Win Now';

  const load = (showLoading = false) => {
    if (showLoading) setLoading(true);
    return fetch('/api/command-center')
      .then(res => {
        if (!res.ok) throw new Error('Command center unavailable');
        return res.json();
      })
      .then((payload: CommandCenterResponse) => {
        setData(payload);
        setLocalIntent(undefined);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  };

  const savePlan = (intent = selectedIntent) => {
    setError(null);
    return fetch('/api/command-center/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ intent }),
    })
      .then(res => {
        if (!res.ok) throw new Error('Plan save failed');
        return res.json();
      })
      .then((payload: CommandCenterResponse) => {
        setData(payload);
        setLocalIntent(undefined);
      })
      .catch(err => setError(err.message));
  };

  const simulate = () => {
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
        onSimComplete?.();
        return load();
      })
      .catch(err => setError(err.message));
  };

  const renderPreSimMode = () => {
    if (loading && !data) return <StatusMessage title="Loading command center">Opening the weekly desk.</StatusMessage>;
    if (error) return <StatusMessage title="Command center unavailable" tone="danger">{error}</StatusMessage>;
    if (!data) return null;

    const plan = data.plan;

    const isSimReady = data.plan.warnings?.length === 0;

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }} data-testid="weekly-command-center">
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
        
        <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
          <label style={{ display: 'block' }}>
            <span className="dm-kicker" style={{ display: 'block', marginBottom: '0.375rem' }}>Intent</span>
            <select
              aria-label="Weekly intent"
              value={selectedIntent}
              onChange={(event) => {
                setLocalIntent(event.target.value);
                savePlan(event.target.value);
              }}
              style={{
                width: '100%',
                maxWidth: '180px',
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
        </div>

        <MatchupCard plan={data.plan} onSimulate={simulate} disabled={!isSimReady} />
        
        <div style={{ display: 'flex', gap: '1.25rem' }}>
          <WeeklyChecklist plan={data.plan} onAcceptPlan={() => savePlan()} />
          <ProgramStatusStrip />
        </div>
      </div>
    );
  };

  const renderPostSimMode = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }} data-testid="match-week-post-sim">
      <PageHeader eyebrow="Match Week" title="Aftermath" description="Match results — full layout in Wave 2." />
      <div className="dm-panel">
        <p>Post-sim aftermath stub. Subplan 06 will replace this with sequenced reveal blocks (Headline, Match Card, Player Growth, Standings Shift, Recruit Reactions).</p>
        {result && (
          <ActionButton onClick={() => { setResult(null); load(); onAdvanceWeek?.(); }}>Advance to Next Week</ActionButton>
        )}
      </div>
    </div>
  );

  const renderOffseasonMode = () => (
    <div data-testid="match-week-offseason">
      <Offseason />
    </div>
  );

  if (mode === 'offseason') return renderOffseasonMode();
  if (mode === 'post-sim') return renderPostSimMode();
  return renderPreSimMode();
}
