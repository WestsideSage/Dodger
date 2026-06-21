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
import { ManagerLessonCard } from './match-week/aftermath/ManagerLessonCard';
import { PreSimDashboard } from './match-week/command-center/PreSimDashboard';
import { SeasonPreview } from './match-week/command-center/SeasonPreview';
import { formatScoreline } from './match-week/matchResult';
import { useState, useEffect } from 'react';
import type { Aftermath, CommandCenterResponse, CommandCenterSimResponse, FastForwardStopPoint, MatchReplayResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { StatusMessage } from '../ui';
import { NAV_RAIL_ATTR } from './shell/appContracts';
import css from './MatchWeek.module.css';
import chrome from './chrome.module.css';

/**
 * Pure helper: returns true if the click target is inside the nav rail —
 * the reveal-skip handler ignores those clicks so navigating does not
 * fast-forward the aftermath reveal. This is the P1↔P2 DOM contract
 * (rewritten from the stale `closest('.dm-left-nav')` no-op to the
 * Phase-1 published `[data-nav-rail]`).
 */
// eslint-disable-next-line react-refresh/only-export-components
export function isNavClick(target: Element | null, navRailAttr: string): boolean {
  return !!target?.closest('[' + navRailAttr + ']');
}
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
  // Official matches score on game points (set wins). The legacy survivor count
  // is not the result and, on a multi-game official match, can contradict it
  // (e.g. a 0-0 foam draw whose box-score reads 0-3 survivors). Always phrase
  // the line in the scoring model's own scale via the shared scoreline.
  const scoreline = formatScoreline(matchCard);
  const isOfficial = scoreline.isOfficial;
  const homeScore = scoreline.home.value;
  const awayScore = scoreline.away.value;
  const sweepNoun = isOfficial ? 'sweep' : 'shutout';
  if (!matchCard.winner_club_id) {
    return isOfficial
      ? `A drawn result: ${homeScore}–${awayScore} on game points.`
      : `A drawn result: ${homeScore}–${awayScore}.`;
  }
  const homeWins = matchCard.winner_club_id === matchCard.home_club_id;
  const winnerScore = homeWins ? homeScore : awayScore;
  const loserScore = homeWins ? awayScore : homeScore;
  const playerWon = playerClubId != null && matchCard.winner_club_id === playerClubId;
  if (playerWon) {
    if (loserScore === 0) return `A ${winnerScore}–0 ${sweepNoun} that leaves no room for excuses.`;
    if (winnerScore >= loserScore * 2) return `A dominant ${winnerScore}–${loserScore} win.`;
    return `A hard-fought ${winnerScore}–${loserScore} win.`;
  }
  // Player perspective on a loss: their score first.
  if (loserScore === 0) return `A ${loserScore}–${winnerScore} ${sweepNoun} loss with nowhere to hide.`;
  if (winnerScore >= loserScore * 2) return `A chastening ${loserScore}–${winnerScore} defeat.`;
  return `A narrow ${loserScore}–${winnerScore} defeat.`;
}

type AftermathParagraph = Aftermath['body'][number];

// Groups the audience-tagged body paragraphs (YOU / THEM / RESULT) into
// distinct lanes instead of one undifferentiated flat list, so the tactical
// narrative reads as "your story / their story / the result" (Brief 4.4,
// criterion #4).
// Color discipline: YOU = Volt (your team = live/primary); THEM = neutral
// (no special role); RESULT = --ok (positive confirmation). No raw hex/rgba.
function AftermathBody({ body }: { body: AftermathParagraph[] }) {
  const groups = [
    { audience: 'you' as const, label: 'YOUR SIDE', sectionClass: css.audienceSectionYou, kickerClass: css.audienceKickerYou },
    { audience: 'them' as const, label: 'THEIR SIDE', sectionClass: css.audienceSectionThem, kickerClass: css.audienceKickerThem },
    { audience: 'result' as const, label: 'THE RESULT', sectionClass: css.audienceSectionResult, kickerClass: css.audienceKickerResult },
  ];
  return (
    <div className={css.bodyStack}>
      {groups.map((group) => {
        const items = body.filter((p) => p.audience === group.audience);
        if (items.length === 0) return null;
        return (
          <section
            key={group.audience}
            aria-label={group.label}
            className={`${css.audienceSection} ${group.sectionClass}`}
          >
            <p className={`${css.audienceKicker} ${group.kickerClass}`}>
              {group.label}
            </p>
            <div className={css.audienceItems}>
              {items.map((paragraph, index) => (
                <p
                  key={`${group.audience}-${index}-${paragraph.text.slice(0, 12)}`}
                  data-testid="aftermath-body-paragraph"
                  className={css.audienceParagraph}
                >
                  {paragraph.text}
                </p>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

export function MatchWeek({
  mode,
  onOpenReplay,
  persistedResult,
  onSimComplete,
  onAdvanceWeek,
  onOffseasonBeatChange,
  onPlanWeek,
}: {
  onOpenReplay?: (matchId: string) => void;
  mode: MatchWeekMode;
  persistedResult?: CommandCenterSimResponse | null;
  onSimComplete?: (result: CommandCenterSimResponse) => void;
  onAdvanceWeek?: () => void;
  onOffseasonBeatChange?: (title: string | null) => void;
  /** Codex issue 9: the banner must show the week being PLANNED. On bye
      weeks the career cursor already points at the next match week, so the
      shell needs the plan's own week to stay consistent with the panels. */
  onPlanWeek?: (week: number) => void;
}) {
  const { data, setData, error, setError, loading, setLoading } = useApiResource<CommandCenterResponse>('/api/command-center');
  const [localIntent, setLocalIntent] = useState<string | undefined>(undefined);
  const [result, setResult] = useState<CommandCenterSimResponse | null>(null);
  const [revealStage, setRevealStage] = useState(4);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isAdvancingWeek, setIsAdvancingWeek] = useState(false);
  const [planConfirmed, setPlanConfirmed] = useState(false);
  const [replayData, setReplayData] = useState<MatchReplayResponse | null>(null);
  const [previewDismissed, setPreviewDismissed] = useState(false);

  const selectedIntent = localIntent ?? data?.plan.intent ?? 'Balanced';

  useEffect(() => {
    if (mode === 'pre-sim' && typeof data?.week === 'number') onPlanWeek?.(data.week);
  }, [data?.week, mode, onPlanWeek]);

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

  const handleSkipPreviewChange = (skipped: boolean) => {
    commandApi.skipSeasonPreview(skipped)
      .then((payload: CommandCenterResponse) => setData(payload))
      .catch(err => setError(err.message));
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

  const scoutOpponent = () => {
    setError(null);
    setSaving(true);
    commandApi.scoutOpponent()
      .then((payload: CommandCenterResponse) => setData(payload))
      .catch(err => setError(err.message))
      .finally(() => setSaving(false));
  };

  const confirmLineup = () => {
    setError(null);
    setSaving(true);
    commandApi.confirmLineup()
      .then((payload: CommandCenterResponse) => setData(payload))
      .catch(err => setError(err.message))
      .finally(() => setSaving(false));
  };

  const fastForward = (stopPoint?: FastForwardStopPoint) => {
    setError(null);
    setIsTransitioning(true);
    setSaving(true);
    commandApi.fastForward(stopPoint ? { stop_point: stopPoint } : {})
      .then(() => {
        setIsTransitioning(false);
        return load();
      })
      .then(() => {
        onAdvanceWeek?.();
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
        if (isNavClick(target, NAV_RAIL_ATTR)) return;
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

    if (data.season_preview && !data.season_preview.skipped && !previewDismissed) {
      return (
        <SeasonPreview
          preview={data.season_preview}
          onContinue={() => setPreviewDismissed(true)}
          onSkipChange={handleSkipPreviewChange}
        />
      );
    }

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
        fastForward={fastForward}
        onScout={scoutOpponent}
        onConfirmLineup={confirmLineup}
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
    const isBye = Boolean(aftermath.bye_recovery);
    const matchId = activeResult.dashboard.match_id;
    const replayForMatch = replayData?.match_id === matchId ? replayData : null;
    const matchCardNames = aftermath.match_card
      ? resolveMatchCardNames({ matchCard: aftermath.match_card, currentData: data, activeResult })
      : null;

    return (
      <div className={chrome.postSim} data-testid="post-week-dashboard">
        {aftermath.championship && <ChampionshipHero championship={aftermath.championship} />}
        {aftermath.playoff_resolution && aftermath.playoff_resolution.decided_by !== 'regulation' && (
          <PlayoffResolutionBanner resolution={aftermath.playoff_resolution} />
        )}
        {revealStage >= 0 && (
          <div className={chrome.reveal}>
            <Headline
              text={aftermath.headline}
              week={activeResult.dashboard.week}
              stage={activeResult.dashboard.stage}
              kicker={isBye ? 'Bye Week' : undefined}
              subLabel={isBye ? 'Rest Report' : undefined}
              accent={isBye ? 'bye' : undefined}
              contextLine={
                isBye
                  ? undefined
                  : buildContextLine(
                      aftermath.match_card,
                      data?.player_club_id ?? activeResult.plan.player_club_id,
                    )
              }
            />
          </div>
        )}

        {/* Bye week: lead with the no-match story instead of a match the squad
            never played (Brief 4.3, primary hierarchy + criterion #2). No
            fatigue/recovery system exists — stamina is a fixed rating — so the
            card must not claim anyone "rested" or "recovered". */}
        {revealStage >= 1 && isBye && aftermath.bye_recovery && (
          <div className={chrome.reveal}>
            <section
              aria-labelledby="bye-recovery-heading"
              className={css.byeCard}
            >
              <p className={`${chrome.dmKicker} ${css.byeKicker}`}>Bye Week</p>
              <h3 id="bye-recovery-heading" className={css.byeHeading}>
                {aftermath.bye_recovery.summary}
              </h3>
              {aftermath.bye_recovery.players.length > 0 && (
                <>
                  <p className={css.byeListLabel}>
                    Recovered this week
                  </p>
                  <ul className={css.byePlayerList}>
                    {aftermath.bye_recovery.players.map((name) => (
                      <li key={name} className={css.byePlayerChip}>
                        <span aria-hidden="true" className={css.byePlayerChipDot}>✦</span>
                        {name}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </section>
          </div>
        )}

        {revealStage >= 1 && aftermath.match_card && matchCardNames && (
          <div className={chrome.reveal}>
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
              games={aftermath.match_card.games}
              isPlayoff={Boolean(aftermath.playoff_resolution)}
            />
            {/* The verdict is a fallback explanation only — when primary_factor
                is present it is the canonical "why", so the verdict is not
                rendered at full weight alongside it (Brief 4.4, criterion #6).
                Color discipline: Win = Volt (live/primary); Loss = --out
                (dim/extinguished, NOT red); Draw = neutral (--line2). */}
            {!aftermath.primary_factor && aftermath.verdict && (
              <p
                data-testid="match-verdict"
                className={`${css.verdict} ${
                  activeResult.dashboard.result === 'Win'
                    ? css.verdictWin
                    : activeResult.dashboard.result === 'Loss'
                      ? css.verdictLoss
                      : css.verdictDraw
                }`}
              >
                {aftermath.verdict}
              </p>
            )}
            {aftermath.primary_factor && <PrimaryFactorCard factor={aftermath.primary_factor} />}
            {aftermath.manager_lesson && <ManagerLessonCard lesson={aftermath.manager_lesson} />}
            {aftermath.body.length > 0 && (
              <AftermathBody body={aftermath.body} />
            )}
          </div>
        )}

        {revealStage >= 2 && !isBye && (
          <div className={chrome.reveal}>
            <div className={chrome.analysisRow}>
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
          <div className={chrome.reveal}>
            <FalloutGrid
              byeRecovery={aftermath.bye_recovery}
              developmentFeedback={aftermath.development_feedback}
              playerGrowth={aftermath.player_growth_deltas}
              standingsShift={aftermath.standings_shift}
              recruitReactions={aftermath.recruit_reactions}
            />
            {/* The replay timeline is a match-engine drill-down; a bye has no
                beats or moments, so it's skipped rather than rendered as an
                empty collapsed shell (Brief 4.3, criterion #1). */}
            {!isBye && (
              <ReplayTimeline
                replay={replayForMatch}
                lanes={activeResult.dashboard.lanes}
                narrativeBeats={aftermath.narrative_beats}
                isBye={false}
              />
            )}
            {aftermath.improvement_panel && aftermath.improvement_panel.length > 0 && (
              <NextBestImprovementPanel panel={aftermath.improvement_panel} />
            )}
          </div>
        )}

        {revealStage >= 4 && (
          <div className={chrome.reveal}>
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
