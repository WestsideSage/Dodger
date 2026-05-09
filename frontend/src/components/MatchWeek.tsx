import { MatchupCard } from './match-week/MatchupCard';
import { WeeklyChecklist } from './match-week/WeeklyChecklist';
import { ProgramStatusStrip } from './match-week/ProgramStatusStrip';
import { Headline } from './match-week/aftermath/Headline';
import { MatchCard as AftermathMatchCard } from './match-week/aftermath/MatchCard';
import { PlayerGrowthBlock } from './match-week/aftermath/PlayerGrowthBlock';
import { StandingsShift } from './match-week/aftermath/StandingsShift';
import { RecruitReactions } from './match-week/aftermath/RecruitReactions';
import { useState, useEffect } from 'react';
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
  const [revealStage, setRevealStage] = useState(0);

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

  useEffect(() => {
    if (mode !== 'post-sim' || !result?.aftermath) return;
    if (revealStage >= 5) return;
    const t = setTimeout(() => setRevealStage(prev => prev + 1), 1000);
    return () => clearTimeout(t);
  }, [revealStage, mode, result]);

  useEffect(() => {
    if (mode !== 'post-sim') return;
    const skip = (e: KeyboardEvent | MouseEvent) => {
      if (e.type === 'keydown' && (e as KeyboardEvent).code !== 'Space') return;
      setRevealStage(5);
    };
    window.addEventListener('keydown', skip);
    window.addEventListener('click', skip);
    return () => {
      window.removeEventListener('keydown', skip);
      window.removeEventListener('click', skip);
    };
  }, [mode]);

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

  const renderPostSimMode = () => {
    if (!result?.aftermath) return (
      <div className="dm-panel">
        <p>Processing results...</p>
      </div>
    );

    const { aftermath } = result;

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }} data-testid="match-week-post-sim">
        <PageHeader eyebrow="Match Week" title="Aftermath" description="Reviewing the weekly fallout." />
        
        {revealStage >= 0 && <Headline text={aftermath.headline} />}
        {revealStage >= 1 && <AftermathMatchCard data={aftermath.match_card} />}
        {revealStage >= 2 && <PlayerGrowthBlock deltas={aftermath.player_growth_deltas} />}
        {revealStage >= 3 && <StandingsShift shifts={aftermath.standings_shift} />}
        {revealStage >= 4 && <RecruitReactions reactions={aftermath.recruit_reactions} />}

        {revealStage >= 5 && (
          <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'center' }}>
            <ActionButton variant="primary" onClick={() => { 
                setRevealStage(0);
                setResult(null); 
                load(); 
                onAdvanceWeek?.(); 
            }}>
              Advance to Next Week
            </ActionButton>
          </div>
        )}
      </div>
    );
  };

  const renderOffseasonMode = () => (
    <div data-testid="match-week-offseason">
      <Offseason />
    </div>
  );

  if (mode === 'offseason') return renderOffseasonMode();
  if (mode === 'post-sim') return renderPostSimMode();
  return renderPreSimMode();
}
