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
    // Class names moved to CSS Modules; key on the stable data-score-side hook.
    expect(document.querySelector('[data-score-side="home"]')?.textContent).toBe('1');
    expect(document.querySelector('[data-score-side="away"]')?.textContent).toBe('0');
    expect(screen.getAllByText('game points').length).toBeGreaterThan(0);
  });

  it('#43: GameSegmentStrip hides games not yet reached during playback', () => {
    render(<MatchReplay data={makeReplay()} onContinue={() => {}} />);
    // Replay starts paused on the first key play (event 1, game 1). Game 2
    // has not been reached, so its chip shows the unrevealed dot, not a score.
    // Class names moved to CSS Modules; key on the stable data-set-chip hook.
    const strip = screen.getByTestId('replay-set-strip');
    const chips = strip.querySelectorAll('[data-set-chip]');
    expect(chips.length).toBe(2);
    // The current/not-yet-revealed game 2 must not display its 0–0 result.
    const g2 = chips[1];
    expect(g2).toHaveAttribute('data-set-revealed', 'false');
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
    expect(document.querySelector('[data-score-side="home"]')?.textContent).toBe('4');
    expect(document.querySelector('[data-score-side="away"]')?.textContent).toBe('1');
  });

  it('#41/Task13: the live court reflects ONLY the current event score_state', () => {
    // The replay opens paused on the first key play (event index 1). At that
    // point the current event's score_state has p2 AND p4 eliminated. p2 was
    // out in game 1 event 0; p4 goes out on the caught play at event 1.
    render(<MatchReplay data={makeReplay()} onContinue={() => {}} />);
    // LiveCourtCanvas is wired in place of DarkCourt — its tokens are the truth.
    expect(screen.getByLabelText(/live .*court/i)).toBeInTheDocument();
    const p2 = document.querySelector('[data-player-token="p2"]');
    const p4 = document.querySelector('[data-player-token="p4"]');
    expect(p2).toHaveAttribute('data-extinguished', 'true');
    expect(p4).toHaveAttribute('data-extinguished', 'true');
    // A player never eliminated stays lit.
    const p1 = document.querySelector('[data-player-token="p1"]');
    expect(p1).toHaveAttribute('data-extinguished', 'false');
  });
});
