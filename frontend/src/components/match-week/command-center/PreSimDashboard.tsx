import { useEffect, useMemo, useState } from 'react';
import { apiGet } from '../../../api/client';
import type {
  CommandCenterResponse,
  ScheduleResponse,
  ScheduleRow,
  StandingRow,
  StandingsResponse,
} from '../../../types';
import { WeeklyChecklist } from '../WeeklyChecklist';
import { MatchCard } from './MatchCard';

const approaches = [
  { id: 'Balanced', label: 'Balanced', desc: 'Even focus on offense and defense.' },
  { id: 'Win Now', label: 'Aggressive', desc: 'Higher pressure, higher foul/risk exposure.' },
  { id: 'Prepare For Playoffs', label: 'Control', desc: 'Slower tempo, better possession security.' },
  { id: 'Preserve Health', label: 'Defensive', desc: 'Lower throwing volume, stronger catch stability.' },
];

const intentLabels = new Map(approaches.map(approach => [approach.id, approach.label]));
const roleCounterMap: Record<string, string> = { Tactical: 'Control', Pressure: 'Defensive', Balanced: 'Balanced' };

function pct(value: number | undefined) {
  if (typeof value !== 'number') return 'n/a';
  return `${Math.round(value * 100)}%`;
}


function humanize(value: string | undefined) {
  if (!value) return 'Not set';
  const s = value.replaceAll('_', ' ').toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function formatEdge(value: number) {
  const rounded = Math.round(value * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

function parseKeyMatchup(raw: string) {
  const parts = raw.split(',').map(s => s.trim());
  if (parts.length >= 3) {
    const name = parts[0];
    const role = parts[1];
    const ovrMatch = parts[2].match(/(\d+)/);
    return { name, role, ovr: ovrMatch ? ovrMatch[1] : null };
  }
  return { name: raw, role: null, ovr: null };
}

function intentForRecommendation(recommendation: string) {
  if (recommendation === 'Control') return 'Prepare For Playoffs';
  if (recommendation === 'Defensive') return 'Preserve Health';
  return 'Balanced';
}

export function PreSimDashboard({
  data,
  simulate,
  onSavePlan,
  selectedIntent,
  onIntentChange,
  planConfirmed,
}: {
  data: CommandCenterResponse;
  simulate: () => void;
  onSavePlan: (intent: string, confirm: boolean) => void;
  selectedIntent: string;
  onIntentChange: (intent: string) => void;
  planConfirmed: boolean;
}) {
  const [standings, setStandings] = useState<StandingRow[]>([]);
  const [schedule, setSchedule] = useState<ScheduleRow[]>([]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      apiGet<StandingsResponse>('/api/standings'),
      apiGet<ScheduleResponse>('/api/schedule'),
    ])
      .then(([standingsPayload, schedulePayload]) => {
        if (cancelled) return;
        setStandings(standingsPayload.standings ?? []);
        setSchedule(schedulePayload.schedule ?? []);
      })
      .catch(() => {
        if (cancelled) return;
        setStandings([]);
        setSchedule([]);
      });
    return () => { cancelled = true; };
  }, [data.season_id]);

  const plan = data.plan;
  const details = plan.matchup_details ?? {
    opponent_record: 'Unknown',
    last_meeting: 'No meeting recorded',
    key_matchup: 'Opponent file unavailable.',
    framing_line: data.current_objective,
  };
  const activePlayers = useMemo(() => plan.lineup?.players?.slice(0, 6) ?? [], [plan.lineup?.players]);
  const opponentPlayers = useMemo(() => plan.opponent_lineup?.players?.slice(0, 6) ?? [], [plan.opponent_lineup?.players]);
  const userStanding = standings.find(row => row.club_id === data.player_club_id);
  const leagueRank = userStanding ? standings.findIndex(row => row.club_id === data.player_club_id) + 1 : null;
  const recentResults = data.history.slice(-5).map(record => record.dashboard?.result).filter(Boolean);
  const recentWins = recentResults.filter(result => result === 'Win').length;
  const recentRecord = recentResults.length ? `${recentWins}-${recentResults.length - recentWins}` : 'No recent matches';
  const latestDashboard = data.latest_dashboard;

  const readinessChecks = useMemo(() => [
    { id: 'scout', label: 'Opponent file available', shortLabel: 'Scout', detail: 'Scout report, threat profile, and staff recommendation available.', ready: Boolean(plan.matchup_details || plan.recommendations.length) },
    { id: 'gameplan', label: 'Command intent selected', shortLabel: 'Intent', detail: selectedIntent, ready: Boolean(selectedIntent) },
    { id: 'training', label: 'Training order saved', shortLabel: 'Training', detail: humanize(plan.department_orders?.training), ready: Boolean(plan.department_orders?.training) },
    { id: 'rotation', label: 'Playable rotation present', shortLabel: 'Rotation', detail: `${activePlayers.length} listed starters`, ready: activePlayers.length >= 6 },
    { id: 'health', label: 'Starter stamina checked', shortLabel: 'Health', detail: activePlayers.some(player => typeof player.stamina === 'number') ? `${Math.round(Math.min(...activePlayers.map(player => player.stamina ?? 100)))} minimum stamina` : 'No stamina warnings reported', ready: activePlayers.every(player => player.stamina === undefined || player.stamina >= 35) },
  ], [activePlayers, plan.department_orders?.training, plan.matchup_details, plan.recommendations.length, selectedIntent]);

  const readyCount = readinessChecks.filter(check => check.ready).length;
  const isReadyToLock = readyCount === readinessChecks.length;
  const itemsRemaining = readinessChecks.length - readyCount;
  const currentApproach = intentLabels.get(selectedIntent) ?? selectedIntent;
  const isAggressive = selectedIntent === 'Win Now';
  const isDefensive = selectedIntent === 'Preserve Health';
  const threat = parseKeyMatchup(details.key_matchup);
  const topOvr = activePlayers.length > 0 ? Math.max(...activePlayers.map(player => player.overall)) : 0;
  const topPlayer = activePlayers.find(player => player.overall === topOvr) ?? null;
  const ovrGap = threat.ovr ? parseInt(threat.ovr) - Math.round(topOvr) : null;
  const hasApproachConflict = selectedIntent === 'Win Now' && (threat.role === 'Tactical' || threat.role === 'Pressure');
  const counterApproach = threat.role ? (roleCounterMap[threat.role] ?? 'Control') : 'Control';
  const hasFatigueIssue = activePlayers.filter(player => player.stamina !== undefined && player.stamina < 60).length > 1;
  const hasPlanConflict = hasApproachConflict || hasFatigueIssue;
  const scoutGapRead = ovrGap !== null && topPlayer
    ? ovrGap > 0
      ? `Primary threat outrates ${topPlayer.name} by +${ovrGap} OVR. `
      : `${topPlayer.name} covers the primary threat by +${Math.abs(ovrGap)} OVR. `
    : '';
  const scoutRead = `${scoutGapRead}${hasApproachConflict ? `${currentApproach} approach is exposed vs ${threat.role} threat.` : hasFatigueIssue ? 'Starter fatigue lowers margin for error this week.' : 'Current approach aligns with the opponent profile.'}`;
  const planRead = hasApproachConflict ? `${currentApproach} is exposed vs ${threat.role} threat.` : hasFatigueIssue ? 'Starter fatigue is elevated.' : 'Current approach aligns with the opponent profile.';
  const recommendationLabel = hasPlanConflict ? `Adjust to ${hasFatigueIssue ? 'Defensive' : counterApproach}` : 'Keep current plan';

  const currentMatch = useMemo(
    () =>
      [...schedule]
        .sort((a, b) => a.week - b.week)
        .find(match => match.is_user_match && match.status !== 'played') ?? null,
    [schedule],
  );
  const displayWeek = currentMatch?.week ?? data.week;
  const playoffStage =
    currentMatch && currentMatch.stage && currentMatch.stage !== 'Regular Season'
      ? currentMatch.stage
      : null;
  const homeTeamName = currentMatch ? currentMatch.home_club_name : data.player_club_name;
  const awayTeamName = currentMatch ? currentMatch.away_club_name : plan.opponent.name;
  const yourStarterTotal = activePlayers.reduce((sum, player) => sum + player.overall, 0);
  const oppStarterTotal = opponentPlayers.reduce((sum, player) => sum + player.overall, 0);
  const netStarterEdge = Math.round((yourStarterTotal - oppStarterTotal) * 10) / 10;
  const playerEdgeLabel = netStarterEdge === 0 ? 'Even starter line' : `${data.player_club_name} ${netStarterEdge > 0 ? '+' : ''}${formatEdge(netStarterEdge)} net OVR`;
  const primaryActionLabel = planConfirmed ? 'SIMULATE WEEK' : 'LOCK PLAN';
  const primaryActionHint = planConfirmed ? 'The weekly plan is locked. Run the match when you are ready to move the season forward.' : isReadyToLock ? 'No blockers. Review the decision, then lock the plan.' : `${itemsRemaining} checklist item${itemsRemaining === 1 ? '' : 's'} still need attention before plan lock.`;
  const unresolvedIssue = !isReadyToLock ? readinessChecks.find(check => !check.ready)?.label ?? 'Review plan setup' : 'No blockers';

  return (
    <div className="command-dashboard" data-testid="weekly-command-center">
      <section className="command-filter-row" aria-label="Week context" data-testid="presim-command-strip">
        <div className="command-strip-meta">
          {playoffStage && <span className="command-strip-stage">{playoffStage}</span>}
          <span title="Upcoming match week">Week {displayWeek}</span>
          <span>{leagueRank ? `League Rank #${leagueRank}` : 'Rank n/a'}</span>
          <span title="Away team @ home team">{awayTeamName} @ {homeTeamName}</span>
          <span title="Opponent record">{details.opponent_record}</span>
          <span title="Your form over the last 5 games">{recentRecord}</span>
          <span title="Starter overall edge vs opponent">{playerEdgeLabel}</span>
        </div>
      </section>

      <section className="command-cockpit-grid" data-testid="plan-details-row">
        <article className="dm-panel command-cockpit-panel command-game-plan" data-testid="plan-editor-panel">
          <div className="command-panel-heading">
            <div>
              <p className="dm-kicker">Plan Editor</p>
              <h3>{currentApproach}</h3>
            </div>
            <div className="command-current-plan">
              <p>{isAggressive ? 'Pressure the weak side and accept higher exposure.' : isDefensive ? 'Protect stamina, lower risk, and win possessions.' : 'Keep the plan balanced across pressure, catches, and tempo.'}</p>
            </div>
          </div>

          {!planConfirmed && (
            <div className={`command-plan-alert ${hasPlanConflict ? 'is-warning' : 'is-fit'}`} data-testid="plan-readout">
              <div>
                <strong>{planRead}</strong>
                <span>{isAggressive ? 'High Risk' : isDefensive ? 'Low Risk' : 'Medium Risk'}</span>
              </div>
              {hasPlanConflict && (
                <button type="button" onClick={() => onIntentChange(intentForRecommendation(hasFatigueIssue ? 'Defensive' : counterApproach))}>
                  Apply {hasFatigueIssue ? 'Defensive' : counterApproach}
                </button>
              )}
            </div>
          )}

          <div className="command-plan-grid">
            <div className="command-approach-column">
              <p className="command-field-label">Tactical Approach</p>
              <div className="command-approach-grid">
                {approaches.map(option => (
                  <button key={option.id} type="button" disabled={planConfirmed} className={selectedIntent === option.id ? 'is-selected' : ''} onClick={() => { if (!planConfirmed) onIntentChange(option.id); }}>
                    <span>{option.label}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="command-priority-column">
              <p className="command-field-label">Tactical Profile</p>
              <div className="command-meter-stack">
                {[
                  { label: 'Target Stars', value: plan.tactics?.target_stars, tone: 'pressure' },
                  { label: 'Catch Bias', value: plan.tactics?.catch_bias, tone: 'control' },
                  { label: 'Risk', value: plan.tactics?.risk_tolerance, tone: 'risk' },
                  { label: 'Tempo', value: plan.tactics?.tempo, tone: 'tempo' },
                ].map(stat => (
                  <article key={stat.label} className={`command-meter-row is-${stat.tone}`}>
                    <span>{stat.label}</span>
                    <b><i style={{ width: pct(stat.value) }} /></b>
                    <strong>{pct(stat.value)}</strong>
                  </article>
                ))}
              </div>
            </div>
          </div>

          <div className="command-order-pills">
            <div><span>Training</span><strong>{humanize(plan.department_orders?.training)}</strong></div>
            <div><span>Development</span><strong>{humanize(plan.department_orders?.dev_focus)}</strong></div>
          </div>
        </article>

        <article id="command-opponent-file" className="dm-panel command-cockpit-panel command-intel-card" data-testid="scout-read-panel" tabIndex={-1}>
          <div className="command-panel-heading">
            <div>
              <p className="dm-kicker">Scout Read</p>
              <h3>{hasPlanConflict ? 'Adjustment advised' : 'Profile aligned'}</h3>
            </div>
          </div>

          <p className="command-overview-copy">{scoutRead}</p>

          <div className={`command-threat-row ${ovrGap !== null && ovrGap > 0 ? 'is-disadvantage' : ''}`}>
            <span>Key Threat</span>
            <strong>{threat.name}</strong>
            <div>{threat.role && <em>{threat.role}</em>}{threat.ovr && <b>{threat.ovr} OVR</b>}</div>
          </div>

          <div className="command-scout-response">
            <span>Recommendation</span>
            <strong>{recommendationLabel}</strong>
            {hasPlanConflict && !planConfirmed && <button type="button" onClick={() => onIntentChange(intentForRecommendation(hasFatigueIssue ? 'Defensive' : counterApproach))}>Apply</button>}
          </div>

          <div className="command-intel-summary-grid">
            <div><span>Starter Edge</span><strong>{playerEdgeLabel}</strong></div>
            <div><span>Last Meeting</span><strong>{details.last_meeting}</strong></div>
            <div><span>Match Note</span><strong>{latestDashboard?.lanes?.[1]?.summary ?? details.framing_line}</strong></div>
          </div>
        </article>

        <article className="dm-panel command-cockpit-panel command-control-tower" data-testid="readiness-panel">
          <div className="command-panel-heading">
            <div>
              <p className="dm-kicker">Week Lock Status</p>
              <h3>{planConfirmed ? 'Locked' : 'Ready to decide'}</h3>
            </div>
          </div>

          <div className="command-readiness-chips">
            {readinessChecks.map(check => (
              <span key={check.id} className={check.ready ? 'is-ready' : 'is-pending'} title={check.detail}>{check.ready ? 'OK' : '!'} {check.shortLabel}</span>
            ))}
          </div>

          <div className="command-decision-card">
            <div><span>Current Decision</span><strong>{currentApproach}</strong></div>
            <div><span>Risk</span><strong className={isAggressive ? 'is-warning' : isDefensive ? 'is-ready' : ''}>{isAggressive ? 'High' : isDefensive ? 'Low' : 'Medium'}</strong></div>
            <div><span>Readiness</span><strong>{readyCount}/{readinessChecks.length}</strong></div>
            <div><span>Recommendation</span><strong>{recommendationLabel}</strong></div>
            <div><span>Next Issue</span><strong>{unresolvedIssue}</strong></div>
          </div>

          <div className="command-control-squad">
            <div className="command-panel-heading"><div><p className="dm-kicker">Lineup Leverage</p></div></div>
            <MatchCard yourPlayers={activePlayers} oppPlayers={opponentPlayers} yourTeamName={data.player_club_name} oppTeamName={plan.opponent.name} compact maxVisibleRows={2} />
          </div>

          <p className="command-lock-note">{primaryActionHint}</p>
          <button
            type="button"
            data-testid={planConfirmed ? 'simulate-command-week' : 'lock-weekly-plan'}
            aria-label={planConfirmed ? 'Simulate Week' : 'Lock Plan'}
            onClick={() => { if (planConfirmed) { simulate(); return; } if (isReadyToLock) onSavePlan(selectedIntent, true); }}
            disabled={!planConfirmed && !isReadyToLock}
            className="command-primary-lock"
          >
            {primaryActionLabel}
          </button>
          {planConfirmed && <button type="button" onClick={() => onSavePlan(selectedIntent, false)} className="command-secondary-button">Unlock Plan</button>}
        </article>
      </section>

      <section className="command-secondary-rail" data-testid="secondary-intel-rail">
        <div className="command-secondary-body">
          <WeeklyChecklist plan={plan} onAcceptPlan={() => { if (isReadyToLock) onSavePlan(selectedIntent, true); }} planConfirmed={planConfirmed} showAction={false} bare />
        </div>
      </section>
    </div>
  );
}
