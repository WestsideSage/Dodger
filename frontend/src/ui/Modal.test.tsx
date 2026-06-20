import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { Modal } from './Modal';

describe('Modal', () => {
  it('renders a labelled dialog and forwards data-testid (anti-strip)', () => {
    render(<Modal onClose={() => {}} label="Settings" data-testid="m"><button>ok</button></Modal>);
    const dlg = screen.getByRole('dialog');
    expect(dlg).toHaveAttribute('aria-label', 'Settings');
    expect(screen.getByTestId('m')).toBeInTheDocument();
  });
  it('closes on Escape', async () => {
    const onClose = vi.fn();
    render(<Modal onClose={onClose} label="x"><button>ok</button></Modal>);
    await userEvent.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalled();
  });
});
