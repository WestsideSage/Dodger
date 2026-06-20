// frontend/src/components/SaveMenu.test.tsx
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

vi.mock('./new-game/IdentityStep', () => ({ IdentityStep: () => <div data-testid="stub-identity" /> }));
vi.mock('./new-game/CoachStep', () => ({ CoachStep: () => <div data-testid="stub-coach" /> }));
vi.mock('./new-game/StaffHiringStep', () => ({ StaffHiringStep: () => <div data-testid="stub-staff" /> }));
vi.mock('./new-game/StartingRecruitmentStep', () => ({ StartingRecruitmentStep: () => <div data-testid="stub-roster" /> }));

import { saveApi } from '../api/client';
import { SaveMenu } from './SaveMenu';

vi.mock('../api/client', () => ({
  saveApi: { list: vi.fn(), clubs: vi.fn(), load: vi.fn(), delete: vi.fn(), create: vi.fn(), buildFromScratch: vi.fn() },
}));

const SAVE = (over: Record<string, unknown> = {}) => ({
  path: 'a.db', name: 'My Career', club_id: 'aurora', club_name: 'Aurora Sentinels',
  season_number: 2, week: 4, last_modified: 1_700_000_000, incompatible: false, ...over,
});

beforeEach(() => {
  window.history.replaceState(null, '', '/');
  vi.clearAllMocks();
  vi.mocked(saveApi.clubs).mockResolvedValue({ clubs: [] } as never);
});
afterEach(() => vi.restoreAllMocks());

describe('SaveMenu save list (audit #9,#85,#86,#91)', () => {
  it('#9: a record renders W-L-D only when wins is defined; never a fabricated 0-0', async () => {
    vi.mocked(saveApi.list).mockResolvedValue({
      active_path: null,
      saves: [SAVE({ path: 'w.db', name: 'With Record', wins: 7, losses: 2, draws: 1 }),
              SAVE({ path: 'n.db', name: 'No Record', wins: undefined })],
    } as never);
    render(<SaveMenu onSaveLoaded={vi.fn()} />);
    // "With Record" appears in both the hero and the list row; find the save-item row specifically
    const saveItems = await screen.findAllByTestId('save-item');
    const withRow = saveItems.find(el => within(el).queryByText('With Record'))!;
    expect(within(withRow).getByText(/7-2-1/)).toBeInTheDocument();
    const noRow = saveItems.find(el => within(el).queryByText('No Record'))!;
    expect(within(noRow).queryByText(/0-0/)).not.toBeInTheDocument();
  });

  it('#85: incompatible saves are hidden by default, labeled, and non-loadable when shown', async () => {
    vi.mocked(saveApi.list).mockResolvedValue({
      active_path: null,
      saves: [SAVE({ path: 'ok.db', name: 'Good' }),
              SAVE({ path: 'bad.db', name: 'Broken', incompatible: true, wins: undefined })],
    } as never);
    render(<SaveMenu onSaveLoaded={vi.fn()} />);
    // "Good" appears in both hero and list row; wait for the save list to load
    await screen.findByTestId('save-list');
    expect(screen.queryByText('Broken')).not.toBeInTheDocument();           // hidden by default
    await userEvent.click(screen.getByTestId('toggle-incompatible'));        // reveal archive
    expect(await screen.findByText('Broken')).toBeInTheDocument();
    expect(screen.getByText('Incompatible')).toBeInTheDocument();            // labeled
    const badRow = screen.getByText('Broken').closest('[data-testid="save-item"]') as HTMLElement;
    expect(within(badRow).getByTestId('load-save-btn')).toBeDisabled();      // non-loadable
  });

  it('#86: the continue hero picks the first non-incompatible, non-debug save', async () => {
    vi.mocked(saveApi.list).mockResolvedValue({
      active_path: null,
      saves: [SAVE({ path: 'inc.db', name: 'Incompatible One', incompatible: true }),
              SAVE({ path: 'real.db', name: 'Real Career' })],
    } as never);
    render(<SaveMenu onSaveLoaded={vi.fn()} />);
    const hero = await screen.findByTestId('continue-career-hero');
    expect(within(hero).getByText('Real Career')).toBeInTheDocument();
  });

  it('#91: a load failure surfaces the error message in the menu (not a broken shell)', async () => {
    vi.mocked(saveApi.list).mockResolvedValue({ active_path: null, saves: [SAVE()] } as never);
    vi.mocked(saveApi.load).mockRejectedValue(new Error('Action blocked — refresh the page and try again.'));
    render(<SaveMenu onSaveLoaded={vi.fn()} />);
    const hero = await screen.findByTestId('continue-career-hero');
    await userEvent.click(within(hero).getByRole('button', { name: 'Continue' }));
    expect(await screen.findByText(/Action blocked/)).toBeInTheDocument();
  });
});
