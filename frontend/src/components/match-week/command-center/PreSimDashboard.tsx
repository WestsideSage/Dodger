import { useEffect, useMemo, useState } from 'react';
import { apiGet } from '../../../api/client';
import type {
  CoachPolicy,
  CommandCenterResponse,
  LineupPlayer,
  ScheduleResponse,
  ScheduleRow,
  StandingRow,
  StandingsResponse,
} from '../../../types';
import { PolicyEditor } from './PolicyEditor';
import { seasonTitle, stakesLine, playerToWatch } from './presimNarrative';

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

function playerAbbrev(name: string) {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return `${parts[0][0].toUpperCase()}.${parts[parts.length - 1].substring(0, 4).toUpperCase()}`;
  }
  return name.substring(0, 5).toUpperCase();
}

const HOME_POS: [number, number][] = [[40,40],[40,90],[40,140],[100,55],[100,125],[150,90]];
const AWAY_POS: [number, number][] = [[220,45],[220,135],[270,90],[320,40],[320,90],[320,140]];

function MiniCourt({
  homePlayers,
  awayPlayers,
  threatName,
}: {
  homePlayers: LineupPlayer[];
  awayPlayers: LineupPlayer[];
  threatName: string | null;
}) {
  const threatIdx = useMemo(() => {
    if (!threatName) return awayPlayers.length > 2 ? 2 : -1;
    const first = threatName.split(' ')[0].toLowerCase();
    const idx = awayPlayers.findIndex(p => p.name.toLowerCase().includes(first));
    return idx >= 0 ? idx : (awayPlayers.length > 2 ? 2 : -1);
  }, [awayPlayers, threatName]);

  const [arrowTx, arrowTy] = threatIdx >= 0 ? AWAY_POS[threatIdx] : [285, 75];
  const [arrowSx, arrowSy] = HOME_POS[5];

  return (
    <svg className="cc-court-svg" viewBox="0 0 360 180" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <pattern id="cc-grid" width="12" height="12" patternUnits="userSpaceOnUse">
          <path d="M 12 0 L 0 0 0 12" fill="none" stroke="rgba(34,211,238,0.07)" strokeWidth="0.5" />
        </pattern>
        <linearGradient id="cc-weak" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="rgba(249,115,22,0.18)" />
          <stop offset="100%" stopColor="rgba(249,115,22,0.04)" />
        </linearGradient>
      </defs>
      <rect x="6" y="6" width="348" height="168" fill="#020617" stroke="#1e293b" strokeWidth="1" rx="3" />
      <rect x="6" y="6" width="348" height="168" fill="url(#cc-grid)" rx="3" />
      {threatIdx >= 0 && <rect x="200" y="6" width="84" height="168" fill="url(#cc-weak)" />}
      <line x1="180" y1="10" x2="180" y2="170" stroke="#334155" strokeWidth="1" strokeDasharray="3 4" />
      <text x="14" y="20" fontFamily="JetBrains Mono, monospace" fontSize="7" letterSpacing="2" fill="#475569">HOME</text>
      <text x="318" y="20" fontFamily="JetBrains Mono, monospace" fontSize="7" letterSpacing="2" fill="#475569">AWAY</text>
      {threatIdx >= 0 && <text x="206" y="170" fontFamily="JetBrains Mono, monospace" fontSize="7" letterSpacing="2" fill="#f97316" opacity="0.85">KEY THREAT</text>}

      {HOME_POS.map(([cx, cy], i) => {
        const player = homePlayers[i];
        return (
          <g key={`h${i}`}>
            <circle cx={cx} cy={cy} r="8" fill="#0f172a" stroke="#f43f5e" strokeWidth="1.4" />
            <circle cx={cx} cy={cy} r="2.2" fill="#f43f5e" />
            {player && (
              <text x={cx} y={cy - 12} textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="5.5" fill="#94a3b8">
                {playerAbbrev(player.name)}
              </text>
            )}
          </g>
        );
      })}

      {AWAY_POS.map(([cx, cy], i) => {
        const player = awayPlayers[i];
        const isHighlighted = i === threatIdx;
        return (
          <g key={`a${i}`}>
            <circle cx={cx} cy={cy} r="8" fill="#0f172a" stroke={isHighlighted ? '#fb7185' : '#3b82f6'} strokeWidth={isHighlighted ? '2' : '1.4'} />
            <circle cx={cx} cy={cy} r="2.2" fill={isHighlighted ? '#fb7185' : '#3b82f6'} />
            {isHighlighted && <circle cx={cx} cy={cy} r="14" fill="none" stroke="#fb7185" strokeWidth="1" strokeDasharray="2 3" opacity="0.7" />}
            {player && (
              <text x={cx} y={cy - 12} textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="5.5" fill={isHighlighted ? '#fb7185' : '#94a3b8'}>
                {playerAbbrev(player.name)}
              </text>
            )}
          </g>
        );
      })}

      {threatIdx >= 0 && (
        <>
          <path
            d={`M ${arrowSx} ${arrowSy} Q ${(arrowSx + arrowTx) / 2} ${Math.min(arrowSy, arrowTy) - 20} ${arrowTx} ${arrowTy}`}
            fill="none" stroke="#f97316" strokeWidth="1.4" strokeDasharray="3 4" opacity="0.9"
          />
          <circle cx={arrowSx} cy={arrowSy} r="3" fill="#f97316" />
        </>
      )}
    </svg>
  );
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
  const recentRecord = recentResults.length ? `${recentWins}-${recentResults.length - recentWins}` : '—';
  const latestDashboard = data.latest_dashboard;
  const lastRecord = data.history.length > 0 ? data.history[data.history.length - 1] : null;
  const seasonName = seasonTitle(data.season_id);
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
  const pendCount = readinessChecks.filter(c => !c.ready).length;
  const currentApproach = intentLabels.get(selectedIntent) ?? selectedIntent;
  const isAggressive = selectedIntent === 'Win Now';
  const isDefensive = selectedIntent === 'Preserve Health';
  const threat = parseKeyMatchup(details.key_matchup);
  const topOvr = activePlayers.length > 0 ? Math.max(...activePlayers.map(player => player.overall)) : 0;
  const topPlayer = activePlayers.find(player => player.overall === topOvr) ?? null;
  const ovrGap = threat.ovr ? parseInt(threat.ovr) - Math.round(topOvr) : null;
  const hasApproachConflict = !isBye && selectedIntent === 'Win Now' && (threat.role === 'Tactical' || threat.role === 'Pressure');
  const counterApproach = threat.role ? (roleCounterMap[threat.role] ?? 'Control') : 'Control';
  const hasFatigueIssue = !isBye && activePlayers.filter(player => player.stamina !== undefined && player.stamina < 60).length > 1;
  const recommendedIntent = hasFatigueIssue ? 'Preserve Health' : intentForRecommendation(counterApproach);
  const hasPlanConflict = !isBye && (hasApproachConflict || hasFatigueIssue) && selectedIntent !== recommendedIntent;

  const scoutGapRead = ovrGap !== null && topPlayer
    ? ovrGap > 0
      ? `Primary threat outrates ${topPlayer.name} by +${ovrGap} OVR. `
      : `${topPlayer.name} covers the primary threat by +${Math.abs(ovrGap)} OVR. `
    : '';
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
  const stakes = stakesLine(leagueRank, gamesRemaining, recentResults, displayWeek);
  const playoffStage =
    currentMatch && currentMatch.stage && currentMatch.stage !== 'Regular Season'
      ? currentMatch.stage
      : null;
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

  const wk = String(displayWeek).padStart(2, '0');
  const topStanding = standings[0];
  const recentLeagueWire = data.history.slice(-3).map(h => ({
    week: h.week ?? '?',
    summary: h.dashboard?.result ? `${h.dashboard.result} vs ${h.dashboard.opponent_name ?? 'opponent'}` : 'No result',
  }));

  type DeptOrder = {
    dept: string;
    title: string;
    body: string;
    state: 'ready' | 'pending';
    clickable: boolean;
    isDevFocus?: boolean;
  };

  const deptOrders: DeptOrder[] = [
    {
      dept: 'Tactical Approach',
      title: humanize(plan.tactics?.approach),
      body: policySummary.find(p => p.label === 'Target focus')?.value ?? '',
      state: plan.tactics?.approach ? 'ready' : 'pending',
      clickable: true,
    },
    {
      dept: 'Training',
      title: humanize(plan.department_orders?.training),
      body: 'Weekly training focus',
      state: plan.department_orders?.training ? 'ready' : 'pending',
      clickable: false,
    },
    {
      dept: 'Catch Posture',
      title: humanize(plan.tactics?.catch_posture),
      body: humanize(plan.tactics?.rush_commit),
      state: plan.tactics?.catch_posture ? 'ready' : 'pending',
      clickable: true,
    },
    {
      dept: 'Development',
      title: humanize(plan.department_orders?.dev_focus ?? 'BALANCED'),
      body: 'Player development direction',
      state: 'ready',
      clickable: false,
      isDevFocus: true,
    },
  ];

  return (
    <div className="max-content" data-testid="weekly-command-center">

      {/* Identity strip */}
      <div className="cc-id-strip" data-testid="presim-command-strip" aria-label="Week context">
        <div>
          <span className="lbl">Program</span>
          <span className="val" title={data.player_club_name}>{data.player_club_name}</span>
        </div>
        <div>
          <span className="lbl">Season</span>
          <span className="val" style={{ fontSize: '0.8rem' }}>{seasonName}</span>
        </div>
        <div>
          <span className="lbl">Week</span>
          <span className="val num">W{wk}{playoffStage ? ` · ${playoffStage}` : ''}</span>
        </div>
        <div>
          <span className="lbl">Form</span>
          <span className="val num">{recentRecord}</span>
        </div>
        <div>
          <span className="lbl">Intent</span>
          <span className="val cyan">{currentApproach}</span>
        </div>
        <div>
          <span className="lbl">Status</span>
          <span className={`val ${planConfirmed ? 'orange' : 'cyan'}`}>{planConfirmed ? 'Locked' : 'Ready'}</span>
        </div>
      </div>

      {/* Hero */}
      <section className={`cc-hero${isBye ? ' is-bye' : ''}`}>
        <div className="cc-hero-left">
          <div className="cc-hero-kick">
            <span className="live-pip" />
            <span>Match Week</span>
            <span className="sep" />
            <span>Week {wk}</span>
            <span className="sep" />
            {isBye ? (
              <span style={{ color: '#67e8f9' }}>Bye Week</span>
            ) : (
              <span>{currentMatch?.home_club_name === data.player_club_name ? 'Home' : 'Away'}</span>
            )}
          </div>

          <h2 className="cc-hero-headline">
            {isBye ? (
              <span className="opp">Bye Week</span>
            ) : (
              <>
                <span className="vs">vs </span>
                <span className="opp">{plan.opponent.name}</span>
              </>
            )}
          </h2>

          <div className="cc-hero-frame">
            {isBye ? (
              <div className="line"><b>This Week</b>No match — rest, recover, and plan ahead.</div>
            ) : (
              <>
                <div className="line"><b>This Week</b>{stakes}</div>
                {watchLine && <div className="line watch"><b>Watch</b>{watchLine}</div>}
              </>
            )}
          </div>

          <div className="cc-hero-stats">
            <div>
              <span className="lbl">Opp Record</span>
              <span className="val">{isBye ? '—' : details.opponent_record}</span>
            </div>
            <div>
              <span className="lbl">Last Meeting</span>
              <span className="val" style={{ fontSize: '0.78rem', textTransform: 'none', fontFamily: 'var(--font-mono)', fontVariantNumeric: 'tabular-nums' }}>{isBye ? '—' : details.last_meeting}</span>
            </div>
            <div>
              <span className="lbl">Rank</span>
              <span className="val">{leagueRank ? `#${leagueRank}` : 'n/a'}</span>
            </div>
            <div>
              <span className="lbl">Starter Edge</span>
              <span className="val" style={{ fontSize: '0.82rem' }}>{isBye ? '—' : playerEdgeLabel}</span>
            </div>
          </div>
        </div>

        {!isBye && (
          <div className="cc-hero-right">
            <div className="cc-court-card">
              <div className="head">
                <span className="lbl">Court Read</span>
                <span className="side">▸ {threat.name ? `${threat.name} flagged` : 'Schematic — live positions'}</span>
              </div>
              <MiniCourt homePlayers={activePlayers} awayPlayers={opponentPlayers} threatName={threat.name} />
            </div>

            <div className={`cc-threat-card-kit command-threat-row${ovrGap !== null && ovrGap > 0 ? ' is-disadvantage' : ''}`}>
              <span className="lbl">Key Threat</span>
              <div className="name">{threat.name || plan.opponent.name}</div>
              <div className="row">
                <span><b>{threat.role ?? 'Anchor'}</b></span>
                {threat.ovr && <span className="ovr">{threat.ovr} OVR</span>}
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Body grid — Plan / Scout / Lock */}
      <div className="cc-body">

        {/* Plan panel */}
        <div className="cc-panel" data-testid="plan-editor-panel">
          <div className="cc-panel-head">
            <span className="kicker">Operational Plan</span>
            <h2>{currentApproach}</h2>
            <p>
              {isAggressive
                ? 'Pressure the weak side and accept higher exposure.'
                : isDefensive
                ? 'Protect stamina, lower risk, and win possessions.'
                : 'Keep the plan balanced across pressure, catches, and tempo.'}
            </p>
          </div>
          <div className="cc-panel-body">
            <div className={`cc-align-callout${hasPlanConflict ? ' is-warning' : ''}`} data-testid="plan-readout">
              <div className="copy">
                <b>{hasPlanConflict ? 'Adjustment advised.' : 'Profile aligned.'}</b>{' '}
                {planRead}
              </div>
              <span className={`cc-pill${hasPlanConflict ? ' amber' : ' emer'}`}>
                {hasPlanConflict ? 'Misaligned' : 'Aligned'}
              </span>
            </div>

            <div className="cc-policy" role="list">
              {deptOrders.map((o, i) => (
                <div
                  key={i}
                  className={`cc-policy-cell ${o.state}`}
                  role="listitem"
                  onClick={o.clickable && !planConfirmed ? () => setPolicyEditorOpen(true) : undefined}
                  style={o.clickable && !planConfirmed ? undefined : { cursor: 'default' }}
                >
                  <span className="lbl">{o.dept}</span>
                  {o.isDevFocus && !planConfirmed ? (
                    <select
                      data-testid="dev-focus-select"
                      aria-label="Development focus"
                      value={plan.department_orders?.dev_focus ?? 'BALANCED'}
                      onChange={event => { event.stopPropagation(); onSaveDevFocus(event.target.value); }}
                      onClick={e => e.stopPropagation()}
                    >
                      {DEV_FOCUS_OPTIONS.map(option => (
                        <option key={option} value={option}>{humanize(option)}</option>
                      ))}
                    </select>
                  ) : (
                    <span className="val">{o.title}</span>
                  )}
                  <span className="helper">{o.body}</span>
                </div>
              ))}
            </div>

            <div className="cc-plan-foot">
              <span className="note">{deptOrders.length} orders · {pendCount} pending</span>
              {!planConfirmed && (
                <button
                  type="button"
                  className="dm-btn"
                  onClick={() => setPolicyEditorOpen(true)}
                  data-testid="open-policy-editor"
                >
                  Edit Policy ▸
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Scout panel */}
        <div className="cc-panel" id="command-opponent-file" data-testid="scout-read-panel" tabIndex={-1}>
          <div className="cc-panel-head">
            <span className="kicker">Opponent File</span>
            <h2>{isBye ? 'Bye Week' : plan.opponent.name}</h2>
            <p>{isBye ? 'No opponent this week.' : scoutRead}</p>
          </div>
          <div className="cc-panel-body">
            {!isBye && (
              <>
                <div className="cc-scout-edge">
                  <div className="row">
                    <span className="lbl">Counter Read</span>
                    <span className="val">{recommendationLabel}</span>
                  </div>
                  <span className="sub">
                    {latestDashboard?.lanes?.[1]?.summary ?? details.framing_line}
                  </span>
                </div>

                <div className="cc-scout-grid">
                  <div>
                    <span className="lbl">Opp Record</span>
                    <span className="val">{details.opponent_record}</span>
                  </div>
                  <div>
                    <span className="lbl">Last Meeting</span>
                    <span className="val mono">{details.last_meeting}</span>
                  </div>
                  <div className="span-2">
                    <span className="lbl">Risk Notes</span>
                    <span className="val mono">{scoutRead}</span>
                  </div>
                </div>

                <div
                  className={`cc-align-callout${hasPlanConflict ? ' is-warning' : ''}`}
                  style={hasPlanConflict ? undefined : { borderColor: 'rgba(34,211,238,0.25)', borderLeftColor: 'var(--dm-cyan)', background: 'rgba(34,211,238,0.05)' }}
                >
                  <div className="copy">
                    <b style={{ color: '#fff' }}>{hasPlanConflict ? 'Recommendation.' : 'Scouting note.'}</b>{' '}
                    <span style={hasPlanConflict ? { color: '#fde68a' } : { color: 'var(--dm-text-secondary)' }}>
                      {hasPlanConflict
                        ? `Switch to ${recommendationLabel.replace('Adjust to ', '')}.`
                        : `${scoutGapRead || 'Current approach aligns with the opponent profile.'}`}
                    </span>
                  </div>
                  <span className={`cc-pill${hasPlanConflict ? ' amber' : ' cyan'}`}>
                    {hasPlanConflict ? 'Adjust' : 'Keep Plan'}
                  </span>
                </div>
              </>
            )}

            {isBye && (
              <div className="cc-scout-edge" style={{ borderLeftColor: 'var(--dm-cyan)', borderColor: 'rgba(34,211,238,0.25)', background: 'rgba(34,211,238,0.05)' }}>
                <div className="row">
                  <span className="lbl">This Week</span>
                  <span className="val" style={{ color: 'var(--dm-cyan-bright)' }}>Rest & Recover</span>
                </div>
                <span className="sub">No match this week. Review your roster health and plan development focus before advancing.</span>
              </div>
            )}
          </div>
        </div>

        {/* Lock panel */}
        <div className="cc-panel cc-lock" data-testid="readiness-panel">
          <div className="cc-panel-head">
            <span className="kicker">Sim Lock</span>
            <h2>{planConfirmed ? 'Locked' : 'Ready to decide'}</h2>
            <div className="cc-ready-row">
              <span className="pulse-em" />
              <span className="lbl">
                {isReadyToLock
                  ? `All gates green · ${readyCount}/${readinessChecks.length}`
                  : `${readyCount} of ${readinessChecks.length} ready · ${pendCount} pending`}
              </span>
            </div>
          </div>
          <div className="cc-panel-body">
            <div className="cc-gates command-readiness-chips">
              {readinessChecks.map(check => (
                <div
                  key={check.id}
                  className={`cc-gate ${check.ready ? 'ok' : 'pend'}`}
                  title={check.detail}
                >
                  <span className="tick">{check.ready ? '✓' : '!'}</span>
                  <span className="lbl">{check.shortLabel}</span>
                </div>
              ))}
            </div>

            {!planConfirmed && (
              <div className="cc-intent-field">
                <span className="lbl">This Week's Intent</span>
                <select
                  value={selectedIntent}
                  onChange={e => onIntentChange(e.target.value)}
                  aria-label="Weekly intent"
                >
                  {approaches.map(a => (
                    <option key={a.id} value={a.id}>{a.label}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="cc-lock-readout">
              <div className="lr">
                <span className="lbl">Decision</span>
                <span className="val">{currentApproach}</span>
              </div>
              <div className="lr">
                <span className="lbl">Risk</span>
                <span className={`val${isAggressive ? ' rose' : isDefensive ? ' em' : ' am'}`}>
                  {isAggressive ? 'High' : isDefensive ? 'Low' : 'Medium'}
                </span>
              </div>
              <div className="lr">
                <span className="lbl">Readiness</span>
                <span className="val mono em">{readyCount} / {readinessChecks.length}</span>
              </div>
              <div className="lr">
                <span className="lbl">Recommendation</span>
                <span className="val">{recommendationLabel}</span>
              </div>
              <div className="lr">
                <span className="lbl">Next Issue</span>
                <span className="val">{unresolvedIssue}</span>
              </div>
            </div>

            <div className="cc-lock-foot">
              <div className="ctx"><b>{primaryActionHint}</b></div>
              <button
                type="button"
                className="cc-btn-sim"
                data-testid={planConfirmed ? 'simulate-command-week' : 'lock-weekly-plan'}
                aria-label={planConfirmed ? 'Simulate Week' : 'Lock Plan'}
                onClick={() => {
                  if (planConfirmed) { simulate(); return; }
                  if (isReadyToLock) onSavePlan(selectedIntent, true);
                }}
                disabled={(!planConfirmed && !isReadyToLock) || saving}
              >
                <span>{saving ? 'Processing...' : primaryActionLabel}</span>
                <span className="arrow">▸</span>
              </button>
              {planConfirmed && (
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => onSavePlan(selectedIntent, false)}
                  className="command-secondary-button"
                >
                  Unlock Plan
                </button>
              )}
              <div className="cc-lock-meta">
                <span>⌘ ⏎ to confirm</span>
                <span>Auto-saved</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Proof bar — League Wire */}
      <div className="cc-proof" data-testid="secondary-intel-rail">
        <span className="tag">League Wire</span>
        <span className="copy">
          {recentLeagueWire.length > 0
            ? recentLeagueWire.map((m, i) => (
                <span key={i}>
                  <b>W{m.week}</b> {m.summary}
                  {i < recentLeagueWire.length - 1 ? '  ·  ' : ''}
                </span>
              ))
            : <span>No recent match history</span>
          }
        </span>
        {topStanding && (
          <span className="wkbadge">Top: {topStanding.club_name ?? topStanding.club_id}</span>
        )}
        {lastRecord && (
          <button type="button" className="show" onClick={() => undefined}>
            League Table ▸
          </button>
        )}
      </div>

      {/* Policy editor overlay */}
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
