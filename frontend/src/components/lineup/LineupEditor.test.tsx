import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import type { Player } from '../../types';
import { commandApi, ApiError } from '../../api/client';
import { LineupEditor } from './LineupEditor';

vi.mock('../../api/client', async (orig) => {
  const actual = await orig<typeof import('../../api/client')>();
  return {
    ...actual,
    commandApi: { saveLineup: vi.fn(), autoAssignLineup: vi.fn(), setLineupAutoReorder: vi.fn() },
  };
});

const P = (id: string, ovr: number, over: Record<string, unknown> = {}) => ({
  id, name: id, age: 24, overall: ovr, role: 'Sharpshooter',
  potential_tier: 'Mid', scouting_confidence: 2, potential_ceiling: 80, headroom: 4,
  projected_growth: 'plateauing', ovr_season_trend: null,
  ratings: { accuracy: ovr, power: ovr, dodge: ovr, catch: ovr, stamina: ovr, tactical_iq: ovr },
  ...over,
});

// 6 starters + 1 bench player who out-rates the weakest starter -> stale note.
const ROSTER = [P('s1', 80), P('s2', 78), P('s3', 76), P('s4', 74), P('s5', 72), P('s6', 60), P('benchStar', 90)] as unknown as Player[];
const DEFAULT = ['s1', 's2', 's3', 's4', 's5', 's6'];

const props = () => ({
  roster: ROSTER, defaultLineup: DEFAULT, autoReorder: true,
  onClose: vi.fn(), onSaved: vi.fn(), onAutoReorderChange: vi.fn(),
});

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.restoreAllMocks());

describe('LineupEditor truth behaviors (#51, #52, #53, #55)', () => {
  it('#53: shows the persistent stale-lineup note via the lineup-stale-note hook (anti-strip)', () => {
    render(<LineupEditor {...props()} />);
    const note = screen.getByTestId('lineup-stale-note');
    expect(note).toHaveTextContent(/benchStar/);
    expect(note).toHaveTextContent(/OVR 90/);
  });

  it('#51: a save splices the SERVER ordered_player_ids, never the local array', async () => {
    const serverOrder = ['benchStar', 's2', 's3', 's4', 's5', 's1'];
    vi.mocked(commandApi.saveLineup).mockResolvedValue({ ordered_player_ids: serverOrder, lineup_auto_reorder: true } as never);
    const p = props();
    render(<LineupEditor {...p} />);
    // select slot 1, then swap in the bench star
    await userEvent.click(screen.getByTestId('lineup-slot-0'));
    await userEvent.click(screen.getByTestId('lineup-bench-benchStar'));
    await waitFor(() => expect(p.onSaved).toHaveBeenCalledWith(serverOrder));
  });

  it('#52: a manual save that flips auto-reorder off announces it once, only on the real change', async () => {
    vi.mocked(commandApi.saveLineup).mockResolvedValue({ ordered_player_ids: DEFAULT, lineup_auto_reorder: false } as never);
    const p = props(); // autoReorder starts true
    render(<LineupEditor {...p} />);
    await userEvent.click(screen.getByTestId('lineup-slot-0'));
    await userEvent.click(screen.getByTestId('lineup-bench-benchStar'));
    expect(await screen.findByText(/Auto-reorder turned off/)).toBeInTheDocument();
    await waitFor(() => expect(p.onAutoReorderChange).toHaveBeenCalledWith(false));
  });

  it('#55: a position_count error maps to plain language with role=alert', async () => {
    vi.mocked(commandApi.saveLineup).mockRejectedValue(new ApiError('position_count', 400));
    render(<LineupEditor {...props()} />);
    await userEvent.click(screen.getByTestId('lineup-slot-0'));
    await userEvent.click(screen.getByTestId('lineup-bench-benchStar'));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/exactly 6 starters/);
  });
});
