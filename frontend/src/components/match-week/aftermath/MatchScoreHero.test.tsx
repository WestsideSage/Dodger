import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MatchScoreHero } from './MatchScoreHero';

const base = {
  homeTeam: 'Aurora',
  awayTeam: 'Granite',
  homeClubId: 'aurora',
  homeSurvivors: 0,
  awaySurvivors: 3,
  winnerClubId: null,
  games: [{ game_number: 1, winner_club_id: 'aurora', home_points: 1, away_points: 0, result_type: 'point' }],
};

describe('MatchScoreHero (#2,#12,#49)', () => {
  it('#2: official match labels each side "game points", never the survivor count', () => {
    render(<MatchScoreHero {...base} scoringModel="official_foam" homeGamePoints={0} awayGamePoints={0} />);
    expect(screen.getAllByText('game points').length).toBeGreaterThan(0);
    expect(screen.queryByText('3 survivors')).not.toBeInTheDocument();
  });

  it('#12: a draw shows the draw badge; in playoffs the footer does NOT promise a standings point', () => {
    render(<MatchScoreHero {...base} scoringModel="official_foam" homeGamePoints={0} awayGamePoints={0} isPlayoff />);
    expect(screen.getByTestId('score-hero-draw')).toBeInTheDocument();
    expect(screen.getByText(/can't stand/i)).toBeInTheDocument();
    expect(screen.queryByText(/standings point/i)).not.toBeInTheDocument();
  });

  it('#12: a non-playoff official draw footer DOES grant a standings point', () => {
    render(<MatchScoreHero {...base} scoringModel="official_foam" homeGamePoints={0} awayGamePoints={0} isPlayoff={false} />);
    expect(screen.getByText(/standings point/i)).toBeInTheDocument();
  });

  it('#49: the set-story strip renders one chip per persisted game', () => {
    render(
      <MatchScoreHero
        {...base}
        winnerClubId="aurora"
        scoringModel="official_foam"
        homeGamePoints={1}
        awayGamePoints={0}
        games={[
          { game_number: 1, winner_club_id: 'aurora', home_points: 1, away_points: 0, result_type: 'point' },
          { game_number: 2, winner_club_id: 'granite', home_points: 0, away_points: 1, result_type: 'point' },
        ]}
      />,
    );
    const strip = screen.getByTestId('aftermath-set-story');
    // Key on the stable inner game label (span.g) — survives the class rename.
    expect(strip.querySelectorAll('span.g').length).toBe(2);
  });

  it('legacy match shows survivor count as the headline number', () => {
    render(<MatchScoreHero {...base} winnerClubId="granite" scoringModel="legacy" />);
    expect(screen.getByText('3 survivors')).toBeInTheDocument();
  });
});
