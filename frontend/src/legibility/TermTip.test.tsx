import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { TermTip } from './TermTip';

// 'archetype.sharpshooter' is kind:'mechanical' in terms.ts (verified).
// 'program.archetype.contender' is kind:'flavor' in terms.ts (verified).
describe('TermTip (audit #19 badge mapping + tooltip contract)', () => {
  it('renders the AFFECTS PLAY badge for a mechanical term on focus', async () => {
    render(<TermTip term="archetype.sharpshooter">Sharpshooter</TermTip>);
    await userEvent.tab(); // focuses the trigger button
    const tip = screen.getByRole('tooltip');
    expect(tip).toHaveTextContent('AFFECTS PLAY');
    expect(tip).not.toHaveTextContent('FLAVOR');
  });

  it('renders the FLAVOR badge for a flavor term (mapping kept verbatim)', async () => {
    render(<TermTip term="program.archetype.contender">Contender</TermTip>);
    await userEvent.tab();
    const tip = screen.getByRole('tooltip');
    expect(tip).toHaveTextContent('FLAVOR');
    expect(tip).not.toHaveTextContent('AFFECTS PLAY');
  });

  it('closes on Escape (tooltip, not a trapped dialog)', async () => {
    render(<TermTip term="archetype.sharpshooter">Sharpshooter</TermTip>);
    await userEvent.tab();
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
    await userEvent.keyboard('{Escape}');
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('does not render a dialog role (no focus-trap)', async () => {
    render(<TermTip term="archetype.sharpshooter">Sharpshooter</TermTip>);
    await userEvent.tab();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
