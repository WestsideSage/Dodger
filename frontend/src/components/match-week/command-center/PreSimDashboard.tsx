import { useEffect, useMemo, useState } from 'react';
import { apiGet } from '../../../api/client';
import type {
  CoachPolicy,
  CommandCenterResponse,
  ScheduleResponse,
  ScheduleRow,
  StandingRow,
  StandingsResponse,
} from '../../../types';
import { BroadcastFrameBlock } from '../../BroadcastFrameBlock';
import { PolicyEditor } from './PolicyEditor';
import { seasonTitle, bulletinLine, stakesLine, playerToWatch } from './presimNarrative';

const approaches = [
  { id: 'Balanced', label: 'Balanced', desc: 'Even focus on offense and defense.' },
  { id: 'Win Now', label: 'Aggressive', desc: 'Higher pressure, higher foul/risk exposure.' },
  { id: 'Prepare For Playoffs', label: 'Control', desc: 'Slower tempo, better possession security.' },
  { id: 'Preserve Health', label: 'Defensive', desc: 'Lower throwing volume, stronger catch stability.' },
];

const intentLabels = new Map(approaches.map(approach => [approach.id, approach.label]));
const roleCounterMap: Record<string, string> = { Tactical: 'Control', Pressure: 'Defensive', Balanced: 'Balanced' };
const DEV_FOCUS_OPTIONS = ['BALANCED', 'YOUTH_ACCELERATION', 'TACTICAL_DRILLS', 'STRENGTH_AND_CONDITIONING'];

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
  onSavePolicy,
  onSaveDevFocus,
  selectedIntent,
  onIntentChange,
  planConfirmed,
  saving = false,
}: {
  data: CommandCenterResponse;
  simulate: () => void;
  onSavePlan: (intent: string, confirm: boolean) => void;
  onSavePolicy: (policy: CoachPolicy) => Promise<void> | void;
  onSaveDevFocus: (devFocus: string) => void;
  selectedIntent: string;
  onIntentChange: (intent: string) => void;
  planConfirmed: boolean;
  saving?: boolean;
}) {
  const [standings, setStandings] = useState<StandingRow[]>([]);
  const [schedule, setSchedule] = useState<ScheduleRow[]>([]);
  const [policyEditorOpen, setPolicyEditorOpen] = useState(false);

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
    last_meeting: 'First meeting — no tape on them yet. Trust your reads.',
    key_matchup: 'Opponent file unavailable.',
    framing_line: data.current_objective,
    broadcast_frame: null,
  };
  const broadcastFrame = details.broadcast_frame ?? null;
  const activePlayers = useMemo(() => plan.lineup?.players?.slice(0, 6) ?? [], [plan.lineup?.players]);
  const opponentPlayers = useMemo(() => plan.opponent_lineup?.players?.slice(0, 6) ?? [], [plan.opponent_lineup?.players]);
  const policySummary = useMemo(() => [
    { label: 'Approach', value: humanize(plan.tactics?.approach) },
    { label: 'Target focus', value: humanize(plan.tactics?.target_focus) },
    { label: 'Catch posture', value: humanize(plan.tactics?.catch_posture) },
    { label: 'Opening commit', value: humanize(plan.tactics?.rush_commit) },
    { label: 'Opening target', value: humanize(plan.tactics?.rush_target) },
  ], [plan.tactics]);
  const userStanding = standings.find(row => row.club_id === data.player_club_id);
  const anyGamesPlayed = standings.some(row =>
    (row.wins ?? 0) + (row.losses ?? 0) + (row.draws ?? 0) > 0
  );
  const leagueRank = (userStanding && anyGamesPlayed)
    ? standings.findIndex(row => row.club_id === data.player_club_id) + 1
    : null;
  const recentResults = data.history
    .slice(-5)
    .map(record => record.dashboard?.result)
    .filter((result): result is string => Boolean(result));
  const recentWins = recentResults.filter(result => result === 'Win').length;
  const recentRecord = recentResults.length ? `${recentWins}-${recentResults.length - recentWins}` : 'No recent matches';
  const latestDashboard = data.latest_dashboard;
  const lastRecord = data.history.length > 0 ? data.history[data.history.length - 1] : null;
  const showLastMatch = !planConfirmed && lastRecord !== null && data.week > 1;
  const seasonName = seasonTitle(data.season_id);
  const bulletin = lastRecord ? bulletinLine(lastRecord, data.player_club_name) : null;
  const watchLine = playerToWatch(activePlayers);
  const isBye = Boolean(plan.is_bye);

  const readinessChecks = useMemo(() => [
    { id: 'scout', label: isBye ? 'Bye week - no scouting needed' : 'Opponent file available', shortLabel: 'Scout', detail: isBye ? 'No scouting needed for a bye week.' : 'Scout report, threat profile, and staff recommendation available.', ready: true },
    { id: 'gameplan', label: 'Command intent selected', shortLabel: 'Intent', detail: selectedIntent, ready: Boolean(selectedIntent) },
    { id: 'training', label: 'Training order saved', shortLabel: 'Training', detail: humanize(plan.department_orders?.training), ready: Boolean(plan.department_orders?.training) },
    { id: 'rotation', label: 'Playable rotation present', shortLabel: 'Rotation', detail: `${activePlayers.length} listed starters`, ready: activePlayers.length >= 6 },
    { id: 'health', label: 'Starter stamina checked', shortLabel: 'Health', detail: activePlayers.some(player => typeof player.stamina === 'number') ? `${Math.round(Math.min(...activePlayers.map(player => player.stamina ?? 100)))} minimum stamina` : 'No stamina warnings reported', ready: activePlayers.every(player => player.stamina === undefined || player.stamina >= 35) },
  ], [activePlayers, plan.department_orders?.training, selectedIntent, isBye]);

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
  const hasApproachConflict = !isBye && selectedIntent === 'Win Now' && (threat.role === 'Tactical' || threat.role === 'Pressure');
  const counterApproach = threat.role ? (roleCounterMap[threat.role] ?? 'Control') : 'Control';
  
  // Fatigue / stamina issue check
  const hasFatigueIssue = !isBye && activePlayers.filter(player => player.stamina !== undefined && player.stamina < 60).length > 1;
  const recommendedIntent = hasFatigueIssue ? 'Preserve Health' : intentForRecommendation(counterApproach);
  
  // Hides/resolves advice when currently matching (Item 12 & 15)
  const hasPlanConflict = !isBye && (hasApproachConflict || hasFatigueIssue) && selectedIntent !== recommendedIntent;
  
  const scoutGapRead = ovrGap !== null && topPlayer
    ? ovrGap > 0
      ? `Primary threat outrates ${topPlayer.name} by +${ovrGap} OVR. `
      : `${topPlayer.name} covers the primary threat by +${Math.abs(ovrGap)} OVR. `
    : '';
    
  // Low Starter Stamina copy alignment (Item 11)
  const staminaWarningText = 'Low Starter Stamina: multiple starters have low stamina ratings, which will cause them to tire quickly.';
  const staminaWarningShortText = 'Low Starter Stamina: multiple starters have low stamina ratings, which will cause them to tire quickly during the match.';

  const scoutRead = isBye
    ? 'This is a bye week. No opponent to scout. Use this time to rest players and plan training.'
    : hasPlanConflict
      ? `${scoutGapRead}${hasApproachConflict ? `${currentApproach} approach is exposed vs ${threat.role} threat.` : staminaWarningText}`
      : `${scoutGapRead}Current approach aligns with the opponent profile.`;
      
  const planRead = isBye
    ? 'Bye week.'
    : hasPlanConflict
      ? (hasApproachConflict ? `${currentApproach} is exposed vs ${threat.role} threat.` : staminaWarningShortText)
      : 'Current approach aligns with the opponent profile.';
      
  const recommendationLabel = isBye
    ? 'n/a'
    : hasPlanConflict ? `Adjust to ${hasFatigueIssue ? 'Defensive' : counterApproach}` : 'Keep current plan';

  const currentMatch = useMemo(
    () =>
      [...schedule]
        .sort((a, b) => a.week - b.week)
        .find(match => match.is_user_match && match.status !== 'played' && match.week === data.week) ?? null,
    [schedule, data.week],
  );
  const displayWeek = currentMatch?.week ?? data.week;
  const gamesRemaining = schedule.filter(match => match.is_user_match && match.status !== 'played').length;
  const stakes = stakesLine(leagueRank, gamesRemaining, recentResults);
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
  const primaryActionHint = planConfirmed
    ? 'The weekly plan is locked. Run the match when you are ready to move the season forward.'
    : isBye
    ? 'The plan is ready. Lock it to advance to the next week.'
    : isReadyToLock
    ? 'No blockers. Review the decision, then lock the plan.'
    : `${itemsRemaining} checklist item${itemsRemaining === 1 ? '' : 's'} still need attention before plan lock.`;
  const unresolvedIssue = !isReadyToLock ? readinessChecks.find(check => !check.ready)?.label ?? 'Review plan setup' : 'No blockers';

  return (
    <div className="command-dashboard" data-testid="weekly-command-center">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
      <section className="command-filter-row" aria-label="Week context" data-testid="presim-command-strip">
        <div className="command-strip-meta">
          {playoffStage && <span className="command-strip-stage">{playoffStage}</span>}
          <span style={{ color: '#f97316', fontWeight: 700 }} title="This season's storyline">
            {seasonName}
          </span>
          <span title="Upcoming match week">Week {displayWeek}</span>
          <span>{leagueRank ? `League Rank #${leagueRank}` : 'Rank n/a'}</span>
          {isBye ? (
            <span style={{ color: '#38bdf8', fontWeight: 600 }}>BYE WEEK</span>
          ) : (
            <>
              <span title="Away team @ home team">{awayTeamName} @ {homeTeamName}</span>
              <span title="Opponent record">{details.opponent_record}</span>
            </>
          )}
          <span title="Your form over the last 5 games">{recentRecord}</span>
          {!isBye && <span title="Starter overall edge vs opponent">{playerEdgeLabel}</span>}
        </div>
      </section>

      {showLastMatch && lastRecord && (
        <div
          data-testid="presim-last-match"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '0.35rem',
            padding: '0.55rem 0.85rem',
            background: '#0a1220',
            border: '1px solid #1e293b',
            borderRadius: '4px',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              flexWrap: 'wrap',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.7rem',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: '#64748b',
            }}
          >
            <span style={{ color: '#94a3b8', fontWeight: 700 }}>Last Match</span>
            <span
              style={{
                color:
                  lastRecord.dashboard.result === 'Win'
                    ? '#10b981'
                    : lastRecord.dashboard.result === 'Loss'
                    ? '#f43f5e'
                    : '#94a3b8',
                fontWeight: 700,
              }}
            >
              {lastRecord.dashboard.result}
            </span>
            <span>vs {lastRecord.dashboard.opponent_name}</span>
            <span style={{ color: '#475569' }}>
              · {intentLabels.get(lastRecord.intent) ?? lastRecord.intent} plan
            </span>
          </div>
          {bulletin && (
            <p style={{ margin: 0, fontSize: '0.78rem', color: '#94a3b8', lineHeight: 1.45 }}>
              {bulletin}
            </p>
          )}
        </div>
      )}

      {!planConfirmed && isBye && (
        <div
          data-testid="presim-this-week"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '0.3rem',
            padding: '0.55rem 0.85rem',
            background: '#0a1628',
            border: '1px solid #1e293b',
            borderLeft: '3px solid #38bdf8',
            borderRadius: '4px',
          }}
        >
          <p style={{ margin: 0, fontSize: '0.82rem', color: '#e2e8f0', lineHeight: 1.45 }}>
            <span
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '0.62rem',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                color: '#38bdf8',
                marginRight: '0.5rem',
              }}
            >
              This Week
            </span>
            Bye Week — no match. Confirm the plan to advance to next week.
          </p>
        </div>
      )}

      {!planConfirmed && !isBye && (
        <div
          data-testid="presim-this-week"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '0.3rem',
            padding: '0.55rem 0.85rem',
            background: '#0a1628',
            border: '1px solid #1e293b',
            borderLeft: '3px solid #f97316',
            borderRadius: '4px',
          }}
        >
          <p style={{ margin: 0, fontSize: '0.82rem', color: '#e2e8f0', lineHeight: 1.45 }}>
            <span
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '0.62rem',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                color: '#f97316',
                marginRight: '0.5rem',
              }}
            >
              This Week
            </span>
            {stakes}
          </p>
          {watchLine && (
            <p style={{ margin: 0, fontSize: '0.78rem', color: '#94a3b8', lineHeight: 1.45 }}>
              <span
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: '0.62rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  color: '#64748b',
                  marginRight: '0.5rem',
                }}
              >
                Watch
              </span>
              {watchLine}
            </p>
          )}
        </div>
      )}

      {!isBye && broadcastFrame && (
        <BroadcastFrameBlock frame={broadcastFrame} title="Broadcast Frame" compact />
      )}
      </div>

      <section className="command-cockpit-grid" data-testid="plan-details-row">
        <article className="dm-panel command-cockpit-panel command-game-plan" data-testid="plan-editor-panel">
          <div className="command-panel-heading">
            <div>
              <p className="dm-kicker">Plan Editor</p>
              <h3>{currentApproach}</h3>
              <p className="command-plan-subtitle">{isAggressive ? 'Pressure the weak side and accept higher exposure.' : isDefensive ? 'Protect stamina, lower risk, and win possessions.' : 'Keep the plan balanced across pressure, catches, and tempo.'}</p>
            </div>
          </div>

          {!planConfirmed && (
            <div className={`command-plan-alert ${hasPlanConflict ? 'is-warning' : 'is-fit'}`} data-testid="plan-readout">
              <div>
                <strong>{planRead}</strong>
                <span>{isAggressive ? 'High Risk' : isDefensive ? 'Low Risk' : 'Medium Risk'}</span>
              </div>
              {hasPlanConflict && (
                <button type="button" disabled={saving} onClick={() => onIntentChange(intentForRecommendation(hasFatigueIssue ? 'Defensive' : counterApproach))}>
                  Apply {hasFatigueIssue ? 'Defensive' : counterApproach}
                </button>
              )}
            </div>
          )}

          <div className="command-policy-summary">
            {policySummary.map(row => (
              <div key={row.label}>
                <span>{row.label}</span>
                <strong>{row.value}</strong>
              </div>
            ))}
          </div>

          {!planConfirmed && (
            <button
              type="button"
              className="command-policy-edit-trigger"
              onClick={() => setPolicyEditorOpen(true)}
              data-testid="open-policy-editor"
            >
              Edit Policy
            </button>
          )}

          <div className="command-order-pills">
            <div><span>Training</span><strong>{humanize(plan.department_orders?.training)}</strong></div>
            <div>
              <span>Development</span>
              {planConfirmed ? (
                <strong>{humanize(plan.department_orders?.dev_focus)}</strong>
              ) : (
                <select
                  data-testid="dev-focus-select"
                  aria-label="Development focus"
                  value={plan.department_orders?.dev_focus ?? 'BALANCED'}
                  onChange={event => onSaveDevFocus(event.target.value)}
                  style={{
                    background: '#0f172a',
                    border: '1px solid #334155',
                    borderRadius: '4px',
                    color: '#22d3ee',
                    fontFamily: 'var(--font-display)',
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    padding: '0.15rem 0.3rem',
                    cursor: 'pointer',
                  }}
                >
                  {DEV_FOCUS_OPTIONS.map(option => (
                    <option key={option} value={option}>{humanize(option)}</option>
                  ))}
                </select>
              )}
            </div>
          </div>
        </article>

        <article id="command-opponent-file" className="dm-panel command-cockpit-panel command-intel-card" data-testid="scout-read-panel" tabIndex={-1}>
          <div className="command-panel-heading">
            <div>
              <p className="dm-kicker">Scout Read</p>
              <h3>{hasPlanConflict ? 'Adjustment advised' : 'Profile aligned'}</h3>
            </div>
          </div>

          <p className="command-overview-copy" title={scoutRead}>{scoutRead}</p>

          <div className={`command-threat-row ${ovrGap !== null && ovrGap > 0 ? 'is-disadvantage' : ''}`}>
            <span>Key Threat</span>
            <strong>{threat.name}</strong>
            <div>{threat.role && <em>{threat.role}</em>}{threat.ovr && <b>{threat.ovr} OVR</b>}</div>
          </div>

          <div className="command-scout-response">
            <span>Recommendation</span>
            <strong>{recommendationLabel}</strong>
            {hasPlanConflict && !planConfirmed && recommendationLabel !== currentApproach && (
              <button type="button" disabled={saving} onClick={() => onIntentChange(intentForRecommendation(hasFatigueIssue ? 'Defensive' : counterApproach))}>Apply</button>
            )}
          </div>

          <div className="command-intel-summary-grid">
            <div><span>Starter Edge</span><strong>{playerEdgeLabel}</strong></div>
            <div><span>Last Meeting</span><strong>{details.last_meeting}</strong></div>
            <div><span>Match Note</span><strong title={latestDashboard?.lanes?.[1]?.summary ?? details.framing_line}>{latestDashboard?.lanes?.[1]?.summary ?? details.framing_line}</strong></div>
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

          <p className="command-lock-note">{primaryActionHint}</p>
          <button
            type="button"
            data-testid={planConfirmed ? 'simulate-command-week' : 'lock-weekly-plan'}
            aria-label={planConfirmed ? 'Simulate Week' : 'Lock Plan'}
            onClick={() => { if (planConfirmed) { simulate(); return; } if (isReadyToLock) onSavePlan(selectedIntent, true); }}
            disabled={(!planConfirmed && !isReadyToLock) || saving}
            className="command-primary-lock"
          >
            {saving ? 'Processing...' : primaryActionLabel}
          </button>
          {planConfirmed && <button type="button" disabled={saving} onClick={() => onSavePlan(selectedIntent, false)} className="command-secondary-button">Unlock Plan</button>}
        </article>
      </section>


      {policyEditorOpen && (
        <div
          className="command-policy-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Edit policy"
          onClick={() => setPolicyEditorOpen(false)}
          data-testid="policy-editor-overlay"
        >
          <div className="command-policy-overlay-body" onClick={event => event.stopPropagation()}>
            <button
              type="button"
              className="command-policy-overlay-close"
              onClick={() => setPolicyEditorOpen(false)}
              aria-label="Close policy editor"
            >
              Close
            </button>
            <PolicyEditor policy={plan.tactics} disabled={planConfirmed} onChange={onSavePolicy} error={null} />
          </div>
        </div>
      )}
    </div>
  );
}
