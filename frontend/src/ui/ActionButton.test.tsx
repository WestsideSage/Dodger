import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ActionButton } from './ActionButton';

describe('ActionButton shim', () => {
  it('defaults type to button and forwards onClick', async () => {
    const onClick = vi.fn();
    render(<ActionButton onClick={onClick}>Go</ActionButton>);
    const btn = screen.getByRole('button', { name: 'Go' });
    expect(btn).toHaveAttribute('type', 'button');
    await userEvent.click(btn);
    expect(onClick).toHaveBeenCalledTimes(1);
  });
  it('honors disabled and an explicit submit type', () => {
    render(<ActionButton type="submit" disabled>Save</ActionButton>);
    const btn = screen.getByRole('button', { name: 'Save' });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute('type', 'submit');
  });
});
