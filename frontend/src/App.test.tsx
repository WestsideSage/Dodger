// frontend/src/App.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

vi.mock('./components/MatchWeek', () => ({ MatchWeek: () => <div data-testid="stub-matchweek" /> }));
vi.mock('./components/DynastyOffice', () => ({ DynastyOffice: () => <div data-testid="stub-dynasty" /> }));
vi.mock('./components/LeagueContext', () => ({ Standings: () => <div data-testid="stub-standings" /> }));
vi.mock('./components/Roster', () => ({ Roster: () => <div data-testid="stub-roster" /> }));
vi.mock('./components/SaveMenu', () => ({ SaveMenu: () => <div data-testid="stub-savemenu" /> }));
vi.mock('./components/MatchReplay', () => ({ default: () => <div data-testid="stub-replay" /> }));

import { careerApi } from './api/client';
import App from './App';

vi.mock('./api/client', () => ({
  careerApi: { saveState: vi.fn(), status: vi.fn(), unloadSave: vi.fn() },
  commandApi: { replay: vi.fn() },
}));

beforeEach(() => {
  window.history.replaceState(null, '', '/');
  vi.clearAllMocks();
});
afterEach(() => vi.restoreAllMocks());

// #82 (live-state-trust on advance): covered by classifyScreen unit test in Task 5 + e2e/maximized-playthrough-qa.spec.ts
describe('App routing / classification (audit #82-#89)', () => {
  it('#89: a save-state fetch failure falls back to the menu, not a broken shell', async () => {
    vi.mocked(careerApi.saveState).mockRejectedValue(new Error('boom'));
    render(<App />);
    expect(await screen.findByTestId('stub-savemenu')).toBeInTheDocument();
  });

  it('#83 + #84: in-season status renders the game shell with a Season N -- Week NN header', async () => {
    vi.mocked(careerApi.saveState).mockResolvedValue({ loaded: true, active_path: 'p.db' });
    vi.mocked(careerApi.status).mockResolvedValue({
      state: { state: 'in_season', season_number: 3, week: 7 },
      context: { season_year: 2031 },
    } as never);
    render(<App />);
    expect(await screen.findByTestId('stub-matchweek')).toBeInTheDocument();
    expect(screen.getByText(/Season 3 -- Week 07/)).toBeInTheDocument();
  });

  it('#83: an offseason state renders the offseason header (no Week NN)', async () => {
    vi.mocked(careerApi.saveState).mockResolvedValue({ loaded: true, active_path: 'p.db' });
    vi.mocked(careerApi.status).mockResolvedValue({
      state: { state: 'season_complete_offseason_beat', season_number: 4, week: 12 },
      context: { season_year: 2032 },
    } as never);
    render(<App />);
    await screen.findByTestId('stub-matchweek');
    expect(screen.getByText(/Season 4 -- Offseason/)).toBeInTheDocument();
    expect(screen.queryByText(/Week/)).not.toBeInTheDocument();
  });

  it('#88: switching tabs persists ?tab= and ignores unknown tabs on load', async () => {
    window.history.replaceState(null, '', '/?tab=bogus');
    vi.mocked(careerApi.saveState).mockResolvedValue({ loaded: true, active_path: 'p.db' });
    vi.mocked(careerApi.status).mockResolvedValue({
      state: { state: 'in_season', season_number: 1, week: 1 },
      context: { season_year: 2029 },
    } as never);
    render(<App />);
    await screen.findByTestId('stub-matchweek'); // bogus tab → defaults to command
    await userEvent.click(screen.getByRole('button', { name: 'Roster' }));
    expect(await screen.findByTestId('stub-roster')).toBeInTheDocument();
    expect(new URLSearchParams(window.location.search).get('tab')).toBe('roster');
  });
});
