import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CeilingGrade } from './CeilingGrade';

describe('CeilingGrade (audit #26 de-collision, #28 null + no-leak)', () => {
  it('renders the distinct arc vocabulary, not potential/pipeline words', () => {
    render(<CeilingGrade grade="HIGH_CEILING" />);
    const pill = screen.getByTestId('ceiling-grade');
    expect(pill).toHaveTextContent('High-ceiling arc');
    expect(pill.textContent).not.toMatch(/Elite|Platinum|Gold|Tier/i);
  });

  it('returns null for an unknown grade', () => {
    // @ts-expect-error intentionally invalid token
    const { container } = render(<CeilingGrade grade="MYSTERY" />);
    expect(container.firstChild).toBeNull();
  });

  it('the visible label never contains a raw ceiling number', () => {
    render(<CeilingGrade grade="SOLID" />);
    expect(screen.getByTestId('ceiling-grade').textContent).not.toMatch(/\d/);
  });
});
