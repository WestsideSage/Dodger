import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

vi.mock('../standings/PlayoffBracket', () => ({ PlayoffBracket: () => <div data-testid="stub-bracket" /> }));
vi.mock('../../hooks/useApiResource', () => ({ useApiResource: () => ({ data: null }) }));

import { ChampionReveal } from './ChampionReveal';

function championBeat(payload: Record<string, unknown>) {
  return { key: 'champion', beat_index: 0, total_beats: 9, title: 'Champions', body: '', payload } as never;
}

describe('ChampionReveal (#31 honest fallback; consumes frozen P4 bracket)', () => {
  it('renders the champion hero with title_count when a champion is present', () => {
    render(<ChampionReveal beat={championBeat({ champion: { club_name: 'Granite City', wins: 9, losses: 1, draws: 0, title_count: 3 } })} onComplete={() => {}} />);
    expect(screen.getByTestId('offseason-champion')).toHaveTextContent('Granite City');
    expect(screen.getByText('3')).toBeInTheDocument(); // title_count, display-only
  });

  it('#31: renders the honest fallback when no champion was determined', () => {
    render(<ChampionReveal beat={{ key: 'champion', beat_index: 0, total_beats: 9, title: 'Champions', payload: { champion: null } } as never} onComplete={() => {}} />);
    expect(screen.getByText(/No champion determined this season/i)).toBeInTheDocument();
  });
});
