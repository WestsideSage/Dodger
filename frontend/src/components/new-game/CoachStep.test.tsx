import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { it, expect, vi } from 'vitest';
import { CoachStep } from './CoachStep';

const coach = { coach_name: '', coach_backstory: 'Tactical Mastermind' };

it('keeps archetype options as aria-pressed toggles and gates Next on a coach name', async () => {
  const setCoach = vi.fn();
  const onNext = vi.fn();
  render(<CoachStep coach={coach} setCoach={setCoach} onNext={onNext} onBack={() => {}} />);
  expect(screen.getByRole('button', { name: /Next: Recruit Roster/i })).toBeDisabled();
  const lifer = screen.getByRole('button', { name: /Former Player/i });
  expect(lifer).toHaveAttribute('aria-pressed', 'false');
  await userEvent.click(lifer);
  expect(setCoach).toHaveBeenCalledWith(expect.objectContaining({ coach_backstory: 'Former Player' }));
});
