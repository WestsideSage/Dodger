import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { KnownValue } from './KnownValue';

describe('KnownValue three-state (audit #21)', () => {
  it('known: shows the value and labels state "known"', () => {
    render(<KnownValue state="known" label="OVR" value={73} />);
    expect(screen.getByRole('group', { name: /OVR: known/ })).toHaveTextContent('73');
  });

  it('estimated: visually distinct (estimated class) and shows the hint', () => {
    render(<KnownValue state="estimated" label="OVR" value="60-70" hint="~" />);
    const g = screen.getByRole('group', { name: /OVR: estimated/ });
    expect(g.className).toMatch(/estimated/);
    expect(g).toHaveTextContent('~');
  });

  it('hidden: scout-to-reveal copy + lock glyph, distinct class from known/estimated', () => {
    render(<KnownValue state="hidden" label="OVR" />);
    const g = screen.getByRole('group', { name: /OVR: unknown, scout to reveal/ });
    expect(g.className).toMatch(/hidden/);
    expect(g).toHaveTextContent('🔒');
  });
});
