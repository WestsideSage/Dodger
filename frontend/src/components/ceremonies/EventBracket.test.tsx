import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { EventBracket } from './EventBracket';

const event = {
  event_key: 'domestic_cup', event_name: 'Domestic Cup',
  champion_club_id: 'you', champion_club_name: 'Your Club', purse_k: 0, meta: {},
  bracket: [
    { round: 'final', home_club_id: 'you', home_club_name: 'Your Club', away_club_id: 'rival', away_club_name: 'Rival', winner_club_id: 'you' },
  ],
} as never;

describe('EventBracket (data-player-outcome anti-strip)', () => {
  it('marks data-player-outcome="advanced" when the player won their match', () => {
    const { container } = render(<EventBracket event={event} playerClubId="you" />);
    expect(container.querySelector('[data-player-outcome="advanced"]')).not.toBeNull();
    expect(screen.getByText('YOU WON')).toBeInTheDocument();
  });

  it('omits data-player-outcome when the player is not in the match', () => {
    const { container } = render(<EventBracket event={event} playerClubId="someone-else" />);
    expect(container.querySelector('[data-player-outcome]')).toBeNull();
  });
});
