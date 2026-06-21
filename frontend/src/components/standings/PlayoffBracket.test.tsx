import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PlayoffBracket } from './PlayoffBracket';
import type { PlayoffBracketResponse, PlayoffBracketMatch } from '../../types';

const baseMatch = (over: Partial<PlayoffBracketMatch>): PlayoffBracketMatch => ({
  match_id: 'm1',
  home_club_id: 'you',
  home_club_name: 'Granite City Hammers',
  away_club_id: 'them',
  away_club_name: 'Harbor Wolves',
  home_survivors: 0,
  away_survivors: 3,
  home_game_points: 2,
  away_game_points: 1,
  scoring_model: 'official_foam',
  winner_club_id: 'you',
  status: 'played',
  decided_by: 'regulation',
  narrative_note: null,
  ...over,
});

function bracket(matches: PlayoffBracketMatch[], over: Partial<PlayoffBracketResponse> = {}): PlayoffBracketResponse {
  return {
    active: true,
    seeds: [],
    rounds: [{ round: 'semifinal', matches }],
    player_club_id: 'you',
    ...over,
  };
}

describe('PlayoffBracket (Phase 4 — #16 + anti-strip)', () => {
  it('renders the panel with its data-testid provenance', () => {
    render(<PlayoffBracket data={bracket([baseMatch({})])} />);
    expect(screen.getByTestId('playoff-bracket')).toBeInTheDocument();
  });

  it('#16: player-outcome ribbon = advanced when the user played and won', () => {
    const { container } = render(<PlayoffBracket data={bracket([baseMatch({ winner_club_id: 'you' })])} />);
    expect(container.querySelector('[data-player-outcome="advanced"]')).not.toBeNull();
    expect(screen.getByText('YOU ADVANCED')).toBeInTheDocument();
  });

  it('#16: player-outcome ribbon = eliminated when the user played and lost', () => {
    const { container } = render(<PlayoffBracket data={bracket([baseMatch({ winner_club_id: 'them' })])} />);
    expect(container.querySelector('[data-player-outcome="eliminated"]')).not.toBeNull();
    expect(screen.getByText('YOU ELIMINATED')).toBeInTheDocument();
  });

  it('#16: NO ribbon when the user is not in the match', () => {
    const { container } = render(
      <PlayoffBracket data={bracket([baseMatch({ home_club_id: 'a', away_club_id: 'b', winner_club_id: 'a' })])} />,
    );
    expect(container.querySelector('[data-player-outcome]')).toBeNull();
  });

  it('#16: NO ribbon when the match is unplayed', () => {
    const { container } = render(
      <PlayoffBracket data={bracket([baseMatch({ status: 'scheduled', winner_club_id: null })])} />,
    );
    expect(container.querySelector('[data-player-outcome]')).toBeNull();
  });

  it('anti-strip: decided_by chip keeps its testid + data attribute on a tiebreaker', () => {
    render(<PlayoffBracket data={bracket([baseMatch({ decided_by: 'overtime' })])} />);
    const chip = screen.getByTestId('playoff-bracket-decided-by-chip');
    expect(chip).toHaveAttribute('data-decided-by', 'overtime');
    expect(chip).toHaveTextContent('OT');
  });

  it('renders nothing when the bracket is inactive', () => {
    const { container } = render(<PlayoffBracket data={{ active: false }} />);
    expect(container.firstChild).toBeNull();
  });
});
