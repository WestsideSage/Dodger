import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock the heavy children so the test exercises Roster's own sort/markup.
vi.mock('./PlayerDetailModal', () => ({ PlayerDetailModal: () => <div data-testid="stub-detail" /> }));
vi.mock('./lineup/LineupEditor', () => ({ LineupEditor: () => <div data-testid="stub-lineup" /> }));
vi.mock('./roster/Sparkline', () => ({ Sparkline: () => <svg data-testid="stub-spark" /> }));

import { useApiResource } from '../hooks/useApiResource';
import { Roster } from './Roster';

vi.mock('../hooks/useApiResource', () => ({ useApiResource: vi.fn() }));

const PLAYER = (over: Record<string, unknown> = {}) => ({
  id: 'p', name: 'Player', age: 24, overall: 70, role: 'Sharpshooter',
  potential_tier: 'Mid', scouting_confidence: 2, potential_ceiling: 80, headroom: 4,
  projected_growth: 'plateauing', ovr_season_trend: null,
  ratings: { accuracy: 70, power: 70, dodge: 70, catch: 70, stamina: 70, tactical_iq: 70 },
  ...over,
});

function mockRoster(roster: Array<ReturnType<typeof PLAYER>>, extra: Record<string, unknown> = {}) {
  vi.mocked(useApiResource).mockReturnValue({
    data: { roster, default_lineup: [], lineup_auto_reorder: true, open_promise_player_ids: [], ...extra },
    loading: false, error: null, setData: vi.fn(), setError: vi.fn(), setLoading: vi.fn(),
  } as never);
}

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.restoreAllMocks());

function rowNames(): string[] {
  return screen.getAllByTestId('roster-row').map((r) => within(r).getByTestId('roster-row-name').textContent ?? '');
}

describe('Roster potential sort (audit #57 — single tier vocabulary, no silent bucket)', () => {
  it('orders ALL five rendered tiers distinctly (Mid/Low/Raw no longer collapse)', async () => {
    mockRoster([
      PLAYER({ id: 'raw',   name: 'Raw One',   potential_tier: 'Raw',   overall: 60 }),
      PLAYER({ id: 'elite', name: 'Elite One', potential_tier: 'Elite', overall: 60 }),
      PLAYER({ id: 'low',   name: 'Low One',   potential_tier: 'Low',   overall: 60 }),
      PLAYER({ id: 'high',  name: 'High One',  potential_tier: 'High',  overall: 60 }),
      PLAYER({ id: 'mid',   name: 'Mid One',   potential_tier: 'Mid',   overall: 60 }),
    ]);
    render(<Roster />);
    await userEvent.selectOptions(screen.getByTestId('roster-sort'), 'potential');
    expect(rowNames()).toEqual(['Elite One', 'High One', 'Mid One', 'Low One', 'Raw One']);
  });
  it('breaks ties within a tier by OVR descending', async () => {
    mockRoster([
      PLAYER({ id: 'midlo', name: 'Mid Lower', potential_tier: 'Mid', overall: 65 }),
      PLAYER({ id: 'midhi', name: 'Mid Higher', potential_tier: 'Mid', overall: 88 }),
    ]);
    render(<Roster />);
    await userEvent.selectOptions(screen.getByTestId('roster-sort'), 'potential');
    expect(rowNames()).toEqual(['Mid Higher', 'Mid Lower']);
  });
});
