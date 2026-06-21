import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const { highlights } = vi.hoisted(() => ({ highlights: vi.fn() }));
vi.mock('../api/client', () => ({ commandApi: { highlights } }));

import MatchReplay from './MatchReplay';
import { makeReplay } from './replay/testPayload';

beforeEach(() => {
  vi.clearAllMocks();
  highlights.mockResolvedValue({ beats: [] });
});
afterEach(() => vi.restoreAllMocks());

describe('MatchReplay integrity (#2,#42,#43,#46,#47)', () => {
  it('#2: the scoreboard shows GAME POINTS for an official match, not survivors', () => {
    render(<MatchReplay data={makeReplay()} onContinue={() => {}} />);
    // Official 1-0 game points; survivors are 2-0. The headline numbers are 1/0.
    const scoreNums = document.querySelectorAll('.mr-score-num');
    expect(scoreNums[0].textContent).toBe('1');
    expect(scoreNums[1].textContent).toBe('0');
    expect(screen.getAllByText('game points').length).toBeGreaterThan(0);
  });

  it('#43: GameSegmentStrip hides games not yet reached during playback', () => {
    render(<MatchReplay data={makeReplay()} onContinue={() => {}} />);
    // Replay starts paused on the first key play (event 1, game 1). Game 2
    // has not been reached, so its chip shows the unrevealed dot, not a score.
    const strip = screen.getByTestId('replay-set-strip');
    const chips = strip.querySelectorAll('.mr-set-chip');
    expect(chips.length).toBe(2);
    // The current/not-yet-revealed game 2 must not display its 0–0 result.
    const g2 = chips[1];
    expect(g2.textContent).not.toMatch(/0–0/);
  });

  it('#46: a highlights fetch rejection hides the reel without crashing', async () => {
    highlights.mockRejectedValue(new Error('boom'));
    render(<MatchReplay data={makeReplay()} onContinue={() => {}} />);
    await waitFor(() => expect(screen.queryByTestId('replay-highlights')).not.toBeInTheDocument());
    // The replay shell still rendered.
    expect(screen.getByTestId('current-event-card')).toBeInTheDocument();
  });

  it('#47: official tokens humanize (no raw enum) in the official panel', () => {
    render(
      <MatchReplay
        data={makeReplay({
          official_state: {
            ruleset: 'official_foam',
            mode: 'no_blocking',
            game_clock: null,
            match_clock: null,
            burden: null,
            balls: [],
            rule_calls: [],
          } as never,
        })}
        onContinue={() => {}}
      />,
    );
    const panel = screen.getByTestId('official-ruleset-banner');
    expect(panel.textContent).toMatch(/No blocking/);
    expect(panel.textContent).not.toMatch(/no_blocking/);
  });

  it('#2: a legacy match scoreboard reads survivors', () => {
    render(
      <MatchReplay
        data={makeReplay({ scoring_model: 'legacy', home_survivors: 4, away_survivors: 1 })}
        onContinue={() => {}}
      />,
    );
    const scoreNums = document.querySelectorAll('.mr-score-num');
    expect(scoreNums[0].textContent).toBe('4');
    expect(scoreNums[1].textContent).toBe('1');
  });
});
