// Phase-4-owned NON-REGRESSION GUARD on the #38 behavior. LeagueView.tsx is
// Phase-5-owned (frozen this window); this test only ASSERTS its current truth
// and must stay green through the P5 reskin. It does NOT modify the file.
//
// Mock shape verified against LeagueView.tsx (LeagueData interface):
//   - `directory`: Array<{ club_id; name }>
//   - `dynasty_rankings`, `records`, `hof`, `rivalries`: required
//   - `worlds`: optional Array<{ season_id; champion_club_id; champion_name;
//       runner_up_club_id; runner_up_name }> — NO final_match_id
//   - useApiResource<LeagueData>('/api/history/league') — single call per render.
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockUseApiResource = vi.fn();
vi.mock('../../../hooks/useApiResource', () => ({
  useApiResource: (_url: string) => mockUseApiResource(_url),
}));

import { LeagueView } from './LeagueView';

const BASE_LEAGUE_DATA = {
  directory: [],
  dynasty_rankings: [],
  records: [],
  hof: [],
  rivalries: [],
};

beforeEach(() => mockUseApiResource.mockReset());

describe('LeagueView worlds roll (#38 guard — cross-phase lock)', () => {
  it('renders the World Championship roll only when worlds data exists', () => {
    mockUseApiResource.mockReturnValue({
      data: {
        ...BASE_LEAGUE_DATA,
        worlds: [
          {
            season_id: 'season_3',
            champion_club_id: 'c1',
            champion_name: 'Granite City Hammers',
            runner_up_club_id: 'c2',
            runner_up_name: 'Harbor Wolves',
          },
        ],
      },
      error: null,
      loading: false,
    });
    render(<LeagueView />);
    expect(screen.getByText('World Championship')).toBeInTheDocument();
    // runner_up clause present only when runner_up_name is set
    expect(screen.getByText(/beat Harbor Wolves in the final/)).toBeInTheDocument();
  });

  it('does NOT render the worlds roll when worlds is empty', () => {
    mockUseApiResource.mockReturnValue({
      data: { ...BASE_LEAGUE_DATA, worlds: [] },
      error: null,
      loading: false,
    });
    render(<LeagueView />);
    expect(screen.queryByText('World Championship')).not.toBeInTheDocument();
  });

  it('does NOT render the worlds roll when worlds is absent (legacy saves)', () => {
    mockUseApiResource.mockReturnValue({
      data: { ...BASE_LEAGUE_DATA },
      error: null,
      loading: false,
    });
    render(<LeagueView />);
    expect(screen.queryByText('World Championship')).not.toBeInTheDocument();
  });
});
