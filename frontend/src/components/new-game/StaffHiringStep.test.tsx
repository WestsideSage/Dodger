import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useState } from 'react';

vi.mock('../../api/client', () => ({
  saveApi: { startingStaff: vi.fn() },
}));
import { saveApi } from '../../api/client';
import { StaffHiringStep } from './StaffHiringStep';
import type { StartingStaffResponse } from '../../types';

const MARKET: StartingStaffResponse = {
  departments: ['offense', 'defense'],
  budget_k: 500,
  mid_table_payout_k: 800,
  rules: 'One head per department.',
  candidates: [
    { candidate_id: 'o-cheap', department: 'offense', tier: 'journeyman', name: 'Cheap O', rating_primary: 50, rating_secondary: 50, salary_k: 100, voice: 'v', effect_summary: 'e' },
    { candidate_id: 'o-pricey', department: 'offense', tier: 'premium', name: 'Pricey O', rating_primary: 80, rating_secondary: 80, salary_k: 900, voice: 'v', effect_summary: 'e' },
    { candidate_id: 'd-cheap', department: 'defense', tier: 'journeyman', name: 'Cheap D', rating_primary: 50, rating_secondary: 50, salary_k: 100, voice: 'v', effect_summary: 'e' },
  ],
};

// A controlled choices container so we can observe defaulting + selection.
// Top-level import (not CJS require) is required for Vite 8 + Vitest ESM.
function Harness({ seed = 7 }: { seed?: number }) {
  const [choices, setChoices] = useState<Record<string, string>>({});
  return <StaffHiringStep seed={seed} choices={choices} setChoices={setChoices} onNext={() => {}} onBack={() => {}} />;
}

beforeEach(() => vi.clearAllMocks());

describe('StaffHiringStep (audit #77 seed continuity, #78 no soft-lock)', () => {
  it('#77: fetches the founding staff market with exactly the seed prop', async () => {
    vi.mocked(saveApi.startingStaff).mockResolvedValue(MARKET);
    render(<Harness seed={4242} />);
    await waitFor(() => expect(saveApi.startingStaff).toHaveBeenCalledWith(4242));
  });
  it('#78: defaults every department to its cheapest candidate and enables Next', async () => {
    vi.mocked(saveApi.startingStaff).mockResolvedValue(MARKET);
    render(<Harness />);
    await screen.findByTestId('staff-budget-bar');
    // cheapest in each dept selected => all filled => Next enabled, not over budget
    await waitFor(() => expect(screen.getByRole('button', { name: /Next: Recruit Roster/i })).toBeEnabled());
  });
  it('#78: selecting an over-budget candidate blocks Next with the cheapen-a-hire label', async () => {
    vi.mocked(saveApi.startingStaff).mockResolvedValue(MARKET);
    render(<Harness />);
    await screen.findByTestId('staff-budget-bar');
    const cards = await screen.findAllByTestId('staff-candidate-card');
    // pick the pricey offense head (900 > 500 budget)
    const pricey = cards.find(c => c.textContent?.includes('Pricey O'))!;
    await userEvent.click(pricey);
    expect(pricey).toHaveAttribute('role', 'radio');
    await waitFor(() => expect(screen.getByRole('button', { name: /Over budget/i })).toBeDisabled());
  });
});
