import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { StandingsResponse, StandingRow, DivisionStandingsBlock } from '../types';

const mockUseApiResource = vi.fn();
vi.mock('../hooks/useApiResource', () => ({
  useApiResource: (url: string) => mockUseApiResource(url),
}));
// Keep Standings' own logic in scope; stub the heavy children.
vi.mock('./standings/PlayoffBracket', () => ({ PlayoffBracket: () => <div data-testid="stub-bracket" /> }));
vi.mock('./dynasty/history/ProgramModal', () => ({ ProgramModal: () => <div data-testid="stub-modal" /> }));

import { Standings } from './LeagueContext';

const row = (over: Partial<StandingRow>): StandingRow => ({
  club_id: 'c', club_name: 'Club', wins: 3, losses: 1, draws: 0, points: 9,
  elimination_differential: 5, game_point_differential: 7, is_user_club: false,
  latest_approach: 'Balanced', ...over,
});

function standings(over: Partial<StandingsResponse> = {}): StandingsResponse {
  return {
    season_id: 'season_1',
    standings: [
      row({ club_id: 'you', club_name: 'Granite City Hammers', is_user_club: true, latest_approach: 'Aggressive' }),
      row({ club_id: 'them', club_name: 'Harbor Wolves' }),
    ],
    total_weeks: 12, current_week: 5, playoff_spots: 4,
    is_official_career: true,
    recent_matches: [],
    ...over,
  };
}

// pyramidDivisions: two DivisionStandingsBlock entries so data.divisions.length > 1
// triggers the PyramidPanel render. The first entry carries
// game_point_differential: 10 and elimination_differential: 3 so both diff-branch
// assertions are non-tautological.
const MOVEMENT: DivisionStandingsBlock['movement'] = {
  auto_promotion: false, promotion_playoff: false, relegation_count: 0, worlds_slots: 1, summary: '',
};
const pyramidDivisions: DivisionStandingsBlock[] = [
  {
    division_id: 'd1', name: 'Premier', short_name: 'PRM', tier: 1, kind: 'league',
    is_user_division: true,
    movement: MOVEMENT,
    standings: [row({ club_id: 'you', club_name: 'Granite City Hammers', is_user_club: true,
      game_point_differential: 10, elimination_differential: 3 })],
  },
  {
    division_id: 'd2', name: 'Circuit', short_name: 'CRC', tier: 2, kind: 'league',
    is_user_division: false,
    movement: MOVEMENT,
    standings: [row({ club_id: 'ai', club_name: 'Harbor Wolves',
      game_point_differential: 5, elimination_differential: 2 })],
  },
];

function mountWith(data: StandingsResponse, bracket: unknown = { active: false }) {
  mockUseApiResource.mockImplementation((url: string) => {
    if (url === '/api/standings') return { data, error: null, loading: false };
    if (url === '/api/playoffs/bracket') return { data: bracket, error: null, loading: false };
    return { data: null, error: null, loading: false };
  });
  return render(<Standings />);
}

beforeEach(() => mockUseApiResource.mockReset());

describe('Standings (Phase 4 — #6/#7/#15 + anti-strip)', () => {
  it('anti-strip: keeps the data-screen-label hook', () => {
    const { container } = mountWith(standings());
    expect(container.querySelector('[data-screen-label="04 Standings"]')).not.toBeNull();
  });

  it('#6: official career → "GP Diff" header', () => {
    mountWith(standings({ is_official_career: true }));
    expect(screen.getByText('GP Diff')).toBeInTheDocument();
    expect(screen.queryByText('Survivor Diff')).not.toBeInTheDocument();
  });

  it('#6: legacy career → "Survivor Diff" header', () => {
    mountWith(standings({ is_official_career: false }));
    expect(screen.getByText('Survivor Diff')).toBeInTheDocument();
    expect(screen.queryByText('GP Diff')).not.toBeInTheDocument();
  });

  it('#6 Pyramid: official career → PyramidPanel uses game_point_differential in diff note', () => {
    mountWith(standings({ is_official_career: true, divisions: pyramidDivisions }));
    expect(screen.getByText(/\+10 diff/)).toBeInTheDocument();
  });

  it('#6 Pyramid: legacy career → PyramidPanel uses elimination_differential in diff note', () => {
    mountWith(standings({ is_official_career: false, divisions: pyramidDivisions }));
    expect(screen.getByText(/\+3 diff/)).toBeInTheDocument();
  });

  it('#7: Plan badge renders the command-center vocabulary', () => {
    mountWith(standings());
    // user row is Aggressive; opponent Balanced
    expect(screen.getAllByText('Aggressive').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Balanced').length).toBeGreaterThan(0);
  });

  it('#15: draw in the wire shows "Draw", does not fabricate a win', () => {
    mountWith(standings({
      recent_matches: [
        { match_id: 'm1', week: 3, summary: 'Granite City Hammers 0-0 Harbor Wolves', winner_name: 'Draw' },
      ],
    }));
    expect(screen.getByText('Draw')).toBeInTheDocument();
  });

  it('#15: unparseable summary falls back to raw text, never dropped', () => {
    mountWith(standings({
      recent_matches: [
        { match_id: 'm2', week: 4, summary: 'Bye week — no match', winner_name: '' },
      ],
    }));
    expect(screen.getByText(/Bye week — no match/)).toBeInTheDocument();
  });
});

describe('Standings phase-aware copy (#33 tiebreaker, #34 race/need)', () => {
  it('#33: tiebreaker SOFT at week 1 (race not yet meaningful)', () => {
    mountWith(standings({ current_week: 1 }));
    expect(screen.getByText('Race Developing')).toBeInTheDocument();
    expect(screen.getByText('Race not yet meaningful')).toBeInTheDocument();
  });

  it('#33: tiebreaker HIDDEN in the offseason', () => {
    mountWith(standings({ is_offseason: true }));
    expect(screen.getByText('Race Concluded')).toBeInTheDocument();
    expect(screen.getByText('Season concluded')).toBeInTheDocument();
  });

  it('#33: tiebreaker LIVE mid-season with points on the board', () => {
    mountWith(standings({ current_week: 6 }));
    // "Top N Race" is the tiebreaker panel h3 (playoff_spots: 4 → "Top 4 Race").
    // Scoped to the heading to avoid the "Playoff Race" glance label, which also ends in "Race".
    expect(screen.getByRole('heading', { name: /^Top \d+ Race$/ })).toBeInTheDocument();
  });

  it('#34: offseason replaces race/need copy with concluded-season phrasing', () => {
    mountWith(standings({ is_offseason: true }));
    expect(screen.getByText('SEASON CONCLUDED')).toBeInTheDocument();
    expect(screen.getByText('Season Concluded')).toBeInTheDocument();
  });

  it('#34: when playoffs are live, the bracket-decides copy replaces regular-season math', () => {
    mountWith(standings({ current_week: 12 }), { active: true });
    expect(screen.getByText('PLAYOFFS LIVE')).toBeInTheDocument();
    expect(screen.getByText('Bracket Decides')).toBeInTheDocument();
  });
});
