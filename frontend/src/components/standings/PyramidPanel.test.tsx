import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PyramidPanel } from './PyramidPanel';
import type { DivisionStandingsBlock, StandingRow } from '../../types';

const row = (over: Partial<StandingRow>): StandingRow => ({
  club_id: 'c', club_name: 'Club', wins: 3, losses: 1, draws: 0, points: 9,
  elimination_differential: 3, game_point_differential: 10, is_user_club: false,
  latest_approach: 'Balanced', ...over,
});

const MOVEMENT: DivisionStandingsBlock['movement'] = {
  auto_promotion: false, promotion_playoff: false, relegation_count: 0, worlds_slots: 1, summary: '',
};

const divisions: DivisionStandingsBlock[] = [
  {
    division_id: 'd1', name: 'Premier', short_name: 'PRM', tier: 1, kind: 'league',
    is_user_division: true,
    movement: MOVEMENT,
    standings: [row({ club_id: 'you', club_name: 'Granite City Hammers', is_user_club: true,
      game_point_differential: 10, elimination_differential: 3 })],
  },
];

describe('PyramidPanel (#6 — pyramid diff branch on the extracted module)', () => {
  it('official career → uses game_point_differential in the diff note', () => {
    render(<PyramidPanel divisions={divisions} isOfficial onClubClick={vi.fn()} />);
    expect(screen.getByText(/\+10 diff/)).toBeInTheDocument();
  });

  it('legacy career → uses elimination_differential in the diff note', () => {
    render(<PyramidPanel divisions={divisions} isOfficial={false} onClubClick={vi.fn()} />);
    expect(screen.getByText(/\+3 diff/)).toBeInTheDocument();
  });
});
