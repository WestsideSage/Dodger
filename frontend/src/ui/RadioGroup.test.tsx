import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { RadioGroup } from './RadioGroup';

const OPTS = [
  { value: 'a', label: 'Alpha', 'data-testid': 'opt-a' },
  { value: 'b', label: 'Bravo', 'data-testid': 'opt-b' },
] as const;

function renderRow({ option, selected, radioProps }: {
  option: { value: string; label: string; 'data-testid'?: string };
  selected: boolean;
  radioProps: Record<string, unknown>;
}) {
  return <div {...radioProps} aria-label={option.label}>{option.label}{selected ? ' ✓' : ''}</div>;
}

describe('RadioGroup shim', () => {
  it('exposes radiogroup + radio roles with aria-checked and roving tabindex', () => {
    render(
      <RadioGroup value="a" onChange={() => {}} options={OPTS} label="Pick" renderOption={renderRow} />,
    );
    expect(screen.getByRole('radiogroup', { name: 'Pick' })).toBeInTheDocument();
    const radios = screen.getAllByRole('radio');
    expect(radios[0]).toHaveAttribute('aria-checked', 'true');
    expect(radios[0]).toHaveAttribute('tabindex', '0');
    expect(radios[1]).toHaveAttribute('tabindex', '-1');
  });
  it('arrow keys move selection (wrapping) and Click selects', async () => {
    const onChange = vi.fn();
    render(
      <RadioGroup value="a" onChange={onChange} options={OPTS} label="Pick" renderOption={renderRow} />,
    );
    const radios = screen.getAllByRole('radio');
    radios[0].focus();
    await userEvent.keyboard('{ArrowDown}');
    expect(onChange).toHaveBeenCalledWith('b');
    await userEvent.click(screen.getByTestId('opt-b'));
    expect(onChange).toHaveBeenLastCalledWith('b');
  });
});
