import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RecapStandings } from './RecapStandings';

function recapBeat(payload: Record<string, unknown>) {
  return {
    key: 'recap', beat_index: 0, total_beats: 9,
    payload: { standings: [], diff_kind: 'game_points', ...payload },
  } as never;
}

describe('RecapStandings trust contract', () => {
  it('#18: shows missed-playoffs banner ONLY when the backend confirms the finish', () => {
    const { rerender } = render(<RecapStandings beat={recapBeat({ missed_playoffs: { finish: 6, total: 8, cutoff: 4 } })} onComplete={() => {}} />);
    expect(screen.getByTestId('recap-missed-playoffs')).toHaveTextContent('6th of 8');
    rerender(<RecapStandings beat={recapBeat({ missed_playoffs: undefined })} onComplete={() => {}} />);
    expect(screen.queryByTestId('recap-missed-playoffs')).not.toBeInTheDocument();
  });

  it('#17: receipts the user OWN Worlds run on a semifinal exit (the PT6 trust-break)', () => {
    render(<RecapStandings beat={recapBeat({
      pyramid: {
        champions: [], promoted: [], relegated: [], user: {},
        worlds: { champion_name: 'Granite City', runner_up_name: 'Harbor' },
        worlds_user: { result: 'semifinalist', qualified_as: 'premier_runner_up' },
      },
    })} onComplete={() => {}} />);
    expect(screen.getByTestId('recap-pyramid')).toHaveTextContent('You reached Worlds');
    expect(screen.getByTestId('recap-pyramid')).toHaveTextContent('out in the semifinal');
  });

  it('#32: league-movement banner suppressed when the user stays (no fabricated movement)', () => {
    render(<RecapStandings beat={recapBeat({
      pyramid: { champions: [], promoted: [], relegated: [], user: { movement: 'stays', division_name: 'D2' } },
    })} onComplete={() => {}} />);
    expect(screen.queryByText(/PROMOTED|RELEGATED/)).not.toBeInTheDocument();
  });

  it('#71: standings diff renders as a signed integer, never a float', () => {
    render(<RecapStandings beat={recapBeat({
      standings: [{ rank: 1, club_name: 'A', is_player_club: true, wins: 7, losses: 2, draws: 1, points: 22, diff: 14 }],
    })} onComplete={() => {}} />);
    const cell = screen.getByText('+14');
    expect(cell.textContent).not.toMatch(/\./);
  });
});
