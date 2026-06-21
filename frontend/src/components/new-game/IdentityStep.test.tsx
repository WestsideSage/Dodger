import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { IdentityStep } from './IdentityStep';

type Identity = { save_name: string; club_name: string; city: string; colors: string };
const base: Identity = { save_name: '', club_name: '', city: '', colors: '#22d3ee,#0f172a' };

function setup(identity: Partial<Identity>, takenNames: string[] = []) {
  const setIdentity = vi.fn();
  const onNext = vi.fn();
  const onBack = vi.fn();
  render(
    <IdentityStep
      identity={{ ...base, ...identity }}
      setIdentity={setIdentity}
      onNext={onNext}
      onBack={onBack}
      takenNames={takenNames}
    />,
  );
  return { setIdentity, onNext, onBack };
}

describe('IdentityStep (audit #76 — save-name uniqueness up front)', () => {
  it('shows the collision banner (role=alert, data-testid) for a case-insensitive taken name', () => {
    setup({ save_name: 'My Career', club_name: 'Hawks', city: 'Northwood' }, ['my career']);
    const banner = screen.getByTestId('save-name-collision-banner');
    expect(banner).toHaveAttribute('role', 'alert');
    expect(banner).toHaveTextContent(/already exists/i);
  });
  it('disables Next while the name collides and marks the input invalid', () => {
    setup({ save_name: 'Dup', club_name: 'Hawks', city: 'Northwood' }, ['dup']);
    expect(screen.getByRole('button', { name: /Next: Coach Profile/i })).toBeDisabled();
    expect(screen.getByLabelText(/Save Name/i)).toHaveAttribute('aria-invalid', 'true');
  });
  it('enables Next and renders no banner when all fields are filled and the name is free', () => {
    setup({ save_name: 'Fresh', club_name: 'Hawks', city: 'Northwood' }, ['other']);
    expect(screen.queryByTestId('save-name-collision-banner')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Next: Coach Profile/i })).toBeEnabled();
  });
  it('keeps color presets as aria-pressed toggles that emit a colors value', async () => {
    const { setIdentity } = setup({ club_name: 'Hawks', city: 'Northwood' });
    const fire = screen.getByRole('button', { name: 'Fire' });
    expect(fire).toHaveAttribute('aria-pressed', 'false');
    await userEvent.click(fire);
    expect(setIdentity).toHaveBeenCalledWith(expect.objectContaining({ colors: expect.stringContaining(',') }));
  });
});
