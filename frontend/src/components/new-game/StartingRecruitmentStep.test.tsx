import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../../api/client', () => ({
  saveApi: { startingProspects: vi.fn() },
}));
import { saveApi } from '../../api/client';
import { StartingRecruitmentStep } from './StartingRecruitmentStep';
import type { ProspectOption } from '../../types';

function prospect(id: string, archetype: string, over = 60): ProspectOption {
  return {
    player_id: id, name: `Player ${id}`, hometown: 'Townsville',
    public_archetype: archetype, public_ovr_band: [over - 5, over + 5],
    age: 18, potential_ceiling: over + 20, potential_tier: 'High',
    ratings: { accuracy: over, power: over, dodge: over, catch: over, stamina: over, tactical_iq: over },
  };
}
// 11 prospects so we can test the hard 11th-cap refusal. Mix archetypes for tally.
const POOL: ProspectOption[] = [
  prospect('a', 'Sharpshooter'), prospect('b', 'Sharpshooter'), prospect('c', 'Net Specialist'),
  prospect('d', 'Net Specialist'), prospect('e', 'Iron Anchor'), prospect('f', 'Two-Way Threat'),
  prospect('g', 'Skirmisher'), prospect('h', 'Ball Hawk'), prospect('i', 'Hit-and-Run'),
  prospect('j', 'Possession Specialist'), prospect('k', 'Sharpshooter'),
];

beforeEach(() => vi.clearAllMocks());

async function loaded(onCommit = vi.fn()) {
  vi.mocked(saveApi.startingProspects).mockResolvedValue({ prospects: POOL });
  render(<StartingRecruitmentStep seed={99} onCommit={onCommit} onBack={() => {}} creating={false} />);
  await screen.findAllByRole('checkbox');
  return { onCommit, rows: screen.getAllByRole('checkbox') };
}

describe('StartingRecruitmentStep (audit #22,#77,#80,#81)', () => {
  it('#77: fetches the founding prospect pool with exactly the seed prop', async () => {
    vi.mocked(saveApi.startingProspects).mockResolvedValue({ prospects: POOL });
    render(<StartingRecruitmentStep seed={314} onCommit={() => {}} onBack={() => {}} creating={false} />);
    await waitFor(() => expect(saveApi.startingProspects).toHaveBeenCalledWith(314));
  });

  it('#22: renders each prospect UNFOGGED — full ratings + numeric ceiling on the row', async () => {
    await loaded();
    const firstRow = screen.getAllByRole('checkbox')[0];
    expect(firstRow).toHaveTextContent('ACC');
    expect(firstRow).toHaveTextContent('IQ');
    expect(firstRow).toHaveTextContent(/Ceil/);
  });

  it('#81: roster bounded 6..10 — Commit disabled below 6, helper copy is state-specific', async () => {
    const { onCommit, rows } = await loaded();
    const commit = () => screen.getByRole('button', { name: /Commit Roster/i });
    expect(commit()).toBeDisabled();
    expect(screen.getByText(/Choose between 6 and 10 players/i)).toBeInTheDocument();
    for (let i = 0; i < 6; i++) await userEvent.click(rows[i]);
    expect(commit()).toBeEnabled();
    expect(screen.getByText(/Roster ready/i)).toBeInTheDocument();
    await userEvent.click(commit());
    expect(onCommit).toHaveBeenCalledWith(expect.arrayContaining([expect.any(String)]));
  });

  it('#81: hard 11th-cap refusal — a non-selected row is non-togglable once 10 are chosen', async () => {
    const { rows } = await loaded();
    for (let i = 0; i < 10; i++) await userEvent.click(rows[i]);
    expect(screen.getAllByRole('checkbox').filter(r => r.getAttribute('aria-checked') === 'true')).toHaveLength(10);
    await userEvent.click(rows[10]); // the 11th
    expect(rows[10]).toHaveAttribute('aria-checked', 'false');
    expect(screen.getAllByRole('checkbox').filter(r => r.getAttribute('aria-checked') === 'true')).toHaveLength(10);
  });

  it('#80: role-coverage tally is advisory — imbalance never blocks Commit', async () => {
    const { rows } = await loaded();
    // Select 6 rows by index: Sharpshooter×2, Net Specialist×2, Iron Anchor, Two-Way Threat.
    // Whether composition is balanced or not, Commit must be enabled (tally is advisory only).
    // Index-based selection avoids coupling to formatPlayerName's output format.
    for (let i = 0; i < 6; i++) await userEvent.click(rows[i]);
    expect(screen.getByRole('button', { name: /Commit Roster/i })).toBeEnabled();
  });
});
