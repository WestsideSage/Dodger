import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MatchScoreHero } from './MatchScoreHero';
import { PlayoffResolutionBanner } from './PlayoffResolutionBanner';

describe('aftermath data-* provenance (anti-strip preconditions)', () => {
  it('MatchScoreHero keeps its testid + draw/set-story hooks', () => {
    render(
      <MatchScoreHero
        homeTeam="Aurora"
        awayTeam="Granite"
        homeSurvivors={0}
        awaySurvivors={3}
        winnerClubId={null}
        homeClubId="aurora"
        scoringModel="official_foam"
        homeGamePoints={0}
        awayGamePoints={0}
        games={[{ game_number: 1, winner_club_id: 'aurora', home_points: 1, away_points: 0, result_type: 'point' }]}
        isPlayoff={false}
      />,
    );
    expect(screen.getByTestId('match-score-hero')).toBeInTheDocument();
    expect(screen.getByTestId('score-hero-draw')).toBeInTheDocument(); // #12 draw outcome
    expect(screen.getByTestId('aftermath-set-story')).toBeInTheDocument(); // #49 set strip
  });

  it('PlayoffResolutionBanner exposes data-player-outcome + data-decided-by (#11, #16)', () => {
    render(
      <PlayoffResolutionBanner
        resolution={{
          decided_by: 'seed_tiebreaker',
          player_outcome: 'eliminated',
          stage: 'Semifinal',
          narrative_note: 'Lost on the seed line.',
        } as never}
      />,
    );
    const banner = screen.getByTestId('playoff-resolution-banner');
    expect(banner).toHaveAttribute('data-player-outcome', 'eliminated');
    expect(banner).toHaveAttribute('data-decided-by', 'seed_tiebreaker');
  });

  it('PlayoffResolutionBanner renders nothing on regulation (#11/#14)', () => {
    const { container } = render(
      <PlayoffResolutionBanner resolution={{ decided_by: 'regulation' } as never} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('overtime advance: chip OVERTIME + outcome advanced (#16)', () => {
    render(
      <PlayoffResolutionBanner
        resolution={{
          decided_by: 'overtime',
          player_outcome: 'advanced',
          stage: 'Final',
          narrative_note: 'Won in OT.',
        } as never}
      />,
    );
    const b = screen.getByTestId('playoff-resolution-banner');
    expect(b).toHaveAttribute('data-player-outcome', 'advanced');
    expect(screen.getByText('OVERTIME')).toBeInTheDocument();
  });
});
