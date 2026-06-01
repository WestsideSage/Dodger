import { useMemo, useState } from 'react';
import type {
  CoachPolicy,
  CommandCenterResponse,
  LineupPlayer,
  WeekBriefing,
} from '../../../types';
import { BroadcastFrameBlock } from '../../BroadcastFrameBlock';
import { PolicyEditor } from './PolicyEditor';
import { seasonTitle, stakesLine, playerToWatch } from './presimNarrative';

const approaches = [
  { id: 'Balanced', label: 'Balanced', desc: 'Even focus on offense and defense.' },
  { id: 'Win Now', label: 'Aggressive', desc: 'Higher pressure, higher foul/risk exposure.' },
  { id: 'Prepare For Playoffs', label: 'Control', desc: 'Slower tempo, better possession security.' },
  { id: 'Preserve Health', label: 'Defensive', desc: 'Lower throwing volume, stronger catch stability.' },
];

const intentLabels = new Map(approaches.map(approach => [approach.id, approach.label]));
const DEV_FOCUS_OPTIONS = ['BALANCED', 'YOUTH_ACCELERATION', 'TACTICAL_DRILLS', 'STRENGTH_AND_CONDITIONING'];

// Neutral default used only if the server omits the briefing (it always sends
// one through command_center_payload); keeps rendering safe without re-deriving.
const FALLBACK_BRIEFING: WeekBriefing = {
  readiness: { gates: [], total: 0, ready_count: 0, is_ready_to_lock: false, items_remaining: 0, next_issue: 'No blockers' },
  edge: { net_starter_ovr: 0, standing: 'even' },
  fatigue: { at_risk_count: 0, min_stamina: null },
  form: { recent_record: '—', rank: null, regular_season_record: '—', games_remaining: 0 },
  threat: null,
  match_context: { is_home: true, playoff_stage: null },
  league_leader: null,
  staff_recommendation: { action: 'keep', recommended_intent: null, reason: '' },
  recommendation: { verdict: 'aligned', advised_intent: null, reason: '', advisory: true },
};

function humanize(value: string | undefined) {
  if (!value) return 'Not set';
  const s = value.replaceAll('_', ' ').toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function formatEdge(value: number) {
  return String(Math.round(value));
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
  fastForward,
  onScout,
  onConfirmLineup,
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
  fastForward?: () => void;
  onScout?: () => void;
  onConfirmLineup?: () => void;
}) {
  const [policyEditorOpen, setPolicyEditorOpen] = useState(false);

  const plan = data.plan;
  const briefing = plan.briefing ?? FALLBACK_BRIEFING;
  const { readiness, edge, form, match_context, recommendation } = briefing;
  const briefingThreat = briefing.threat;
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
  const isBye = Boolean(plan.is_bye);

  const leagueRank = form.rank;
  const regularSeasonRecord = form.regular_season_record;
  const recentRecord = form.recent_record;
  const gamesRemaining = form.games_remaining;
  const playoffStage = match_context.playoff_stage;
  const leagueLeader = briefing.league_leader;
  // Ordered W/L sequence is still derived locally — stakesLine needs the streak,
  // which the briefing's record string can't express.
  const recentResults = data.history
    .slice(-5)
    .map(record => record.dashboard?.result)
    .filter((result): result is string => Boolean(result));
  const latestDashboard = data.latest_dashboard;
  const lastRecord = data.history.length > 0 ? data.history[data.history.length - 1] : null;
  const seasonName = seasonTitle(data.season_id);
  const watchLine = playerToWatch(activePlayers);

  const readinessChecks = readiness.gates;
  const scoutGateReady = readinessChecks.some(g => g.id === 'scout' && g.ready);
  const confirmLineupGateReady = readinessChecks.some(g => g.id === 'confirm_lineup' && g.ready);
  const readyCount = readiness.ready_count;
  const isReadyToLock = readiness.is_ready_to_lock;
  const itemsRemaining = readiness.items_remaining;
  const pendCount = readiness.items_remaining;
  const currentApproach = intentLabels.get(selectedIntent) ?? selectedIntent;
  const isAggressive = selectedIntent === 'Win Now';
  const isDefensive = selectedIntent === 'Preserve Health';

  const threatName = briefingThreat?.name ?? null;
  const threatArchetype = briefingThreat?.archetype ?? null;
  const threatOvr = briefingThreat?.ovr ?? null;
  const topOvr = activePlayers.length > 0 ? Math.max(...activePlayers.map(player => player.overall)) : 0;
  const topPlayer = activePlayers.find(player => player.overall === topOvr) ?? null;
  const ovrGap = threatOvr !== null ? threatOvr - Math.round(topOvr) : null;

  const hasPlanConflict = recommendation.verdict === 'adjust';
  const advisedIntentLabel = recommendation.advised_intent
    ? intentLabels.get(recommendation.advised_intent) ?? recommendation.advised_intent
    : null;
  const recommendationLabel = isBye
    ? 'n/a'
    : hasPlanConflict && advisedIntentLabel
      ? `Adjust to ${advisedIntentLabel}`
      : 'Keep current plan';

  const scoutGapRead = ovrGap !== null && topPlayer
    ? ovrGap > 0
      ? `Primary threat outrates ${topPlayer.name} by +${ovrGap} OVR. `
      : `${topPlayer.name} covers the primary threat by +${Math.abs(ovrGap)} OVR. `
    : '';

  const scoutRead = isBye
    ? 'This is a bye week. No opponent to scout. Use this time to rest players and plan training.'
    : `${scoutGapRead}${recommendation.reason}`;

  const planRead = isBye ? 'Bye week.' : recommendation.reason;

  const displayWeek = data.week;
  const stakes = stakesLine(leagueRank, gamesRemaining, recentResults, displayWeek, playoffStage);
  const identityRecordLabel = playoffStage ? 'Record' : 'Form';
  const identityRecordValue = playoffStage ? regularSeasonRecord : recentRecord;
  const netStarterEdge = edge.net_starter_ovr;
  // D2: the BAND is the headline; the signed net OVR is a small advisory
  // "roster strength" note, never a headline that reads like a win-probability.
  const edgeHeadline = edge.headline
    ?? (edge.standing === 'favorite' ? 'Favorite' : edge.standing === 'underdog' ? 'Underdog' : 'Even Matchup');
  const edgeAdvisory = edge.advisory_detail
    ?? `${netStarterEdge > 0 ? '+' : ''}${formatEdge(netStarterEdge)} net starter OVR`;
  const primaryActionLabel = planConfirmed ? 'SIMULATE WEEK' : 'LOCK PLAN';
  const primaryActionHint = planConfirmed
    ? 'The weekly plan is locked. Run the match when you are ready to move the season forward.'
    : isBye
    ? 'The plan is ready. Lock it to advance to the next week.'
    : isReadyToLock
    ? 'No blockers. Review the decision, then lock the plan.'
    : `${itemsRemaining} checklist item${itemsRemaining === 1 ? '' : 's'} still need attention before plan lock.`;
  const unresolvedIssue = readiness.next_issue;

  const wk = String(displayWeek).padStart(2, '0');
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

  // 2.4: the Operational Plan alignment indicator must reflect the REAL state
  // of the operational orders, not only the staff intent verdict. A plan with
  // pending department orders is NOT aligned, even if the staff has no intent
  // adjustment to advise — the previous code showed a green "Aligned" pill
  // while orders were still pending (green-while-misaligned). The pending count
  // shown here is the operational-order count, not the readiness-gate count
  // (which counts unrelated scout/confirm gates).
  const operationalPending = deptOrders.filter(o => o.state === 'pending').length;
  const operationalMisaligned = hasPlanConflict || operationalPending > 0;

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
          <span className="lbl">{identityRecordLabel}</span>
          <span className="val num">{identityRecordValue}</span>
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
              <span>{match_context.is_home ? 'Home' : 'Away'}</span>
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
              <div className="line"><b>This Week</b>{' '}No match — rest, recover, and plan ahead.</div>
            ) : (
              <>
                <div className="line"><b>This Week</b>{' '}{stakes}</div>
                {watchLine && <div className="line watch"><b>Watch</b>{' '}{watchLine}</div>}
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
              <span className="lbl">Matchup</span>
              {isBye ? (
                <span className="val" style={{ fontSize: '0.82rem' }}>—</span>
              ) : (
                <span
                  className="val"
                  data-testid="matchup-band"
                  data-standing={edge.standing}
                  style={{ fontSize: '0.82rem' }}
                  title="Banded from your fielded six vs theirs. Advisory only — it never implies a mechanical edge."
                >
                  {edgeHeadline}
                  <span className="sub" style={{ display: 'block', opacity: 0.7, fontSize: '0.7rem' }}>
                    {edgeAdvisory}
                  </span>
                </span>
              )}
            </div>
          </div>
        </div>

        {!isBye && (
          <div className="cc-hero-right">
            <div className="cc-court-card">
              <div className="head">
                <span className="lbl">Court Read</span>
                <span
                  className="side"
                  title={threatName ? 'Opponent key threat — watch this player' : undefined}
                >
                  ▸ {threatName ? `${threatName} flagged` : 'Schematic — live positions'}
                </span>
              </div>
              <MiniCourt homePlayers={activePlayers} awayPlayers={opponentPlayers} threatName={threatName} />
            </div>

            <div className={`cc-threat-card-kit command-threat-row${ovrGap !== null && ovrGap > 0 ? ' is-disadvantage' : ''}`}>
              <span className="lbl">Key Threat</span>
              <div className="name">{threatName || plan.opponent.name}</div>
              <div className="row">
                <span><b>{threatArchetype ?? 'Anchor'}</b></span>
                {threatOvr !== null && <span className="ovr">{threatOvr} OVR</span>}
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
            <div className={`cc-align-callout${operationalMisaligned ? ' is-warning' : ''}`} data-testid="plan-readout">
              <div className="copy">
                <b>
                  {operationalPending > 0
                    ? `${operationalPending} order${operationalPending === 1 ? '' : 's'} still pending.`
                    : hasPlanConflict
                    ? 'Adjustment advised.'
                    : 'Profile aligned.'}
                </b>{' '}
                {planRead}
              </div>
              <span className={`cc-pill${operationalMisaligned ? ' amber' : ' emer'}`}>
                {operationalMisaligned ? 'Misaligned' : 'Aligned'}
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
              <span className="note">{deptOrders.length} orders · {operationalPending} pending</span>
              {!planConfirmed && (
                <button
                  type="button"
                  className="dm-btn"
                  onClick={() => setPolicyEditorOpen(true)}
                  data-testid="open-policy-editor"
                >
                  Edit Game Plan ▸
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

                {details.broadcast_frame && (
                  <BroadcastFrameBlock frame={details.broadcast_frame} title="Broadcast Frame" compact />
                )}

                {details.tactical_diff && (
                  <div data-testid="tactical-diff" style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.5rem' }}>
                    <span className="lbl">Tactical Diff — Your Plan vs Their Tendencies</span>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                      {details.tactical_diff.player_plan.map((row) => (
                        <div
                          key={row.axis}
                          data-testid="tactical-diff-row"
                          data-axis={row.axis}
                          style={{
                            display: 'grid',
                            gridTemplateColumns: '8rem 1fr 1fr',
                            gap: '0.5rem',
                            alignItems: 'baseline',
                            padding: '0.3rem 0.55rem',
                            background: 'rgba(15,23,42,0.6)',
                            border: '1px solid rgba(30,41,59,0.8)',
                            borderRadius: '4px',
                            fontSize: '0.75rem',
                          }}
                        >
                          <span className="lbl" style={{ fontSize: '0.6rem' }}>{row.label}</span>
                          <span data-testid="tactical-diff-player" style={{ color: 'var(--dm-cyan)', fontWeight: 600 }}>{row.player_value}</span>
                          <span
                            data-testid="tactical-diff-opponent"
                            style={{ color: row.opponent_known ? '#e2e8f0' : '#64748b', fontStyle: row.opponent_known ? 'normal' : 'italic' }}
                          >
                            {row.opponent_known && row.opponent_value ? row.opponent_value : 'Unscouted'}
                          </span>
                        </div>
                      ))}
                    </div>
                    {details.tactical_diff.opponent_intel.length > 0 && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', marginTop: '0.15rem' }}>
                        {details.tactical_diff.opponent_intel.map((item, index) => (
                          <p
                            key={`${item.source}-${index}`}
                            data-testid="tactical-diff-intel"
                            data-source={item.source}
                            style={{ margin: 0, fontSize: '0.72rem', color: '#94a3b8', lineHeight: 1.4 }}
                          >
                            <span style={{ color: '#475569', textTransform: 'uppercase', fontSize: '0.6rem', marginRight: '0.4rem' }}>
                              {item.source === 'adaptation' ? 'Observed' : 'Prior'}
                            </span>
                            {item.text}
                          </p>
                        ))}
                      </div>
                    )}
                    <p style={{ margin: '0.1rem 0 0', fontSize: '0.68rem', color: '#475569', fontStyle: 'italic', lineHeight: 1.4 }}>
                      {details.tactical_diff.note}
                    </p>
                  </div>
                )}

                {details.staff_impact && details.staff_impact.length > 0 && (
                  <div data-testid="staff-impact" style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.5rem' }}>
                    <span className="lbl">Match-Day Staff</span>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                      {details.staff_impact.map((staff) => (
                        <div
                          key={staff.department}
                          data-testid="staff-impact-row"
                          data-department={staff.department}
                          style={{
                            display: 'flex',
                            alignItems: 'baseline',
                            gap: '0.5rem',
                            padding: '0.4rem 0.55rem',
                            background: 'rgba(15,23,42,0.6)',
                            border: '1px solid rgba(30,41,59,0.8)',
                            borderRadius: '4px',
                          }}
                        >
                          <span className="dm-data" style={{ fontSize: '0.7rem', color: 'var(--dm-cyan)', textTransform: 'uppercase', letterSpacing: '0.05em', flexShrink: 0 }}>
                            {staff.department}
                          </span>
                          <span style={{ fontSize: '0.75rem', color: '#e2e8f0', fontWeight: 600, flexShrink: 0 }}>
                            {staff.name} ({Math.round(staff.rating_primary)})
                          </span>
                          <span style={{ fontSize: '0.75rem', color: '#94a3b8', lineHeight: 1.4 }}>
                            {staff.effect}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div
                  className={`cc-align-callout${hasPlanConflict ? ' is-warning' : ''}`}
                  style={hasPlanConflict ? undefined : { borderColor: 'rgba(34,211,238,0.25)', borderLeftColor: 'var(--dm-cyan)', background: 'rgba(34,211,238,0.05)' }}
                >
                  <div className="copy">
                    <b style={{ color: '#fff' }}>{hasPlanConflict ? 'Recommendation.' : 'Scouting note.'}</b>{' '}
                    <span style={hasPlanConflict ? { color: '#fde68a' } : { color: 'var(--dm-text-secondary)' }}>
                      {hasPlanConflict
                        ? `Switch to ${recommendationLabel.replace('Adjust to ', '')}.`
                        : `${scoutGapRead || recommendation.reason}`}
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
                  ? `All gates green · ${readyCount}/${readiness.total}`
                  : `${readyCount} of ${readiness.total} ready · ${pendCount} pending`}
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
                  aria-label={check.detail ? `${check.short_label}: ${check.detail}` : check.short_label}
                >
                  <span className="tick" aria-hidden="true">{check.ready ? '✓' : '!'}</span>
                  <span className="lbl">{check.short_label}</span>
                  {/* WT-4: blocking detail must be visible + accessible, not
                      title-only. Show it inline for pending gates. */}
                  {!check.ready && check.detail && (
                    <span
                      className="cc-gate-detail"
                      style={{ display: 'block', fontSize: '0.75rem', opacity: 0.85, marginTop: '0.15rem' }}
                    >
                      {check.detail}
                    </span>
                  )}
                </div>
              ))}
            </div>

            {!planConfirmed && !isBye && (onScout || onConfirmLineup) && (
              <div className="cc-readiness-actions" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
                {onScout && !scoutGateReady && (
                  <button
                    type="button"
                    data-testid="scout-opponent"
                    className="command-secondary-button"
                    disabled={saving}
                    onClick={onScout}
                  >
                    Scout Opponent
                  </button>
                )}
                {onConfirmLineup && !confirmLineupGateReady && (
                  <button
                    type="button"
                    data-testid="confirm-lineup"
                    className="command-secondary-button"
                    disabled={saving}
                    onClick={onConfirmLineup}
                  >
                    Confirm Lineup
                  </button>
                )}
              </div>
            )}

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
                <span className="val mono em">{readyCount} / {readiness.total}</span>
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
              {fastForward && (
                <button
                  type="button"
                  data-testid="fast-forward-season"
                  disabled={saving}
                  onClick={fastForward}
                  className="command-secondary-button"
                  title="Auto-pilot the rest of the season with the persisted plan and best lineup."
                >
                  Fast-forward Season ⏭
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
        {leagueLeader && (
          <span className="wkbadge">Top: {leagueLeader}</span>
        )}
        {lastRecord && (
          <button
            type="button"
            className="show"
            onClick={() => {
              const params = new URLSearchParams(window.location.search);
              params.set('tab', 'standings');
              window.location.assign(`${window.location.pathname}?${params.toString()}`);
            }}
          >
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
