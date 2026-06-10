import { useEffect, useMemo, useRef, useState } from 'react';
import type {
  CoachPolicy,
  CommandCenterResponse,
  FastForwardStopPoint,
  LineupPlayer,
  WeekBriefing,
} from '../../../types';
import { BroadcastFrameBlock } from '../../BroadcastFrameBlock';
import { Dialog } from '../../ui';
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

const STOP_POINT_OPTIONS: { id: FastForwardStopPoint; label: string; desc: string }[] = [
  {
    id: 'next_bye',
    label: 'To my next bye',
    desc: 'Stop at your next scheduled bye week. If no bye remains this season, this stops just before the playoffs instead.',
  },
  {
    id: 'pre_playoffs',
    label: 'To pre-playoffs',
    desc: 'Play out the rest of the regular season and stop before the playoffs begin, so you can set your bracket plan.',
  },
  {
    id: 'offseason',
    label: 'To the offseason',
    desc: 'Run all the way through the playoffs to the offseason. This is an explicit acceptance of your current defaults through every remaining match, including the playoffs.',
  },
];

/**
 * WT-29: one disclosure dialog shown before fast-forward. It (a) truthfully
 * enumerates what will be auto-decided (the weekly decision loop is skipped and
 * each skipped week reuses your persisted plan and the canonical best-six
 * lineup) and (b) lets the player choose a stop point aligned to a real
 * decision boundary. Focus-trapped, Escape-dismissable, focus-restoring — a
 * self-contained accessible dialog until Phase 6 introduces shared primitives.
 */
function FastForwardDialog({
  onConfirm,
  onCancel,
  saving,
}: {
  onConfirm: (stopPoint: FastForwardStopPoint) => void;
  onCancel: () => void;
  saving: boolean;
}) {
  const [stopPoint, setStopPoint] = useState<FastForwardStopPoint>('pre_playoffs');
  const dialogRef = useRef<HTMLDivElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);

  useEffect(() => {
    previouslyFocused.current = document.activeElement as HTMLElement | null;
    // Move focus into the dialog on open.
    confirmRef.current?.focus();
    return () => {
      // Restore focus to the trigger when the dialog closes.
      previouslyFocused.current?.focus?.();
    };
  }, []);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      event.stopPropagation();
      onCancel();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    );
    if (!focusable || focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const active = document.activeElement;
    if (event.shiftKey && active === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return (
    <div
      className="command-policy-overlay"
      role="presentation"
      onClick={onCancel}
      data-testid="fast-forward-overlay"
    >
      <div
        ref={dialogRef}
        className="command-policy-overlay-body"
        role="dialog"
        aria-modal="true"
        aria-labelledby="fast-forward-title"
        aria-describedby="fast-forward-desc"
        data-testid="fast-forward-dialog"
        onClick={event => event.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        <h2 id="fast-forward-title" style={{ marginTop: 0 }}>Fast-forward the season?</h2>
        <p id="fast-forward-desc" style={{ color: 'var(--dm-text-secondary)', fontSize: '0.85rem', lineHeight: 1.5 }}>
          Fast-forward skips the weekly decision loop. For every week you skip, the
          game auto-decides using <b>your last saved weekly plan</b> (intent,
          tactics, and department orders) and fields the <b>canonical best-six
          lineup</b>. The pre-match desk and weekly ceremony are not shown for the
          skipped weeks.
        </p>

        <fieldset style={{ border: 'none', padding: 0, margin: '0.5rem 0' }}>
          <legend className="lbl" style={{ fontSize: '0.7rem', marginBottom: '0.35rem' }}>Stop point</legend>
          <div role="radiogroup" aria-label="Fast-forward stop point" style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {STOP_POINT_OPTIONS.map(option => (
              <label
                key={option.id}
                data-testid={`stop-point-${option.id}`}
                style={{
                  display: 'flex',
                  gap: '0.5rem',
                  alignItems: 'flex-start',
                  padding: '0.5rem 0.6rem',
                  border: `1px solid ${stopPoint === option.id ? 'var(--dm-cyan)' : 'rgba(30,41,59,0.9)'}`,
                  borderRadius: '5px',
                  background: stopPoint === option.id ? 'rgba(34,211,238,0.06)' : 'rgba(15,23,42,0.6)',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="radio"
                  name="fast-forward-stop-point"
                  value={option.id}
                  checked={stopPoint === option.id}
                  onChange={() => setStopPoint(option.id)}
                  style={{ marginTop: '0.2rem' }}
                />
                <span style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                  <span style={{ fontWeight: 600, color: '#e2e8f0', fontSize: '0.82rem' }}>{option.label}</span>
                  <span style={{ fontSize: '0.72rem', color: '#94a3b8', lineHeight: 1.4 }}>{option.desc}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '0.75rem' }}>
          <button
            type="button"
            className="command-secondary-button"
            onClick={onCancel}
            disabled={saving}
            data-testid="fast-forward-cancel"
          >
            Cancel
          </button>
          <button
            type="button"
            ref={confirmRef}
            className="cc-btn-sim"
            onClick={() => onConfirm(stopPoint)}
            disabled={saving}
            data-testid="fast-forward-confirm"
          >
            <span>{saving ? 'Processing...' : 'Fast-forward'}</span>
            <span className="arrow">▸</span>
          </button>
        </div>
      </div>
    </div>
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
  fastForward?: (stopPoint?: FastForwardStopPoint) => void;
  onScout?: () => void;
  onConfirmLineup?: () => void;
}) {
  const [policyEditorOpen, setPolicyEditorOpen] = useState(false);
  const [scoutFileOpen, setScoutFileOpen] = useState(false);
  const [fastForwardOpen, setFastForwardOpen] = useState(false);

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
  const lastRecord = data.history.length > 0 ? data.history[data.history.length - 1] : null;
  const seasonName = seasonTitle(data.season_id);
  const watchLine = playerToWatch(activePlayers);

  const readinessChecks = readiness.gates;
  const confirmLineupGateReady = readinessChecks.some(g => g.id === 'confirm_lineup' && g.ready);
  const pendingGates = readinessChecks.filter(g => !g.ready);
  // Directive subtitle — the pending steps phrased as one order.
  const gatePhrase = (id: string, shortLabel: string) =>
    id === 'scout' ? 'scout their projected six'
    : id === 'confirm_lineup' ? 'confirm the six you will field'
    : (shortLabel || '').toLowerCase();
  const pendingPhrases = pendingGates.map(g => gatePhrase(g.id, g.short_label));
  const objectiveSubBody =
    pendingPhrases.length > 1
      ? `${pendingPhrases.slice(0, -1).join(', ')} and ${pendingPhrases[pendingPhrases.length - 1]}`
      : pendingPhrases[0] ?? '';
  const objectiveSub = objectiveSubBody
    ? `${objectiveSubBody.charAt(0).toUpperCase()}${objectiveSubBody.slice(1)} before you sim.`
    : '';
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
    ? 'Plan locked. Run the match when ready.'
    : isBye
    ? 'Bye week — lock to advance.'
    : isReadyToLock
    ? 'All gates green. Lock it in.'
    : `${itemsRemaining} item${itemsRemaining === 1 ? '' : 's'} left before lock.`;
  const unresolvedIssue = readiness.next_issue;

  const wk = String(displayWeek).padStart(2, '0');
  const recentLeagueWire = data.history.slice(-3).map(h => ({
    week: h.week ?? '?',
    summary: h.dashboard?.result ? `${h.dashboard.result} vs ${h.dashboard.opponent_name ?? 'opponent'}` : 'No result',
  }));
  // Ticker items — only real news rides the wire (your recent results plus
  // the league leader); an empty league shows one honest static line.
  const wireItems = [
    ...recentLeagueWire.map(m => `W${m.week} — ${m.summary}`),
    ...(leagueLeader ? [`League leader: ${leagueLeader}`] : []),
  ];

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

      {/* League Wire — the broadcast ticker opens the page like a network
          rundown. It scrolls only when there is actual news; a quiet league
          gets one honest static line. */}
      <div
        className={`cc-proof cc-wire cc-wire-top${wireItems.length > 0 ? ' has-news' : ''}`}
        data-testid="secondary-intel-rail"
      >
        <span className="tag">
          {wireItems.length > 0 && <span className="pip" aria-hidden="true" />}
          League Wire
        </span>
        <div className="feed">
          {wireItems.length > 0 ? (
            <div className="scroll" aria-label={wireItems.join(' — ')}>
              <span className="half">
                {wireItems.map((item, i) => (
                  <span key={i} className="item">{item}</span>
                ))}
              </span>
              {/* duplicate for a seamless loop; hidden from AT */}
              <span className="half" aria-hidden="true">
                {wireItems.map((item, i) => (
                  <span key={i} className="item">{item}</span>
                ))}
              </span>
            </div>
          ) : (
            <span className="copy">Quiet week on the wire — no league results logged yet.</span>
          )}
        </div>
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

      {/* Identity strip — four facts of standing context. Intent and lock
          status live in the decision rail where they are actually set, not
          here as read-only echoes. */}
      <div className="cc-id-strip cc-id-strip-4" data-testid="presim-command-strip" aria-label="Week context">
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
          <span className="val num">
            W{wk}
            {playoffStage ? ` · ${playoffStage}` : isBye ? ' · Bye Week' : ''}
          </span>
        </div>
        <div>
          <span className="lbl">{identityRecordLabel}</span>
          <span className="val num">{identityRecordValue}</span>
        </div>
      </div>

      {/* Weekly directive — the week's next step, issued once at the top as
          a command-desk order. Pending gates surface here as direct actions;
          once everything is green it hands off to the Sim Lock dock. */}
      {!isBye && (
        <div
          className={`cc-objective${planConfirmed ? ' is-live' : isReadyToLock ? ' is-ready' : ''}`}
          data-testid="current-objective"
          role="status"
        >
          <span className="tag" aria-hidden="true">W{wk} · Directive</span>
          <div className="msg">
            {planConfirmed ? (
              <>
                <span className="state">Plan locked</span>
                <span className="sub">Simulate the week when ready.</span>
              </>
            ) : isReadyToLock ? (
              <>
                <span className="state">Ready to lock</span>
                <span className="sub">All gates green — lock the plan in the Sim Lock panel.</span>
              </>
            ) : (
              <>
                <span className="state">
                  {itemsRemaining} action{itemsRemaining === 1 ? '' : 's'} left before lock
                </span>
                <span className="sub">{objectiveSub}</span>
              </>
            )}
          </div>
          {!planConfirmed && !isReadyToLock && (
            <span className="actions">
              {pendingGates.map(gate => {
                const onAction =
                  gate.id === 'scout' ? onScout
                  : gate.id === 'confirm_lineup' ? onConfirmLineup
                  : undefined;
                const actionLabel =
                  gate.id === 'scout' ? 'Scout Opponent'
                  : gate.id === 'confirm_lineup' ? 'Confirm Lineup'
                  : gate.short_label;
                return onAction ? (
                  <button
                    key={gate.id}
                    type="button"
                    className="act"
                    onClick={onAction}
                    disabled={saving}
                    data-testid={`objective-${gate.id}`}
                  >
                    {actionLabel} ▸
                  </button>
                ) : (
                  <span key={gate.id} className="chip">{actionLabel}</span>
                );
              })}
            </span>
          )}
        </div>
      )}

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

          {/* The matchup band is the week's single most decision-relevant
              read — it sits with the headline, not buried in a stat row. */}
          {!isBye && (
            <div
              className="cc-hero-band"
              data-testid="matchup-band"
              data-standing={edge.standing}
              title="Banded from your fielded six vs theirs. Advisory only — it never implies a mechanical edge."
            >
              <span className="band">{edgeHeadline}</span>
              <span className="adv">{edgeAdvisory}</span>
            </div>
          )}

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

          {/* The broadcast frame IS billboard material — proof-backed stakes
              and the historical hook frame the matchup, so it rides the hero
              instead of padding out the scouting desk. */}
          {!isBye && details.broadcast_frame && (
            <BroadcastFrameBlock frame={details.broadcast_frame} title="Broadcast Frame" compact />
          )}

          {/* Single source for these three facts — they no longer repeat in
              the Opponent File below. */}
          {!isBye && (
            <div className="cc-hero-stats cc-hero-stats-3">
              <div>
                <span className="lbl">Rank</span>
                <span className="val">{leagueRank ? `#${leagueRank}` : 'n/a'}</span>
              </div>
              <div>
                <span className="lbl">Opp Record</span>
                <span className="val">{details.opponent_record}</span>
              </div>
              <div>
                <span className="lbl">Last Meeting</span>
                <span className="val" style={{ fontSize: '0.78rem', textTransform: 'none', fontFamily: 'var(--font-mono)', fontVariantNumeric: 'tabular-nums' }}>{details.last_meeting}</span>
              </div>
            </div>
          )}
        </div>

        {!isBye && (
          <div className="cc-hero-right">
            <div className="cc-court-card">
              <div className="head">
                <span className="lbl">Court Read</span>
                <span
                  className="side"
                  title={threatName ? 'Opponent key threat — watch this player' : 'A schematic of the projected sixes — not live positions'}
                >
                  ▸ {threatName ? `${threatName} flagged` : 'Projected sixes'}
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
            {/* One verdict line. The staff's reasoning lives in the Opponent
                File's Counter Read — not repeated here. */}
            <div className={`cc-align-callout${operationalMisaligned ? ' is-warning' : ''}`} data-testid="plan-readout">
              <div className="copy">
                <b>
                  {operationalPending > 0
                    ? `${operationalPending} order${operationalPending === 1 ? '' : 's'} still pending.`
                    : hasPlanConflict
                    ? 'Adjustment advised.'
                    : 'Profile aligned.'}
                </b>{' '}
                {operationalPending > 0
                  ? 'Set every department order before lock.'
                  : hasPlanConflict
                  ? 'See the Counter Read in the Opponent File.'
                  : isBye
                  ? 'Bye week.'
                  : 'All orders set for this matchup.'}
              </div>
              <span className={`cc-pill${operationalMisaligned ? ' amber' : ' emer'}`}>
                {operationalMisaligned ? 'Misaligned' : 'Aligned'}
              </span>
            </div>

            <div className="cc-policy">
              {deptOrders.map((o, i) => {
                const opensEditor = o.clickable && !planConfirmed;
                // Tactics cells are real buttons (keyboard path into the
                // editor — the redundant "Edit Game Plan" button is gone).
                // The first one carries the canonical editor testid.
                if (opensEditor) {
                  return (
                    <button
                      key={i}
                      type="button"
                      className={`cc-policy-cell is-button ${o.state}`}
                      onClick={() => setPolicyEditorOpen(true)}
                      aria-label={`${o.dept}: ${o.title} — edit the game plan`}
                      data-testid={o.dept === 'Tactical Approach' ? 'open-policy-editor' : undefined}
                    >
                      <span className="lbl">{o.dept}</span>
                      <span className="val">{o.title}</span>
                      <span className="helper">{o.body}</span>
                    </button>
                  );
                }
                return (
                  <div key={i} className={`cc-policy-cell is-static ${o.state}`}>
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
                );
              })}
            </div>

            {/* Match-day staff are YOUR operation — they live on the plan
                desk, not in the opponent's file. */}
            {details.staff_impact && details.staff_impact.length > 0 && (
              <div data-testid="staff-impact" className="cc-staff-strip">
                <span className="lbl">Match-Day Staff</span>
                <div className="rows">
                  {details.staff_impact.map((staff) => (
                    <div
                      key={staff.department}
                      data-testid="staff-impact-row"
                      data-department={staff.department}
                      className="row"
                    >
                      <span className="dept">{staff.department}</span>
                      <span className="who">{staff.name} ({Math.round(staff.rating_primary)})</span>
                      <span className="effect">{staff.effect}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="cc-plan-foot">
              <span className="note">{deptOrders.length} orders · {operationalPending} pending</span>
              {!planConfirmed && (
                <span className="note">Click a tactics cell to edit</span>
              )}
            </div>
          </div>
        </div>

        {/* Scout panel */}
        <div className="cc-panel" id="command-opponent-file" data-testid="scout-read-panel" tabIndex={-1}>
          <div className="cc-panel-head">
            <span className="kicker">Opponent File</span>
            {/* The hero owns the cinematic matchup name — this desk owns the
                tactical read, so its title says what it does. */}
            <h2>{isBye ? 'Bye Week' : 'Scouting Report'}</h2>
            <p>{isBye ? 'No opponent this week.' : (scoutGapRead || details.framing_line)}</p>
          </div>
          <div className="cc-panel-body">
            {!isBye && (
              <>
                <div
                  className={`cc-scout-edge${hasPlanConflict ? ' is-warning' : ''}`}
                  data-testid="counter-read"
                >
                  <div className="row">
                    <span className="lbl">Counter Read</span>
                    <span className="val">{recommendationLabel}</span>
                  </div>
                  <span className="sub">{recommendation.reason || details.framing_line}</span>
                </div>

                {details.tactical_diff && (() => {
                  const diffRows = details.tactical_diff.player_plan;
                  const revealedCount = diffRows.filter(row => row.opponent_known).length;
                  const allRevealed = revealedCount === diffRows.length && diffRows.length > 0;
                  return (
                  <div data-testid="tactical-diff" data-scouted={details.tactical_diff.scouted ? 'true' : 'false'} style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <span className="lbl">Tactical Diff — Your Plan vs Their Tendencies</span>
                      <span style={{ display: 'inline-flex', gap: '0.4rem', alignItems: 'baseline' }}>
                        {/* The intel meter makes scouting's payoff explicit:
                            a locked layer with a fill state, not absent data. */}
                        <span
                          className={`cc-intel-meter${allRevealed ? ' is-open' : revealedCount > 0 ? ' is-partial' : ''}`}
                          data-testid="tactical-diff-intel-meter"
                          title={
                            allRevealed
                              ? 'All tendency reads revealed from tape.'
                              : 'Locked intel — scouting reveals their observed tendencies row by row.'
                          }
                        >
                          {revealedCount}/{diffRows.length} reads revealed
                        </span>
                        {/* Week 1 trap: the scout action can reveal only
                            pre-tape facts, leaving 0/5 tendency reads — an
                            emerald "New intel revealed" beside "0/5" reads as
                            a contradiction. When no reads exist, say what
                            actually happened instead. */}
                        {details.tactical_diff.intel_revealed && revealedCount > 0 && (
                          <span
                            data-testid="tactical-diff-revealed"
                            style={{ fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#34d399', border: '1px solid rgba(52,211,153,0.4)', borderRadius: '3px', padding: '0.05rem 0.35rem' }}
                          >
                            New intel revealed
                          </span>
                        )}
                        {details.tactical_diff.intel_revealed && revealedCount === 0 && (
                          <span
                            data-testid="tactical-diff-revealed"
                            title="Scouting logged the pre-tape file. Tendency reads appear once this opponent has match tape to study."
                            style={{ fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8', border: '1px solid rgba(100,116,139,0.4)', borderRadius: '3px', padding: '0.05rem 0.35rem' }}
                          >
                            Scouted · no tape yet
                          </span>
                        )}
                      </span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                      {details.tactical_diff.player_plan.map((row) => (
                        <div
                          key={row.axis}
                          data-testid="tactical-diff-row"
                          data-axis={row.axis}
                          data-opponent-source={row.opponent_source ?? ''}
                          style={{
                            display: 'grid',
                            gridTemplateColumns: '8rem 1fr 1fr',
                            gap: '0.5rem',
                            alignItems: 'baseline',
                            padding: '0.24rem 0.55rem',
                            background: 'rgba(15,23,42,0.6)',
                            border: '1px solid rgba(30,41,59,0.8)',
                            borderRadius: '4px',
                            fontSize: '0.74rem',
                          }}
                        >
                          <span className="lbl" style={{ fontSize: '0.6rem' }}>{row.label}</span>
                          <span data-testid="tactical-diff-player" style={{ color: 'var(--dm-cyan)', fontWeight: 600 }}>{row.player_value}</span>
                          <span
                            data-testid="tactical-diff-opponent"
                            style={{ color: row.opponent_known ? '#e2e8f0' : undefined }}
                          >
                            {row.opponent_known && row.opponent_value ? (
                              row.opponent_value
                            ) : (
                              <span
                                className="cc-fog"
                                title="Locked intel — scout the opponent to reveal observed tendencies."
                              >
                                Unscouted
                              </span>
                            )}
                            {row.opponent_known && row.opponent_source === 'tape' && (
                              <span
                                data-testid="tactical-diff-tape-meta"
                                title={`Observed on tape across ${row.sample ?? 0} game${row.sample === 1 ? '' : 's'} — ${
                                  // Backend sends 'strong' / 'leans' / 'mixed'; phrase each
                                  // so the sentence reads as English, not template output.
                                  row.confidence_label === 'strong' ? 'a strong lean'
                                  : row.confidence_label === 'leans' ? 'a moderate lean'
                                  : row.confidence_label === 'mixed' ? 'a mixed read'
                                  : 'a lean'
                                }, not their hidden plan.`}
                                style={{ marginLeft: '0.4rem', fontSize: '0.58rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em', whiteSpace: 'nowrap' }}
                              >
                                {typeof row.confidence === 'number' ? `${Math.round(row.confidence * 100)}%` : (row.confidence_label ?? 'tape')}
                                {typeof row.sample === 'number' ? ` · n${row.sample}` : ''}
                              </span>
                            )}
                          </span>
                        </div>
                      ))}
                    </div>

                    <p style={{ margin: '0.1rem 0 0', fontSize: '0.68rem', color: '#475569', fontStyle: 'italic', lineHeight: 1.4 }}>
                      {details.tactical_diff.note}
                    </p>
                  </div>
                  );
                })()}

                {/* Depth intel (pre-tape facts, observed adaptation notes)
                    folds into the Full File dialog. The trigger pins to the
                    panel foot so the three desks share a crisp bottom edge. */}
                {details.tactical_diff && (details.tactical_diff.cold_start || details.tactical_diff.opponent_intel.length > 0) && (
                  <div className="cc-intel-foot">
                    <button
                      type="button"
                      className="dm-btn"
                      onClick={() => setScoutFileOpen(true)}
                      data-testid="open-scouting-file"
                    >
                      Full Scouting File ▸
                    </button>
                  </div>
                )}
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
            <h2>{planConfirmed ? 'Locked' : 'Ready to Lock?'}</h2>
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
              {readinessChecks.map(check => {
                // P3: the blocker carries its own resolving action — the
                // current step visually dominates the (disabled) lock button.
                const gateAction =
                  !planConfirmed && !isBye && !check.ready
                    ? check.id === 'scout' && onScout
                      ? { label: 'Scout now', onClick: onScout, testid: 'scout-opponent', disabled: saving }
                      : check.id === 'confirm_lineup' && onConfirmLineup
                        ? { label: 'Confirm six', onClick: onConfirmLineup, testid: 'confirm-lineup', disabled: saving || activePlayers.length === 0 }
                        : null
                    : null;
                return (
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
                    {gateAction && (
                      <button
                        type="button"
                        className="cc-gate-action"
                        data-testid={gateAction.testid}
                        disabled={gateAction.disabled}
                        onClick={gateAction.onClick}
                      >
                        {gateAction.label} ▸
                      </button>
                    )}
                  </div>
                );
              })}
            </div>

            {/* BUG #6: "Confirm Lineup" must be an INFORMED confirmation, not a
                blind rubber-stamp. Surface the exact six being confirmed (the
                canonical fielded-6 the sim will field — always populated, see
                command_center._lineup_recommendation) right at the confirm
                point, so the player sees WHO they are confirming before the gate
                clears. To CHANGE the six, the player edits the game plan; this
                read-only preview just makes the confirm deliberate. */}
            {!planConfirmed && !isBye && onConfirmLineup && !confirmLineupGateReady && (
              <div
                className="cc-confirm-lineup-preview"
                data-testid="confirm-lineup-preview"
                style={{ marginTop: '0.5rem', padding: '0.5rem 0.6rem', background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(30,41,59,0.9)', borderRadius: '5px' }}
              >
                <span className="lbl" style={{ fontSize: '0.7rem', color: '#475569' }}>
                  The six you are confirming
                </span>
                {activePlayers.length > 0 ? (
                  <ol
                    data-testid="confirm-lineup-list"
                    style={{ listStyle: 'none', padding: 0, margin: '0.35rem 0 0', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}
                  >
                    {activePlayers.map((player, index) => (
                      <li
                        key={player.id}
                        data-testid="confirm-lineup-player"
                        style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: '0.6rem', fontSize: '0.8rem' }}
                      >
                        <span style={{ display: 'flex', alignItems: 'baseline', gap: '0.45rem' }}>
                          <span className="lbl" style={{ fontSize: '0.66rem', color: '#475569' }}>{index + 1}</span>
                          <span style={{ fontWeight: 600, color: '#e2e8f0' }}>{player.name}</span>
                        </span>
                        <span style={{ display: 'flex', alignItems: 'baseline', gap: '0.55rem' }}>
                          <span className="val mono" style={{ color: 'var(--dm-cyan)' }}>{player.overall} OVR</span>
                          {typeof player.stamina === 'number' && (
                            <span className="val mono" style={{ fontSize: '0.72rem', color: player.stamina < 60 ? '#f59e0b' : '#94a3b8' }}>
                              {player.stamina} STA
                            </span>
                          )}
                        </span>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p data-testid="confirm-lineup-empty" style={{ margin: '0.35rem 0 0', color: '#f59e0b', fontSize: '0.78rem' }}>
                    No lineup is available yet. Build the game plan first.
                  </p>
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

            {/* Three facts the lock decision actually turns on. Decision
                (= the intent above) and Recommendation (= the Counter Read)
                are not repeated here. */}
            <div className="cc-lock-readout">
              <div className="lr">
                <span className="lbl">Risk</span>
                <span className={`val${isAggressive ? ' rose' : isDefensive ? ' em' : ' am'}`}>
                  {isAggressive ? 'High' : isDefensive ? 'Low' : 'Medium'}
                </span>
              </div>
              <div className="lr">
                <span className="lbl">Readiness</span>
                <span className={`val mono${isReadyToLock ? ' em' : ' am'}`}>{readyCount} / {readiness.total}</span>
              </div>
              <div className="lr">
                <span className="lbl">Next Issue</span>
                <span className="val">{unresolvedIssue}</span>
              </div>
            </div>

            {/* Launch dock — the one action this whole page builds toward. */}
            <div className={`cc-launch${planConfirmed ? ' is-live' : isReadyToLock ? ' is-armed' : ''}`}>
              <div className="ctx">{primaryActionHint}</div>
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
              <div className="cc-launch-secondary">
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
                    onClick={() => setFastForwardOpen(true)}
                    className="command-secondary-button"
                    title="Auto-pilot ahead with the persisted plan and best lineup. Pick a stop point first."
                  >
                    Fast-forward Season ⏭
                  </button>
                )}
              </div>
              <div className="cc-lock-meta">
                <span>{planConfirmed ? 'Locked in' : `${readyCount} of ${readiness.total} gates green`}</span>
                <span>Auto-saved</span>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Policy editor overlay — WT-21: the raw overlay shell is now the shared
          Dialog primitive (focus-trap/restore + Escape). The PolicyEditor
          inside is left exactly as-is (wrap, not rewrite). */}
      {policyEditorOpen && (
        <Dialog
          label="Edit policy"
          onClose={() => setPolicyEditorOpen(false)}
          className="command-policy-overlay"
          panelClassName="command-policy-overlay-body"
          overlayStyle={{ backgroundColor: undefined, backdropFilter: undefined, padding: undefined }}
          panelStyle={{}}
          data-testid="policy-editor-overlay"
        >
            <button
              type="button"
              className="command-policy-overlay-close"
              onClick={() => setPolicyEditorOpen(false)}
              aria-label="Close policy editor"
            >
              Close
            </button>
            <PolicyEditor
              policy={plan.tactics}
              disabled={planConfirmed}
              onChange={onSavePolicy}
              error={null}
              officialRuleset={Boolean(data.ruleset_selection?.startsWith('official'))}
            />
        </Dialog>
      )}

      {/* Full Scouting File — depth intel folded out of the card so the
          three desks stay uniform. Same overlay pattern as the policy
          editor; all payload-backed facts, nothing re-derived. */}
      {scoutFileOpen && details.tactical_diff && (
        <Dialog
          label={`Full scouting file — ${plan.opponent.name}`}
          onClose={() => setScoutFileOpen(false)}
          className="command-policy-overlay"
          panelClassName="command-policy-overlay-body"
          overlayStyle={{ backgroundColor: undefined, backdropFilter: undefined, padding: undefined }}
          panelStyle={{}}
          data-testid="scouting-file-overlay"
        >
          <button
            type="button"
            className="command-policy-overlay-close"
            onClick={() => setScoutFileOpen(false)}
            aria-label="Close scouting file"
          >
            Close
          </button>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
            <div>
              <span className="dm-kicker">Full Scouting File</span>
              <h2 style={{ margin: '0.25rem 0 0', fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 800, textTransform: 'uppercase', color: '#fff' }}>
                {plan.opponent.name}
              </h2>
            </div>

            {details.tactical_diff.cold_start && (
              <div
                data-testid="tactical-diff-cold-start"
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.3rem',
                  padding: '0.6rem 0.7rem',
                  // Fog-of-war framing: the pre-tape intel layer, styled as
                  // locked intelligence rather than missing data.
                  background: 'repeating-linear-gradient(45deg, rgba(34,211,238,0.03) 0 5px, rgba(15,23,42,0.6) 5px 10px)',
                  border: '1px dashed rgba(34,211,238,0.28)',
                  borderRadius: '4px',
                }}
              >
                <span className="lbl" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6rem', letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--dm-cyan)' }}>
                  Pre-tape intel — what the league already knows
                </span>
                {details.tactical_diff.cold_start.program_archetype && (
                  <span data-testid="cold-start-archetype" style={{ fontSize: '0.78rem', color: '#e2e8f0' }}>
                    Program identity: <b>{details.tactical_diff.cold_start.program_archetype}</b>
                  </span>
                )}
                {details.tactical_diff.cold_start.roster_shape && (
                  <span data-testid="cold-start-roster-shape" style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                    Roster shape: {details.tactical_diff.cold_start.roster_shape.throwers} throwing-oriented · {details.tactical_diff.cold_start.roster_shape.defenders} defense-oriented
                  </span>
                )}
                {details.tactical_diff.cold_start.position_groups && (
                  <span data-testid="cold-start-position-groups" style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                    {details.tactical_diff.cold_start.position_groups.single_family ? (
                      <>Group depth: only a <b style={{ color: '#e2e8f0' }}>{details.tactical_diff.cold_start.position_groups.strongest.label}</b> core ({details.tactical_diff.cold_start.position_groups.strongest.avg_ovr} avg OVR)</>
                    ) : (
                      <>Strongest group: <b style={{ color: '#e2e8f0' }}>{details.tactical_diff.cold_start.position_groups.strongest.label}</b> ({details.tactical_diff.cold_start.position_groups.strongest.avg_ovr} avg OVR) · Weakest: {details.tactical_diff.cold_start.position_groups.weakest.label} ({details.tactical_diff.cold_start.position_groups.weakest.avg_ovr} avg OVR)</>
                    )}
                  </span>
                )}
                {details.tactical_diff.cold_start.recent_form && (
                  <span data-testid="cold-start-recent-form" style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                    Recent form: <b style={{ color: '#e2e8f0' }}>{details.tactical_diff.cold_start.recent_form}</b> this season ({details.tactical_diff.cold_start.recent_form.split('-').length === 3 ? 'W-L-D' : 'W-L'})
                  </span>
                )}
                {details.tactical_diff.cold_start.threat && (
                  <span data-testid="cold-start-threat" style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                    Top threat: <b style={{ color: '#e2e8f0' }}>{details.tactical_diff.cold_start.threat.name}</b> · {details.tactical_diff.cold_start.threat.archetype} · {details.tactical_diff.cold_start.threat.ovr} OVR
                  </span>
                )}
              </div>
            )}

            {details.tactical_diff.opponent_intel.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                <span className="lbl" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6rem', letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--dm-cyan)' }}>
                  Intel Notes
                </span>
                {details.tactical_diff.opponent_intel.map((item, index) => (
                  <p
                    key={`${item.source}-${index}`}
                    data-testid="tactical-diff-intel"
                    data-source={item.source}
                    style={{ margin: 0, fontSize: '0.78rem', color: '#94a3b8', lineHeight: 1.45 }}
                  >
                    <span style={{ color: '#475569', textTransform: 'uppercase', fontSize: '0.62rem', marginRight: '0.4rem' }}>
                      {item.source === 'adaptation' ? 'Observed' : 'Prior'}
                    </span>
                    {item.text}
                  </p>
                ))}
              </div>
            )}

            <p style={{ margin: 0, fontSize: '0.7rem', color: '#475569', fontStyle: 'italic', lineHeight: 1.4 }}>
              {details.tactical_diff.note}
            </p>
          </div>
        </Dialog>
      )}

      {/* Fast-forward disclosure dialog (WT-29) */}
      {fastForwardOpen && fastForward && (
        <FastForwardDialog
          saving={saving}
          onCancel={() => setFastForwardOpen(false)}
          onConfirm={(stopPoint) => {
            setFastForwardOpen(false);
            fastForward(stopPoint);
          }}
        />
      )}

    </div>
  );
}
