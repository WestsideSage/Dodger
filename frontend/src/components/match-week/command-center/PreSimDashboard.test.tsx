import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PreSimDashboard } from './PreSimDashboard';
import type {
  CoachPolicy,
  CommandCenterResponse,
  CommandCenterPlan,
  CommandHistoryRecord,
  WeekBriefing,
} from '../../../types';

const TACTICS: CoachPolicy = {
  approach: 'Balanced',
  target_focus: 'Best Available',
  catch_posture: 'Balanced',
  rush_commit: 'Balanced',
  rush_target: 'Center',
} as never;

function makeBriefing(over: Partial<WeekBriefing> = {}): WeekBriefing {
  return {
    readiness: { gates: [], total: 0, ready_count: 0, is_ready_to_lock: true, items_remaining: 0, next_issue: 'No blockers' },
    edge: { net_starter_ovr: 3, standing: 'favorite' },
    fatigue: { at_risk_count: 0, min_stamina: null },
    form: { recent_record: 'W-W-L', rank: 2, regular_season_record: '5-2', games_remaining: 4 },
    threat: null,
    match_context: { is_home: true, playoff_stage: null },
    league_leader: null,
    staff_recommendation: { action: 'keep', recommended_intent: null, reason: '' },
    recommendation: { verdict: 'aligned', advised_intent: null, reason: '', advisory: true },
    ...over,
  } as WeekBriefing;
}

function makePlan(over: Partial<CommandCenterPlan> = {}): CommandCenterPlan {
  return {
    season_id: '2031',
    week: 3,
    player_club_id: 'aurora',
    is_bye: false,
    intent: 'Balanced',
    available_intents: ['Balanced', 'Win Now'],
    opponent: { club_id: 'granite', name: 'Granite' },
    department_heads: [],
    department_orders: { training: 'BALANCED', dev_focus: 'BALANCED' },
    recommendations: [],
    warnings: [],
    lineup: { player_ids: [], players: [], summary: '' },
    tactics: TACTICS,
    history_count: 0,
    briefing: makeBriefing(),
    ...over,
  } as CommandCenterPlan;
}

function makeHistory(records: Array<Partial<CommandHistoryRecord['dashboard']> & { week: number }>): CommandHistoryRecord[] {
  return records.map((d) => ({
    history_id: d.week,
    season_id: '2031',
    week: d.week,
    club_id: 'aurora',
    match_id: `m${d.week}`,
    opponent_club_id: 'granite',
    intent: 'Balanced',
    plan: makePlan(),
    dashboard: {
      season_id: '2031',
      week: d.week,
      match_id: `m${d.week}`,
      opponent_name: d.opponent_name ?? 'Granite',
      result: d.result ?? 'Win',
      score: d.score ?? null,
      lanes: [],
    },
    created_at: '2031-01-01',
  })) as never;
}

function makeData(over: Partial<CommandCenterResponse> = {}): CommandCenterResponse {
  return {
    season_id: '2031',
    week: 3,
    player_club_id: 'aurora',
    player_club_name: 'Aurora',
    current_objective: 'Win the week.',
    plan: makePlan(),
    latest_dashboard: null,
    history: [],
    ...over,
  } as CommandCenterResponse;
}

const noop = vi.fn();
const cb = {
  simulate: noop,
  onSavePlan: noop,
  onSavePolicy: noop,
  onSaveDevFocus: noop,
  selectedIntent: 'Balanced',
  onIntentChange: noop,
  planConfirmed: false,
  saving: false,
  fastForward: noop,
  onScout: noop,
  onConfirmLineup: noop,
};

describe('PreSimDashboard Command Center truth (#3,#32,#39,#93,#94,#95)', () => {
  it('#3: the League Wire shows the game-point scoreline, not a bare Win/Loss', () => {
    render(
      <PreSimDashboard
        data={makeData({ history: makeHistory([{ week: 2, result: 'Win', score: '9–2', opponent_name: 'Granite' }]) })}
        {...cb}
      />,
    );
    const rail = screen.getByTestId('secondary-intel-rail');
    expect(rail.textContent).toMatch(/9–2/);
    expect(rail.textContent).toMatch(/Granite/);
  });

  it('#32: an empty wire shows one honest static line in the rail (no fabricated marquee)', () => {
    render(<PreSimDashboard data={makeData({ history: [] })} {...cb} />);
    const rail = screen.getByTestId('secondary-intel-rail');
    expect(rail).toBeInTheDocument();
    expect(rail.className).not.toMatch(/has-news/);
    expect(rail.textContent).toMatch(/Quiet week on the wire/i);
  });

  it('#39: a bye week shows ADVANCE BYE WEEK and no fatigue/recover panels', () => {
    render(
      <PreSimDashboard
        data={makeData({ plan: makePlan({ is_bye: true }) })}
        {...cb}
        planConfirmed
      />,
    );
    expect(screen.getByText(/ADVANCE BYE WEEK/i)).toBeInTheDocument();
    // A bye has no opponent matchup band and no current-objective directive.
    expect(screen.queryByTestId('matchup-band')).not.toBeInTheDocument();
    expect(screen.queryByTestId('current-objective')).not.toBeInTheDocument();
  });

  it('#94: alignment is NOT green while operational orders are pending', () => {
    // A pending department order (empty training) drives operationalPending > 0.
    render(
      <PreSimDashboard
        data={makeData({ plan: makePlan({ department_orders: { training: '', dev_focus: 'BALANCED' } }) })}
        {...cb}
      />,
    );
    const readout = screen.getByTestId('plan-readout');
    expect(readout.className).toMatch(/is-warning|warning/);
    expect(readout.textContent).toMatch(/Misaligned/);
  });

  it('#94: alignment IS aligned when every order is set and staff agrees', () => {
    render(<PreSimDashboard data={makeData()} {...cb} />);
    const readout = screen.getByTestId('plan-readout');
    expect(readout.className).not.toMatch(/is-warning/);
    expect(readout.textContent).toMatch(/Aligned/);
  });

  it('#93/#95: the command center mounts from defaults without crashing on a sparse payload', () => {
    render(<PreSimDashboard data={makeData()} {...cb} />);
    expect(screen.getByTestId('weekly-command-center')).toBeInTheDocument();
    expect(screen.getByTestId('presim-command-strip')).toBeInTheDocument();
    expect(screen.getByTestId('matchup-band')).toBeInTheDocument();
  });
});
