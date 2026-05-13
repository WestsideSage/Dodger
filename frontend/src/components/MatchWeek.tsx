import { ProgramStatusStrip } from './match-week/ProgramStatusStrip';
import { SimTransition } from './match-week/SimTransition';
import { Headline } from './match-week/aftermath/Headline';
import { MatchScoreHero } from './match-week/aftermath/MatchScoreHero';
import { FalloutGrid } from './match-week/aftermath/FalloutGrid';
import { AftermathActionBar } from './match-week/aftermath/AftermathActionBar';
import { ReplayTimeline } from './match-week/aftermath/ReplayTimeline';
import { KeyPlayersPanel } from './match-week/aftermath/KeyPlayersPanel';
import { TacticalSummaryCard } from './match-week/aftermath/TacticalSummaryCard';
import { useState, useEffect, useRef } from 'react';
import type { Aftermath, CommandCenterResponse, CommandCenterSimResponse, MatchReplayResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { ActionButton, PageHeader, StatusMessage } from './ui';
import { Offseason } from './Offseason';

type MatchWeekMode = 'pre-sim' | 'post-sim' | 'offseason';

function resolveMatchCardNames({
  matchCard,
  currentData,
  activeResult,
}: {
  matchCard: NonNullable<Aftermath['match_card']>;
  currentData: CommandCenterResponse | null;
  activeResult: CommandCenterSimResponse;
}) {
  const playerClubId = currentData?.player_club_id ?? activeResult.plan.player_club_id;
  const playerClubName = currentData?.player_club_name ?? 'Your Club';
  const opponentName = currentData?.plan.opponent.name ?? activeResult.dashboard.opponent_name ?? 'Opponent';
  const homeIsPlayer = matchCard.home_club_id === playerClubId;

  return {
    homeTeam: homeIsPlayer ? playerClubName : opponentName,
    awayTeam: homeIsPlayer ? opponentName : playerClubName,
  };
}

export function MatchWeek({
  mode,
  onOpenReplay,
  persistedResult,
  onSimComplete,
  onAdvanceWeek,
}: {
  onOpenReplay?: (matchId: string) => void;
  mode: MatchWeekMode;
  persistedResult?: CommandCenterSimResponse | null;
  onSimComplete?: (result: CommandCenterSimResponse) => void;
  onAdvanceWeek?: () => void;
}) {
  const { data, setData, error, setError, loading, setLoading } = useApiResource<CommandCenterResponse>('/api/command-center');
  const [localIntent, setLocalIntent] = useState<string | undefined>(undefined);
  const [result, setResult] = useState<CommandCenterSimResponse | null>(null);
  const [revealStage, setRevealStage] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isAdvancingWeek, setIsAdvancingWeek] = useState(false);
  const [planConfirmed, setPlanConfirmed] = useState(false);
  const [replayData, setReplayData] = useState<MatchReplayResponse | null>(null);
  const opponentFileRef = useRef<HTMLElement | null>(null);

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

  const savePlan = (intent = selectedIntent, confirm = false) => {
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
        setPlanConfirmed(confirm);
      })
      .catch(err => setError(err.message));
  };

  const simulate = () => {
    setError(null);
    setIsTransitioning(true);
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
      .catch(err => {
        setError(err.message);
        setIsTransitioning(false);
      });
  };

  const handleSimTransitionComplete = () => {
    setIsTransitioning(false);
    if (result) {
      onSimComplete?.(result);
    }
  };

  const handleAdvanceWeek = () => {
    setIsAdvancingWeek(true);
    setTimeout(() => {
        setRevealStage(0);
        setResult(null); 
        setPlanConfirmed(false);
        load(); 
        onAdvanceWeek?.();
        setIsAdvancingWeek(false);
    }, 400); // brief fade transition for advancing week
  };

  useEffect(() => {
    const activeResult = result ?? persistedResult;
    if (mode !== 'post-sim' || !activeResult?.aftermath) return;
    if (revealStage >= 4) return;
    const t = setTimeout(() => setRevealStage(prev => prev + 1), 1000);
    return () => clearTimeout(t);
  }, [revealStage, mode, result, persistedResult]);

  useEffect(() => {
    if (mode !== 'post-sim') return;
    const skip = (e: KeyboardEvent | MouseEvent) => {
      if (e.type === 'keydown' && (e as KeyboardEvent).code !== 'Space') return;
      setRevealStage(4);
    };
    window.addEventListener('keydown', skip);
    window.addEventListener('click', skip);
    return () => {
      window.removeEventListener('keydown', skip);
      window.removeEventListener('click', skip);
    };
  }, [mode]);

  useEffect(() => {
    const activeResult = result ?? persistedResult;
    const matchId = activeResult?.dashboard?.match_id;
    if (mode !== 'post-sim' || !matchId) return;
    if (replayData?.match_id === matchId) return;

    let cancelled = false;
    fetch(`/api/matches/${encodeURIComponent(matchId)}/replay`)
      .then(res => {
        if (!res.ok) throw new Error('Replay unavailable');
        return res.json();
      })
      .then((payload: MatchReplayResponse) => {
        if (!cancelled) setReplayData(payload);
      })
      .catch(() => {
        if (!cancelled) setReplayData(null);
      });

    return () => {
      cancelled = true;
    };
  }, [mode, result, persistedResult, replayData?.match_id]);

  const renderPreSimMode = () => {
    if (loading && !data) return <StatusMessage title="Loading command center">Opening the weekly desk.</StatusMessage>;
    if (error) return <StatusMessage title="Command center unavailable" tone="danger">{error}</StatusMessage>;
    if (!data) return null;

    const plan = data.plan;
    const hasValidLineup = (data.plan.lineup?.player_ids?.length ?? 0) >= 6;
    const hasTactics = Boolean(data.plan.tactics && Object.keys(data.plan.tactics).length > 0);
    const isSimReady = planConfirmed && hasValidLineup && hasTactics;
    const disabledReason = !hasValidLineup
      ? 'Set a valid six-player lineup before simulating.'
      : !hasTactics
      ? 'Choose a tactic before simulating.'
      : !planConfirmed
      ? 'Confirm the staff plan before simulating.'
      : undefined;
    const details = plan.matchup_details ?? {
      opponent_record: 'No record',
      last_meeting: 'None',
      key_matchup: 'Opponent file unavailable.',
      framing_line: data.current_objective,
    };
    const starterNames = (plan.lineup?.players ?? []).slice(0, 6).map(player => player.name);
    const recommendations = plan.recommendations ?? [];
    const departmentOrders = Object.entries(plan.department_orders ?? {}).slice(0, 6);
    const planningStepsComplete = [hasValidLineup, hasTactics, planConfirmed].filter(Boolean).length;
    const departmentCopy: Record<string, string> = {
      tactics: "Prioritize the next opponent's tendencies.",
      training: 'Maintain core execution and weekly fundamentals.',
      conditioning: 'Preserve stamina without overloading the roster.',
      medical: 'Reduce avoidable injury risk before match day.',
      scouting: 'Prepare for the upcoming matchup.',
      culture: 'Keep morale stable during match week.',
    };
    const viewScoutingDetail = () => {
      opponentFileRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      opponentFileRef.current?.focus({ preventScroll: true });
    };

    const renderCockpit = () => (
      <div className="command-home" data-testid="weekly-command-center">
        <div className="command-home-header-row">
          <PageHeader
            eyebrow="War Room / Match Week"
            title="Command Center"
            description="Review the matchup, confirm the staff plan, then simulate the week."
          />
          <aside className="dm-panel command-home-state-card" aria-label="Current command state">
            <span>{planConfirmed ? 'Ready' : 'Pending'}</span>
            <div>
              <p>{data.player_club_name} - Week {data.week}</p>
              <strong>{planConfirmed ? 'Plan Accepted' : 'Plan Pending'}</strong>
            </div>
          </aside>
        </div>

        <section className="dm-panel command-home-hero-card" aria-label="Match Week decision">
          <div className="command-home-hero-copy">
            <p className="dm-kicker">This Week</p>
            <h2>{plan.opponent.name}</h2>
            <p>{details.framing_line}</p>
            <div className="command-home-hero-stats">
              <div>
                <span>Record</span>
                <strong>{details.opponent_record}</strong>
              </div>
              <div>
                <span>Last Meeting</span>
                <strong>{details.last_meeting}</strong>
              </div>
              <div>
                <span>Next Match</span>
                <strong>Week {data.week}</strong>
              </div>
            </div>
          </div>

          <div className="command-home-hero-control">
            <label className="command-home-intent-field">
              <span className="dm-kicker">Current Intent</span>
              <select
                aria-label="Weekly intent"
                value={selectedIntent}
                onChange={(event) => {
                  setLocalIntent(event.target.value);
                  setPlanConfirmed(false);
                  savePlan(event.target.value);
                }}
              >
                {plan.available_intents.map(intent => <option key={intent}>{intent}</option>)}
              </select>
            </label>

            <div className="command-home-readiness">
              <span>{planningStepsComplete} of 3 planning steps confirmed</span>
              <strong>{planConfirmed ? 'Ready to simulate' : 'Plan pending'}</strong>
              {disabledReason && <p>{disabledReason}</p>}
            </div>

            <div className="command-home-hero-actions">
              <ActionButton variant="primary" disabled={!isSimReady} onClick={simulate} data-testid="simulate-command-week">
                Simulate Week
              </ActionButton>
              <ActionButton variant="secondary" onClick={viewScoutingDetail}>
                View Detail
              </ActionButton>
            </div>
          </div>
        </section>

        <div className="command-home-body-grid">
          <main className="command-home-operations" aria-label="Weekly operations">
            <section className="dm-panel command-home-panel">
              <div className="command-section-heading">
                <p className="dm-kicker">Weekly Operations</p>
                <h3>Staff orders</h3>
              </div>
              <div className="command-home-orders">
                {departmentOrders.length === 0 ? (
                  <p className="command-empty-copy">No department orders available.</p>
                ) : departmentOrders.map(([department, order]) => (
                  <div key={department}>
                    <span>{department.replaceAll('_', ' ')}</span>
                    <strong>{order.replaceAll('_', ' ')}</strong>
                    <p>{departmentCopy[department] ?? 'Keep the weekly plan aligned with match-day priorities.'}</p>
                  </div>
                ))}
              </div>
            </section>

          </main>

          <aside className="command-home-rail" aria-label="Command readiness rail">
            <ProgramStatusStrip />

            <section className="dm-panel command-home-panel command-home-checklist">
              <div className="command-section-heading">
                <p className="dm-kicker">Pre-Game</p>
                <h3>Weekly Checklist</h3>
              </div>
              <div className="command-home-checklist-items">
                <div className={hasValidLineup ? 'is-ready' : 'is-pending'}>
                  <span>{hasValidLineup ? 'Ready' : 'Pending'}</span>
                  <strong>Lineup</strong>
                  <p>{starterNames.length > 0 ? starterNames.join(' - ') : plan.lineup?.summary ?? 'No lineup submitted.'}</p>
                </div>
                <div className={planConfirmed ? 'is-ready' : 'is-pending'}>
                  <span>{planConfirmed ? 'Ready' : 'Pending'}</span>
                  <strong>Plan Lock</strong>
                  <p>{planConfirmed ? 'Staff plan is confirmed.' : 'Confirm the staff plan before simulating.'}</p>
                </div>
                <div className={hasTactics ? 'is-ready' : 'is-pending'}>
                  <span>{hasTactics ? 'Ready' : 'Pending'}</span>
                  <strong>Tactics Prep</strong>
                  <p>{recommendations[0]?.text ?? 'Attach a tactical package before match day.'}</p>
                </div>
              </div>
              {!planConfirmed && (
                <ActionButton variant="accent" onClick={() => savePlan(selectedIntent, true)}>
                  Confirm Plan
                </ActionButton>
              )}
            </section>
          </aside>
        </div>

        <section
          ref={opponentFileRef}
          tabIndex={-1}
          className="dm-panel command-home-panel command-home-opponent-file"
        >
          <div className="command-section-heading">
            <p className="dm-kicker">Opponent File</p>
            <h3>Scouting read</h3>
          </div>
          <div className="command-home-scout-grid">
            <div>
              <span>Opponent record</span>
              <strong>{details.opponent_record}</strong>
            </div>
            <div>
              <span>Last meeting</span>
              <strong>{details.last_meeting}</strong>
            </div>
            <div>
              <span>Key matchup</span>
              <strong>{details.key_matchup}</strong>
            </div>
          </div>
          {details.key_matchup === 'Opponent file unavailable.' && (
            <p className="command-home-muted-note">Scouting file will populate after opponent tendencies are available.</p>
          )}
        </section>
      </div>
    );

    return renderCockpit();

  };

  const renderPostSimMode = () => {
    const activeResult = result ?? persistedResult;
    if (!activeResult?.aftermath) return (
      <div className="dm-panel">
        <p>Processing results...</p>
      </div>
    );

    const { aftermath } = activeResult;
    const matchId = activeResult.dashboard.match_id;
    const replayForMatch = replayData?.match_id === matchId ? replayData : null;
    const matchCardNames = aftermath.match_card
      ? resolveMatchCardNames({ matchCard: aftermath.match_card, currentData: data, activeResult })
      : null;

    return (
      <div className="command-post-sim" data-testid="post-week-dashboard">
        <PageHeader eyebrow="WAR ROOM" title="Match Week" description="Review the match result, replay identity, and weekly fallout." />
        
        {revealStage >= 0 && (
          <div className="command-reveal">
            <Headline text={aftermath.headline} />
          </div>
        )}

        {revealStage >= 1 && aftermath.match_card && matchCardNames && (
          <div className="command-reveal">
            <MatchScoreHero
              homeTeam={matchCardNames.homeTeam}
              awayTeam={matchCardNames.awayTeam}
              homeSurvivors={aftermath.match_card.home_survivors}
              awaySurvivors={aftermath.match_card.away_survivors}
              winnerClubId={aftermath.match_card.winner_club_id}
              homeClubId={aftermath.match_card.home_club_id}
            />
          </div>
        )}

        {revealStage >= 2 && (
          <div className="command-story-grid command-reveal" data-testid="command-story-grid">
            <ReplayTimeline lanes={activeResult.dashboard.lanes} />
            <div className="command-story-side">
              <KeyPlayersPanel performers={replayForMatch?.report.top_performers ?? []} />
              <TacticalSummaryCard
                turningPoint={replayForMatch?.report.turning_point ?? ''}
                evidenceLanes={replayForMatch?.report.evidence_lanes ?? activeResult.dashboard.lanes}
              />
            </div>
          </div>
        )}

        {revealStage >= 3 && (
          <div className="command-reveal">
            <FalloutGrid
              playerGrowth={aftermath.player_growth_deltas}
              standingsShift={aftermath.standings_shift}
              recruitReactions={aftermath.recruit_reactions}
            />
          </div>
        )}

        {revealStage >= 4 && (
          <div className="command-reveal">
            <AftermathActionBar
              onAdvance={handleAdvanceWeek}
              onViewReplay={onOpenReplay ? () => onOpenReplay(matchId) : undefined}
              matchId={matchId}
              isAdvancing={isAdvancingWeek}
            />
          </div>
        )}
      </div>
    );
  };

  if (isTransitioning) return <SimTransition onComplete={handleSimTransitionComplete} isFast={false} />;

  if (mode === 'offseason') return (
    <div data-testid="match-week-offseason" className={isAdvancingWeek ? 'fade-out' : ''}>
      <Offseason />
    </div>
  );
  if (mode === 'post-sim') return renderPostSimMode();
  return renderPreSimMode();
}
