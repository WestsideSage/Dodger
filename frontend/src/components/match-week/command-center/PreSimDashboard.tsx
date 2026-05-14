import { useEffect, useMemo, useState } from 'react';
import type { CommandCenterResponse, StandingRow, StandingsResponse } from '../../../types';
import { MatchCard } from './MatchCard';

const approaches = [
  { id: 'Balanced', label: 'Balanced', desc: 'Even focus on offense and defense.' },
  { id: 'Win Now', label: 'Aggressive', desc: 'Higher pressure, higher foul/risk exposure.' },
  { id: 'Prepare For Playoffs', label: 'Control', desc: 'Slower tempo, better possession security.' },
  { id: 'Preserve Health', label: 'Defensive', desc: 'Lower throwing volume, stronger catch stability.' },
];

const intentLabels = new Map(approaches.map(approach => [approach.id, approach.label]));

const roleCounterMap: Record<string, string> = {
  Tactical: 'Control',
  Pressure: 'Defensive',
  Balanced: 'Balanced',
};

function pct(value: number | undefined) {
  if (typeof value !== 'number') return 'n/a';
  return `${Math.round(value * 100)}%`;
}

function humanize(value: string | undefined) {
  if (!value) return 'Not set';
  const s = value.replaceAll('_', ' ').toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
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

  useEffect(() => {
    let cancelled = false;
    fetch('/api/standings')
      .then(res => res.ok ? res.json() : null)
      .then((payload: StandingsResponse | null) => {
        if (!cancelled && payload?.standings) setStandings(payload.standings);
      })
      .catch(() => {
        if (!cancelled) setStandings([]);
      });
    return () => {
      cancelled = true;
    };
  }, [data.season_id]);

  const plan = data.plan;
  const details = plan.matchup_details ?? {
    opponent_record: 'Unknown',
    last_meeting: 'No meeting recorded',
    key_matchup: 'Opponent file unavailable.',
    framing_line: data.current_objective,
  };
  const activePlayers = useMemo(
    () => plan.lineup?.players?.slice(0, 6) ?? [],
    [plan.lineup?.players],
  );
  const userStanding = standings.find(row => row.club_id === data.player_club_id);
  const leagueRank = userStanding ? standings.findIndex(row => row.club_id === data.player_club_id) + 1 : null;
  const recentResults = data.history.slice(-5).map(record => record.dashboard?.result).filter(Boolean);
  const recentWins = recentResults.filter(result => result === 'Win').length;
  const recentRecord = recentResults.length ? `${recentWins}-${recentResults.length - recentWins}` : 'No recent matches';
  const latestDashboard = data.latest_dashboard;
  const readinessChecks = useMemo(() => [
    {
      id: 'scout',
      label: 'Opponent file available',
      detail: details.key_matchup,
      ready: Boolean(plan.matchup_details || plan.recommendations.length),
    },
    {
      id: 'gameplan',
      label: 'Command intent selected',
      detail: selectedIntent,
      ready: Boolean(selectedIntent),
    },
    {
      id: 'training',
      label: 'Training order saved',
      detail: humanize(plan.department_orders?.training),
      ready: Boolean(plan.department_orders?.training),
    },
    {
      id: 'rotation',
      label: 'Playable rotation present',
      detail: `${activePlayers.length} listed starters`,
      ready: activePlayers.length >= 6,
    },
    {
      id: 'health',
      label: 'Starter stamina checked',
      detail: activePlayers.some(player => typeof player.stamina === 'number')
        ? `${Math.round(Math.min(...activePlayers.map(player => player.stamina ?? 100)))} minimum stamina`
        : 'No stamina warnings reported',
      ready: activePlayers.every(player => player.stamina === undefined || player.stamina >= 35),
    },
  ], [activePlayers, details.key_matchup, plan.department_orders?.training, plan.matchup_details, plan.recommendations.length, selectedIntent]);

  const readyCount = readinessChecks.filter(check => check.ready).length;
  const isReadyToLock = readyCount === readinessChecks.length;
  const itemsRemaining = readinessChecks.length - readyCount;
  const planStatus = planConfirmed ? 'Locked In' : (isReadyToLock ? 'Ready to Lock' : 'Needs Review');
  const planStatusColor = planConfirmed ? '#10b981' : (isReadyToLock ? '#22d3ee' : '#f59e0b');
  const currentApproach = intentLabels.get(selectedIntent) ?? selectedIntent;
  const isAggressive = selectedIntent === 'Win Now';
  const isDefensive = selectedIntent === 'Preserve Health';
  const threat = parseKeyMatchup(details.key_matchup);

  const topOvr = activePlayers.length > 0 ? Math.max(...activePlayers.map(p => p.overall)) : 0;
  const topPlayer = activePlayers.find(p => p.overall === topOvr);
  const ovrGap = threat.ovr ? parseInt(threat.ovr) - Math.round(topOvr) : null;

  const hasApproachConflict = selectedIntent === 'Win Now' &&
    (threat.role === 'Tactical' || threat.role === 'Pressure');

  const counterApproach = threat.role ? (roleCounterMap[threat.role] ?? 'Control') : 'Control';

  const hasFatigueIssue = activePlayers.filter(
    p => p.stamina !== undefined && p.stamina < 60
  ).length > 1;

  const hasPlanConflict = hasApproachConflict || hasFatigueIssue;

  return (
    <div className="command-dashboard" data-testid="weekly-command-center">
      <div className="command-dashboard-header">
        <div>
          <h1>Command Center</h1>
          <div className="command-dashboard-subtitle">Week {data.week} vs {plan.opponent.name}</div>
        </div>
        <div className="command-dashboard-metrics">
          <div>
            <span>League Rank</span>
            <strong>{leagueRank ? `#${leagueRank}` : 'n/a'} <small>of {standings.length || '?'}</small></strong>
          </div>
          <div>
            <span>Recent Form</span>
            <strong>{recentRecord}</strong>
          </div>
          <div>
            <span>Plan Status</span>
            <strong style={{ color: planStatusColor, whiteSpace: 'nowrap', fontSize: '0.7rem' }}>{planStatus.toUpperCase()}</strong>
          </div>
        </div>
      </div>

      {!planConfirmed && (
        <div className="command-alert-strip">
          <div>Attention<br />Required</div>
          <article>
            <strong>Staff recommendation</strong>
            <span>{plan.recommendations[0]?.text ?? data.current_objective}</span>
          </article>
          <article>
            <strong>Opponent file</strong>
            <span>{details.framing_line}</span>
          </article>
          <article>
            <strong>Readiness</strong>
            <span>{isReadyToLock ? 'Plan can be locked.' : `${itemsRemaining} item${itemsRemaining === 1 ? '' : 's'} need attention.`}</span>
          </article>
        </div>
      )}

      <div className="command-dashboard-main">
        <section className="dm-panel command-game-plan">
          <div className="command-panel-heading">
            <div>
              <p className="dm-kicker">Game Plan</p>
              <h3>Weekly Strategy</h3>
            </div>
            <div className="command-current-plan">
              <span>Active Doctrine</span>
              <strong>{currentApproach}</strong>
              <p>{isAggressive ? 'Pressure the weak side and accept higher exposure.' : isDefensive ? 'Protect stamina, lower risk, and win possessions.' : 'Keep the plan balanced across pressure, catches, and tempo.'}</p>
            </div>
          </div>

          <div className="command-plan-grid">
            <div className="command-approach-column">
              <p className="command-field-label">Tactical Approach</p>
              <div className="command-approach-grid">
                {approaches.map(opt => (
                  <button
                    key={opt.id}
                    onClick={() => {
                      if (!planConfirmed) onIntentChange(opt.id);
                    }}
                    disabled={planConfirmed}
                    className={selectedIntent === opt.id ? 'is-selected' : ''}
                    type="button"
                  >
                    <span>{opt.label}</span>
                    {selectedIntent === opt.id && <small>{opt.desc}</small>}
                  </button>
                ))}
              </div>
            </div>

            <div className="command-priority-column">
              <p className="command-field-label">Tactical Profile</p>
              <div className="command-tendency-grid">
                {[
                  { label: 'Target Stars', value: plan.tactics?.target_stars, tone: 'pressure' },
                  { label: 'Catch Bias', value: plan.tactics?.catch_bias, tone: 'control' },
                  { label: 'Risk', value: plan.tactics?.risk_tolerance, tone: 'risk' },
                  { label: 'Tempo', value: plan.tactics?.tempo, tone: 'tempo' },
                ].map(stat => (
                  <article key={stat.label} className={`command-tendency-card is-${stat.tone}`}>
                    <span>{stat.label}</span>
                    <strong>{pct(stat.value)}</strong>
                  </article>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="dm-panel command-control-tower">
          <div className="command-panel-heading">
            <p className="dm-kicker">Control Tower</p>
            <span style={{ color: planStatusColor }}>{planStatus}</span>
          </div>
          <p className="command-field-label">Readiness Checklist</p>
          <div className="command-readiness-list">
            {readinessChecks.map(check => (
              <div key={check.id} className={check.ready ? 'is-ready' : 'is-pending'}>
                <span aria-hidden="true">{check.ready ? 'OK' : '!'}</span>
                <div>
                  <strong>{check.label}</strong>
                  <p>{check.detail}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="command-plan-summary">
            <div><span>Approach:</span><strong>{currentApproach}</strong></div>
            <div><span>Training:</span><strong>{humanize(plan.department_orders?.training)}</strong></div>
            <div><span>Development:</span><strong>{humanize(plan.department_orders?.dev_focus)}</strong></div>
            <div>
              <span>Risk Exposure:</span>
              <strong style={{ color: isAggressive ? '#f87171' : isDefensive ? '#10b981' : '#22d3ee' }}>
                {isAggressive ? 'High' : isDefensive ? 'Low' : 'Medium'}
              </strong>
            </div>
          </div>
          <div className="command-control-squad">
            <div className="command-panel-heading">
              <p className="command-field-label">Match Card</p>
            </div>
            <MatchCard
              yourPlayers={activePlayers}
              oppPlayers={plan.opponent_lineup?.players ?? []}
              yourTeamName={data.player_club_name}
              oppTeamName={plan.opponent.name}
            />
          </div>
          {!planConfirmed ? (
            <>
              {/* Smart pre-lock flag */}
              <div style={{
                display: 'flex', alignItems: 'flex-start', gap: '10px',
                padding: '9px 12px', borderRadius: '6px', marginBottom: '10px',
                background: hasPlanConflict ? 'rgba(249,115,22,0.1)' : 'rgba(16,185,129,0.1)',
                border: `1px solid ${hasPlanConflict ? 'rgba(249,115,22,0.2)' : 'rgba(16,185,129,0.2)'}`,
                fontSize: '11px', lineHeight: 1.5,
              }}>
                <span>{hasPlanConflict ? '⚠️' : '✓'}</span>
                <span style={{ color: '#94a3b8' }}>
                  {hasPlanConflict ? (
                    <>
                      <strong style={{ color: '#f1f5f9' }}>Plan conflict:</strong>{' '}
                      {hasApproachConflict
                        ? <><em style={{ fontStyle: 'normal', color: '#f97316' }}>Aggressive</em> approach vs. {threat.role} threat — consider {counterApproach}.</>
                        : <>Multiple starters have low stamina — consider <em style={{ fontStyle: 'normal', color: '#f97316' }}>Preserve Health</em>.</>
                      }
                    </>
                  ) : (
                    <>
                      <strong style={{ color: '#f1f5f9' }}>Plan looks solid.</strong>{' '}
                      {currentApproach} approach aligns with the {threat.role ?? 'opponent'} threat. Stamina is healthy.
                    </>
                  )}
                </span>
              </div>
              {!isReadyToLock && (
                <p className="command-lock-note">{itemsRemaining} {itemsRemaining === 1 ? 'item' : 'items'} must be ready before locking the plan.</p>
              )}
              <button
                type="button"
                data-testid="lock-weekly-plan"
                aria-label="Confirm Plan"
                onClick={() => {
                  if (isReadyToLock) onSavePlan(selectedIntent, true);
                }}
                disabled={!isReadyToLock}
                className="command-primary-button"
              >
                {isReadyToLock ? 'Lock Weekly Plan' : 'Complete Readiness Checklist'}
              </button>
            </>
          ) : (
            <>
              <button type="button" data-testid="simulate-command-week" onClick={simulate} className="command-primary-button is-live">
                Simulate Match
              </button>
              <button type="button" onClick={() => onSavePlan(selectedIntent, false)} className="command-secondary-button">
                Unlock Plan
              </button>
            </>
          )}
        </section>

        <div className="command-dashboard-lower">
          <section id="command-opponent-file" className="dm-panel command-intel-card" tabIndex={-1}>
            <div className="command-panel-heading">
              <p className="dm-kicker">Opponent Intel</p>
              <span>Last: {details.last_meeting}</span>
            </div>
            <div className="command-scout-headline">
              <strong>{plan.opponent.name}</strong>
              <span>{details.opponent_record}</span>
            </div>
            <div className="command-intel-grid">
              <div>
                <div className="command-verdict command-verdict-compact">
                  {details.framing_line}
                </div>
                <div className="command-threat-card">
                  <div className="command-threat-card-icon">⚠️</div>
                  <div className="command-threat-card-body">
                    <span className="command-threat-card-kicker">Key Threat</span>
                    <span className="command-threat-card-name">{threat.name}</span>
                    {threat.role && <span className="command-threat-card-role">{threat.role}</span>}
                  </div>
                  {threat.ovr && (
                    <div className="command-threat-card-ovr">
                      <strong>{threat.ovr}</strong>
                      <span>OVR</span>
                    </div>
                  )}
                </div>
                {/* Key Threat insight rows */}
                {(threat.ovr || threat.role) && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '10px' }}>
                  {threat.ovr && ovrGap !== null && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '13px', flexShrink: 0 }}>⚡</span>
                      <span style={{ flex: 1, fontSize: '11px', color: '#94a3b8' }}>
                        {ovrGap > 0
                          ? `Outrates your top starter${topPlayer ? ` (${topPlayer.name})` : ''} by +${ovrGap} OVR`
                          : `Your top starter${topPlayer ? ` (${topPlayer.name})` : ''} covers this threat by +${Math.abs(ovrGap)} OVR`}
                      </span>
                      <span style={{
                        fontSize: '9px', fontWeight: 700, letterSpacing: '0.06em',
                        padding: '2px 6px', borderRadius: '3px',
                        background: ovrGap > 0 ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)',
                        color: ovrGap > 0 ? '#ef4444' : '#10b981',
                        border: `1px solid ${ovrGap > 0 ? 'rgba(239,68,68,0.3)' : 'rgba(16,185,129,0.3)'}`,
                        whiteSpace: 'nowrap', flexShrink: 0,
                      }}>
                        {ovrGap > 0 ? 'DANGER' : 'COVERED'}
                      </span>
                    </div>
                  )}
                  {threat.role && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '13px', flexShrink: 0 }}>🎯</span>
                      <span style={{ flex: 1, fontSize: '11px', color: '#94a3b8' }}>
                        {hasApproachConflict
                          ? `Aggressive approach vs. ${threat.role} threat — expect direct pressure`
                          : `Approach is compatible with this role`}
                      </span>
                      <span style={{
                        fontSize: '9px', fontWeight: 700, letterSpacing: '0.06em',
                        padding: '2px 6px', borderRadius: '3px',
                        background: hasApproachConflict ? 'rgba(249,115,22,0.15)' : 'rgba(16,185,129,0.15)',
                        color: hasApproachConflict ? '#f97316' : '#10b981',
                        border: `1px solid ${hasApproachConflict ? 'rgba(249,115,22,0.3)' : 'rgba(16,185,129,0.3)'}`,
                        whiteSpace: 'nowrap', flexShrink: 0,
                      }}>
                        {hasApproachConflict ? 'EXPOSED' : 'ALIGNED'}
                      </span>
                    </div>
                  )}
                  {threat.role && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '13px', flexShrink: 0 }}>🛡️</span>
                      <span style={{ flex: 1, fontSize: '11px', color: '#94a3b8' }}>
                        Counter: switch to {counterApproach} to neutralize {threat.role} threats
                      </span>
                      <span style={{
                        fontSize: '9px', fontWeight: 700, letterSpacing: '0.06em',
                        padding: '2px 6px', borderRadius: '3px',
                        background: 'rgba(34,211,238,0.1)',
                        color: '#22d3ee',
                        border: '1px solid rgba(34,211,238,0.2)',
                        whiteSpace: 'nowrap', flexShrink: 0,
                      }}>
                        COUNTER
                      </span>
                    </div>
                  )}
                </div>
                )}
                <p className="command-field-label" style={{ marginBottom: '0.3rem' }}>Scouting</p>
                <p className="command-muted-copy">{plan.recommendations[0]?.text ?? 'No recommendation returned.'}</p>
              </div>
              <div>
                <div className="command-fit-note">
                  <strong>Win Condition:</strong> {latestDashboard?.lanes?.[1]?.summary ?? 'Force the opponent into the plan you saved.'}
                </div>
                <div className="command-fit-note">
                  <strong>Best Fit:</strong> {plan.lineup?.summary ?? 'Use the active lineup snapshot.'}
                </div>
                {isAggressive ? (
                  <div className="command-fit-note is-fit"><strong>Plan Fit:</strong> Current approach is aggressive.</div>
                ) : (
                  <div className="command-fit-note is-warning"><strong>Review:</strong> Compare the current approach against staff recommendations.</div>
                )}
              </div>
            </div>
            <div className="command-week-pills">
              <div className="command-week-pill">
                <span className="command-week-pill-icon">🏋️</span>
                <div>
                  <span className="command-week-pill-label">Practice</span>
                  <span className="command-week-pill-value">{humanize(plan.department_orders?.training)}</span>
                </div>
              </div>
              <div className="command-week-pill">
                <span className="command-week-pill-icon">🎯</span>
                <div>
                  <span className="command-week-pill-label">Meeting</span>
                  <span className="command-week-pill-value">{currentApproach} Review</span>
                </div>
              </div>
              <div className="command-week-pill is-matchday">
                <span className="command-week-pill-icon">⚡</span>
                <div>
                  <span className="command-week-pill-label">Match Day</span>
                  <span className="command-week-pill-value">vs {plan.opponent.name}</span>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
