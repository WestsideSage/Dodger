import { SimTransition } from './match-week/SimTransition';
import { Headline } from './match-week/aftermath/Headline';
import { PlayoffResolutionBanner } from './match-week/aftermath/PlayoffResolutionBanner';
import { EliminationCeremony } from './match-week/aftermath/EliminationCeremony';
import { ChampionshipHero } from './match-week/aftermath/ChampionshipHero';
import { NextBestImprovementPanel } from './match-week/aftermath/NextBestImprovementPanel';
import { MatchScoreHero } from './match-week/aftermath/MatchScoreHero';
import { FalloutGrid } from './match-week/aftermath/FalloutGrid';
import { AftermathActionBar } from './match-week/aftermath/AftermathActionBar';
import { ReplayTimeline } from './match-week/aftermath/ReplayTimeline';
import { KeyPlayersPanel } from './match-week/aftermath/KeyPlayersPanel';
import { TacticalSummaryCard } from './match-week/aftermath/TacticalSummaryCard';
import { PrimaryFactorCard } from './match-week/aftermath/PrimaryFactorCard';
import { PreSimDashboard } from './match-week/command-center/PreSimDashboard';
import { useState, useEffect } from 'react';
import type { Aftermath, CommandCenterResponse, CommandCenterSimResponse, MatchReplayResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { StatusMessage } from './ui';
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

function buildContextLine(
  matchCard: Aftermath['match_card'] | undefined,
  playerClubId: string | undefined,
): string | undefined {
  if (!matchCard) return undefined;
  if (!matchCard.winner_club_id) {
    return `A drawn result: ${matchCard.home_survivors}–${matchCard.away_survivors}.`;
  }
  const homeWins = matchCard.winner_club_id === matchCard.home_club_id;
  const winnerSurvs = homeWins ? matchCard.home_survivors : matchCard.away_survivors;
  const loserSurvs = homeWins ? matchCard.away_survivors : matchCard.home_survivors;
  const playerWon = playerClubId != null && matchCard.winner_club_id === playerClubId;
  if (playerWon) {
    if (loserSurvs === 0) return `A ${winnerSurvs}–0 shutout that leaves no room for excuses.`;
    if (winnerSurvs >= loserSurvs * 2) return `A dominant ${winnerSurvs}–${loserSurvs} win.`;
    return `A hard-fought ${winnerSurvs}–${loserSurvs} win.`;
  }
  // Player perspective on a loss: their survivors first.
  if (loserSurvs === 0) return `A ${loserSurvs}–${winnerSurvs} shutout loss with nowhere to hide.`;
  if (winnerSurvs >= loserSurvs * 2) return `A chastening ${loserSurvs}–${winnerSurvs} defeat.`;
  return `A narrow ${loserSurvs}–${winnerSurvs} defeat.`;
}

export function MatchWeek({
  mode,
  onOpenReplay,
  persistedResult,
  onSimComplete,
  onAdvanceWeek,
  onOffseasonBeatChange,
}: {
  onOpenReplay?: (matchId: string) => void;
  mode: MatchWeekMode;
  persistedResult?: CommandCenterSimResponse | null;
  onSimComplete?: (result: CommandCenterSimResponse) => void;
  onAdvanceWeek?: () => void;
  onOffseasonBeatChange?: (title: string | null) => void;
}) {
  const { data, setData, error, setError, loading, setLoading } = useApiResource<CommandCenterResponse>('/api/command-center');
  const [localIntent, setLocalIntent] = useState<string | undefined>(undefined);
  const [result, setResult] = useState<CommandCenterSimResponse | null>(null);
  const [revealStage, setRevealStage] = useState(4);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isAdvancingWeek, setIsAdvancingWeek] = useState(false);
  const [planConfirmed, setPlanConfirmed] = useState(false);
  const [replayData, setReplayData] = useState<MatchReplayResponse | null>(null);

  const selectedIntent = localIntent ?? data?.plan.intent ?? 'Balanced';

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

  const [saving, setSaving] = useState(false);

  const savePlan = (intent = selectedIntent, confirm = false) => {
    setError(null);
    setSaving(true);
    return commandApi.savePlan({ intent })
      .then((payload: CommandCenterResponse) => {
        setData(payload);
        setLocalIntent(undefined);
        setPlanConfirmed(confirm);
      })
      .catch(err => setError(err.message))
      .finally(() => setSaving(false));
  };

  const savePolicy = async (policy: CommandCenterResponse['plan']['tactics']) => {
    if (!data) return;
    const previousPlan = data.plan;
    setError(null);
    setSaving(true);
    setData({
      ...data,
      plan: {
        ...data.plan,
        tactics: policy,
      },
    });
    try {
      const payload = await commandApi.savePlan({ intent: selectedIntent, tactics: policy });
      setData(payload);
      setLocalIntent(undefined);
    } catch (err) {
      setData({ ...data, plan: previousPlan });
      const message = err instanceof Error ? err.message : 'Unable to save policy.';
      setError(message);
      throw err;
    } finally {
      setSaving(false);
    }
  };

  const saveDevFocus = (devFocus: string) => {
    setError(null);
    setSaving(true);
    return commandApi.savePlan({ intent: selectedIntent, department_orders: { dev_focus: devFocus } })
      .then((payload: CommandCenterResponse) => {
        setData(payload);
        setLocalIntent(undefined);
      })
      .catch(err => setError(err.message))
      .finally(() => setSaving(false));
  };

  const simulate = () => {
    setError(null);
    setIsTransitioning(true);
    setSaving(true);
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
      })
      .finally(() => setSaving(false));
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
        onSavePolicy={savePolicy}
        onSaveDevFocus={saveDevFocus}
        selectedIntent={selectedIntent}
        onIntentChange={handleIntentChange}
        planConfirmed={planConfirmed}
        saving={saving}
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
        {aftermath.championship && <ChampionshipHero championship={aftermath.championship} />}
        {aftermath.playoff_resolution && aftermath.playoff_resolution.decided_by !== 'regulation' && (
          <PlayoffResolutionBanner resolution={aftermath.playoff_resolution} />
        )}
        {revealStage >= 0 && (
          <div className="command-reveal">
            <Headline
              text={aftermath.headline}
              week={activeResult.dashboard.week}
              stage={activeResult.dashboard.stage}
              contextLine={buildContextLine(
                aftermath.match_card,
                data?.player_club_id ?? activeResult.plan.player_club_id,
              )}
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
              scoringModel={aftermath.match_card.scoring_model}
              homeGamePoints={aftermath.match_card.home_game_points}
              awayGamePoints={aftermath.match_card.away_game_points}
            />
            {aftermath.verdict && (
              <p
                data-testid="match-verdict"
                style={{
                  margin: '12px 0 0',
                  padding: '10px 14px',
                  fontFamily: 'Oswald, sans-serif',
                  fontSize: '0.95rem',
                  letterSpacing: '0.3px',
                  color: '#e2e8f0',
                  background: '#0f172a',
                  border: '1px solid #1e293b',
                  borderLeft: `3px solid ${
                    activeResult.dashboard.result === 'Win'
                      ? '#10b981'
                      : activeResult.dashboard.result === 'Loss'
                        ? '#f43f5e'
                        : '#64748b'
                  }`,
                  borderRadius: '4px',
                }}
              >
                {aftermath.verdict}
              </p>
            )}
            {aftermath.primary_factor && <PrimaryFactorCard factor={aftermath.primary_factor} />}
            {aftermath.body.length > 0 && (
              <div style={{ display: 'grid', gap: '0.65rem', marginBottom: '1.5rem' }}>
                {aftermath.body.map((paragraph, index) => {
                  const label = paragraph.audience === 'you' ? 'YOU' : paragraph.audience === 'them' ? 'THEM' : 'RESULT';
                  const tone = paragraph.audience === 'you' ? 'accent' : paragraph.audience === 'them' ? 'warning' : 'success';

                  const badgeColor = tone === 'accent' ? '#22d3ee' : tone === 'warning' ? '#f59e0b' : '#10b981';
                  const badgeBg = tone === 'accent' ? 'rgba(34,211,238,0.1)' : tone === 'warning' ? 'rgba(245,158,11,0.1)' : 'rgba(16,185,129,0.1)';
                  const badgeBorder = tone === 'accent' ? 'rgba(34,211,238,0.3)' : tone === 'warning' ? 'rgba(245,158,11,0.3)' : 'rgba(16,185,129,0.3)';

                  return (
                    <p
                      key={`${index}-${paragraph.text.slice(0, 12)}`}
                      data-testid="aftermath-body-paragraph"
                      style={{
                        margin: 0,
                        padding: '0.7rem 0.85rem',
                        background: '#08101f',
                        border: '1px solid #1e293b',
                        borderRadius: '4px',
                        color: '#cbd5e1',
                        lineHeight: 1.5,
                        fontSize: '0.82rem',
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '0.75rem',
                      }}
                    >
                      <span style={{
                        fontSize: '0.625rem',
                        fontFamily: 'var(--font-mono-data)',
                        fontWeight: 900,
                        letterSpacing: '0.05em',
                        color: badgeColor,
                        background: badgeBg,
                        border: `1px solid ${badgeBorder}`,
                        padding: '0.1rem 0.35rem',
                        borderRadius: '3px',
                        flexShrink: 0,
                        marginTop: '0.1rem',
                        userSelect: 'none',
                      }}>
                        {label}
                      </span>
                      <span style={{ flex: 1 }}>{paragraph.text}</span>
                    </p>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {revealStage >= 2 && (
          <div className="command-reveal">
            <div className="command-analysis-row">
              <TacticalSummaryCard
                turningPoint={replayForMatch?.report.turning_point ?? ''}
                evidenceLanes={replayForMatch?.report.evidence_lanes ?? activeResult.dashboard.lanes}
              />
              <KeyPlayersPanel
                performers={replayForMatch?.report.top_performers ?? aftermath.top_performers ?? []}
                playerClubName={data?.player_club_name}
              />
            </div>
          </div>
        )}

        {revealStage >= 3 && (
          <div className="command-reveal">
            <FalloutGrid
              byeRecovery={aftermath.bye_recovery}
              developmentFeedback={aftermath.development_feedback}
              playerGrowth={aftermath.player_growth_deltas}
              standingsShift={aftermath.standings_shift}
              recruitReactions={aftermath.recruit_reactions}
            />
            <ReplayTimeline
              replay={replayForMatch}
              lanes={activeResult.dashboard.lanes}
              narrativeBeats={aftermath.narrative_beats}
              isBye={Boolean(aftermath.bye_recovery)}
            />
            {aftermath.improvement_panel && aftermath.improvement_panel.length > 0 && (
              <NextBestImprovementPanel panel={aftermath.improvement_panel} />
            )}
          </div>
        )}

        {revealStage >= 4 && (
          <div className="command-reveal">
            {aftermath.elimination ? (
              <EliminationCeremony
                elimination={aftermath.elimination}
                onContinue={handleAdvanceWeek}
                isAdvancing={isAdvancingWeek}
              />
            ) : (
              <AftermathActionBar
                onAdvance={handleAdvanceWeek}
                onViewReplay={onOpenReplay ? () => onOpenReplay(matchId) : undefined}
                matchId={matchId}
                result={activeResult.dashboard.result}
                isAdvancing={isAdvancingWeek}
              />
            )}
          </div>
        )}
      </div>
    );
  };

  if (mode === 'offseason') return (
    <div data-testid="match-week-offseason" className={isAdvancingWeek ? 'fade-out' : ''}>
      <Offseason onBeatChange={onOffseasonBeatChange} />
    </div>
  );

  return (
    <div className="match-week-shell">
      {mode === 'post-sim' ? renderPostSimMode() : renderPreSimMode()}
      {isTransitioning && <SimTransition />}
    </div>
  );
}
