import { useEffect, useMemo, useState } from 'react';
import type { CommandCenterResponse, StandingRow, StandingsResponse } from '../../../types';

const approaches = [
  { id: 'Balanced', label: 'Balanced', desc: 'Even focus on offense and defense.' },
  { id: 'Win Now', label: 'Aggressive', desc: 'Higher pressure, higher foul/risk exposure.' },
  { id: 'Prepare For Playoffs', label: 'Control', desc: 'Slower tempo, better possession security.' },
  { id: 'Preserve Health', label: 'Defensive', desc: 'Lower throwing volume, stronger catch stability.' },
];

const intentLabels = new Map(approaches.map(approach => [approach.id, approach.label]));

function pct(value: number | undefined) {
  if (typeof value !== 'number') return 'n/a';
  return `${Math.round(value * 100)}%`;
}

function humanize(value: string | undefined) {
  return value ? value.replaceAll('_', ' ').toLowerCase() : 'not set';
}

function resultTone(result: string | undefined) {
  if (result === 'Win') return '#10b981';
  if (result === 'Loss') return '#f43f5e';
  return '#f59e0b';
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
            <strong style={{ color: planStatusColor }}>{planStatus.toUpperCase()}</strong>
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
        <section id="command-opponent-file" className="dm-panel command-opponent-file" tabIndex={-1}>
          <div className="command-panel-heading">
            <p className="dm-kicker">Opponent Briefing</p>
            <span>Last: {details.last_meeting}</span>
          </div>
          <h2>{plan.opponent.name}</h2>
          <div className="command-opponent-meta">
            <span>{details.opponent_record}</span>
            <em>{details.key_matchup}</em>
          </div>
          <div className="command-verdict">
            {details.framing_line}
          </div>
          <div className="command-two-column">
            <div>
              <p className="dm-kicker">Staff Reads</p>
              <ul>
                {plan.recommendations.slice(0, 3).map(recommendation => (
                  <li key={`${recommendation.department}-${recommendation.text}`}>
                    <span>{recommendation.department}</span>
                    {recommendation.text}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="dm-kicker">Warnings</p>
              {plan.warnings.length ? (
                <ul>
                  {plan.warnings.slice(0, 3).map(warning => (
                    <li key={warning}><span>Risk</span>{warning}</li>
                  ))}
                </ul>
              ) : (
                <p className="command-muted-copy">No command warnings on the current plan.</p>
              )}
            </div>
          </div>
          <a className="command-secondary-link" href="#command-opponent-file">Opponent file reviewed</a>
        </section>

        <section className="dm-panel command-game-plan">
          <div className="command-panel-heading">
            <div>
              <p className="dm-kicker">Game Plan</p>
              <h3>Weekly Strategy</h3>
            </div>
            <div className="command-current-plan">
              <span>Current Plan:</span>
              <strong>{currentApproach} / {humanize(plan.department_orders?.training)} / {humanize(plan.department_orders?.dev_focus)}</strong>
            </div>
          </div>

          <div className="command-plan-grid">
            <div>
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
              <div className="command-impact-list">
                <article>
                  <span>Win Condition</span>
                  <strong>{latestDashboard?.lanes?.[1]?.summary ?? 'Force the opponent into the plan you saved.'}</strong>
                </article>
                <article>
                  <span>Risk</span>
                  <strong>{plan.warnings[0] ?? 'No current command warning.'}</strong>
                </article>
                <article>
                  <span>Best Fit</span>
                  <strong>{plan.lineup?.summary ?? 'Use the active lineup snapshot.'}</strong>
                </article>
              </div>
            </div>

            <div>
              <p className="command-field-label">Focus Priorities</p>
              <div className="command-priority-list">
                {[
                  { label: 'Target Stars', value: plan.tactics?.target_stars },
                  { label: 'Catch Bias', value: plan.tactics?.catch_bias },
                  { label: 'Risk Tolerance', value: plan.tactics?.risk_tolerance },
                  { label: 'Tempo', value: plan.tactics?.tempo },
                ].map(stat => (
                  <div key={stat.label}>
                    <div>
                      <span>{stat.label}</span>
                      <span>{pct(stat.value)}</span>
                    </div>
                    <meter min={0} max={1} value={stat.value ?? 0} />
                  </div>
                ))}
              </div>

              <div className="command-orders-grid">
                <div>
                  <span>Training Order</span>
                  <strong>{humanize(plan.department_orders?.training)}</strong>
                </div>
                <div>
                  <span>Development Focus</span>
                  <strong>{humanize(plan.department_orders?.dev_focus)}</strong>
                </div>
                <div>
                  <span>Medical Order</span>
                  <strong>{humanize(plan.department_orders?.medical)}</strong>
                </div>
                <div>
                  <span>Scouting Order</span>
                  <strong>{humanize(plan.department_orders?.scouting)}</strong>
                </div>
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
          {!planConfirmed ? (
            <>
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
      </div>

      <div className="command-dashboard-lower">
        <section className="dm-panel">
          <div className="command-panel-heading">
            <p className="dm-kicker">Player Readiness</p>
            <span>{activePlayers.length}/6 ready</span>
          </div>
          <div className="command-player-list">
            {activePlayers.map((player, index) => (
              <div key={player.id}>
                <span>{index + 1}</span>
                <strong>{player.name}</strong>
                <small>{Math.round(player.overall)}</small>
                <small>{player.stamina === undefined ? 'ready' : `${Math.round(player.stamina)} sta`}</small>
              </div>
            ))}
          </div>
        </section>

        <section className="dm-panel">
          <div className="command-panel-heading">
            <p className="dm-kicker">Team Form</p>
            <span>{userStanding ? `${userStanding.wins}-${userStanding.losses}-${userStanding.draws}` : recentRecord}</span>
          </div>
          <div className="command-stat-list">
            <div><strong>{userStanding?.points ?? '-'}</strong><span>Points</span></div>
            <div><strong>{userStanding?.elimination_differential ?? '-'}</strong><span>Elim Diff</span></div>
            <div><strong style={{ color: resultTone(latestDashboard?.result) }}>{latestDashboard?.result ?? '-'}</strong><span>Last Result</span></div>
            <div><strong>{data.history.length}</strong><span>Plans Saved</span></div>
          </div>
        </section>

        <section className="dm-panel">
          <div className="command-panel-heading">
            <p className="dm-kicker">Scout Snapshot</p>
          </div>
          <p className="command-muted-copy">{details.key_matchup}</p>
          <p className="command-muted-copy">{plan.recommendations[0]?.text ?? 'No recommendation returned.'}</p>
          {isAggressive ? (
            <div className="command-fit-note is-fit"><strong>Plan Fit:</strong> Current approach is aggressive.</div>
          ) : (
            <div className="command-fit-note is-warning"><strong>Review:</strong> Compare the current approach against staff recommendations.</div>
          )}
        </section>

        <section className="dm-panel">
          <div className="command-panel-heading">
            <p className="dm-kicker">Week Timeline</p>
          </div>
          <div className="command-week-timeline">
            <div><strong>Practice</strong><span>{humanize(plan.department_orders?.training)}</span></div>
            <div><strong>Team Meeting</strong><span>{currentApproach} review</span></div>
            <div><strong>Match Day</strong><span>vs {plan.opponent.name}</span></div>
          </div>
        </section>
      </div>
    </div>
  );
}
