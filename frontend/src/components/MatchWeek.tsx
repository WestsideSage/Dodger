import { SimTransition } from './match-week/SimTransition';
import { Headline } from './match-week/aftermath/Headline';
import { MatchScoreHero } from './match-week/aftermath/MatchScoreHero';
import { FalloutGrid } from './match-week/aftermath/FalloutGrid';
import { AftermathActionBar } from './match-week/aftermath/AftermathActionBar';
import { ReplayTimeline } from './match-week/aftermath/ReplayTimeline';
import { KeyPlayersPanel } from './match-week/aftermath/KeyPlayersPanel';
import { TacticalSummaryCard } from './match-week/aftermath/TacticalSummaryCard';
import { PreSimDashboard } from './match-week/command-center/PreSimDashboard';
import { useState, useEffect } from 'react';
import type { Aftermath, CommandCenterResponse, CommandCenterSimResponse, MatchReplayResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { PageHeader, StatusMessage } from './ui';
import { Offseason } from './Offseason';
import { commandApi } from '../api/client';

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
  const opponentName = activeResult.dashboard.opponent_name ?? activeResult.plan.opponent.name ?? 'Opponent';
  const homeIsPlayer = matchCard.home_club_id === playerClubId;

  return {
    homeTeam: homeIsPlayer ? playerClubName : opponentName,
    awayTeam: homeIsPlayer ? opponentName : playerClubName,
  };
}

function buildContextLine(matchCard: Aftermath['match_card'] | undefined): string | undefined {
  if (!matchCard) return undefined;
  if (!matchCard.winner_club_id) return undefined;
  const homeWins = matchCard.winner_club_id === matchCard.home_club_id;
  const winnerSurvs = homeWins ? matchCard.home_survivors : matchCard.away_survivors;
  const loserSurvs = homeWins ? matchCard.away_survivors : matchCard.home_survivors;
  if (loserSurvs === 0) return `A ${winnerSurvs}–0 shutout that leaves no room for excuses.`;
  if (winnerSurvs >= loserSurvs * 2) return `A dominant ${winnerSurvs}–${loserSurvs} result.`;
  return `The final score: ${winnerSurvs}–${loserSurvs}.`;
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
  const [revealStage, setRevealStage] = useState(4);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isAdvancingWeek, setIsAdvancingWeek] = useState(false);
  const [planConfirmed, setPlanConfirmed] = useState(false);
  const [replayData, setReplayData] = useState<MatchReplayResponse | null>(null);

  const selectedIntent = localIntent ?? data?.plan.intent ?? 'Win Now';

  const load = (showLoading = false) => {
    if (showLoading) setLoading(true);
    return commandApi.center()
      .then((payload: CommandCenterResponse) => {
        setData(payload);
        setLocalIntent(undefined);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  };

  const savePlan = (intent = selectedIntent, confirm = false) => {
    setError(null);
    return commandApi.savePlan({ intent })
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
    commandApi.simulate({ intent: selectedIntent })
      .then((payload: CommandCenterSimResponse) => {
        setResult(payload);
        setRevealStage(4);
        setIsTransitioning(false);
        onSimComplete?.(payload);
        return load();
      })
      .catch(err => {
        setError(err.message);
        setIsTransitioning(false);
      });
  };

  const handleAdvanceWeek = () => {
    setIsAdvancingWeek(true);
    setRevealStage(4);
    setResult(null);
    setPlanConfirmed(false);
    load()
      .finally(() => {
        onAdvanceWeek?.();
        setIsAdvancingWeek(false);
      });
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
      if (e.type === 'click') {
        const target = e.target as Element | null;
        if (target?.closest('.dm-left-nav')) return;
      }
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
    commandApi.replay(matchId)
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

    const handleIntentChange = (intent: string) => {
      setLocalIntent(intent);
      setPlanConfirmed(false);
      savePlan(intent, false);
    };

    return (
      <PreSimDashboard
        data={data}
        simulate={simulate}
        onSavePlan={savePlan}
        selectedIntent={selectedIntent}
        onIntentChange={handleIntentChange}
        planConfirmed={planConfirmed}
      />
    );
  };

  const renderPostSimMode = () => {
    const activeResult = result ?? persistedResult;
    if (!activeResult?.aftermath) {
      return (
        <StatusMessage title="Processing results">
          Building the Command Center aftermath.
        </StatusMessage>
      );
    }

    const { aftermath } = activeResult;
    const matchId = activeResult.dashboard.match_id;
    const replayForMatch = replayData?.match_id === matchId ? replayData : null;
    const matchCardNames = aftermath.match_card
      ? resolveMatchCardNames({ matchCard: aftermath.match_card, currentData: data, activeResult })
      : null;

    return (
      <div className="command-post-sim" data-testid="post-week-dashboard">
        <PageHeader eyebrow="WAR ROOM" title={`Week ${activeResult.dashboard.week} Debrief`} />

        {revealStage >= 0 && (
          <div className="command-reveal">
            <Headline
              text={aftermath.headline}
              week={activeResult.dashboard.week}
              contextLine={buildContextLine(aftermath.match_card)}
            />
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
          <div className="command-reveal">
            <ReplayTimeline lanes={activeResult.dashboard.lanes} />
            <div className="command-analysis-row">
              <TacticalSummaryCard
                turningPoint={replayForMatch?.report.turning_point ?? ''}
                evidenceLanes={replayForMatch?.report.evidence_lanes ?? activeResult.dashboard.lanes}
              />
              <KeyPlayersPanel
                performers={replayForMatch?.report.top_performers ?? []}
                playerClubName={data?.player_club_name}
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

  if (mode === 'offseason') return (
    <div data-testid="match-week-offseason" className={isAdvancingWeek ? 'fade-out' : ''}>
      <Offseason />
    </div>
  );

  return (
    <div className="match-week-shell">
      {mode === 'post-sim' ? renderPostSimMode() : renderPreSimMode()}
      {isTransitioning && <SimTransition />}
    </div>
  );
}
