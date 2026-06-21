// frontend/src/components/dynasty/history/LeagueView.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { LeagueView } from './LeagueView';

const useApiResource = vi.fn();
vi.mock('../../../hooks/useApiResource', () => ({ useApiResource: (...a: unknown[]) => useApiResource(...a) }));
vi.mock('./ProgramModal', () => ({ ProgramModal: () => <div data-testid="stub-program-modal" /> }));

function leagueData(overrides: Record<string, unknown> = {}) {
  return {
    directory: [{ club_id: 'hammers', name: 'Granite City Hammers' }],
    dynasty_rankings: [],
    records: [{
      record_type: 'most_eliminations_season', holder_id: 'plr_zed_99', record_value: 41,
      set_in_season: 'season_2', record: { holder_name: 'Zed Calloway' },
    }],
    hof: [],
    rivalries: [],
    ...overrides,
  };
}

describe('LeagueView (#66 holder name, #38 worlds-gated, #35 empty states)', () => {
  it('#66: records use the persisted holder display name, not the humanized id', () => {
    useApiResource.mockReturnValue({ data: leagueData(), error: null, loading: false });
    render(<LeagueView />);
    expect(screen.getByText(/Zed Calloway/)).toBeInTheDocument();
    expect(screen.queryByText(/plr zed 99/i)).not.toBeInTheDocument();
  });
  it('#38: the World Championship roll renders only when worlds data exists', () => {
    useApiResource.mockReturnValue({ data: leagueData(), error: null, loading: false });
    const { rerender } = render(<LeagueView />);
    expect(screen.queryByText('World Championship')).not.toBeInTheDocument();
    useApiResource.mockReturnValue({
      data: leagueData({ worlds: [{ season_id: 'season_2', champion_club_id: 'hammers', champion_name: 'Granite City Hammers', runner_up_club_id: null, runner_up_name: null }] }),
      error: null, loading: false,
    });
    rerender(<LeagueView />);
    expect(screen.getByText('World Championship')).toBeInTheDocument();
  });
  it('#35 (LeagueView surface only): empty dynasty rankings show a truthful empty state, not a fabricated row', () => {
    // NOTE: #35 is PRIMARILY a Phase-6 behavior (ceremony / offseason empty states);
    // it is assigned to Phase 6 in the preservation checklist. The assertion below is a
    // DEFENSE-IN-DEPTH guard for the LeagueView surface only. Phase 6 owns the full #35
    // contract; the Phase-6 implementer must NOT skip #35 on other surfaces.
    useApiResource.mockReturnValue({ data: leagueData(), error: null, loading: false });
    render(<LeagueView />);
    expect(screen.getByText(/No dynasty rankings yet/)).toBeInTheDocument();
  });
});
